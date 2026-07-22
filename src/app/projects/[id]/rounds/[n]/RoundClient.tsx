"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import {
  Activity,
  AlertCircle,
  CheckCircle2,
  Clock3,
  Copy,
  Cpu,
  Download,
  FileText,
  Gauge,
  GitCompareArrows,
  Languages,
  ListVideo,
  PackageCheck,
  Pause,
  Play,
  RefreshCw,
  ScrollText,
  Sparkles,
  Video,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { ProjectManageButton } from "@/app/ProjectActionsClient";
import type { EngineJob } from "@/lib/engine-types";
import type { EditImpactReport } from "@/lib/edit-impact";
import {
  DEFAULT_LLM_MODEL,
  llmModelLabel,
  llmModelOptions,
} from "@/lib/llm-model-options";

type Project = {
  id: string;
  name: string;
  targetEpisodeCount: number;
  status: string;
  metaJson?: string | null;
};
type PlatformSession = {
  userEmail: string;
  tenantSlug: string;
  tenantName: string;
  source: "browser" | "api_key" | "default";
};
type Round = {
  id: string;
  roundNum: number;
  epRange: string;
  status: string;
  summaryJson: string | null;
};
type Episode = {
  id: string;
  roundId: string;
  epNum: number;
  status: string;
  score: number | null;
  scriptTxt: string | null;
  reviewJson?: string | null;
  retryCount: number;
};
type EngineRoundSummary = {
  quality_report?: {
    status: string;
    scores: Record<string, number>;
    blocking_issues: string[];
  };
  runtime_report?: {
    generation_variant?: string;
    repair_budget?: string;
    llm_model?: string | null;
    total_duration_ms?: number;
    stages?: Array<{
      name: string;
      duration_ms: number;
      status: string;
      error?: string | null;
    }>;
    llm_calls?: Array<{
      usage?: {
        prompt_tokens?: number | null;
        completion_tokens?: number | null;
        total_tokens?: number | null;
      } | null;
    }>;
  };
  next_round_context?: {
    current_episode: number;
    summary: string;
    open_hooks: string[];
    forbidden_reveals: string[];
  };
  adaptation_quality_report?: {
    source_fidelity?: {
      score: number;
      blocking_warnings: string[];
      advisory_warnings: string[];
    };
    continuity?: {
      score: number;
      blocking_warnings: string[];
      advisory_warnings: string[];
    };
    blocking_warnings: string[];
    advisory_warnings: string[];
  };
  source_evidence_report?: {
    coverage_score: number;
    missing_items: string[];
  };
  drama_quality_report?: {
    dimensions: Array<{
      name: string;
      score: number;
      status: "passed" | "advisory" | "blocking";
    }>;
  };
  story_state_ledger?: {
    current_episode: number;
    entries: Array<{
      episode?: number | null;
      kind: string;
      key: string;
      value: string;
      status: string;
    }>;
    warnings: string[];
  };
  source_strength_profile?: {
    overall_level: "strong" | "medium" | "weak";
    recommended_intensity: "light" | "medium" | "heavy";
    reasons: string[];
  };
  methodology_context?: {
    source_strength_level: "strong" | "medium" | "weak";
    adaptation_intensity: "light" | "medium" | "heavy";
    cards: Array<{
      id: string;
      name: string;
      category: string;
      trigger: string;
      generation_rule: string;
      quality_rule: string;
    }>;
  };
  methodology_quality_report?: {
    issues: Array<{
      card_id: string;
      card_name: string;
      severity: "advisory" | "blocking";
      episode?: number | null;
      message: string;
      evidence: string[];
    }>;
    rewrite_instruction: string;
  };
};
type DeliveryPreflight = {
  ready: boolean;
  warnings: string[];
  files: Array<{ path: string; bytes: number }>;
};
type LocalizationProfileOption = {
  id: string;
  label: string;
  locale: string;
  platform: string;
  targetLanguage: string;
};
type ProjectPayload = {
  project: Project;
  rounds: Round[];
  episodes: Episode[];
  jobs: EngineJob[];
};

type ProjectMeta = {
  control?: {
    runAll?: {
      enabled?: boolean;
    };
    qualityGate?: {
      status?: string | null;
      round?: number | null;
      pausedAt?: string | null;
      rewriteInstruction?: string | null;
    };
  };
};

const repairBudgetOptions = [
  { value: "episode", label: "逐集修复" },
  { value: "rewrite", label: "改写一次" },
  { value: "none", label: "不自动修复" },
];

const episodeCountOptions = [1, 2, 3, 4, 5];

type EpisodeStatusFilter = "all" | "review" | "issue" | "active";
type RoundTopDrawer = "episodes" | "quality" | "issues" | null;

const qualityLabels: Record<string, string> = {
  hook: "开场",
  conflict: "冲突",
  cliffhanger: "断点",
  continuity: "连续",
  video_feasibility: "可拍",
};

function parseSummary(round?: Round): EngineRoundSummary | null {
  if (!round?.summaryJson) return null;
  try {
    return JSON.parse(round.summaryJson) as EngineRoundSummary;
  } catch {
    return null;
  }
}

type JobResultSummary = {
  runtimeMs?: number | null;
  llmCalls?: number | null;
  qualityStatus?: string | null;
  targetEpisodeRange?: string | null;
  generationVariant?: string | null;
  repairBudget?: string | null;
  episodesPerRound?: number | null;
  llmModel?: string | null;
  methodologyCards?: string[] | null;
  sourceStrength?: string | null;
  adaptationIntensity?: string | null;
};

function parseJobResult(job?: EngineJob | null): JobResultSummary | null {
  if (!job?.resultJson) return null;
  try {
    return JSON.parse(job.resultJson) as JobResultSummary;
  } catch {
    return null;
  }
}

function parseProjectMeta(project: Project): ProjectMeta {
  if (!project.metaJson) return {};
  try {
    return JSON.parse(project.metaJson) as ProjectMeta;
  } catch {
    return {};
  }
}

function formatDuration(ms?: number | null): string {
  if (typeof ms !== "number" || !Number.isFinite(ms)) return "-";
  if (ms < 1000) return `${Math.max(0, Math.round(ms))} ms`;
  const seconds = ms / 1000;
  if (seconds < 60) return `${seconds.toFixed(1)} s`;
  const minutes = Math.floor(seconds / 60);
  const rest = Math.round(seconds % 60);
  return `${minutes}m ${rest}s`;
}

function formatNumber(value?: number | null): string {
  if (typeof value !== "number" || !Number.isFinite(value)) return "-";
  return Math.round(value).toLocaleString();
}

function clampQualityScore(value: number): number {
  if (!Number.isFinite(value)) return 0;
  return Math.max(0, Math.min(10, value));
}

const GEMINI_FLASH_LITE_INPUT_USD_PER_MILLION = 0.25;
const GEMINI_FLASH_LITE_OUTPUT_USD_PER_MILLION = 1.5;

type RuntimeTokenSummary = {
  inputTokens: number | null;
  outputTokens: number | null;
  totalTokens: number | null;
  estimatedUsd: number | null;
};

function runtimeTokenSummary(
  calls?: NonNullable<EngineRoundSummary["runtime_report"]>["llm_calls"] | null
): RuntimeTokenSummary {
  if (!calls?.length) {
    return {
      inputTokens: null,
      outputTokens: null,
      totalTokens: null,
      estimatedUsd: null,
    };
  }
  const inputTokens = calls.reduce((sum, call) => {
    const value = call.usage?.prompt_tokens;
    return sum + (typeof value === "number" ? value : 0);
  }, 0);
  const outputTokens = calls.reduce((sum, call) => {
    const value = call.usage?.completion_tokens;
    return sum + (typeof value === "number" ? value : 0);
  }, 0);
  const totalTokens = calls.reduce((sum, call) => {
    const value = call.usage?.total_tokens;
    return sum + (typeof value === "number" ? value : 0);
  }, 0);
  const hasSplitUsage = inputTokens > 0 || outputTokens > 0;
  return {
    inputTokens: inputTokens || null,
    outputTokens: outputTokens || null,
    totalTokens: totalTokens || (hasSplitUsage ? inputTokens + outputTokens : null),
    estimatedUsd: hasSplitUsage
      ? (inputTokens / 1_000_000) * GEMINI_FLASH_LITE_INPUT_USD_PER_MILLION +
        (outputTokens / 1_000_000) * GEMINI_FLASH_LITE_OUTPUT_USD_PER_MILLION
      : null,
  };
}

function formatUsd(value?: number | null): string {
  if (typeof value !== "number" || !Number.isFinite(value)) return "-";
  if (value > 0 && value < 0.01) return `$${value.toFixed(4)}`;
  return `$${value.toFixed(2)}`;
}

function jobLabel(job: EngineJob): string {
  if (job.status === "queued") return job.isQueuedTooLong ? "等待过久" : "排队中";
  if (job.status === "running") return job.isStale ? "疑似中断" : "运行中";
  if (job.status === "succeeded") return "已完成";
  return "失败";
}

function qualityStatusText(status?: string | null): string {
  if (status === "usable") return "可交付";
  if (status === "needs_human_review") return "待复核";
  if (status === "needs_rewrite") return "需重写";
  if (status === "context_conflict") return "上下文冲突";
  if (status === "failed") return "失败";
  return status ?? "未评估";
}

function parseEpisodeReviewStatus(episode: Episode): string | null {
  if (!episode.reviewJson) return null;
  try {
    const review = JSON.parse(episode.reviewJson) as { status?: string | null };
    return review.status ?? null;
  } catch {
    return null;
  }
}

function episodeDisplay(episode: Episode): {
  label: string;
  tone: "ready" | "active" | "danger" | "muted" | "review";
  badgeVariant: "default" | "destructive" | "outline";
  badgeClassName?: string;
} {
  const status = episode.status;
  const reviewStatus = parseEpisodeReviewStatus(episode);
  if (status === "green") {
    return { label: "通过", tone: "ready", badgeVariant: "default" };
  }
  if (status === "red" && reviewStatus === "needs_human_review") {
    return {
      label: "待复核",
      tone: "review",
      badgeVariant: "outline",
      badgeClassName: "border-black/10 bg-white text-muted-foreground",
    };
  }
  if (status === "red" && reviewStatus) {
    return {
      label: qualityStatusText(reviewStatus),
      tone: "danger",
      badgeVariant: "destructive",
    };
  }
  if (status === "red") {
    return { label: "需修", tone: "danger", badgeVariant: "destructive" };
  }
  if (status === "pending") return { label: "等待", tone: "active", badgeVariant: "outline" };
  if (status === "failed") return { label: "失败", tone: "danger", badgeVariant: "destructive" };
  if (status === "running") return { label: "生成中", tone: "active", badgeVariant: "outline" };
  return { label: status, tone: "muted", badgeVariant: "outline" };
}

function extractEpisodeTitle(ep: Episode): string {
  const fallback = `第 ${ep.epNum} 集`;
  if (!ep.scriptTxt) return fallback;
  const firstLine = ep.scriptTxt
    .split(/\r?\n/)
    .map((line) => line.trim())
    .find(Boolean);
  if (!firstLine) return fallback;
  return firstLine.replace(/^第\s*\d+\s*集\s*/, "").trim() || firstLine;
}

function scriptLineCount(ep?: Episode): number {
  if (!ep?.scriptTxt) return 0;
  return ep.scriptTxt.split(/\r?\n/).filter((line) => line.trim()).length;
}

async function copyText(text: string): Promise<void> {
  if (navigator.clipboard?.writeText && window.isSecureContext) {
    await navigator.clipboard.writeText(text);
    return;
  }

  const textarea = document.createElement("textarea");
  textarea.value = text;
  textarea.setAttribute("readonly", "");
  textarea.style.position = "fixed";
  textarea.style.top = "0";
  textarea.style.left = "-9999px";
  document.body.appendChild(textarea);
  textarea.focus();
  textarea.select();
  try {
    const copied = document.execCommand("copy");
    if (!copied) throw new Error("copy command failed");
  } finally {
    document.body.removeChild(textarea);
  }
}

function filenameFromDisposition(
  disposition: string | null,
  fallback: string
): string {
  if (!disposition) return fallback;
  const encoded = disposition.match(/filename\*=UTF-8''([^;]+)/i)?.[1];
  if (encoded) {
    try {
      return decodeURIComponent(encoded.replace(/^"|"$/g, ""));
    } catch {
      return fallback;
    }
  }
  return disposition.match(/filename="([^"]+)"/i)?.[1] ?? fallback;
}

async function readResponseError(res: Response, fallback: string): Promise<string> {
  const text = await res.text().catch(() => "");
  if (!text) return `${fallback} (${res.status})`;
  try {
    const payload = JSON.parse(text) as { error?: string };
    return payload.error ?? text;
  } catch {
    return text;
  }
}

function episodeCountFromRange(range?: string | null): number | null {
  if (!range) return null;
  const match = range.match(/E(?:P)?0*(\d+)\s*-\s*E(?:P)?0*(\d+)/i);
  if (!match) return null;
  const start = Number(match[1]);
  const end = Number(match[2]);
  if (!Number.isFinite(start) || !Number.isFinite(end) || end < start) {
    return null;
  }
  return end - start + 1;
}

function fullSeriesEpisodes(episodes: Episode[], rounds: Round[]): Episode[] {
  const roundNumberById = new Map(rounds.map((round) => [round.id, round.roundNum]));
  const earliestByEpisode = new Map<number, Episode>();
  const orderedEpisodes = [...episodes].sort((a, b) => {
    if (a.epNum !== b.epNum) return a.epNum - b.epNum;
    return (roundNumberById.get(a.roundId) ?? 0) - (roundNumberById.get(b.roundId) ?? 0);
  });
  for (const episode of orderedEpisodes) {
    const current = earliestByEpisode.get(episode.epNum);
    if (!current || (!current.scriptTxt && episode.scriptTxt)) {
      earliestByEpisode.set(episode.epNum, episode);
    }
  }
  return [...earliestByEpisode.values()].sort((a, b) => a.epNum - b.epNum);
}

function visibleScriptCount(episodes: Episode[]): number {
  return episodes.filter((episode) => episode.scriptTxt).length;
}

function activeOrLatestJob(jobs: EngineJob[]): EngineJob | undefined {
  return (
    jobs.find((job) => job.status === "running" || job.status === "queued") ??
    jobs[0]
  );
}

function shouldKeepPollingProject(data: ProjectPayload, roundNum: number): boolean {
  const currentRound = data.rounds.find((round) => round.roundNum === roundNum);
  if (currentRound?.status === "failed") return false;
  if (data.project.status === "done" || data.project.status === "failed") {
    return false;
  }
  const runAllEnabled = parseProjectMeta(data.project).control?.runAll?.enabled === true;
  const hasActiveJob = data.jobs.some(
    (job) => job.status === "running" || job.status === "queued"
  );
  if (data.project.status === "running" && (runAllEnabled || hasActiveJob)) {
    return true;
  }
  if (
    visibleScriptCount(fullSeriesEpisodes(data.episodes, data.rounds)) >=
    data.project.targetEpisodeCount
  ) {
    return false;
  }
  return currentRound?.status !== "done";
}

export function RoundClient({
  projectId,
  roundNum,
  project,
  platformSession,
}: {
  projectId: string;
  roundNum: number;
  project: Project;
  platformSession: PlatformSession;
}) {
  const [data, setData] = useState<ProjectPayload | null>(null);
  const [delivery, setDelivery] = useState<DeliveryPreflight | null>(null);
  const [actionMessage, setActionMessage] = useState<string | null>(null);
  const [busyAction, setBusyAction] = useState<string | null>(null);
  const [pollKey, setPollKey] = useState(0);
  const [profiles, setProfiles] = useState<LocalizationProfileOption[]>([]);
  const [selectedProfile, setSelectedProfile] = useState("us_tiktok");
  const [selectedEpisodeNum, setSelectedEpisodeNum] = useState<number | null>(
    null
  );
  const [selectedRepairBudget, setSelectedRepairBudget] = useState("episode");
  const [selectedEpisodesPerRound, setSelectedEpisodesPerRound] = useState("5");
  const [selectedLlmModel, setSelectedLlmModel] = useState<string>(DEFAULT_LLM_MODEL);
  const [episodeOptimizeInstruction, setEpisodeOptimizeInstruction] = useState("");
  const [impactDraft, setImpactDraft] = useState("");
  const [impactReport, setImpactReport] = useState<EditImpactReport | null>(null);
  const [episodeStatusFilter, setEpisodeStatusFilter] =
    useState<EpisodeStatusFilter>("all");
  const [topDrawer, setTopDrawer] = useState<RoundTopDrawer>(null);

  function assertPlatformResponseContext(response: Response): void {
    const responseTenant = response.headers.get("x-novel-tenant-slug");
    if (responseTenant && responseTenant !== platformSession.tenantSlug) {
      throw new Error(
        `当前页面工作区是 ${platformSession.tenantSlug}，但接口返回 ${responseTenant}，已停止操作以避免串任务。`
      );
    }
  }

  async function platformFetch(
    input: RequestInfo | URL,
    init: RequestInit = {}
  ): Promise<Response> {
    const response = await globalThis.fetch(input, {
      ...init,
      credentials: "same-origin",
    });
    assertPlatformResponseContext(response);
    return response;
  }

  async function loadProjectData(): Promise<ProjectPayload> {
    const res = await platformFetch(`/api/projects/${projectId}`, {
      cache: "no-store",
      headers: { "cache-control": "no-cache" },
    });
    const d = (await res.json()) as ProjectPayload & { error?: string };
    if (!res.ok) throw new Error(d.error ?? "项目状态加载失败");
    setData(d);
    return d;
  }

  useEffect(() => {
    let stopped = false;
    async function poll() {
      while (!stopped) {
        try {
          const d = await loadProjectData();
          if (!shouldKeepPollingProject(d, roundNum)) {
            break;
          }
        } catch (error) {
          console.warn("[round-poll] project refresh failed; retrying", error);
        }
        await new Promise((resolve) => setTimeout(resolve, 3000));
      }
    }
    poll();
    return () => {
      stopped = true;
    };
  }, [projectId, roundNum, pollKey]);

  useEffect(() => {
    let cancelled = false;
    async function loadProfiles() {
      const res = await platformFetch(`/api/projects/${projectId}/localization`);
      if (!res.ok) return;
      const loaded = (await res.json()) as LocalizationProfileOption[];
      if (cancelled) return;
      setProfiles(loaded);
      if (loaded.length > 0 && !loaded.some((item) => item.id === selectedProfile)) {
        setSelectedProfile(loaded[0].id);
      }
    }
    loadProfiles();
    return () => {
      cancelled = true;
    };
  }, [projectId, selectedProfile]);

  useEffect(() => {
    if (!data) return;
    const candidateEpisodes = fullSeriesEpisodes(data.episodes, data.rounds);
    if (candidateEpisodes.length === 0) return;
    if (!candidateEpisodes.some((episode) => episode.epNum === selectedEpisodeNum)) {
      setSelectedEpisodeNum(candidateEpisodes[0].epNum);
    }
  }, [data, roundNum, selectedEpisodeNum]);

  useEffect(() => {
    if (!data) return;
    const candidateEpisodes = fullSeriesEpisodes(data.episodes, data.rounds);
    const currentEpisode =
      candidateEpisodes.find((episode) => episode.epNum === selectedEpisodeNum) ?? null;
    setImpactDraft(currentEpisode?.scriptTxt ?? "");
    setEpisodeOptimizeInstruction("");
    setImpactReport((currentReport) =>
      currentReport?.episodeId === currentEpisode?.id ? currentReport : null
    );
  }, [data, roundNum, selectedEpisodeNum]);

  if (!data) {
    return (
      <section className="page-shell">
        <Card className="round-loading-card">
          <RefreshCw className="size-4 animate-spin text-[color:var(--reela-pink)]" />
          <span>正在打开剧集工作台...</span>
        </Card>
      </section>
    );
  }

  const round = data.rounds.find((r) => r.roundNum === roundNum);
  const summary = parseSummary(round);
  const quality = summary?.quality_report;
  const context = summary?.next_round_context;
  const runtime = summary?.runtime_report;
  const adaptationQuality = summary?.adaptation_quality_report;
  const sourceEvidence = summary?.source_evidence_report;
  const dramaQuality = summary?.drama_quality_report;
  const storyLedger = summary?.story_state_ledger;
  const sourceStrength = summary?.source_strength_profile;
  const methodologyContext = summary?.methodology_context;
  const projectEpisodes = fullSeriesEpisodes(data.episodes, data.rounds);
  const latestRound = data.rounds.reduce<Round | undefined>(
    (latest, item) => (!latest || item.roundNum > latest.roundNum ? item : latest),
    undefined
  );
  const eps = projectEpisodes;
  const selectedEpisode =
    eps.find((episode) => episode.epNum === selectedEpisodeNum) ?? eps[0] ?? null;
  const selectedTitle = selectedEpisode
    ? extractEpisodeTitle(selectedEpisode)
    : "暂无剧集";
  const selectedEpisodeDisplay = selectedEpisode
    ? episodeDisplay(selectedEpisode)
    : null;
  const currentRoundJob =
    data.jobs.find((job) => job.roundId === round?.id) ??
    data.jobs.find((job) => job.kind === "round_generation");
  const roundJob = activeOrLatestJob(data.jobs) ?? currentRoundJob;
  const jobResult = parseJobResult(roundJob);
  const tokenSummary = runtimeTokenSummary(runtime?.llm_calls);
  const totalTokens = tokenSummary.totalTokens;
  const runtimeMs = runtime?.total_duration_ms ?? jobResult?.runtimeMs ?? null;
  const llmCalls = runtime?.llm_calls?.length ?? jobResult?.llmCalls ?? null;
  const slowestStage = runtime?.stages?.length
    ? [...runtime.stages].sort((a, b) => b.duration_ms - a.duration_ms)[0]
    : null;

  const projectDone = data.project.status === "done";
  const projectPaused = data.project.status === "paused";
  const projectMeta = parseProjectMeta(data.project);
  const projectQualityGate = projectMeta.control?.qualityGate;
  const runAllEnabled =
    projectMeta.control?.runAll?.enabled === true && !projectDone;
  const reachedTarget =
    (context?.current_episode ?? 0) >= data.project.targetEpisodeCount ||
    visibleScriptCount(projectEpisodes) >= data.project.targetEpisodeCount;
  const expectedEpisodeCount =
    Math.max(data.project.targetEpisodeCount, eps.at(-1)?.epNum ?? 0, 1);
  const visibleEpisodeCount = visibleScriptCount(eps);
  const latestRoundDone = latestRound?.status === "done";
  const nextRoundNum = (latestRound?.roundNum ?? roundNum) + 1;
  const episodeProgress = Math.round(
    (visibleEpisodeCount / Math.max(expectedEpisodeCount, 1)) * 100
  );
  const rawQualityAverage = quality
    ? Object.values(quality.scores).reduce((sum, value) => sum + value, 0) /
      Math.max(Object.values(quality.scores).length, 1)
    : null;
  const creativeQualityScore =
    rawQualityAverage == null ? null : clampQualityScore(rawQualityAverage);
  const qualityStatusLabel = qualityStatusText(quality?.status);
  const projectStatusLabel = projectQualityGate?.status
    ? qualityStatusText(projectQualityGate.status)
    : data.project.status;
  const projectStatusBadgeClassName = projectQualityGate?.status
    ? "border-black/10 bg-white text-muted-foreground"
    : undefined;
  const qualityBadgeClassName =
    quality?.status === "needs_human_review"
      ? "border-black/10 bg-white text-muted-foreground"
      : undefined;
  const workerStatusLabel = roundJob ? jobLabel(roundJob) : "暂无任务";
  const hasGenerationMetrics =
    runtime || jobResult?.runtimeMs != null || jobResult?.llmCalls != null;
  const exportProjectName = data.project.name || "novel-to-drama";
  const methodologyCards =
    methodologyContext?.cards ??
    jobResult?.methodologyCards?.map((name, index) => ({
      id: `job-methodology-${index}`,
      name,
      category: "runtime",
      trigger: "",
      generation_rule: "",
      quality_rule: "",
    })) ??
    [];
  const scoreEntries = quality
    ? Object.entries(quality.scores).map(([key, value]) => ({
        key,
        label: qualityLabels[key] ?? key,
        value,
      }))
    : [];
  const sourceFidelityScore =
    adaptationQuality?.source_fidelity?.score != null
      ? Math.max(0, Math.min(10, Math.floor(adaptationQuality.source_fidelity.score / 10)))
      : null;
  const sourceEvidenceScore =
    sourceEvidence?.coverage_score != null
      ? clampQualityScore(sourceEvidence.coverage_score / 10)
      : null;
  const dramaSourceScore =
    dramaQuality?.dimensions?.find(
      (dimension) => dimension.name === "source_asset_preservation"
    )?.score ?? null;
  const effectiveSourceScore = [
    sourceFidelityScore,
    sourceEvidenceScore,
    dramaSourceScore,
  ]
    .filter((value): value is number => typeof value === "number")
    .reduce<number | null>(
      (minimum, value) =>
        minimum == null ? clampQualityScore(value) : Math.min(minimum, clampQualityScore(value)),
      null
    );
  const roundGateScore =
    creativeQualityScore == null
      ? null
      : Math.min(
          creativeQualityScore,
          effectiveSourceScore ?? creativeQualityScore
        );
  const sourceDisplayScore = effectiveSourceScore ?? sourceFidelityScore;
  const blockingIssueCount =
    (quality?.blocking_issues.length ?? 0) +
    (adaptationQuality?.blocking_warnings.length ?? 0) +
    (summary?.methodology_quality_report?.issues.filter(
      (issue) => issue.severity === "blocking"
    ).length ?? 0);
  const advisoryIssueCount =
    (adaptationQuality?.advisory_warnings.length ?? 0) +
    (summary?.methodology_quality_report?.issues.filter(
      (issue) => issue.severity === "advisory"
    ).length ?? 0);
  const projectStageLabel = projectDone
    ? "已完成"
    : projectPaused
      ? "已暂停"
      : runAllEnabled
        ? "批量运行中"
        : roundJob?.status === "running"
          ? "生成中"
          : roundJob?.status === "queued"
            ? "排队中"
            : latestRoundDone && !reachedTarget
              ? "等待下一轮"
              : reachedTarget
                ? "可交付"
                : "待启动";
  const nextActionHint = projectPaused
    ? "继续项目后恢复后台生成"
    : runAllEnabled
      ? "等待当前 worker 写出下一集"
      : roundJob?.retryable
        ? "先恢复或重试当前任务"
        : latestRoundDone && !projectDone && !reachedTarget
          ? `启动第 ${nextRoundNum} 轮`
          : reachedTarget || projectDone
            ? "进入完成页或导出成品"
            : "等待本轮生成完成";
  const attentionItems = [
    blockingIssueCount > 0
      ? `${blockingIssueCount} 个阻断问题需要处理`
      : null,
    roundJob?.retryable ? "Worker 可重试" : null,
    projectQualityGate ? "质量门禁暂停在项目控制中" : null,
    advisoryIssueCount > 0 ? `${advisoryIssueCount} 个建议项` : null,
  ].filter((item): item is string => Boolean(item));
  const reviewEpisodeCount = eps.filter((episode) => {
    const reviewStatus = parseEpisodeReviewStatus(episode);
    const display = episodeDisplay(episode);
    return reviewStatus === "needs_human_review" || display.tone === "review";
  }).length;
  const issueEpisodeCount = eps.filter((episode) => {
    const display = episodeDisplay(episode);
    return episode.status === "failed" || display.tone === "danger";
  }).length;
  const activeEpisodeCount = eps.filter((episode) => {
    const display = episodeDisplay(episode);
    return display.tone === "active" || episode.status === "queued";
  }).length;
  const filteredEpisodes = eps.filter((episode) => {
    const display = episodeDisplay(episode);
    const reviewStatus = parseEpisodeReviewStatus(episode);
    if (episodeStatusFilter === "review") {
      return reviewStatus === "needs_human_review" || display.tone === "review";
    }
    if (episodeStatusFilter === "issue") {
      return episode.status === "failed" || display.tone === "danger";
    }
    if (episodeStatusFilter === "active") {
      return display.tone === "active" || episode.status === "queued";
    }
    return true;
  });
  const unresolvedIssueCount = blockingIssueCount + advisoryIssueCount + issueEpisodeCount;
  const primaryActionLabel =
    reachedTarget || projectDone
      ? "进入完成页"
      : latestRoundDone && !projectDone && !reachedTarget
        ? `开始第 ${nextRoundNum} 轮`
        : runAllEnabled
          ? "停止批量"
          : "批量运行";

  function toggleTopDrawer(drawer: Exclude<RoundTopDrawer, null>) {
    setTopDrawer((current) => (current === drawer ? null : drawer));
  }

  function setFilterAndDrawer(
    filter: EpisodeStatusFilter,
    drawer: Exclude<RoundTopDrawer, null>
  ) {
    setEpisodeStatusFilter(filter);
    toggleTopDrawer(drawer);
  }

  async function nextRound() {
    setBusyAction("next-round");
    setActionMessage(null);
    try {
      const res = await platformFetch(`/api/projects/${projectId}/rounds/start`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          repairBudget: selectedRepairBudget,
          episodesPerRound: Number(selectedEpisodesPerRound),
          llmModel: selectedLlmModel,
        }),
      });
      if (!res.ok) throw new Error(await res.text());
      const payload = (await res.json()) as { roundNum?: number };
      window.location.href = `/projects/${projectId}/rounds/${
        payload.roundNum ?? roundNum + 1
      }`;
    } catch (error) {
      setActionMessage(error instanceof Error ? error.message : String(error));
    } finally {
      setBusyAction(null);
    }
  }

  async function retryJob(jobId: string) {
    const actionName = `retry-${jobId}`;
    setBusyAction(actionName);
    setActionMessage(null);
    try {
      const res = await platformFetch(`/api/jobs/${jobId}/retry`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ llmModel: selectedLlmModel }),
      });
      let payload: { error?: string } | null = null;
      try {
        payload = (await res.json()) as { error?: string };
      } catch {
        payload = null;
      }
      if (!res.ok) throw new Error(payload?.error ?? "任务重试失败");
      await loadProjectData();
      setPollKey((value) => value + 1);
      setActionMessage("任务已重新排队");
    } catch (error) {
      setActionMessage(error instanceof Error ? error.message : String(error));
    } finally {
      setBusyAction(null);
    }
  }

  async function cloneProject() {
    setBusyAction("clone");
    setActionMessage(null);
    try {
      const res = await platformFetch(`/api/projects/${projectId}/clone`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          repairBudget: selectedRepairBudget,
          episodesPerRound: Number(selectedEpisodesPerRound),
          llmModel: selectedLlmModel,
        }),
      });
      const payload = (await res.json()) as {
        id?: string;
        roundNum?: number;
        error?: string;
      };
      if (!res.ok || !payload.id) {
        throw new Error(payload.error ?? "复制项目失败");
      }
      window.location.href = `/projects/${payload.id}/rounds/${
        payload.roundNum ?? 1
      }`;
    } catch (error) {
      setActionMessage(error instanceof Error ? error.message : String(error));
    } finally {
      setBusyAction(null);
    }
  }

  async function controlProject(
    action: "pause" | "resume" | "run_all" | "stop_run_all"
  ) {
    const actionName = `project-${action}`;
    setBusyAction(actionName);
    setActionMessage(null);
    try {
      const res = await platformFetch(`/api/projects/${projectId}/control`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          action,
          repairBudget: selectedRepairBudget,
          episodesPerRound: action === "run_all" ? 5 : Number(selectedEpisodesPerRound),
          llmModel: selectedLlmModel,
        }),
      });
      const payload = (await res.json()) as { error?: string };
      if (!res.ok) throw new Error(payload.error ?? "项目控制失败");
      await loadProjectData();
      setPollKey((value) => value + 1);
      if (action === "pause") setActionMessage("项目已暂停");
      if (action === "resume") setActionMessage("项目已继续");
      if (action === "run_all") setActionMessage("已开启批量运行");
      if (action === "stop_run_all") setActionMessage("已停止批量运行");
    } catch (error) {
      setActionMessage(error instanceof Error ? error.message : String(error));
    } finally {
      setBusyAction(null);
    }
  }

  async function runAction(name: string, action: () => Promise<string>) {
    setBusyAction(name);
    setActionMessage(null);
    try {
      setActionMessage(await action());
    } catch (error) {
      setActionMessage(error instanceof Error ? error.message : String(error));
    } finally {
      setBusyAction(null);
    }
  }

  async function checkDelivery() {
    const res = await platformFetch(`/api/projects/${projectId}/delivery?round=${roundNum}`);
    if (!res.ok) throw new Error(await res.text());
    const report = (await res.json()) as DeliveryPreflight;
    setDelivery(report);
    return report.ready ? "交付预检通过" : "交付预检有 warning";
  }

  async function exportVideoBrief() {
    const res = await platformFetch(`/api/projects/${projectId}/video-brief?round=${roundNum}`, {
      method: "POST",
    });
    if (!res.ok) throw new Error(await res.text());
    setPollKey((value) => value + 1);
    return "视频 brief 导出已排队";
  }

  async function exportLocalization() {
    const res = await platformFetch(
      `/api/projects/${projectId}/localization?round=${roundNum}&profile=${selectedProfile}`,
      { method: "POST" }
    );
    if (!res.ok) throw new Error(await res.text());
    setPollKey((value) => value + 1);
    const profile = profiles.find((item) => item.id === selectedProfile);
    return `${profile?.label ?? selectedProfile} 本地化包导出已排队`;
  }

  async function exportDeliveryPackage() {
    const res = await platformFetch(
      `/api/projects/${projectId}/export?round=${roundNum}&allowIssues=1`,
      { method: "POST" }
    );
    if (!res.ok) throw new Error(await res.text());
    setPollKey((value) => value + 1);
    return "交付包导出已排队";
  }

  async function copySelectedScript() {
    if (!selectedEpisode?.scriptTxt) return;
    try {
      await copyText(selectedEpisode.scriptTxt);
      setActionMessage(`第 ${selectedEpisode.epNum} 集脚本已复制`);
    } catch {
      setActionMessage("复制失败，请直接选中文本复制");
    }
  }

  async function downloadNovelExport(format: "txt" | "word") {
    const actionName = `novel-export-${format}`;
    setBusyAction(actionName);
    setActionMessage(null);
    try {
      const res = await platformFetch(
        `/api/projects/${projectId}/novel-export?format=${format}`
      );
      if (!res.ok) {
        throw new Error(await readResponseError(res, "导出失败"));
      }
      const blob = await res.blob();
      const ext = format === "word" ? "docx" : "txt";
      const fallback = `${exportProjectName}.${ext}`;
      const filename = filenameFromDisposition(
        res.headers.get("content-disposition"),
        fallback
      );
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = filename;
      document.body.appendChild(anchor);
      anchor.click();
      document.body.removeChild(anchor);
      window.setTimeout(() => URL.revokeObjectURL(url), 1000);
      setActionMessage(format === "word" ? "Word 已开始下载" : "TXT 已开始下载");
    } catch (error) {
      setActionMessage(error instanceof Error ? error.message : String(error));
    } finally {
      setBusyAction(null);
    }
  }

  async function analyzeImpact() {
    if (!selectedEpisode) return;
    setBusyAction("impact");
    setActionMessage(null);
    try {
      const res = await platformFetch(`/api/episodes/${selectedEpisode.id}/impact`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          editedScriptText: impactDraft,
          applyEdit: true,
          optimizeDownstream: true,
          llmModel: selectedLlmModel,
        }),
      });
      const payload = (await res.json()) as EditImpactReport & {
        error?: string;
        jobId?: string;
        status?: string;
      };
      if (!res.ok) throw new Error(payload.error ?? "编辑影响分析失败");
      if (payload.status !== "queued") setImpactReport(payload);
      await loadProjectData();
      setPollKey((value) => value + 1);
      if (payload.status === "queued") {
        setActionMessage("改稿已进入后台队列，完成后页面会自动更新");
        return;
      }
      if (payload.applied) {
        const optimizedCount =
          payload.optimizedEpisodes?.filter((item) => item.status === "optimized")
            .length ?? 0;
        setActionMessage(
          optimizedCount > 0
            ? `已应用当前集改稿，并优化 ${optimizedCount} 个后续承接剧集`
            : "已应用当前集改稿，后续承接要求已写入系统上下文"
        );
      }
    } catch (error) {
      setActionMessage(error instanceof Error ? error.message : String(error));
    } finally {
      setBusyAction(null);
    }
  }

  async function optimizeSelectedEpisode() {
    if (!selectedEpisode?.scriptTxt) return;
    setBusyAction("episode-optimize");
    setActionMessage(null);
    try {
      const res = await platformFetch(`/api/episodes/${selectedEpisode.id}/optimize`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          instruction: episodeOptimizeInstruction,
          llmModel: selectedLlmModel,
        }),
      });
      const payload = (await res.json()) as {
        scriptTxt?: string;
        error?: string;
        jobId?: string;
        status?: string;
      };
      if (!res.ok) throw new Error(payload.error ?? "AI 优化失败");
      if (payload.scriptTxt) {
        setImpactDraft(payload.scriptTxt);
      }
      await loadProjectData();
      setPollKey((value) => value + 1);
      setActionMessage(
        payload.status === "queued"
          ? `第 ${selectedEpisode.epNum} 集已进入 AI 优化队列，完成后页面会自动更新`
          : `第 ${selectedEpisode.epNum} 集已完成 AI 优化，状态已标记为待复核`
      );
    } catch (error) {
      setActionMessage(error instanceof Error ? error.message : String(error));
    } finally {
      setBusyAction(null);
    }
  }

  return (
    <section className="page-shell round-page">
      <header className="round-control-hero">
        <div className="round-control-main">
          <div className="round-title-row">
            <h1 className="round-project-title">{data.project.name}</h1>
            <div className="round-title-meta">
              <span>{projectStageLabel}</span>
              <span>Round {roundNum}</span>
              <span>{round?.epRange ?? "等待轮次"}</span>
              <span>{platformSession.tenantSlug}</span>
              {(projectPaused || projectQualityGate || runAllEnabled) && (
                <Badge
                  variant="outline"
                  className={projectStatusBadgeClassName}
                >
                  {runAllEnabled ? "批量运行中" : projectStatusLabel}
                </Badge>
              )}
            </div>
          </div>
          <div className="round-control-strip" aria-label="项目控制栏">
            <label className="round-episode-switch">
              <span>当前查看</span>
              <select
                value={selectedEpisode?.epNum ?? ""}
                onChange={(event) => setSelectedEpisodeNum(Number(event.target.value))}
                aria-label="切换当前剧集"
              >
                {eps.map((episode) => (
                  <option key={episode.id} value={episode.epNum}>
                    E{String(episode.epNum).padStart(2, "0")} · {extractEpisodeTitle(episode)}
                  </option>
                ))}
              </select>
            </label>
            <button
              type="button"
              className="round-control-chip"
              data-active={topDrawer === "episodes"}
              onClick={() => setFilterAndDrawer("all", "episodes")}
            >
              <ListVideo className="size-4" />
              <span>轮次进度</span>
              <strong>{visibleEpisodeCount}/{expectedEpisodeCount}</strong>
            </button>
            <button
              type="button"
              className="round-control-chip"
              data-active={topDrawer === "quality"}
              onClick={() => toggleTopDrawer("quality")}
            >
              <Gauge className="size-4" />
              <span>质量门禁</span>
              <strong>{roundGateScore != null ? roundGateScore.toFixed(1) : "-"}</strong>
            </button>
            <button
              type="button"
              className="round-control-chip"
              data-tone={reviewEpisodeCount + unresolvedIssueCount > 0 ? "warning" : "neutral"}
              data-active={topDrawer === "issues" || episodeStatusFilter === "review"}
              onClick={() => setFilterAndDrawer("review", "issues")}
            >
              <AlertCircle className="size-4" />
              <span>待复核</span>
              <strong>{reviewEpisodeCount + unresolvedIssueCount}</strong>
            </button>
            {activeEpisodeCount > 0 && (
              <button
                type="button"
                className="round-control-chip"
                data-active={episodeStatusFilter === "active"}
                onClick={() => setFilterAndDrawer("active", "episodes")}
              >
                <Activity className="size-4" />
                <span>运行中</span>
                <strong>{activeEpisodeCount}</strong>
              </button>
            )}
          </div>
        </div>
        <div className="round-control-actions">
          {reachedTarget || projectDone ? (
            <Button size="sm" asChild>
              <Link href={`/projects/${projectId}/complete`}>
                <PackageCheck className="size-4" />
                {primaryActionLabel}
              </Link>
            </Button>
          ) : latestRoundDone && !projectPaused && !runAllEnabled ? (
            <Button
              size="sm"
              disabled={busyAction === "next-round"}
              onClick={nextRound}
            >
              <Play className="size-4" />
              {busyAction === "next-round" ? "启动中" : primaryActionLabel}
            </Button>
          ) : runAllEnabled ? (
            <Button
              variant="outline"
              size="sm"
              disabled={busyAction !== null}
              onClick={() => controlProject("stop_run_all")}
            >
              <Pause className="size-4" />
              {busyAction === "project-stop_run_all" ? "处理中" : primaryActionLabel}
            </Button>
          ) : (
            <Button
              size="sm"
              disabled={busyAction !== null || projectDone || reachedTarget}
              onClick={() => controlProject("run_all")}
            >
              <Play className="size-4" />
              {busyAction === "project-run_all" ? "启动中" : primaryActionLabel}
            </Button>
          )}
          {projectPaused ? (
            <Button
              variant="outline"
              size="sm"
              disabled={busyAction !== null}
              onClick={() => controlProject("resume")}
            >
              <Play className="size-4" />
              {busyAction === "project-resume" ? "处理中" : "继续项目"}
            </Button>
          ) : (
            <Button
              variant="outline"
              size="sm"
              disabled={busyAction !== null || projectDone}
              onClick={() => controlProject("pause")}
            >
              <Pause className="size-4" />
              {busyAction === "project-pause" ? "处理中" : "暂停项目"}
            </Button>
          )}
          <Button
            variant="outline"
            size="sm"
            disabled={busyAction !== null}
            onClick={cloneProject}
          >
            <Copy className="size-4" />
            {busyAction === "clone" ? "复制中" : "复制项目"}
          </Button>
          <ProjectManageButton
            projectId={projectId}
            projectName={data.project.name}
            targetEpisodeCount={data.project.targetEpisodeCount}
            status={data.project.status}
            deleteRedirectHref="/"
            onUpdated={() => {
              void loadProjectData();
            }}
          />
        </div>
      </header>

      {topDrawer && (
        <section className="round-top-drawer" aria-label="控制栏详情">
          {topDrawer === "episodes" && (
            <>
              <div className="round-top-drawer-head">
                <strong>剧集状态</strong>
                <span>点击左侧剧集列表可直接定位；筛选只影响列表显示。</span>
              </div>
              <div className="round-top-drawer-grid">
                <button
                  type="button"
                  className="round-top-drawer-card"
                  data-active={episodeStatusFilter === "all"}
                  onClick={() => setEpisodeStatusFilter("all")}
                >
                  <span>全部</span>
                  <strong>{eps.length}</strong>
                </button>
                <button
                  type="button"
                  className="round-top-drawer-card"
                  data-active={episodeStatusFilter === "active"}
                  onClick={() => setEpisodeStatusFilter("active")}
                >
                  <span>运行/排队</span>
                  <strong>{activeEpisodeCount}</strong>
                </button>
                <button
                  type="button"
                  className="round-top-drawer-card"
                  data-active={episodeStatusFilter === "review"}
                  onClick={() => setEpisodeStatusFilter("review")}
                >
                  <span>待复核</span>
                  <strong>{reviewEpisodeCount}</strong>
                </button>
                <button
                  type="button"
                  className="round-top-drawer-card"
                  data-active={episodeStatusFilter === "issue"}
                  onClick={() => setEpisodeStatusFilter("issue")}
                >
                  <span>异常</span>
                  <strong>{issueEpisodeCount}</strong>
                </button>
              </div>
            </>
          )}
          {topDrawer === "quality" && (
            <>
              <div className="round-top-drawer-head">
                <strong>质量报告</strong>
                <span>
                  {qualityStatusLabel} · Worker {workerStatusLabel} · 源文{" "}
                  {sourceDisplayScore != null ? sourceDisplayScore.toFixed(1) : "-"}
                </span>
              </div>
              <div className="round-top-score-grid">
                {scoreEntries.map((score) => (
                  <div key={score.key} className="round-top-score">
                    <span>{score.label}</span>
                    <Progress value={score.value * 10} />
                    <strong>{score.value}</strong>
                  </div>
                ))}
              </div>
              {attentionItems.length > 0 && (
                <div className="round-top-issues">
                  {attentionItems.slice(0, 4).map((item) => (
                    <Badge key={item} variant="outline">
                      {item}
                    </Badge>
                  ))}
                </div>
              )}
            </>
          )}
          {topDrawer === "issues" && (
            <>
              <div className="round-top-drawer-head">
                <strong>待处理入口</strong>
                <span>{nextActionHint}</span>
              </div>
              <div className="round-top-drawer-grid">
                <button
                  type="button"
                  className="round-top-drawer-card"
                  data-active={episodeStatusFilter === "review"}
                  onClick={() => setEpisodeStatusFilter("review")}
                >
                  <span>待复核剧集</span>
                  <strong>{reviewEpisodeCount}</strong>
                </button>
                <button
                  type="button"
                  className="round-top-drawer-card"
                  data-active={episodeStatusFilter === "issue"}
                  onClick={() => setEpisodeStatusFilter("issue")}
                >
                  <span>异常剧集</span>
                  <strong>{issueEpisodeCount}</strong>
                </button>
                <button
                  type="button"
                  className="round-top-drawer-card"
                  onClick={() => toggleTopDrawer("quality")}
                >
                  <span>门禁问题</span>
                  <strong>{blockingIssueCount + advisoryIssueCount}</strong>
                </button>
              </div>
            </>
          )}
        </section>
      )}

      {actionMessage && (
        <div className="status-line round-action-message">{actionMessage}</div>
      )}

      <section className="round-workbench">
        <Card className="round-episode-panel">
          <div className="round-panel-head">
            <div>
              <div className="round-panel-title">
                <ListVideo className="size-4" />
                全集
              </div>
              <div className="round-panel-sub">
                {episodeStatusFilter === "all"
                  ? `全剧已输出 ${visibleEpisodeCount}/${expectedEpisodeCount} 集`
                  : `已筛选 ${filteredEpisodes.length}/${eps.length} 集`}
              </div>
            </div>
            <Badge variant="outline">{episodeProgress}%</Badge>
          </div>
          <Progress value={episodeProgress} />
          {eps.length === 0 ? (
            <div className="round-empty">
              <ScrollText className="size-5" />
              worker 开始写出单集后会显示在这里
            </div>
          ) : (
            <div className="round-episode-list">
              {filteredEpisodes.length === 0 && (
                <div className="round-filter-empty">
                  当前筛选下没有剧集
                  <button type="button" onClick={() => setEpisodeStatusFilter("all")}>
                    查看全部
                  </button>
                </div>
              )}
              {filteredEpisodes.map((ep) => {
                const selected = selectedEpisode?.id === ep.id;
                const display = episodeDisplay(ep);
                return (
                  <button
                    key={ep.id}
                    type="button"
                    className="round-episode-item"
                    data-selected={selected}
                    data-tone={display.tone}
                    onClick={() => setSelectedEpisodeNum(ep.epNum)}
                  >
                    <span className="round-episode-index">
                      E{String(ep.epNum).padStart(2, "0")}
                    </span>
                    <span className="round-episode-copy">
                      <span className="round-episode-title">
                        {extractEpisodeTitle(ep)}
                      </span>
                      <span className="round-episode-meta">
                        {display.label}
                        {ep.score != null ? ` · ${ep.score.toFixed(1)} 分` : ""}
                        {ep.retryCount > 0 ? ` · 重试 ${ep.retryCount}` : ""}
                      </span>
                    </span>
                  </button>
                );
              })}
            </div>
          )}
        </Card>

        <Card className="round-script-panel">
          <div className="round-script-head">
            <div className="min-w-0">
              <div className="round-script-kicker">当前剧本</div>
              <h2>{selectedTitle}</h2>
              {selectedEpisode && selectedEpisodeDisplay && (
                <div className="round-script-meta">
                  <Badge
                    variant={selectedEpisodeDisplay.badgeVariant}
                    className={selectedEpisodeDisplay.badgeClassName}
                  >
                    {selectedEpisodeDisplay.label}
                  </Badge>
                  {selectedEpisode.score != null && (
                    <span>{selectedEpisode.score.toFixed(1)} 分</span>
                  )}
                  <span>{scriptLineCount(selectedEpisode)} 行</span>
                </div>
              )}
            </div>
            <div className="round-script-actions">
              <Button
                variant="outline"
                size="sm"
                disabled={!selectedEpisode?.scriptTxt || busyAction !== null}
                onClick={optimizeSelectedEpisode}
              >
                <Sparkles className="size-4" />
                {busyAction === "episode-optimize" ? "优化中" : "AI优化"}
              </Button>
              <Button
                variant="outline"
                size="sm"
                disabled={!selectedEpisode?.scriptTxt}
                onClick={copySelectedScript}
              >
                <Copy className="size-4" />
                复制脚本
              </Button>
            </div>
          </div>

          {selectedEpisode?.scriptTxt && (
            <div className="round-optimize-box">
              <label htmlFor="episode-optimize-instruction">
                AI 修改意见
              </label>
              <textarea
                id="episode-optimize-instruction"
                className="round-optimize-input"
                value={episodeOptimizeInstruction}
                onChange={(event) =>
                  setEpisodeOptimizeInstruction(event.target.value)
                }
                placeholder="例如：强化第3场情绪递进，镜头更细，女主台词更克制，不改变前后剧情。"
              />
            </div>
          )}

          {selectedEpisode?.scriptTxt ? (
            <pre className="round-script-reader">{selectedEpisode.scriptTxt}</pre>
          ) : (
            <div className="round-script-empty">
              <FileText className="size-8" />
              <div>
                <h3>还没有可展示的正片脚本</h3>
                <p>任务运行中时，这里会在单集写入后自动出现内容。</p>
              </div>
            </div>
          )}

          {selectedEpisode && (
            <div className="round-impact-box">
              <div className="round-impact-head">
                <div>
                  <div className="round-panel-title">
                    <GitCompareArrows className="size-4" />
                    编辑影响
                  </div>
                  <p>粘贴运营改过的当前集脚本，系统会保存为新基准，并优化后续开头承接和全局剧情点。</p>
                </div>
                <Button
                  variant="outline"
                  size="sm"
                  disabled={busyAction !== null}
                  onClick={analyzeImpact}
                >
                  <GitCompareArrows className="size-4" />
                  {busyAction === "impact" ? "处理中" : "应用并分析"}
                </Button>
              </div>
              <textarea
                className="round-impact-editor"
                value={impactDraft}
                onChange={(event) => setImpactDraft(event.target.value)}
                aria-label="编辑后的当前集脚本"
              />
              {impactReport && (
                <div className="round-impact-report">
                  <div className="round-impact-summary">
                    <Badge variant={impactReport.changed ? "outline" : "default"}>
                      {impactReport.changed ? "有改动" : "无改动"}
                    </Badge>
                    <span>{impactReport.changeSummary}</span>
                  </div>
                  <div className="round-impact-action">
                    {impactReport.recommendedAction}
                  </div>
                  {impactReport.applied && (
                    <div className="round-impact-action">
                      已保存当前集改稿为新基准；后续轮次会按这版剧情承接。
                    </div>
                  )}
                  {impactReport.optimizedEpisodes?.length ? (
                    <div className="round-impact-list">
                      {impactReport.optimizedEpisodes.map((item) => (
                        <div key={`${item.id}-${item.status}`} className="round-impact-item">
                          <b>E{String(item.epNum).padStart(2, "0")}</b>
                          <span>
                            {item.status === "optimized"
                              ? "已优化承接"
                              : item.status === "failed"
                                ? `优化失败：${item.message}`
                                : item.message}
                          </span>
                        </div>
                      ))}
                    </div>
                  ) : null}
                  {impactReport.continuityInstruction && (
                    <div className="round-impact-action">
                      {impactReport.continuityInstruction}
                    </div>
                  )}
                  {impactReport.impactedEpisodes.length > 0 && (
                    <div className="round-impact-list">
                      {impactReport.impactedEpisodes.map((item) => (
                        <div key={item.id} className="round-impact-item">
                          <b>E{String(item.epNum).padStart(2, "0")}</b>
                          <span>{item.reason}</span>
                        </div>
                      ))}
                    </div>
                  )}
                  {impactReport.impactedState.length > 0 && (
                    <div className="round-impact-state">
                      {impactReport.impactedState.slice(0, 6).map((item) => (
                        <Badge key={item} variant="outline">
                          {item}
                        </Badge>
                      ))}
                    </div>
                  )}
                  {impactReport.warnings.length > 0 && (
                    <div className="round-impact-state">
                      <Badge variant="outline">
                        warning {impactReport.warnings.length}
                      </Badge>
                    </div>
                  )}
                </div>
              )}
            </div>
          )}
        </Card>

        <aside className="round-inspector">
          <section className="round-side-panel round-next-panel">
            <div className="round-panel-title">
              <Play className="size-4" />
              下一步
            </div>
            <div className="round-next-copy">
              <strong>{nextActionHint}</strong>
              <span>
                {attentionItems.length > 0
                  ? attentionItems.join(" · ")
                  : `当前 ${projectStageLabel}，可继续查看或导出已有剧集。`}
              </span>
            </div>
            {latestRoundDone &&
              !projectDone &&
              !reachedTarget &&
              !projectPaused && (
                <Button
                  className="w-full"
                  onClick={nextRound}
                  disabled={busyAction === "next-round"}
                >
                  <Play className="size-4" />
                  {busyAction === "next-round"
                    ? "启动中"
                    : `开始第 ${nextRoundNum} 轮`}
                </Button>
              )}
            {roundJob?.retryable && (
              <Button
                variant="outline"
                className="w-full"
                disabled={busyAction !== null}
                onClick={() => retryJob(roundJob.id)}
              >
                <RefreshCw className="size-4" />
                {busyAction === `retry-${roundJob.id}` ? "处理中" : "重试当前任务"}
              </Button>
            )}
            {(projectDone || reachedTarget) && (
              <Button className="w-full" asChild>
                <Link href={`/projects/${projectId}/complete`}>
                  <PackageCheck className="size-4" />
                  项目完成
                </Link>
              </Button>
            )}
            <details className="round-inline-details">
              <summary>运行设置</summary>
              <div className="round-control-grid">
                <select
                  value={selectedEpisodesPerRound}
                  onChange={(event) => setSelectedEpisodesPerRound(event.target.value)}
                  className="form-select"
                  aria-label="本轮生成集数"
                >
                  {episodeCountOptions.map((count) => (
                    <option key={count} value={count}>
                      本轮 {count} 集
                    </option>
                  ))}
                </select>
                <select
                  value={selectedRepairBudget}
                  onChange={(event) => setSelectedRepairBudget(event.target.value)}
                  className="form-select"
                  aria-label="修复预算"
                >
                  {repairBudgetOptions.map((option) => (
                    <option key={option.value} value={option.value}>
                      {option.label}
                    </option>
                  ))}
                </select>
                <select
                  value={selectedLlmModel}
                  onChange={(event) => setSelectedLlmModel(event.target.value)}
                  className="form-select"
                  aria-label="生成模型"
                >
                  {llmModelOptions.map((option) => (
                    <option key={option.value} value={option.value}>
                      {option.label}
                    </option>
                  ))}
                </select>
                <Button variant="outline" className="w-full" asChild>
                  <Link href={`/projects/${projectId}/bible`}>系统 Bible</Link>
                </Button>
              </div>
            </details>
          </section>

          <section className="round-side-panel">
            <div className="round-panel-title">
              <Activity className="size-4" />
              Worker
            </div>
            {roundJob ? (
              <>
                <div className="round-job-row">
                  <div>
                    <div className="round-job-title">{roundJob.title}</div>
                    <div className="round-muted">
                      {roundJob.message ?? "等待状态更新"}
                    </div>
                  </div>
                  <Badge
                    variant={
                      roundJob.status === "failed" || roundJob.isStale
                        ? "destructive"
                        : "outline"
                    }
                  >
                    {jobLabel(roundJob)}
                  </Badge>
                </div>
                <Progress value={roundJob.progress} />
                <div className="round-job-foot">
                  <span>{roundJob.progress}%</span>
                  <span>{new Date(roundJob.updatedAt).toLocaleString()}</span>
                </div>
                {roundJob.retryable && (
                  <Button
                    variant="outline"
                    size="sm"
                    disabled={busyAction !== null}
                    onClick={() => retryJob(roundJob.id)}
                  >
                    <RefreshCw className="size-4" />
                    {busyAction === `retry-${roundJob.id}`
                      ? "处理中"
                      : roundJob.isStale
                        ? "恢复队列"
                        : "重试任务"}
                  </Button>
                )}
                {roundJob.errorText && (
                  <div className="round-error">
                    <AlertCircle className="size-4" />
                    {roundJob.errorText}
                  </div>
                )}
                {(roundJob.statusReason || roundJob.operatorHint) && (
                  <div className="round-error round-warning">
                    <AlertCircle className="size-4" />
                    <span>
                      {roundJob.statusReason}
                      {roundJob.operatorHint ? ` · ${roundJob.operatorHint}` : ""}
                    </span>
                  </div>
                )}
              </>
            ) : (
              <div className="round-muted">暂无任务记录</div>
            )}
          </section>

          {quality && (
            <section className="round-side-panel">
              <div className="round-panel-title">
                <Gauge className="size-4" />
                质量门禁
              </div>
              <div className="round-quality-head">
                <Badge
                  variant={quality.status === "usable" ? "default" : "outline"}
                  className={qualityBadgeClassName}
                >
                  {qualityStatusText(quality.status)}
                </Badge>
                {roundGateScore != null && (
                  <strong>{roundGateScore.toFixed(1)}</strong>
                )}
              </div>
              <div className="round-score-list">
                {creativeQualityScore != null && (
                  <div className="round-score-row">
                    <span>创作</span>
                    <div className="round-score-track">
                      <span
                        style={{
                          width: `${Math.min(creativeQualityScore * 10, 100)}%`,
                        }}
                      />
                    </div>
                    <b>{creativeQualityScore.toFixed(1)}</b>
                  </div>
                )}
                {scoreEntries.map((score) => (
                  <div key={score.key} className="round-score-row">
                    <span>{score.label}</span>
                    <div className="round-score-track">
                      <span style={{ width: `${Math.min(score.value * 10, 100)}%` }} />
                    </div>
                    <b>{score.value}</b>
                  </div>
                ))}
                {sourceDisplayScore != null && (
                  <div className="round-score-row">
                    <span>源文门禁</span>
                    <div className="round-score-track">
                      <span
                        style={{
                          width: `${Math.min(sourceDisplayScore * 10, 100)}%`,
                        }}
                      />
                    </div>
                    <b>{sourceDisplayScore}</b>
                  </div>
                )}
                {adaptationQuality?.continuity && (
                  <div className="round-score-row">
                    <span>承接</span>
                    <div className="round-score-track">
                      <span
                        style={{
                          width: `${Math.min(
                            adaptationQuality.continuity.score,
                            100
                          )}%`,
                        }}
                      />
                    </div>
                    <b>{adaptationQuality.continuity.score}</b>
                  </div>
                )}
              </div>
            </section>
          )}

          {hasGenerationMetrics && (
            <details className="round-side-panel round-collapsible-panel">
              <summary className="round-panel-title">
                <Cpu className="size-4" />
                运行数据
              </summary>
              <div className="round-mini-metrics">
                <div>
                  <Clock3 className="size-4" />
                  <span>耗时</span>
                  <strong>{formatDuration(runtimeMs)}</strong>
                </div>
                <div>
                  <Cpu className="size-4" />
                  <span>LLM</span>
                  <strong>{formatNumber(llmCalls)}</strong>
                </div>
                <div>
                  <FileText className="size-4" />
                  <span>Token</span>
                  <strong>{formatNumber(totalTokens)}</strong>
                </div>
              </div>
              {runtime?.llm_calls?.length ? (
                <div className="round-mini-metrics">
                  <div>
                    <FileText className="size-4" />
                    <span>Input</span>
                    <strong>{formatNumber(tokenSummary.inputTokens)}</strong>
                  </div>
                  <div>
                    <FileText className="size-4" />
                    <span>Output</span>
                    <strong>{formatNumber(tokenSummary.outputTokens)}</strong>
                  </div>
                  <div>
                    <Gauge className="size-4" />
                    <span>估算成本</span>
                    <strong>{formatUsd(tokenSummary.estimatedUsd)}</strong>
                  </div>
                </div>
              ) : null}
              <div className="round-hook-list">
                <Badge variant="outline">
                  {llmModelLabel(runtime?.llm_model ?? jobResult?.llmModel ?? selectedLlmModel)}
                </Badge>
                <Badge variant="outline">
                  {runtime?.generation_variant ?? jobResult?.generationVariant ?? "drama_engine_first"}
                </Badge>
                <Badge variant="outline">
                  repair {runtime?.repair_budget ?? jobResult?.repairBudget ?? "episode"}
                </Badge>
                {jobResult?.episodesPerRound ? (
                  <Badge variant="outline">{jobResult.episodesPerRound}集/轮</Badge>
                ) : null}
                {slowestStage ? (
                  <Badge variant="outline">
                    最慢 {slowestStage.name} · {formatDuration(slowestStage.duration_ms)}
                  </Badge>
                ) : null}
              </div>
            </details>
          )}

          {(methodologyCards.length > 0 || sourceStrength || methodologyContext) && (
            <details className="round-side-panel round-collapsible-panel">
              <summary className="round-panel-title">
                <ScrollText className="size-4" />
                方法论复盘
              </summary>
              <div className="round-mini-metrics">
                <div>
                  <Gauge className="size-4" />
                  <span>源文</span>
                  <strong>
                    {sourceStrength?.overall_level ??
                      methodologyContext?.source_strength_level ??
                      jobResult?.sourceStrength ??
                      "-"}
                  </strong>
                </div>
                <div>
                  <GitCompareArrows className="size-4" />
                  <span>改编</span>
                  <strong>
                    {sourceStrength?.recommended_intensity ??
                      methodologyContext?.adaptation_intensity ??
                      jobResult?.adaptationIntensity ??
                      "-"}
                  </strong>
                </div>
                <div>
                  <ScrollText className="size-4" />
                  <span>卡片</span>
                  <strong>{methodologyCards.length}</strong>
                </div>
              </div>
              {methodologyCards.length > 0 && (
                <div className="round-hook-list">
                  {methodologyCards.slice(0, 6).map((card) => (
                    <Badge key={card.id} variant="outline">
                      {card.name}
                    </Badge>
                  ))}
                </div>
              )}
            </details>
          )}

          {context && (
            <details className="round-side-panel round-collapsible-panel">
              <summary className="round-panel-title">
                <CheckCircle2 className="size-4" />
                状态承接
              </summary>
              <div className="round-context-current">
                当前到第 {storyLedger?.current_episode ?? context.current_episode} 集
              </div>
              {storyLedger && (
                <div className="round-ledger-metrics">
                  <span>台账 {storyLedger.entries.length} 条</span>
                  <span>warning {storyLedger.warnings.length}</span>
                </div>
              )}
              {context.open_hooks.length > 0 && (
                <div className="round-hook-list">
                  {context.open_hooks.slice(0, 4).map((hook) => (
                    <Badge key={hook} variant="outline">
                      {hook}
                    </Badge>
                  ))}
                </div>
              )}
            </details>
          )}

          {round?.status === "done" && (
            <details className="round-side-panel round-collapsible-panel">
              <summary className="round-panel-title">
                <PackageCheck className="size-4" />
                交付工具
              </summary>
              <div className="round-control-grid">
                <Button
                  variant="outline"
                  size="sm"
                  disabled={busyAction !== null}
                  onClick={() => downloadNovelExport("txt")}
                >
                  <Download className="size-4" />
                  {busyAction === "novel-export-txt" ? "导出中" : "TXT"}
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  disabled={busyAction !== null}
                  onClick={() => downloadNovelExport("word")}
                >
                  <Download className="size-4" />
                  {busyAction === "novel-export-word" ? "导出中" : "Word"}
                </Button>
              </div>
              <Button
                variant="outline"
                size="sm"
                className="w-full"
                disabled={busyAction === "video"}
                onClick={() => runAction("video", exportVideoBrief)}
              >
                <Video className="size-4" />
                生成视频 brief
              </Button>
              <div className="round-control-grid">
                <select
                  value={selectedProfile}
                  onChange={(event) => setSelectedProfile(event.target.value)}
                  className="form-select"
                  aria-label="本地化 profile"
                >
                  {profiles.map((profile) => (
                    <option key={profile.id} value={profile.id}>
                      {profile.label}
                    </option>
                  ))}
                </select>
                <Button
                  variant="outline"
                  size="sm"
                  disabled={busyAction === "localization"}
                  onClick={() => runAction("localization", exportLocalization)}
                >
                  <Languages className="size-4" />
                  本地化
                </Button>
              </div>
              <Button
                variant="outline"
                size="sm"
                className="w-full"
                disabled={busyAction === "delivery"}
                onClick={() => runAction("delivery", checkDelivery)}
              >
                <PackageCheck className="size-4" />
                交付预检
              </Button>
              <Button
                variant="outline"
                size="sm"
                className="w-full"
                disabled={busyAction === "delivery-export"}
                onClick={() => runAction("delivery-export", exportDeliveryPackage)}
              >
                <Download className="size-4" />
                导出交付包
              </Button>
            </details>
          )}
        </aside>
      </section>

      {delivery && (
        <Card className="round-delivery-panel">
          <div className="round-panel-head">
            <div className="round-panel-title">
              <PackageCheck className="size-4" />
              交付预检
            </div>
            <Badge variant={delivery.ready ? "default" : "destructive"}>
              {delivery.ready ? "ready" : "warning"}
            </Badge>
          </div>
          <div className="round-delivery-grid">
            {delivery.files.slice(0, 12).map((file) => (
              <div key={file.path} className="round-delivery-file">
                <span>{file.path}</span>
                <b>{file.bytes} bytes</b>
              </div>
            ))}
            {delivery.files.length > 12 && (
              <div className="round-muted">
                还有 {delivery.files.length - 12} 个文件会进入交付包
              </div>
            )}
          </div>
          {delivery.warnings.length > 0 && (
            <div className="round-hook-list">
              <Badge variant="outline">warning {delivery.warnings.length}</Badge>
            </div>
          )}
        </Card>
      )}
    </section>
  );
}
