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
  Video,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import type { EngineJob } from "@/lib/engine-types";
import type { EditImpactReport } from "@/lib/edit-impact";

type Project = {
  id: string;
  name: string;
  targetEpisodeCount: number;
  status: string;
  metaJson?: string | null;
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
  };
};

const generationVariantOptions = [
  { value: "drama_engine_first", label: "强剧情优先" },
  { value: "sop_full_stack", label: "SOP 全链路（慢速精修）" },
];

const repairBudgetOptions = [
  { value: "episode", label: "逐集修复" },
  { value: "rewrite", label: "改写一次" },
  { value: "none", label: "不自动修复" },
];

const episodeCountOptions = [1, 2, 3, 4, 5];

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
      badgeClassName: "border-amber-200 bg-amber-50 text-amber-700",
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
  const latestByEpisode = new Map<number, Episode>();
  for (const episode of episodes) {
    const current = latestByEpisode.get(episode.epNum);
    const episodeRound = roundNumberById.get(episode.roundId) ?? 0;
    const currentRound = current ? (roundNumberById.get(current.roundId) ?? 0) : -1;
    if (!current || episodeRound >= currentRound) {
      latestByEpisode.set(episode.epNum, episode);
    }
  }
  return [...latestByEpisode.values()].sort((a, b) => a.epNum - b.epNum);
}

function visibleScriptCount(episodes: Episode[]): number {
  return episodes.filter((episode) => episode.scriptTxt).length;
}

function shouldShowFullSeries(project: Project, episodes: Episode[]): boolean {
  const runAllEnabled = parseProjectMeta(project).control?.runAll?.enabled === true;
  return (
    runAllEnabled ||
    project.status === "done" ||
    visibleScriptCount(episodes) >= project.targetEpisodeCount
  );
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
  if (shouldShowFullSeries(data.project, fullSeriesEpisodes(data.episodes, data.rounds))) {
    return false;
  }
  const runAllEnabled = parseProjectMeta(data.project).control?.runAll?.enabled === true;
  if (runAllEnabled && data.project.status === "running") return true;
  return currentRound?.status !== "done";
}

export function RoundClient({
  projectId,
  roundNum,
  project,
}: {
  projectId: string;
  roundNum: number;
  project: Project;
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
  const [selectedGenerationVariant, setSelectedGenerationVariant] =
    useState("drama_engine_first");
  const [selectedRepairBudget, setSelectedRepairBudget] = useState("episode");
  const [selectedEpisodesPerRound, setSelectedEpisodesPerRound] = useState("5");
  const [impactDraft, setImpactDraft] = useState("");
  const [impactReport, setImpactReport] = useState<EditImpactReport | null>(null);

  async function loadProjectData(): Promise<ProjectPayload> {
    const res = await fetch(`/api/projects/${projectId}`);
    const d = (await res.json()) as ProjectPayload & { error?: string };
    if (!res.ok) throw new Error(d.error ?? "项目状态加载失败");
    setData(d);
    return d;
  }

  useEffect(() => {
    let stopped = false;
    async function poll() {
      while (!stopped) {
        const d = await loadProjectData();
        if (!shouldKeepPollingProject(d, roundNum)) {
          break;
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
      const res = await fetch(`/api/projects/${projectId}/localization`);
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
    const currentRound = data.rounds.find((item) => item.roundNum === roundNum);
    const projectEpisodes = fullSeriesEpisodes(data.episodes, data.rounds);
    const candidateEpisodes = shouldShowFullSeries(data.project, projectEpisodes)
      ? projectEpisodes
      : data.episodes
          .filter((episode) => episode.roundId === currentRound?.id)
          .sort((a, b) => a.epNum - b.epNum);
    if (candidateEpisodes.length === 0) return;
    if (!candidateEpisodes.some((episode) => episode.epNum === selectedEpisodeNum)) {
      setSelectedEpisodeNum(candidateEpisodes[0].epNum);
    }
  }, [data, roundNum, selectedEpisodeNum]);

  useEffect(() => {
    if (!data) return;
    const currentRound = data.rounds.find((item) => item.roundNum === roundNum);
    const projectEpisodes = fullSeriesEpisodes(data.episodes, data.rounds);
    const candidateEpisodes = shouldShowFullSeries(data.project, projectEpisodes)
      ? projectEpisodes
      : data.episodes.filter((episode) => episode.roundId === currentRound?.id);
    const currentEpisode =
      candidateEpisodes.find((episode) => episode.epNum === selectedEpisodeNum) ?? null;
    setImpactDraft(currentEpisode?.scriptTxt ?? "");
    setImpactReport(null);
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
  const storyLedger = summary?.story_state_ledger;
  const sourceStrength = summary?.source_strength_profile;
  const methodologyContext = summary?.methodology_context;
  const methodologyQuality = summary?.methodology_quality_report;
  const roundEpisodes = data.episodes
    .filter((e) => e.roundId === round?.id)
    .sort((a, b) => a.epNum - b.epNum);
  const projectEpisodes = fullSeriesEpisodes(data.episodes, data.rounds);
  const fullSeriesMode = shouldShowFullSeries(data.project, projectEpisodes);
  const eps = fullSeriesMode ? projectEpisodes : roundEpisodes;
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
  const roundJob = fullSeriesMode
    ? (activeOrLatestJob(data.jobs) ?? currentRoundJob)
    : currentRoundJob;
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
  const runAllEnabled =
    parseProjectMeta(data.project).control?.runAll?.enabled === true && !projectDone;
  const reachedTarget =
    (context?.current_episode ?? 0) >= data.project.targetEpisodeCount ||
    visibleScriptCount(projectEpisodes) >= data.project.targetEpisodeCount;
  const expectedEpisodeCount =
    fullSeriesMode
      ? data.project.targetEpisodeCount
      : episodeCountFromRange(round?.epRange) ?? Math.max(eps.length, 1);
  const visibleEpisodeCount = visibleScriptCount(eps);
  const episodeProgress = Math.round(
    (visibleEpisodeCount / Math.max(expectedEpisodeCount, 1)) * 100
  );
  const qualityAverage = quality
    ? Object.values(quality.scores).reduce((sum, value) => sum + value, 0) /
      Math.max(Object.values(quality.scores).length, 1)
    : null;
  const selectedEpisodeCode = selectedEpisode
    ? `E${String(selectedEpisode.epNum).padStart(2, "0")}`
    : "E--";
  const qualityStatusLabel = qualityStatusText(quality?.status);
  const qualityBadgeClassName =
    quality?.status === "needs_human_review"
      ? "border-amber-200 bg-amber-50 text-amber-700"
      : undefined;
  const workerStatusLabel = roundJob ? jobLabel(roundJob) : "暂无任务";
  const hasGenerationMetrics =
    runtime || jobResult?.runtimeMs != null || jobResult?.llmCalls != null;
  const exportProjectName = data.project.name || project.name || "novel-to-drama";
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
  const methodologyIssuePreview = methodologyQuality?.issues.slice(0, 4) ?? [];

  const scoreEntries = quality
    ? Object.entries(quality.scores).map(([key, value]) => ({
        key,
        label: qualityLabels[key] ?? key,
        value,
      }))
    : [];
  const issuePreview = quality?.blocking_issues.slice(0, 5) ?? [];
  const hiddenIssueCount = Math.max(
    (quality?.blocking_issues.length ?? 0) - issuePreview.length,
    0
  );
  const adaptationIssuePreview = [
    ...(adaptationQuality?.blocking_warnings ?? []),
    ...(adaptationQuality?.advisory_warnings ?? []),
  ].slice(0, 4);

  async function nextRound() {
    setBusyAction("next-round");
    setActionMessage(null);
    try {
      const res = await fetch(`/api/projects/${projectId}/rounds/start`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          generationVariant: selectedGenerationVariant,
          repairBudget: selectedRepairBudget,
          episodesPerRound: Number(selectedEpisodesPerRound),
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
      const res = await fetch(`/api/jobs/${jobId}/retry`, { method: "POST" });
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
      const res = await fetch(`/api/projects/${projectId}/clone`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          generationVariant: selectedGenerationVariant,
          repairBudget: selectedRepairBudget,
          episodesPerRound: Number(selectedEpisodesPerRound),
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
      const res = await fetch(`/api/projects/${projectId}/control`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          action,
          generationVariant: selectedGenerationVariant,
          repairBudget: selectedRepairBudget,
          episodesPerRound: action === "run_all" ? 5 : Number(selectedEpisodesPerRound),
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
    const res = await fetch(`/api/projects/${projectId}/delivery?round=${roundNum}`);
    if (!res.ok) throw new Error(await res.text());
    const report = (await res.json()) as DeliveryPreflight;
    setDelivery(report);
    return report.ready ? "交付预检通过" : "交付预检有 warning";
  }

  async function exportVideoBrief() {
    const res = await fetch(`/api/projects/${projectId}/video-brief?round=${roundNum}`, {
      method: "POST",
    });
    if (!res.ok) throw new Error(await res.text());
    await checkDelivery();
    return "视频 brief 已生成";
  }

  async function exportLocalization() {
    const res = await fetch(
      `/api/projects/${projectId}/localization?round=${roundNum}&profile=${selectedProfile}`,
      { method: "POST" }
    );
    if (!res.ok) throw new Error(await res.text());
    await checkDelivery();
    const profile = profiles.find((item) => item.id === selectedProfile);
    return `${profile?.label ?? selectedProfile} 本地化包已生成`;
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
      const res = await fetch(
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
      const res = await fetch(`/api/episodes/${selectedEpisode.id}/impact`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ editedScriptText: impactDraft }),
      });
      const payload = (await res.json()) as EditImpactReport & { error?: string };
      if (!res.ok) throw new Error(payload.error ?? "编辑影响分析失败");
      setImpactReport(payload);
    } catch (error) {
      setActionMessage(error instanceof Error ? error.message : String(error));
    } finally {
      setBusyAction(null);
    }
  }

  return (
    <section className="page-shell round-page">
      <header className="round-hero">
        <div className="round-hero-main">
          <div className="page-kicker">
            {fullSeriesMode
              ? `全集 · 已汇总 ${visibleEpisodeCount}/${expectedEpisodeCount} 集`
              : `Round ${roundNum} · ${round?.epRange ?? "等待轮次"}`}{" "}
            · 目标 {project.targetEpisodeCount} 集
          </div>
          <h1 className="page-title">
            {project.name} · {fullSeriesMode ? "全集" : `第 ${roundNum} 轮`}
          </h1>
          <div className="round-hero-meta">
            <Badge variant={projectPaused ? "outline" : "default"}>
              {data.project.status}
            </Badge>
            <Badge variant="outline">{round?.status ?? "pending"}</Badge>
            {fullSeriesMode && <Badge variant="outline">全集视图</Badge>}
            {runAllEnabled && <Badge variant="outline">批量运行中</Badge>}
            {qualityAverage != null && (
              <Badge variant="outline">均分 {qualityAverage.toFixed(1)}</Badge>
            )}
            <span className="round-hero-progress">
              已输出 {visibleEpisodeCount}/{expectedEpisodeCount}
              {roundJob ? ` · ${jobLabel(roundJob)}` : ""}
            </span>
          </div>
        </div>
        <div className="round-hero-actions">
          <Button
            variant="outline"
            size="sm"
            disabled={busyAction !== null}
            onClick={cloneProject}
          >
            <Copy className="size-4" />
            {busyAction === "clone" ? "复制中" : "复制项目"}
          </Button>
          <Button
            variant="outline"
            size="sm"
            disabled={busyAction !== null}
            onClick={() => downloadNovelExport("txt")}
          >
            <Download className="size-4" />
            {busyAction === "novel-export-txt" ? "导出中" : "导出TXT"}
          </Button>
          <Button
            variant="outline"
            size="sm"
            disabled={busyAction !== null}
            onClick={() => downloadNovelExport("word")}
          >
            <Download className="size-4" />
            {busyAction === "novel-export-word" ? "导出中" : "导出Word"}
          </Button>
          {projectPaused ? (
            <Button
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
          {runAllEnabled ? (
            <Button
              variant="outline"
              size="sm"
              disabled={busyAction !== null}
              onClick={() => controlProject("stop_run_all")}
            >
              <Pause className="size-4" />
              {busyAction === "project-stop_run_all" ? "处理中" : "停止批量运行"}
            </Button>
          ) : (
            <Button
              size="sm"
              disabled={busyAction !== null || projectDone || reachedTarget}
              onClick={() => controlProject("run_all")}
            >
              <Play className="size-4" />
              {busyAction === "project-run_all" ? "启动中" : "批量运行 · 每轮5集"}
            </Button>
          )}
        </div>
      </header>

      {actionMessage && (
        <div className="status-line round-action-message">{actionMessage}</div>
      )}

      <section className="round-status-strip" aria-label="轮次概览">
        <div className="round-status-cell" data-primary="true">
          <span className="round-status-icon">
            <FileText className="size-4" />
          </span>
          <span className="round-status-copy">
            <span className="round-status-label">当前查看</span>
            <strong>{selectedEpisodeCode}</strong>
            <span>{selectedTitle}</span>
          </span>
        </div>
        <div className="round-status-cell">
          <span className="round-status-icon">
            <ListVideo className="size-4" />
          </span>
          <span className="round-status-copy">
            <span className="round-status-label">轮次进度</span>
            <strong>
              {visibleEpisodeCount}/{expectedEpisodeCount}
            </strong>
            <span>{fullSeriesMode ? "全剧" : "本轮"} {episodeProgress}% 已写出</span>
          </span>
        </div>
        <div className="round-status-cell">
          <span className="round-status-icon">
            <Activity className="size-4" />
          </span>
          <span className="round-status-copy">
            <span className="round-status-label">Worker</span>
            <strong>{workerStatusLabel}</strong>
            <span>{roundJob?.message ?? "等待任务更新"}</span>
          </span>
        </div>
        <div className="round-status-cell">
          <span className="round-status-icon">
            <Gauge className="size-4" />
          </span>
          <span className="round-status-copy">
            <span className="round-status-label">质量门禁</span>
            <strong>
              {qualityAverage != null ? qualityAverage.toFixed(1) : "-"}
            </strong>
            <span>{qualityStatusLabel}</span>
          </span>
        </div>
      </section>

      <section className="round-workbench">
        <Card className="round-episode-panel">
          <div className="round-panel-head">
            <div>
              <div className="round-panel-title">
                <ListVideo className="size-4" />
                {fullSeriesMode ? "全集" : "剧集"}
              </div>
              <div className="round-panel-sub">
                {fullSeriesMode ? "全剧已输出" : "本轮已输出"}{" "}
                {visibleEpisodeCount}/{expectedEpisodeCount} 集
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
              {eps.map((ep) => {
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
                  <p>改动当前集后，检查后续开头、状态台账和道具/伏笔是否需要承接。</p>
                </div>
                <Button
                  variant="outline"
                  size="sm"
                  disabled={busyAction !== null}
                  onClick={analyzeImpact}
                >
                  <GitCompareArrows className="size-4" />
                  {busyAction === "impact" ? "分析中" : "分析影响"}
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
                    <div className="round-issue-list">
                      {impactReport.warnings.map((warning) => (
                        <div key={warning} className="round-issue">
                          <AlertCircle className="size-3.5" />
                          <span>{warning}</span>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}
            </div>
          )}
        </Card>

        <aside className="round-inspector">
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
                {qualityAverage != null && (
                  <strong>{qualityAverage.toFixed(1)}</strong>
                )}
              </div>
              <div className="round-score-list">
                {scoreEntries.map((score) => (
                  <div key={score.key} className="round-score-row">
                    <span>{score.label}</span>
                    <div className="round-score-track">
                      <span style={{ width: `${Math.min(score.value * 10, 100)}%` }} />
                    </div>
                    <b>{score.value}</b>
                  </div>
                ))}
                {adaptationQuality?.source_fidelity && (
                  <div className="round-score-row">
                    <span>源文</span>
                    <div className="round-score-track">
                      <span
                        style={{
                          width: `${Math.min(
                            adaptationQuality.source_fidelity.score,
                            100
                          )}%`,
                        }}
                      />
                    </div>
                    <b>{adaptationQuality.source_fidelity.score}</b>
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
              {adaptationIssuePreview.length > 0 && (
                <div className="round-issue-list">
                  {adaptationIssuePreview.map((issue) => (
                    <div key={issue} className="round-issue">
                      <AlertCircle className="size-3.5" />
                      <span>{issue}</span>
                    </div>
                  ))}
                </div>
              )}
              {issuePreview.length > 0 && (
                <div className="round-issue-list">
                  {issuePreview.map((issue) => (
                    <div key={issue} className="round-issue">
                      <AlertCircle className="size-3.5" />
                      <span>{issue}</span>
                    </div>
                  ))}
                  {hiddenIssueCount > 0 && (
                    <div className="round-issue-more">
                      还有 {hiddenIssueCount} 条问题，完整列表保留在质量报告里
                    </div>
                  )}
                </div>
              )}
            </section>
          )}

          {hasGenerationMetrics && (
            <section className="round-side-panel">
              <div className="round-panel-title">
                <Cpu className="size-4" />
                运行数据
              </div>
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
              <div className="round-muted">
                {runtime?.generation_variant ?? jobResult?.generationVariant ?? "drama_engine_first"}
                {" · repair "}
                {runtime?.repair_budget ?? jobResult?.repairBudget ?? "episode"}
                {jobResult?.episodesPerRound ? ` · ${jobResult.episodesPerRound}集/轮` : ""}
              </div>
              {slowestStage && (
                <div className="round-muted">
                  最慢阶段：{slowestStage.name} · {formatDuration(slowestStage.duration_ms)}
                </div>
              )}
              {tokenSummary.estimatedUsd != null && (
                <div className="round-muted">
                  按 Gemini 3.1 Flash Lite 公开价估算：input $0.25/M，output $1.50/M。
                </div>
              )}
            </section>
          )}

          {(methodologyCards.length > 0 || sourceStrength || methodologyContext) && (
            <section className="round-side-panel">
              <div className="round-panel-title">
                <ScrollText className="size-4" />
                方法论复盘
              </div>
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
              {sourceStrength?.reasons.length ? (
                <p className="round-context-summary">
                  {sourceStrength.reasons.slice(0, 2).join("；")}
                </p>
              ) : null}
              {methodologyCards.length > 0 && (
                <div className="round-hook-list">
                  {methodologyCards.slice(0, 6).map((card) => (
                    <Badge key={card.id} variant="outline">
                      {card.name}
                    </Badge>
                  ))}
                </div>
              )}
              {methodologyIssuePreview.length > 0 ? (
                <div className="round-issue-list">
                  {methodologyIssuePreview.map((issue) => (
                    <div key={`${issue.card_id}-${issue.message}`} className="round-issue">
                      <AlertCircle className="size-3.5" />
                      <span>
                        {issue.episode ? `EP${String(issue.episode).padStart(2, "0")} · ` : ""}
                        {issue.message}
                      </span>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="round-muted">本轮无方法论阻断问题</div>
              )}
            </section>
          )}

          {context && (
            <section className="round-side-panel">
              <div className="round-panel-title">
                <CheckCircle2 className="size-4" />
                状态承接
              </div>
              <div className="round-context-current">
                当前到第 {storyLedger?.current_episode ?? context.current_episode} 集
              </div>
              <p className="round-context-summary">{context.summary}</p>
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
              {storyLedger?.warnings.length ? (
                <div className="round-issue-list">
                  {storyLedger.warnings.slice(0, 3).map((warning) => (
                    <div key={warning} className="round-issue">
                      <AlertCircle className="size-3.5" />
                      <span>{warning}</span>
                    </div>
                  ))}
                </div>
              ) : null}
            </section>
          )}

          <section className="round-side-panel">
            <div className="round-panel-title">
              <Play className="size-4" />
              下一步
            </div>
            <div className="round-control-grid">
              <select
                value={selectedGenerationVariant}
                onChange={(event) => setSelectedGenerationVariant(event.target.value)}
                className="form-select"
                aria-label="改编策略"
              >
                {generationVariantOptions.map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
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
            </div>
            {round?.status === "done" &&
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
                    : `开始第 ${roundNum + 1} 轮 · ${selectedEpisodesPerRound}集`}
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
            <Button variant="outline" className="w-full" asChild>
              <Link href={`/projects/${projectId}/bible`}>系统 Bible</Link>
            </Button>
          </section>

          {round?.status === "done" && (
            <section className="round-side-panel">
              <div className="round-panel-title">
                <PackageCheck className="size-4" />
                交付工具
              </div>
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
              <Button variant="outline" size="sm" className="w-full" asChild>
                <a
                  href={`/api/projects/${projectId}/export?round=${roundNum}&allowIssues=1`}
                >
                  <Download className="size-4" />
                  下载交付包
                </a>
              </Button>
            </section>
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
            <div className="round-issue-list">
              {delivery.warnings.map((warning) => (
                <div key={warning} className="round-issue">
                  <AlertCircle className="size-3.5" />
                  <span>{warning}</span>
                </div>
              ))}
            </div>
          )}
        </Card>
      )}
    </section>
  );
}
