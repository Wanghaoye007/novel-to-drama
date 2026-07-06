import fs from "fs/promises";
import path from "path";
import { spawn } from "child_process";
import { v4 as uuid } from "uuid";
import { and, desc, eq, ne } from "drizzle-orm";
import { db, schema } from "@/db/client";
import { ensureProjectDir, ensureSystemDir, projectDir } from "./storage";
import { writeEpisodeTxt } from "./m6-export";
import { assertTenantJobQuota } from "./platform-context";
import {
  latestRoundForProject,
  projectNeedsNextRound,
  projectRunAllSettings,
} from "./project-controls";
import {
  createJob,
  failJob,
  classifyJobFailureText,
  listJobViews,
  parseJobPayload,
  succeedJob,
  updateJob,
  type JobRow,
} from "./jobs";
import {
  type DeliveryPreflightReport,
  type EngineEpisode,
  type EngineRoundResult,
  type EngineRuntimeReport,
  type QualitySampleEvaluationPayload,
  qualityAverage,
  qualityToEpisodeStatus,
  renderEngineEpisode,
  renderInternalPlanningMarkdown,
  renderStoryBibleMarkdown,
} from "./engine-types";

type ProjectRow = typeof schema.projects.$inferSelect;

type RoundGenerationPayload = {
  projectId: string;
  roundId: string;
  roundNumber: number;
  generationVariant?: string;
  repairBudget?: string;
  episodesPerRound?: number;
};

type QualitySamplesPayload = {
  rounds: number;
  variants?: string[];
};

type QualitySampleManifest = {
  samples?: Array<{
    sample_id?: string;
    label?: string;
  }>;
};

type QualitySampleProgressTarget = {
  sampleId: string;
  label: string;
  variant: string;
  roundNumber: number;
  runtimeReportPath: string;
  roundResultPath: string;
};

type RoundGenerationOptions = {
  generationVariant?: string | null;
  repairBudget?: string | null;
  episodesPerRound?: number | string | null;
};

type EpisodeSyncTarget = {
  project: ProjectRow;
  roundId: string;
  roundNumber: number;
  status?: "pending" | "running" | "green" | "red" | "failed";
  reviewJson?: string | null;
};

const generationVariants = new Set([
  "current_density",
  "drama_engine_first",
  "sop_full_stack",
]);
const repairBudgets = new Set(["none", "rewrite", "episode"]);
const MAX_EPISODES_PER_ROUND = 5;

function pythonPathEnv(): NodeJS.ProcessEnv {
  const sourcePath = path.join(/*turbopackIgnore: true*/ process.cwd(), "src");
  const existing = process.env.PYTHONPATH;
  return {
    ...process.env,
    PYTHONPATH: existing ? `${sourcePath}${path.delimiter}${existing}` : sourcePath,
    NOVEL_DRAMA_SCRIPT_EPISODE_FIRST:
      process.env.NOVEL_DRAMA_SCRIPT_EPISODE_FIRST ?? "0",
  };
}

function novelDramaCommand(args: string[]): { command: string; args: string[] } {
  const cli = process.env.NOVEL_DRAMA_CLI;
  if (cli) return { command: cli, args };

  const python = process.env.NOVEL_DRAMA_PYTHON ?? process.env.PYTHON ?? "python3";
  return {
    command: python,
    args: ["-m", "novel_drama_engine.cli", ...args],
  };
}

function shouldUseMockEngine(): boolean {
  if (process.env.NOVEL_DRAMA_WEB_MOCK === "1") return true;
  if (process.env.NOVEL_DRAMA_WEB_MOCK === "0") return false;
  return !process.env.OPENAI_API_KEY;
}

function realEngineConfigProblem(): string | null {
  if (shouldUseMockEngine()) return null;
  if (!process.env.OPENAI_API_KEY) {
    return "OPENAI_API_KEY is not set while NOVEL_DRAMA_WEB_MOCK=0";
  }
  if (!process.env.OPENAI_MODEL) {
    return "OPENAI_MODEL is not set while real Engine mode is enabled";
  }
  return null;
}

function redactedProviderConfig(): Record<string, unknown> {
  let baseUrlHost: string | null = null;
  if (process.env.OPENAI_BASE_URL) {
    try {
      baseUrlHost = new URL(process.env.OPENAI_BASE_URL).host;
    } catch {
      baseUrlHost = "invalid-url";
    }
  }
  return {
    mode: shouldUseMockEngine() ? "mock" : "real",
    provider: process.env.NOVEL_DRAMA_LLM_PROVIDER ?? null,
    model: process.env.OPENAI_MODEL ?? null,
    baseUrlHost,
    hasApiKey: Boolean(process.env.OPENAI_API_KEY),
  };
}

function generationVariant(value?: string | null): string {
  const candidate = value ?? process.env.NOVEL_DRAMA_GENERATION_VARIANT;
  if (candidate && generationVariants.has(candidate)) return candidate;
  return "drama_engine_first";
}

function repairBudget(value?: string | null): string {
  const candidate = value ?? process.env.NOVEL_DRAMA_REPAIR_BUDGET;
  if (candidate && repairBudgets.has(candidate)) return candidate;
  return "episode";
}

function episodesPerRound(value?: number | string | null): number {
  const raw = value ?? process.env.NOVEL_DRAMA_EPISODES_PER_ROUND ?? MAX_EPISODES_PER_ROUND;
  const parsed = typeof raw === "number" ? raw : Number.parseInt(String(raw), 10);
  if (!Number.isFinite(parsed)) return MAX_EPISODES_PER_ROUND;
  return Math.min(MAX_EPISODES_PER_ROUND, Math.max(1, Math.floor(parsed)));
}

function qualitySampleRepairBudget(): string {
  const candidate = process.env.NOVEL_DRAMA_QUALITY_REPAIR_BUDGET;
  if (candidate && repairBudgets.has(candidate)) return candidate;
  return "rewrite";
}

function normalizeGenerationVariants(values?: string[] | null): string[] {
  const candidates = values?.length ? values : [generationVariant()];
  const normalized = candidates.filter((value) => generationVariants.has(value));
  return Array.from(new Set(normalized.length ? normalized : [generationVariant()]));
}

function engineTimeoutMs(): number {
  const value = Number(process.env.NOVEL_DRAMA_ENGINE_TIMEOUT_MS ?? "1800000");
  return Number.isFinite(value) ? Math.max(0, Math.floor(value)) : 1800000;
}

function qualitySampleTimeoutMs(): number {
  const value = Number(
    process.env.NOVEL_DRAMA_QUALITY_TIMEOUT_MS ??
      process.env.NOVEL_DRAMA_ENGINE_TIMEOUT_MS ??
      "3600000"
  );
  return Number.isFinite(value) ? Math.max(0, Math.floor(value)) : 3600000;
}

async function runNovelDrama(
  args: string[],
  options: { timeoutMs?: number } = {}
): Promise<string> {
  const { command, args: commandArgs } = novelDramaCommand(args);
  return new Promise((resolve, reject) => {
    const timeoutMs = options.timeoutMs ?? engineTimeoutMs();
    let timedOut = false;
    let timeout: NodeJS.Timeout | null = null;
    let forceKill: NodeJS.Timeout | null = null;
    const child = spawn(command, commandArgs, {
      cwd: /*turbopackIgnore: true*/ process.cwd(),
      env: pythonPathEnv(),
    });
    let stdout = "";
    let stderr = "";
    if (timeoutMs > 0) {
      timeout = setTimeout(() => {
        timedOut = true;
        child.kill("SIGTERM");
        forceKill = setTimeout(() => child.kill("SIGKILL"), 5000);
      }, timeoutMs);
    }
    child.stdout.on("data", (chunk) => {
      stdout += chunk.toString();
    });
    child.stderr.on("data", (chunk) => {
      stderr += chunk.toString();
    });
    child.on("error", reject);
    child.on("close", (code) => {
      if (timeout) clearTimeout(timeout);
      if (forceKill) clearTimeout(forceKill);
      if (timedOut) {
        reject(
          new Error(
            [
              `novel-drama timed out after ${timeoutMs}ms`,
              stdout.trim(),
              stderr.trim(),
            ]
              .filter(Boolean)
              .join("\n")
          )
        );
        return;
      }
      if (code === 0) {
        resolve(stdout);
        return;
      }
      reject(
        new Error(
          [
            `novel-drama exited with code ${code}`,
            stdout.trim(),
            stderr.trim(),
          ]
            .filter(Boolean)
            .join("\n")
        )
      );
    });
  });
}

export function engineProjectDir(projectId: string): string {
  return path.join(/*turbopackIgnore: true*/ projectDir(projectId), "engine");
}

function roundDirName(roundNumber: number): string {
  return `round_${String(roundNumber).padStart(3, "0")}`;
}

async function writeActiveMethodologyCardsForEngine(
  tenantId: string | null,
  engineDir: string
): Promise<{ path: string | null; activeCount: number; totalCount: number }> {
  if (!tenantId) return { path: null, activeCount: 0, totalCount: 0 };

  const tenantCards = await db.query.methodologyCards.findMany({
    where: eq(schema.methodologyCards.tenantId, tenantId),
    orderBy: [desc(schema.methodologyCards.updatedAt)],
  });
  if (tenantCards.length === 0) {
    return { path: null, activeCount: 0, totalCount: 0 };
  }

  const activeCards = tenantCards
    .filter((card) => card.status === "active")
    .map((card) => ({
      id: card.id,
      source_id: card.sourceId,
      name: card.name,
      category: card.category,
      applies_to_channel: JSON.parse(card.appliesToChannelJson) as string[],
      applies_to_genre: JSON.parse(card.appliesToGenreJson) as string[],
      applies_to_stage: JSON.parse(card.appliesToStageJson) as string[],
      trigger: card.trigger,
      generation_rule: card.generationRule,
      quality_rule: card.qualityRule,
      positive_examples: card.positiveExamplesJson
        ? (JSON.parse(card.positiveExamplesJson) as string[])
        : [],
      negative_examples: card.negativeExamplesJson
        ? (JSON.parse(card.negativeExamplesJson) as string[])
        : [],
      status: card.status,
      version: card.version,
    }));
  const cardsPath = path.join(
    /*turbopackIgnore: true*/
    engineDir,
    "active_methodology_cards.json"
  );
  await fs.writeFile(cardsPath, JSON.stringify(activeCards, null, 2), "utf-8");
  return {
    path: cardsPath,
    activeCount: activeCards.length,
    totalCount: tenantCards.length,
  };
}

const engineStageProgress: Record<string, { progress: number; label: string }> = {
  source_analysis: { progress: 42, label: "源文结构解析" },
  viral_asset_report: { progress: 45, label: "爆款资产提炼" },
  episode_context: { progress: 48, label: "自动识别对应集数和上下文" },
  normalize_episode_context: { progress: 50, label: "校准集数范围" },
  story_bible: { progress: 55, label: "系统 Story Bible" },
  series_structure_plan: { progress: 60, label: "全剧结构规划" },
  normalize_series_structure_plan: { progress: 62, label: "校准全剧结构" },
  episode_plan: { progress: 66, label: "分集爆点规划" },
  normalize_episode_plan: { progress: 68, label: "校准分集规划" },
  episode_source_packets: { progress: 70, label: "生成逐集原文包" },
  script_batch: { progress: 72, label: "生成可拍摄脚本" },
  quality_report: { progress: 76, label: "质量门禁自检" },
  script_batch_rewrite: { progress: 78, label: "整轮脚本改写" },
  quality_report_after_rewrite: { progress: 80, label: "改写后复检" },
  episode_repair: { progress: 81, label: "逐集定向修复" },
  apply_episode_repair: { progress: 82, label: "合并逐集修复" },
  episode_quality_polish: { progress: 83, label: "镜头和台词精修" },
  apply_episode_quality_polish: { progress: 84, label: "合并精修版本" },
  hook_dialogue_polish: { progress: 84, label: "开场对白强化" },
  apply_hook_dialogue_polish: { progress: 84, label: "合并开场强化" },
  quality_report_after_episode_repair: { progress: 84, label: "修复后复检" },
  mark_human_review_after_episode_repair: { progress: 84, label: "标记人工复核" },
  mark_human_review_after_rewrite_budget: { progress: 84, label: "标记人工复核" },
  mark_human_review_without_repair: { progress: 84, label: "标记人工复核" },
  next_round_context: { progress: 84, label: "写入下一轮上下文" },
};

async function readRuntimeReport(
  runtimeReportPath: string
): Promise<EngineRuntimeReport | null> {
  try {
    const raw = await fs.readFile(runtimeReportPath, "utf-8");
    return JSON.parse(raw) as EngineRuntimeReport;
  } catch (error) {
    const code = (error as NodeJS.ErrnoException).code;
    if (code === "ENOENT") return null;
    if (error instanceof SyntaxError) return null;
    throw error;
  }
}

function runtimeStageUpdate(report: EngineRuntimeReport): {
  progress: number;
  label: string;
  status: string;
} | null {
  const call = report.llm_calls.at(-1);
  if (call?.status === "running") {
    const mapped = engineStageProgress[call.stage];
    if (mapped) {
      return {
        progress: mapped.progress,
        label: `${mapped.label} · ${call.response_model} 请求中 ${formatShortDuration(
          call.duration_ms
        )}`,
        status: "running",
      };
    }
  }
  const stage = report.stages.at(-1);
  if (!stage) return null;
  const mapped = engineStageProgress[stage.name];
  if (!mapped) return null;
  return { progress: mapped.progress, label: mapped.label, status: stage.status };
}

function runtimeReportProgress(
  report: EngineRuntimeReport
): { progress: number; message: string } | null {
  const update = runtimeStageUpdate(report);
  if (!update) return null;
  const suffix =
    update.status === "running" ? "" : update.status === "failed" ? "失败" : "完成";
  return {
    progress: update.progress,
    message: `Engine：${update.label}${suffix}`,
  };
}

function runtimeStageFraction(report: EngineRuntimeReport): number {
  const update = runtimeStageUpdate(report);
  if (!update) return 0;
  return Math.max(0, Math.min(1, (update.progress - 35) / (84 - 35)));
}

function safeSampleDirName(sampleId: string): string {
  return sampleId
    .split("")
    .map((character) =>
      /[a-zA-Z0-9_-]/.test(character) ? character : "_"
    )
    .join("");
}

function formatShortDuration(ms: number): string {
  if (!Number.isFinite(ms) || ms <= 0) return "0s";
  const seconds = Math.round(ms / 1000);
  if (seconds < 60) return `${seconds}s`;
  return `${Math.floor(seconds / 60)}m${String(seconds % 60).padStart(2, "0")}s`;
}

async function qualitySampleTargets(
  manifestPath: string,
  projectsDir: string,
  rounds: number,
  variants: string[] = [generationVariant()]
): Promise<QualitySampleProgressTarget[]> {
  const raw = await fs.readFile(manifestPath, "utf-8");
  const manifest = JSON.parse(raw) as QualitySampleManifest;
  const samples = manifest.samples ?? [];
  return samples.flatMap((sample) => variants.flatMap((variant) => {
    const sampleId = sample.sample_id ?? "sample";
    const safeSampleId = safeSampleDirName(sampleId);
    const sampleDir = path.join(
      /*turbopackIgnore: true*/
      projectsDir,
      safeSampleId,
      variants.length > 1 ? variant : ""
    );
    return Array.from({ length: rounds }, (_, index) => {
      const roundNumber = index + 1;
      const roundDir = path.join(
        /*turbopackIgnore: true*/
        sampleDir,
        roundDirName(roundNumber)
      );
      return {
        sampleId,
        label: sample.label ?? sampleId,
        variant,
        roundNumber,
        runtimeReportPath: path.join(roundDir, "runtime_report.json"),
        roundResultPath: path.join(roundDir, "round_result.json"),
      };
    });
  }));
}

async function isFreshFile(filePath: string, freshAfter: Date): Promise<boolean> {
  try {
    const stat = await fs.stat(filePath);
    return stat.mtime >= freshAfter;
  } catch (error) {
    const code = (error as NodeJS.ErrnoException).code;
    if (code === "ENOENT") return false;
    throw error;
  }
}

async function clearQualitySampleArtifacts(
  targets: QualitySampleProgressTarget[],
  reportPath: string
): Promise<void> {
  await Promise.all([
    fs.rm(reportPath, { force: true }),
    ...targets.map((target) =>
      fs.rm(path.dirname(target.runtimeReportPath), {
        recursive: true,
        force: true,
      })
    ),
  ]);
}

function createQualitySampleProgressSync({
  jobId,
  targets,
  freshAfter,
}: {
  jobId: string;
  targets: QualitySampleProgressTarget[];
  freshAfter: Date;
}): { tick: () => Promise<void>; stop: () => void } {
  let stopped = false;
  let syncing = false;
  let lastProgress = 25;
  let lastMessage = "";

  const tick = async () => {
    if (stopped || syncing || targets.length === 0) return;
    syncing = true;
    try {
      let completed = 0;
      let message = "";
      let progress = lastProgress;

      for (const target of targets) {
        if (await isFreshFile(target.roundResultPath, freshAfter)) {
          completed += 1;
          continue;
        }

        const runtimeReportIsFresh = await isFreshFile(
          target.runtimeReportPath,
          freshAfter
        );
        if (!runtimeReportIsFresh) break;

        const report = await readRuntimeReport(target.runtimeReportPath);
        const stageUpdate = report ? runtimeStageUpdate(report) : null;
        if (!report || !stageUpdate) break;

        const fraction = runtimeStageFraction(report);
        const suffix =
          stageUpdate.status === "running"
            ? ""
            : stageUpdate.status === "failed"
              ? "失败"
              : "完成";
        progress = Math.min(
          92,
          25 + ((completed + fraction) / targets.length) * 67
        );
        message = `内部回归：${target.label} · ${target.variant} R${target.roundNumber} · ${stageUpdate.label}${suffix}`;

        if (stageUpdate.status === "failed") {
          completed += 1;
          continue;
        }
        break;
      }

      if (!message && completed > 0) {
        progress = Math.min(92, 25 + (completed / targets.length) * 67);
        message = `内部回归：已完成 ${completed}/${targets.length} 轮`;
      }
      if (!message) return;

      const roundedProgress = Math.max(lastProgress, Math.round(progress));
      if (roundedProgress === lastProgress && message === lastMessage) return;
      lastProgress = roundedProgress;
      lastMessage = message;
      await updateJob(jobId, { progress: roundedProgress, message });
    } finally {
      syncing = false;
    }
  };

  const timer = setInterval(() => {
    void tick();
  }, 5000);

  return {
    tick,
    stop: () => {
      stopped = true;
      clearInterval(timer);
    },
  };
}

function createEngineProgressSync(
  jobId: string | undefined,
  runtimeReportPath: string,
  episodeSyncTarget?: EpisodeSyncTarget
): { tick: () => Promise<void>; stop: () => void } {
  let stopped = false;
  let syncing = false;
  let lastProgress = 35;
  let lastMessage = "";

  const tick = async () => {
    if (!jobId || stopped || syncing) return;
    syncing = true;
    try {
      const syncedEpisodes = episodeSyncTarget
        ? await syncIncrementalRoundEpisodes(episodeSyncTarget)
        : 0;
      const report = await readRuntimeReport(runtimeReportPath);
      if (!report) {
        if (syncedEpisodes > 0) {
          await updateJob(jobId, {
            progress: lastProgress,
            message: `已生成 ${syncedEpisodes} 集，正在同步到页面`,
          });
        }
        return;
      }
      const update = runtimeReportProgress(report);
      if (!update) {
        if (syncedEpisodes > 0) {
          await updateJob(jobId, {
            progress: lastProgress,
            message: `已同步 ${syncedEpisodes} 集到页面`,
          });
        }
        return;
      }
      const progress = Math.max(lastProgress, update.progress);
      if (progress === lastProgress && update.message === lastMessage) return;
      lastProgress = progress;
      lastMessage = update.message;
      await updateJob(jobId, { progress, message: update.message });
    } finally {
      syncing = false;
    }
  };

  const timer = jobId
    ? setInterval(() => {
        void tick();
      }, 3000)
    : null;

  return {
    tick,
    stop: () => {
      stopped = true;
      if (timer) clearInterval(timer);
    },
  };
}

function qualitySampleReportName(): string {
  return "quality_sample_report.json";
}

function qualitySamplesPath(): string {
  return path.join(
    /*turbopackIgnore: true*/ process.cwd(),
    "examples",
    "quality_samples.json"
  );
}

async function qualityEvaluationDir(tenantId?: string): Promise<string> {
  const root =
    process.env.NOVEL_DRAMA_QUALITY_DIR ?? (await ensureSystemDir("quality_samples"));
  if (!tenantId) return root;
  const dir = path.join(/*turbopackIgnore: true*/ root, "tenants", tenantId);
  await fs.mkdir(dir, { recursive: true });
  return dir;
}

async function readEngineRoundResult(
  projectId: string,
  roundNumber: number
): Promise<EngineRoundResult> {
  const raw = await fs.readFile(
    path.join(
      /*turbopackIgnore: true*/ engineProjectDir(projectId),
      roundDirName(roundNumber),
      "round_result.json"
    ),
    "utf-8"
  );
  return JSON.parse(raw) as EngineRoundResult;
}

function storyBibleChannel(bibleGenre: string): "male" | "female" | null {
  if (/男频|逆袭|赘婿|修仙|战神/.test(bibleGenre)) return "male";
  if (/女频|豪门|千金|追妻|重生/.test(bibleGenre)) return "female";
  return null;
}

function renderRoundEpisodeSummary(episode: EngineEpisode): string {
  return JSON.stringify(
    {
      episode: episode.episode,
      title: episode.title,
      hook_3s: episode.hook_3s,
      cliffhanger: episode.cliffhanger,
      state_update: episode.state_update,
    },
    null,
    2
  );
}

async function upsertEpisodeRow({
  project,
  roundId,
  episode,
  status,
  score,
  reviewJson,
}: {
  project: ProjectRow;
  roundId: string;
  episode: EngineEpisode;
  status: "pending" | "running" | "green" | "red" | "failed";
  score: number | null;
  reviewJson: string | null;
}): Promise<boolean> {
  const now = new Date();
  const scriptTxt = renderEngineEpisode(episode);
  const values = {
    draftMd: renderRoundEpisodeSummary(episode),
    scriptTxt,
    score,
    reviewJson,
    epSummaryJson: JSON.stringify(episode.state_update, null, 2),
    status,
    updatedAt: now,
  };
  const existing = await db.query.episodes.findFirst({
    where: and(
      eq(schema.episodes.projectId, project.id),
      eq(schema.episodes.roundId, roundId),
      eq(schema.episodes.epNum, episode.episode)
    ),
  });

  if (existing) {
    const changed =
      existing.scriptTxt !== scriptTxt ||
      existing.status !== status ||
      existing.score !== score ||
      existing.reviewJson !== reviewJson;
    await db
      .update(schema.episodes)
      .set(values)
      .where(eq(schema.episodes.id, existing.id));
    if (changed) {
      await writeEpisodeTxt(project.id, episode.episode, scriptTxt);
    }
    return changed;
  }

  const crossRoundExisting = await db.query.episodes.findFirst({
    where: and(
      eq(schema.episodes.projectId, project.id),
      eq(schema.episodes.epNum, episode.episode),
      ne(schema.episodes.roundId, roundId)
    ),
  });
  if (crossRoundExisting) {
    throw new Error(
      `episode E${String(episode.episode).padStart(
        2,
        "0"
      )} already exists in another round; refusing to overwrite existing output`
    );
  }

  await db.insert(schema.episodes).values({
    id: uuid(),
    projectId: project.id,
    roundId,
    epNum: episode.episode,
    retryCount: 0,
    ...values,
  });
  await writeEpisodeTxt(project.id, episode.episode, scriptTxt);
  return true;
}

async function syncIncrementalRoundEpisodes({
  project,
  roundId,
  roundNumber,
  status = "running",
  reviewJson = null,
}: EpisodeSyncTarget): Promise<number> {
  const roundDir = path.join(
    /*turbopackIgnore: true*/
    engineProjectDir(project.id),
    roundDirName(roundNumber)
  );
  let files: string[];
  try {
    files = await fs.readdir(roundDir);
  } catch (error) {
    const code = (error as NodeJS.ErrnoException).code;
    if (code === "ENOENT") return 0;
    throw error;
  }

  let changed = 0;
  for (const file of files.sort()) {
    if (!/^episode_\d{3}\.json$/.test(file)) continue;
    try {
      const raw = await fs.readFile(path.join(roundDir, file), "utf-8");
      const episode = JSON.parse(raw) as EngineEpisode;
      if (!Number.isFinite(episode.episode) || !episode.scenes) continue;
      const didChange = await upsertEpisodeRow({
        project,
        roundId,
        episode,
        status,
        score: null,
        reviewJson,
      });
      if (didChange) changed += 1;
    } catch (error) {
      if (error instanceof SyntaxError) continue;
      throw error;
    }
  }
  return changed;
}

async function syncBible(projectId: string, result: EngineRoundResult): Promise<void> {
  const existing = await db.query.bibles.findFirst({
    where: eq(schema.bibles.projectId, projectId),
  });
  const values = {
    channel: storyBibleChannel(result.story_bible.genre),
    sixAssetsJson: JSON.stringify(result.story_bible, null, 2),
    charactersMd: renderStoryBibleMarkdown(result.story_bible),
    episodePlanMd: renderInternalPlanningMarkdown(result),
    prevRoundSummaryJson: JSON.stringify(result.next_round_context, null, 2),
    updatedAt: new Date(),
  };

  if (existing) {
    await db
      .update(schema.bibles)
      .set(values)
      .where(eq(schema.bibles.projectId, projectId));
    return;
  }

  await db.insert(schema.bibles).values({
    id: uuid(),
    projectId,
    ...values,
  });
}

async function syncMethodologyRun(
  project: ProjectRow,
  roundId: string,
  result: EngineRoundResult
): Promise<void> {
  if (
    !result.source_strength_profile &&
    !result.methodology_context &&
    !result.methodology_quality_report
  ) {
    return;
  }

  await db
    .delete(schema.methodologyRuns)
    .where(eq(schema.methodologyRuns.roundId, roundId));

  await db.insert(schema.methodologyRuns).values({
    id: uuid(),
    tenantId: project.tenantId,
    projectId: project.id,
    roundId,
    sourceStrengthJson: result.source_strength_profile
      ? JSON.stringify(result.source_strength_profile, null, 2)
      : null,
    methodologyContextJson: result.methodology_context
      ? JSON.stringify(result.methodology_context, null, 2)
      : null,
    methodologyQualityJson: result.methodology_quality_report
      ? JSON.stringify(result.methodology_quality_report, null, 2)
      : null,
    createdAt: new Date(),
  });
}

async function syncEngineRoundToDb(
  project: ProjectRow,
  roundId: string,
  result: EngineRoundResult
): Promise<void> {
  await syncBible(project.id, result);
  await syncMethodologyRun(project, roundId, result);

  const status = qualityToEpisodeStatus(result.quality_report.status);
  const score = qualityAverage(result.quality_report);
  const finalEpisodeNumbers = new Set(
    result.script_batch.episodes.map((episode) => episode.episode)
  );
  const existingRows = await db.query.episodes.findMany({
    where: eq(schema.episodes.roundId, roundId),
  });
  await Promise.all(
    existingRows
      .filter((episode) => !finalEpisodeNumbers.has(episode.epNum))
      .map((episode) =>
        db.delete(schema.episodes).where(eq(schema.episodes.id, episode.id))
      )
  );

  for (const episode of result.script_batch.episodes) {
    await upsertEpisodeRow({
      project,
      roundId,
      episode,
      status,
      score,
      reviewJson: JSON.stringify(result.quality_report, null, 2),
    });
  }

  await db
    .update(schema.rounds)
    .set({
      epRange: result.episode_context.target_episode_range,
      summaryJson: JSON.stringify(result, null, 2),
      status: "done",
    })
    .where(eq(schema.rounds.id, roundId));

  const latestProject = await db.query.projects.findFirst({
    where: eq(schema.projects.id, project.id),
  });
  const targetReached =
    result.next_round_context.current_episode >= project.targetEpisodeCount;
  const projectStatus = targetReached
    ? "done"
    : latestProject?.status === "paused"
      ? "paused"
      : "running";
  await db
    .update(schema.projects)
    .set({ status: projectStatus, updatedAt: new Date() })
    .where(eq(schema.projects.id, project.id));
}

async function executeEngineRound(
  project: ProjectRow,
  roundNumber: number,
  roundId: string,
  jobId?: string,
  options: RoundGenerationOptions = {}
): Promise<void> {
  try {
    const selectedGenerationVariant = generationVariant(options.generationVariant);
    const selectedRepairBudget = repairBudget(options.repairBudget);
    const selectedEpisodesPerRound = episodesPerRound(options.episodesPerRound);
    const configProblem = realEngineConfigProblem();
    if (configProblem) throw new Error(configProblem);
    await updateJob(jobId, {
      message: `准备小说原文和 Engine 工作目录 · ${selectedGenerationVariant}/${selectedRepairBudget}/${selectedEpisodesPerRound}集`,
      progress: 15,
    });
    const storageDir = await ensureProjectDir(project.id);
    const engineDir = path.join(/*turbopackIgnore: true*/ storageDir, "engine");
    await fs.mkdir(engineDir, { recursive: true });
    const methodologyCards = await writeActiveMethodologyCardsForEngine(
      project.tenantId,
      engineDir
    );
    const runtimeReportPath = path.join(
      /*turbopackIgnore: true*/
      engineDir,
      roundDirName(roundNumber),
      "runtime_report.json"
    );
    await fs.rm(runtimeReportPath, { force: true });
    const sourcePath = path.join(
      /*turbopackIgnore: true*/
      engineDir,
      `source_round_${String(roundNumber).padStart(3, "0")}.txt`
    );
    await fs.writeFile(sourcePath, project.novelText, "utf-8");

    const args = [
      "run",
      "--input",
      sourcePath,
      "--project-dir",
      engineDir,
      "--project-id",
      project.id,
      "--round-number",
      String(roundNumber),
      "--target-episode-count",
      String(project.targetEpisodeCount),
      "--episodes-per-round",
      String(selectedEpisodesPerRound),
      "--generation-variant",
      selectedGenerationVariant,
      "--repair-budget",
      selectedRepairBudget,
    ];
    if (methodologyCards.path) {
      args.push("--methodology-cards", methodologyCards.path);
    }
    if (shouldUseMockEngine()) args.push("--mock");

    await updateJob(jobId, {
      message:
        methodologyCards.path && methodologyCards.totalCount > 0
          ? `调用 Engine 生成轮次脚本 · active 方法卡 ${methodologyCards.activeCount}/${methodologyCards.totalCount}`
          : "调用 Engine 生成轮次脚本",
      progress: 35,
    });
    const progressSync = createEngineProgressSync(jobId, runtimeReportPath, {
      project,
      roundId,
      roundNumber,
    });
    try {
      await runNovelDrama(args);
    } finally {
      await progressSync.tick();
      progressSync.stop();
    }
    await updateJob(jobId, {
      message: "同步 Engine artifacts 到 Web 数据库",
      progress: 85,
    });
    const result = await readEngineRoundResult(project.id, roundNumber);
    await syncEngineRoundToDb(project, roundId, result);
    const nextJob = await scheduleNextRoundIfRunAll(project.id);
    await succeedJob(jobId, {
      message: `第 ${roundNumber} 轮完成`,
      result: {
        projectId: project.id,
        roundId,
        roundNumber,
        targetEpisodeRange: result.episode_context.target_episode_range,
        qualityStatus: result.quality_report.status,
        generationVariant: selectedGenerationVariant,
        repairBudget: selectedRepairBudget,
        episodesPerRound: selectedEpisodesPerRound,
        runtimeMs: result.runtime_report?.total_duration_ms,
        llmCalls: result.runtime_report?.llm_calls.length,
        sourceStrength: result.source_strength_profile?.overall_level ?? null,
        adaptationIntensity:
          result.source_strength_profile?.recommended_intensity ?? null,
        methodologyCards:
          result.methodology_context?.cards?.map((card) => card.name) ?? [],
        nextJobId: nextJob?.jobId ?? null,
      },
    });
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    const failure = classifyJobFailureText(message);
    const userError = failure
      ? `${failure.userMessage}。${failure.operatorHint}`
      : message;
    let partialEpisodes = 0;
    try {
      partialEpisodes = await syncIncrementalRoundEpisodes({
        project,
        roundId,
        roundNumber,
        status: "red",
        reviewJson: JSON.stringify(
          {
            status: "failed",
            error: userError,
            failureCategory: failure?.category ?? "engine_error",
          },
          null,
          2
        ),
      });
    } catch (syncError) {
      console.error("[engine-runner] partial episode sync failed:", syncError);
    }
    const failureSummary = {
      error: userError,
      rawError: message.slice(0, 4000),
      failureCategory: failure?.category ?? "engine_error",
      operatorHint:
        failure?.operatorHint ??
        "查看错误详情后重试；若连续失败，需要检查 prompt、模型或输入文本。",
      partialEpisodes,
      provider: redactedProviderConfig(),
    };
    await db
      .update(schema.rounds)
      .set({
        status: "failed",
        summaryJson: JSON.stringify(failureSummary, null, 2),
      })
      .where(eq(schema.rounds.id, roundId));
    await db
      .update(schema.projects)
      .set({ status: "failed", updatedAt: new Date() })
      .where(eq(schema.projects.id, project.id));
    await failJob(jobId, error, {
      message: failure?.userMessage ?? "生成失败",
      errorText: userError,
      result: failureSummary,
    });
    console.error("[engine-runner] failed:", error);
  }
}

export async function executeEngineRoundJob(job: JobRow): Promise<void> {
  const payload = parseJobPayload<RoundGenerationPayload>(job);
  const project = await db.query.projects.findFirst({
    where: eq(schema.projects.id, payload.projectId),
  });
  if (!project) throw new Error("project not found");
  await executeEngineRound(project, payload.roundNumber, payload.roundId, job.id, {
    generationVariant: payload.generationVariant,
    repairBudget: payload.repairBudget,
    episodesPerRound: payload.episodesPerRound,
  });
}

export async function startEngineRound(
  projectId: string,
  roundNumber: number,
  options: RoundGenerationOptions = {}
): Promise<{ roundId: string; roundNum: number; jobId: string }> {
  const project = await db.query.projects.findFirst({
    where: eq(schema.projects.id, projectId),
  });
  if (!project) throw new Error("project not found");
  if (project.status === "paused") throw new Error("project is paused");
  if (project.tenantId) await assertTenantJobQuota(project.tenantId);

  const existing = await db.query.rounds.findFirst({
    where: and(
      eq(schema.rounds.projectId, projectId),
      eq(schema.rounds.roundNum, roundNumber)
    ),
  });

  const roundId = existing?.id ?? uuid();
  if (existing) {
    await db
      .update(schema.rounds)
      .set({ status: "running" })
      .where(eq(schema.rounds.id, roundId));
  } else {
    await db.insert(schema.rounds).values({
      id: roundId,
      projectId,
      roundNum: roundNumber,
      epRange: `Round ${roundNumber}`,
      summaryJson: null,
      status: "running",
      createdAt: new Date(),
    });
  }

  await db
    .update(schema.projects)
    .set({ status: "running", updatedAt: new Date() })
    .where(eq(schema.projects.id, projectId));

  const selectedGenerationVariant = generationVariant(options.generationVariant);
  const selectedRepairBudget = repairBudget(options.repairBudget);
  const selectedEpisodesPerRound = episodesPerRound(options.episodesPerRound);
  const job = await createJob({
    kind: "round_generation",
    title: `${project.name} · 第 ${roundNumber} 轮 · ${selectedEpisodesPerRound}集`,
    projectId,
    tenantId: project.tenantId,
    roundId,
    message: `等待 worker 执行 · ${selectedGenerationVariant}/${selectedRepairBudget}/${selectedEpisodesPerRound}集`,
    payload: {
      projectId,
      roundId,
      roundNumber,
      generationVariant: selectedGenerationVariant,
      repairBudget: selectedRepairBudget,
      episodesPerRound: selectedEpisodesPerRound,
    } satisfies RoundGenerationPayload,
  });

  return { roundId, roundNum: roundNumber, jobId: job.id };
}

export async function startNextEngineRound(
  projectId: string,
  options: RoundGenerationOptions = {}
): Promise<{ roundId: string; roundNum: number; jobId: string } | null> {
  const project = await db.query.projects.findFirst({
    where: eq(schema.projects.id, projectId),
  });
  if (!project) throw new Error("project not found");
  if (!(await projectNeedsNextRound(project))) return null;
  const latest = await latestRoundForProject(projectId);
  return startEngineRound(projectId, (latest?.roundNum ?? 0) + 1, options);
}

export async function scheduleNextRoundIfRunAll(
  projectId: string
): Promise<{ roundId: string; roundNum: number; jobId: string } | null> {
  const project = await db.query.projects.findFirst({
    where: eq(schema.projects.id, projectId),
  });
  if (!project) throw new Error("project not found");
  const settings = projectRunAllSettings(project);
  if (!settings.enabled) return null;
  return startNextEngineRound(projectId, {
    generationVariant: settings.generationVariant,
    repairBudget: settings.repairBudget,
    episodesPerRound: MAX_EPISODES_PER_ROUND,
  });
}

export async function latestRoundNumber(projectId: string): Promise<number | null> {
  const rounds = await db.query.rounds.findMany({
    where: eq(schema.rounds.projectId, projectId),
    orderBy: [desc(schema.rounds.roundNum)],
  });
  return rounds[0]?.roundNum ?? null;
}

export async function getDeliveryPreflight(
  projectId: string,
  roundNumber?: number
): Promise<DeliveryPreflightReport> {
  const args = ["check-delivery", "--project-dir", engineProjectDir(projectId), "--json"];
  if (roundNumber) args.push("--round-number", String(roundNumber));
  const stdout = await runNovelDrama(args);
  return JSON.parse(stdout) as DeliveryPreflightReport;
}

export async function exportDeliveryZip(
  projectId: string,
  roundNumber?: number,
  allowIssues = false
): Promise<string> {
  const resolvedRoundNumber = roundNumber ?? (await latestRoundNumber(projectId));
  if (!resolvedRoundNumber) throw new Error("no completed round found");
  const output = path.join(
    /*turbopackIgnore: true*/
    projectDir(projectId),
    `delivery_round_${String(resolvedRoundNumber).padStart(3, "0")}.zip`
  );
  const args = [
    "export-delivery",
    "--project-dir",
    engineProjectDir(projectId),
    "--round-number",
    String(resolvedRoundNumber),
    "--output",
    output,
  ];
  if (allowIssues) args.push("--allow-issues");
  await runNovelDrama(args);
  return output;
}

export async function exportVideoBrief(
  projectId: string,
  roundNumber?: number
): Promise<{ jsonPath: string; markdownPath: string }> {
  const args = ["export-video-brief", "--project-dir", engineProjectDir(projectId)];
  if (roundNumber) args.push("--round-number", String(roundNumber));
  await runNovelDrama(args);
  const resolvedRoundNumber = roundNumber ?? (await latestRoundNumber(projectId));
  if (!resolvedRoundNumber) throw new Error("no completed round found");
  const roundDir = path.join(
    /*turbopackIgnore: true*/
    engineProjectDir(projectId),
    roundDirName(resolvedRoundNumber)
  );
  return {
    jsonPath: path.join(roundDir, "video_brief.json"),
    markdownPath: path.join(roundDir, "video_brief.md"),
  };
}

export async function exportLocalization(
  projectId: string,
  profilePath: string,
  roundNumber?: number,
  profileId = "us_tiktok"
): Promise<{ jsonPath: string; markdownPath: string }> {
  const safeProfileId = profileId.replace(/[^a-zA-Z0-9_-]/g, "_");
  const args = [
    "export-localization",
    "--project-dir",
    engineProjectDir(projectId),
    "--profile",
    profilePath,
  ];
  if (roundNumber) args.push("--round-number", String(roundNumber));
  await runNovelDrama(args);
  const resolvedRoundNumber = roundNumber ?? (await latestRoundNumber(projectId));
  if (!resolvedRoundNumber) throw new Error("no completed round found");
  const roundDir = path.join(
    /*turbopackIgnore: true*/
    engineProjectDir(projectId),
    roundDirName(resolvedRoundNumber)
  );
  const baseName = `localization_${safeProfileId}`;
  return {
    jsonPath: path.join(roundDir, `${baseName}.json`),
    markdownPath: path.join(roundDir, `${baseName}.md`),
  };
}

export async function getQualitySampleEvaluation(
  tenantId?: string
): Promise<QualitySampleEvaluationPayload> {
  const projectsDir = await qualityEvaluationDir(tenantId);
  const reportPath = path.join(
    /*turbopackIgnore: true*/
    projectsDir,
    qualitySampleReportName()
  );

  let report: QualitySampleEvaluationPayload["report"] = null;
  let updatedAt: string | null = null;
  try {
    const [raw, stat] = await Promise.all([
      fs.readFile(reportPath, "utf-8"),
      fs.stat(reportPath),
    ]);
    report = JSON.parse(raw) as QualitySampleEvaluationPayload["report"];
    updatedAt = stat.mtime.toISOString();
  } catch (error) {
    const code = (error as NodeJS.ErrnoException).code;
    if (code !== "ENOENT") throw error;
  }

  return {
    report,
    jobs: await listJobViews({ tenantId, kind: "quality_samples", limit: 8 }),
    reportPath,
    projectsDir,
    samplesPath: qualitySamplesPath(),
    updatedAt,
    mode: shouldUseMockEngine() ? "mock" : "real",
  };
}

async function executeQualitySampleEvaluation(
  rounds: number,
  jobId: string,
  tenantId?: string,
  variants?: string[]
): Promise<void> {
  const projectsDir = await qualityEvaluationDir(tenantId);
  const normalizedRounds = Math.max(1, Math.floor(rounds));
  const samplesPath = qualitySamplesPath();
  const selectedRepairBudget = qualitySampleRepairBudget();
  const selectedVariants = normalizeGenerationVariants(variants);
  const args = [
    "evaluate-samples",
    "--samples",
    samplesPath,
    "--projects-dir",
    projectsDir,
    "--rounds",
    String(normalizedRounds),
    "--generation-variants",
    selectedVariants.join(","),
    "--repair-budget",
    selectedRepairBudget,
  ];
  if (shouldUseMockEngine()) args.push("--mock");

  try {
    const startedAt = Date.now();
    const targets = await qualitySampleTargets(
      samplesPath,
      projectsDir,
      normalizedRounds,
      selectedVariants
    );
    await clearQualitySampleArtifacts(
      targets,
      path.join(projectsDir, qualitySampleReportName())
    );
    const progressSync = createQualitySampleProgressSync({
      jobId,
      targets,
      freshAfter: new Date(startedAt - 1000),
    });
    await updateJob(jobId, {
      message: "运行内部模型/Prompt 回归测试",
      progress: 25,
    });
    try {
      await runNovelDrama(args, { timeoutMs: qualitySampleTimeoutMs() });
    } finally {
      await progressSync.tick();
      progressSync.stop();
    }
    const runtimeMs = Date.now() - startedAt;
    const payload = await getQualitySampleEvaluation(tenantId);
    await succeedJob(jobId, {
      message: "内部回归测试完成",
      result: {
        passed: payload.report?.samples.filter((sample) =>
          sample.rounds.every((round) => round.warnings.length === 0)
        ).length,
        total: payload.report?.samples.length ?? 0,
        rounds: normalizedRounds,
        variants: selectedVariants,
        repairBudget: selectedRepairBudget,
        runtimeMs,
        reportPath: payload.reportPath,
      },
    });
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    const failure = classifyJobFailureText(message);
    await failJob(jobId, error, {
      message: failure?.userMessage ?? "内部回归失败",
      errorText: failure
        ? `${failure.userMessage}。${failure.operatorHint}`
        : message,
      result: {
        failureCategory: failure?.category ?? "engine_error",
        operatorHint:
          failure?.operatorHint ??
          "查看 quality worker 日志和样本 runtime_report 后重试。",
        reportPath: path.join(projectsDir, qualitySampleReportName()),
        projectsDir,
        variants: selectedVariants,
        rounds: normalizedRounds,
      },
    });
    console.error("[quality-samples] failed:", error);
  }
}

export async function executeQualitySampleJob(job: JobRow): Promise<void> {
  const payload = parseJobPayload<QualitySamplesPayload>(job);
  await executeQualitySampleEvaluation(
    payload.rounds,
    job.id,
    job.tenantId ?? undefined,
    payload.variants
  );
}

export async function executePlatformJob(job: JobRow): Promise<void> {
  if (job.kind === "round_generation") {
    await executeEngineRoundJob(job);
    return;
  }
  if (job.kind === "quality_samples") {
    await executeQualitySampleJob(job);
    return;
  }
  throw new Error(`Unsupported job kind: ${job.kind}`);
}

export async function startQualitySampleEvaluation(
  rounds = 2,
  tenantId?: string,
  variants?: string[]
): Promise<QualitySampleEvaluationPayload> {
  const normalizedRounds = Math.max(1, Math.floor(rounds));
  const selectedVariants = normalizeGenerationVariants(variants);
  if (tenantId) await assertTenantJobQuota(tenantId);
  const job = await createJob({
    kind: "quality_samples",
    tenantId,
    title: `内部回归测试 · ${normalizedRounds} 轮 · ${selectedVariants.join("/")}`,
    message: "等待低优先级 worker 执行",
    payload: {
      rounds: normalizedRounds,
      variants: selectedVariants,
    } satisfies QualitySamplesPayload,
  });

  return getQualitySampleEvaluation(tenantId);
}
