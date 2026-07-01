"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import {
  Activity,
  Clock3,
  Cpu,
  Download,
  Languages,
  PackageCheck,
  Play,
  RefreshCw,
  Video,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import type { EngineJob } from "@/lib/engine-types";

type Project = {
  id: string;
  name: string;
  targetEpisodeCount: number;
  status: string;
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

const generationVariantOptions = [
  { value: "sop_full_stack", label: "SOP 全链路" },
  { value: "drama_engine_first", label: "强剧情优先" },
  { value: "current_density", label: "当前密度" },
];

const repairBudgetOptions = [
  { value: "episode", label: "逐集修复" },
  { value: "rewrite", label: "改写一次" },
  { value: "none", label: "不自动修复" },
];

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
};

function parseJobResult(job?: EngineJob | null): JobResultSummary | null {
  if (!job?.resultJson) return null;
  try {
    return JSON.parse(job.resultJson) as JobResultSummary;
  } catch {
    return null;
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
  const [selectedGenerationVariant, setSelectedGenerationVariant] =
    useState("sop_full_stack");
  const [selectedRepairBudget, setSelectedRepairBudget] = useState("episode");

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
        const round = d.rounds.find((r: Round) => r.roundNum === roundNum);
        if (round?.status === "done" || round?.status === "failed") break;
        await new Promise((r) => setTimeout(r, 3000));
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

  if (!data) return <main className="p-8">加载中...</main>;

  const round = data.rounds.find((r) => r.roundNum === roundNum);
  const summary = parseSummary(round);
  const quality = summary?.quality_report;
  const context = summary?.next_round_context;
  const runtime = summary?.runtime_report;
  const eps = data.episodes
    .filter((e) => e.roundId === round?.id)
    .sort((a, b) => a.epNum - b.epNum);
  const roundJob =
    data.jobs.find((job) => job.roundId === round?.id) ??
    data.jobs.find((job) => job.kind === "round_generation");
  const jobResult = parseJobResult(roundJob);
  const totalTokens =
    runtime?.llm_calls?.reduce((sum, call) => {
      const total = call.usage?.total_tokens;
      return sum + (typeof total === "number" ? total : 0);
    }, 0) ?? null;
  const runtimeMs = runtime?.total_duration_ms ?? jobResult?.runtimeMs ?? null;
  const llmCalls = runtime?.llm_calls?.length ?? jobResult?.llmCalls ?? null;

  const projectDone = data.project.status === "done";
  const reachedTarget =
    (context?.current_episode ?? 0) >= data.project.targetEpisodeCount;

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

  function jobLabel(job: EngineJob): string {
    if (job.status === "queued") return "排队中";
    if (job.status === "running") return job.isStale ? "疑似中断" : "运行中";
    if (job.status === "succeeded") return "已完成";
    return "失败";
  }

  return (
    <main className="max-w-4xl mx-auto p-8 space-y-6">
      <header className="flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold">
            {project.name} · 第 {roundNum} 轮
          </h1>
          <p className="text-sm text-gray-500">
            {round?.epRange} · 目标 {project.targetEpisodeCount} 集
          </p>
        </div>
        <Badge>{round?.status ?? "pending"}</Badge>
      </header>

      {roundJob && (
        <Card className="gap-3 p-4">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <div className="flex flex-wrap items-center gap-2">
                <Activity className="size-4 text-gray-500" />
                <span className="font-medium">{roundJob.title}</span>
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
              <p className="text-sm text-gray-500">
                {roundJob.message ?? "等待状态更新"}
              </p>
            </div>
            <div className="flex items-center gap-3">
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
                      : "重试"}
                </Button>
              )}
              <div className="text-right text-sm">
                <div className="font-medium">{roundJob.progress}%</div>
                <div className="text-xs text-gray-500">
                  {new Date(roundJob.updatedAt).toLocaleString()}
                </div>
              </div>
            </div>
          </div>
          <div className="h-2 overflow-hidden rounded bg-gray-100">
            <div
              className="h-full bg-black transition-all"
              style={{ width: `${roundJob.progress}%` }}
            />
          </div>
          {roundJob.errorText && (
            <p className="text-sm text-red-600">{roundJob.errorText}</p>
          )}
          {(jobResult?.runtimeMs != null ||
            jobResult?.llmCalls != null ||
            jobResult?.qualityStatus ||
            jobResult?.targetEpisodeRange) && (
            <div className="flex flex-wrap gap-2 text-xs text-gray-500">
              {jobResult?.targetEpisodeRange && (
                <Badge variant="outline">{jobResult.targetEpisodeRange}</Badge>
              )}
              {jobResult?.qualityStatus && (
                <Badge variant="outline">{jobResult.qualityStatus}</Badge>
              )}
              {jobResult?.generationVariant && (
                <span>{jobResult.generationVariant}</span>
              )}
              {jobResult?.repairBudget && (
                <span>repair {jobResult.repairBudget}</span>
              )}
              {jobResult?.runtimeMs != null && (
                <span>耗时 {formatDuration(jobResult.runtimeMs)}</span>
              )}
              {jobResult?.llmCalls != null && (
                <span>LLM {formatNumber(jobResult.llmCalls)} 次</span>
              )}
            </div>
          )}
        </Card>
      )}

      {actionMessage && (
        <p className="text-sm text-gray-600">{actionMessage}</p>
      )}

      {(runtime || jobResult?.runtimeMs != null || jobResult?.llmCalls != null) && (
        <section className="grid gap-3 md:grid-cols-4">
          <Card className="gap-2 p-4">
            <div className="flex items-center gap-2 text-sm text-gray-500">
              <Clock3 className="size-4" />
              生成耗时
            </div>
            <div className="text-xl font-semibold">{formatDuration(runtimeMs)}</div>
          </Card>
          <Card className="gap-2 p-4">
            <div className="flex items-center gap-2 text-sm text-gray-500">
              <Cpu className="size-4" />
              LLM 调用
            </div>
            <div className="text-xl font-semibold">{formatNumber(llmCalls)}</div>
          </Card>
          <Card className="gap-2 p-4">
            <div className="text-sm text-gray-500">Token</div>
            <div className="text-xl font-semibold">{formatNumber(totalTokens)}</div>
          </Card>
          <Card className="gap-2 p-4">
            <div className="text-sm text-gray-500">策略</div>
            <div className="text-sm font-medium">
              {runtime?.generation_variant ?? "sop_full_stack"}
              <span className="block text-xs text-gray-500">
                repair: {runtime?.repair_budget ?? "episode"}
              </span>
            </div>
          </Card>
        </section>
      )}

      {quality && (
        <Card className="p-4 space-y-3">
          <div className="flex flex-wrap items-center gap-2">
            <Badge variant={quality.status === "usable" ? "default" : "destructive"}>
              {quality.status}
            </Badge>
            {Object.entries(quality.scores).map(([name, value]) => (
              <span key={name} className="text-sm text-gray-600">
                {name}: {value}
              </span>
            ))}
          </div>
          {quality.blocking_issues.length > 0 && (
            <ul className="list-disc pl-5 text-sm text-red-600">
              {quality.blocking_issues.map((issue) => (
                <li key={issue}>{issue}</li>
              ))}
            </ul>
          )}
        </Card>
      )}

      {context && (
        <Card className="p-4 space-y-2">
          <div className="text-sm text-gray-600">
            当前集数：{context.current_episode}
          </div>
          <p className="text-sm whitespace-pre-wrap">{context.summary}</p>
          {context.open_hooks.length > 0 && (
            <div className="flex flex-wrap gap-2">
              {context.open_hooks.map((hook) => (
                <Badge key={hook} variant="outline">
                  {hook}
                </Badge>
              ))}
            </div>
          )}
        </Card>
      )}

      <div className="space-y-3">
        {eps.map((ep) => (
          <Card key={ep.id} className="p-4">
            <div className="flex justify-between items-start gap-4">
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-2">
                  <h3 className="font-medium">
                    E{String(ep.epNum).padStart(2, "0")}
                  </h3>
                  <Badge
                    variant={ep.status === "green" ? "default" : "destructive"}
                  >
                    {ep.status}
                  </Badge>
                  {ep.score != null && (
                    <span className="text-sm text-gray-500">
                      score: {ep.score}
                    </span>
                  )}
                </div>
                {ep.scriptTxt && (
                  <pre className="mt-2 text-xs bg-gray-50 p-3 rounded max-h-72 overflow-auto whitespace-pre-wrap">
                    {ep.scriptTxt}
                  </pre>
                )}
              </div>
            </div>
          </Card>
        ))}
      </div>

      {round?.status === "done" && (
        <div className="space-y-4 pt-4">
          <div className="flex flex-wrap gap-2">
            {!projectDone && !reachedTarget && (
              <>
                <div className="flex items-center gap-2">
                  <select
                    value={selectedGenerationVariant}
                    onChange={(event) =>
                      setSelectedGenerationVariant(event.target.value)
                    }
                    className="h-9 rounded-md border px-2 text-sm"
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
                    className="h-9 rounded-md border px-2 text-sm"
                    aria-label="修复预算"
                  >
                    {repairBudgetOptions.map((option) => (
                      <option key={option.value} value={option.value}>
                        {option.label}
                      </option>
                    ))}
                  </select>
                </div>
                <Button
                  onClick={nextRound}
                  disabled={busyAction === "next-round"}
                >
                  <Play className="size-4" />
                  {busyAction === "next-round"
                    ? "启动中"
                    : `开始第 ${roundNum + 1} 轮`}
                </Button>
              </>
            )}
            {(projectDone || reachedTarget) && (
              <Link href={`/projects/${projectId}/complete`}>
                <Button>
                  <PackageCheck className="size-4" />
                  项目完成
                </Button>
              </Link>
            )}
            <Button
              variant="outline"
              disabled={busyAction === "video"}
              onClick={() => runAction("video", exportVideoBrief)}
            >
              <Video className="size-4" />
              生成视频 brief
            </Button>
            <div className="flex items-center gap-2">
              <select
                value={selectedProfile}
                onChange={(event) => setSelectedProfile(event.target.value)}
                className="h-9 rounded-md border px-2 text-sm"
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
                disabled={busyAction === "localization"}
                onClick={() => runAction("localization", exportLocalization)}
              >
                <Languages className="size-4" />
                生成本地化包
              </Button>
            </div>
            <Button
              variant="outline"
              disabled={busyAction === "delivery"}
              onClick={() => runAction("delivery", checkDelivery)}
            >
              <PackageCheck className="size-4" />
              交付预检
            </Button>
            <a href={`/api/projects/${projectId}/export?round=${roundNum}`}>
              <Button variant="outline">
                <Download className="size-4" />
                下载交付包
              </Button>
            </a>
            <Link href={`/projects/${projectId}/bible`}>
              <Button variant="outline">系统 Bible</Button>
            </Link>
          </div>

          {delivery && (
            <Card className="p-4 space-y-2">
              <div className="flex items-center gap-2">
                <Badge variant={delivery.ready ? "default" : "destructive"}>
                  {delivery.ready ? "ready" : "warning"}
                </Badge>
                <span className="text-sm text-gray-600">
                  文件 {delivery.files.length}
                </span>
              </div>
              <div className="grid gap-1 text-xs text-gray-600">
                {delivery.files.slice(0, 12).map((file) => (
                  <div
                    key={file.path}
                    className="flex items-center justify-between gap-4 rounded bg-gray-50 px-2 py-1"
                  >
                    <span className="truncate">{file.path}</span>
                    <span>{file.bytes} bytes</span>
                  </div>
                ))}
                {delivery.files.length > 12 && (
                  <div className="text-gray-500">
                    还有 {delivery.files.length - 12} 个文件会进入交付包
                  </div>
                )}
              </div>
              {delivery.warnings.length > 0 && (
                <ul className="list-disc pl-5 text-sm text-red-600">
                  {delivery.warnings.map((warning) => (
                    <li key={warning}>{warning}</li>
                  ))}
                </ul>
              )}
            </Card>
          )}
        </div>
      )}
    </main>
  );
}
