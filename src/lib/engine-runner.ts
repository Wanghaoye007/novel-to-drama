import fs from "fs/promises";
import path from "path";
import { spawn } from "child_process";
import { v4 as uuid } from "uuid";
import { and, desc, eq } from "drizzle-orm";
import { db, schema } from "@/db/client";
import { ensureProjectDir, ensureSystemDir, projectDir } from "./storage";
import { writeEpisodeTxt } from "./m6-export";
import { assertTenantJobQuota } from "./platform-context";
import {
  createJob,
  failJob,
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
  type QualitySampleEvaluationPayload,
  qualityAverage,
  qualityToEpisodeStatus,
  renderEngineEpisode,
  renderEpisodeContextMarkdown,
  renderStoryBibleMarkdown,
} from "./engine-types";

type ProjectRow = typeof schema.projects.$inferSelect;

type RoundGenerationPayload = {
  projectId: string;
  roundId: string;
  roundNumber: number;
};

type QualitySamplesPayload = {
  rounds: number;
};

function pythonPathEnv(): NodeJS.ProcessEnv {
  const sourcePath = path.join(/*turbopackIgnore: true*/ process.cwd(), "src");
  const existing = process.env.PYTHONPATH;
  return {
    ...process.env,
    PYTHONPATH: existing ? `${sourcePath}${path.delimiter}${existing}` : sourcePath,
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

async function runNovelDrama(args: string[]): Promise<string> {
  const { command, args: commandArgs } = novelDramaCommand(args);
  return new Promise((resolve, reject) => {
    const child = spawn(command, commandArgs, {
      cwd: /*turbopackIgnore: true*/ process.cwd(),
      env: pythonPathEnv(),
    });
    let stdout = "";
    let stderr = "";
    child.stdout.on("data", (chunk) => {
      stdout += chunk.toString();
    });
    child.stderr.on("data", (chunk) => {
      stderr += chunk.toString();
    });
    child.on("error", reject);
    child.on("close", (code) => {
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

async function syncBible(projectId: string, result: EngineRoundResult): Promise<void> {
  const existing = await db.query.bibles.findFirst({
    where: eq(schema.bibles.projectId, projectId),
  });
  const values = {
    channel: storyBibleChannel(result.story_bible.genre),
    sixAssetsJson: JSON.stringify(result.story_bible, null, 2),
    charactersMd: renderStoryBibleMarkdown(result.story_bible),
    episodePlanMd: renderEpisodeContextMarkdown(result.episode_context),
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

async function syncEngineRoundToDb(
  project: ProjectRow,
  roundId: string,
  result: EngineRoundResult
): Promise<void> {
  await syncBible(project.id, result);

  await db.delete(schema.episodes).where(eq(schema.episodes.roundId, roundId));

  const status = qualityToEpisodeStatus(result.quality_report.status);
  const score = qualityAverage(result.quality_report);
  const now = new Date();
  const episodeRows = result.script_batch.episodes.map((episode) => ({
    id: uuid(),
    projectId: project.id,
    roundId,
    epNum: episode.episode,
    draftMd: renderRoundEpisodeSummary(episode),
    scriptTxt: renderEngineEpisode(episode),
    score,
    reviewJson: JSON.stringify(result.quality_report, null, 2),
    epSummaryJson: JSON.stringify(episode.state_update, null, 2),
    retryCount: 0,
    status,
    updatedAt: now,
  }));

  if (episodeRows.length) {
    await db.insert(schema.episodes).values(episodeRows);
    await Promise.all(
      result.script_batch.episodes.map((episode) =>
        writeEpisodeTxt(project.id, episode.episode, renderEngineEpisode(episode))
      )
    );
  }

  await db
    .update(schema.rounds)
    .set({
      epRange: result.episode_context.target_episode_range,
      summaryJson: JSON.stringify(result, null, 2),
      status: "done",
    })
    .where(eq(schema.rounds.id, roundId));

  const projectStatus =
    result.next_round_context.current_episode >= project.targetEpisodeCount
      ? "done"
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
  jobId?: string
): Promise<void> {
  try {
    await updateJob(jobId, {
      message: "准备小说原文和 Engine 工作目录",
      progress: 15,
    });
    const storageDir = await ensureProjectDir(project.id);
    const engineDir = path.join(/*turbopackIgnore: true*/ storageDir, "engine");
    await fs.mkdir(engineDir, { recursive: true });
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
    ];
    if (shouldUseMockEngine()) args.push("--mock");

    await updateJob(jobId, {
      message: "调用 Engine 生成轮次脚本",
      progress: 35,
    });
    await runNovelDrama(args);
    await updateJob(jobId, {
      message: "同步 Engine artifacts 到 Web 数据库",
      progress: 85,
    });
    const result = await readEngineRoundResult(project.id, roundNumber);
    await syncEngineRoundToDb(project, roundId, result);
    await succeedJob(jobId, {
      message: `第 ${roundNumber} 轮完成`,
      result: {
        projectId: project.id,
        roundId,
        roundNumber,
        targetEpisodeRange: result.episode_context.target_episode_range,
        qualityStatus: result.quality_report.status,
      },
    });
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    await db
      .update(schema.rounds)
      .set({
        status: "failed",
        summaryJson: JSON.stringify({ error: message }, null, 2),
      })
      .where(eq(schema.rounds.id, roundId));
    await db
      .update(schema.projects)
      .set({ status: "failed", updatedAt: new Date() })
      .where(eq(schema.projects.id, project.id));
    await failJob(jobId, error);
    console.error("[engine-runner] failed:", error);
  }
}

export async function executeEngineRoundJob(job: JobRow): Promise<void> {
  const payload = parseJobPayload<RoundGenerationPayload>(job);
  const project = await db.query.projects.findFirst({
    where: eq(schema.projects.id, payload.projectId),
  });
  if (!project) throw new Error("project not found");
  await executeEngineRound(project, payload.roundNumber, payload.roundId, job.id);
}

export async function startEngineRound(
  projectId: string,
  roundNumber: number
): Promise<{ roundId: string; roundNum: number; jobId: string }> {
  const project = await db.query.projects.findFirst({
    where: eq(schema.projects.id, projectId),
  });
  if (!project) throw new Error("project not found");
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

  const job = await createJob({
    kind: "round_generation",
    title: `${project.name} · 第 ${roundNumber} 轮`,
    projectId,
    tenantId: project.tenantId,
    roundId,
    message: "等待 worker 执行",
    payload: { projectId, roundId, roundNumber } satisfies RoundGenerationPayload,
  });

  return { roundId, roundNum: roundNumber, jobId: job.id };
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
  tenantId?: string
): Promise<void> {
  const projectsDir = await qualityEvaluationDir(tenantId);
  const args = [
    "evaluate-samples",
    "--samples",
    qualitySamplesPath(),
    "--projects-dir",
    projectsDir,
    "--rounds",
    String(Math.max(1, Math.floor(rounds))),
  ];
  if (shouldUseMockEngine()) args.push("--mock");

  try {
    await updateJob(jobId, {
      message: "运行五类短剧样本评估",
      progress: 25,
    });
    await runNovelDrama(args);
    const payload = await getQualitySampleEvaluation(tenantId);
    await succeedJob(jobId, {
      message: "样本质检完成",
      result: {
        passed: payload.report?.samples.filter((sample) =>
          sample.rounds.every((round) => round.warnings.length === 0)
        ).length,
        total: payload.report?.samples.length ?? 0,
        rounds,
        reportPath: payload.reportPath,
      },
    });
  } catch (error) {
    await failJob(jobId, error);
    throw error;
  }
}

export async function executeQualitySampleJob(job: JobRow): Promise<void> {
  const payload = parseJobPayload<QualitySamplesPayload>(job);
  await executeQualitySampleEvaluation(payload.rounds, job.id, job.tenantId ?? undefined);
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
  tenantId?: string
): Promise<QualitySampleEvaluationPayload> {
  const normalizedRounds = Math.max(1, Math.floor(rounds));
  if (tenantId) await assertTenantJobQuota(tenantId);
  const job = await createJob({
    kind: "quality_samples",
    tenantId,
    title: `质量样本评估 · ${normalizedRounds} 轮`,
    message: "等待 worker 执行",
    payload: { rounds: normalizedRounds } satisfies QualitySamplesPayload,
  });

  return getQualitySampleEvaluation(tenantId);
}
