"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import {
  AlertTriangle,
  ArrowLeft,
  BarChart3,
  CheckCircle2,
  Clock3,
  FolderOpen,
  Gauge,
  GitCompareArrows,
  Info,
  Layers3,
  Play,
  RefreshCw,
  ServerCog,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import type {
  EngineJob,
  QualitySampleEvaluationPayload,
  QualitySampleRoundReport,
  QualitySampleResult,
} from "@/lib/engine-types";

function roundPassed(round: QualitySampleRoundReport): boolean {
  return combinedRoundWarnings(round).length === 0;
}

function samplePassed(sample: QualitySampleResult): boolean {
  return sample.rounds.length > 0 && sample.rounds.every(roundPassed);
}

function averageScores(rounds: QualitySampleRoundReport[]): number | null {
  const values = rounds.flatMap((round) =>
    [
      round.hook_score,
      round.conflict_score,
      round.cliffhanger_score,
      round.continuity_score,
      round.video_feasibility_score,
    ].filter((value): value is number => typeof value === "number")
  );
  if (!values.length) return null;
  return values.reduce((sum, value) => sum + value, 0) / values.length;
}

function formatDate(value: string | null): string {
  if (!value) return "尚未运行";
  return new Date(value).toLocaleString();
}

function jobStatusLabel(job: EngineJob): string {
  if (job.status === "queued") return job.isQueuedTooLong ? "等待过久" : "排队中";
  if (job.status === "running") return job.isStale ? "疑似中断" : "运行中";
  if (job.status === "succeeded") return "已完成";
  return "失败";
}

function jobStatusVariant(job: EngineJob): "default" | "destructive" | "outline" {
  if (job.status === "failed" || job.isStale) return "destructive";
  if (job.status === "succeeded") return "default";
  return "outline";
}

function qualityStatusLabel(status: string | null | undefined): string {
  if (status === "usable") return "可用";
  if (status === "needs_rewrite") return "需重写";
  if (status === "context_conflict") return "上下文冲突";
  if (status === "needs_human_review") return "需人工看";
  return "缺失";
}

function passRate(passed: number, total: number): string {
  if (!total) return "-";
  return `${Math.round((passed / total) * 100)}%`;
}

function scoreTone(value: number | null | undefined): string {
  if (value == null) return "text-gray-400";
  if (value >= 8) return "text-emerald-700";
  if (value >= 6) return "text-amber-700";
  return "text-red-700";
}

type QualityJobResult = {
  passed?: number | null;
  total?: number | null;
  rounds?: number | null;
  variants?: string[] | null;
  runtimeMs?: number | null;
};

function parseJobResult(job?: EngineJob | null): QualityJobResult | null {
  if (!job?.resultJson) return null;
  try {
    return JSON.parse(job.resultJson) as QualityJobResult;
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

function combinedRoundWarnings(round: QualitySampleRoundReport): string[] {
  return [
    ...round.warnings,
    ...(round.source_fidelity_warnings ?? []),
    ...(round.continuity_warnings ?? []),
    ...(round.ledger_warnings ?? []),
  ];
}

export function QualitySamplesClient() {
  const [payload, setPayload] = useState<QualitySampleEvaluationPayload | null>(
    null
  );
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function load() {
    const res = await fetch("/api/quality-samples");
    const data = await res.json();
    if (!res.ok) throw new Error(data.error ?? "quality samples load failed");
    setPayload(data as QualitySampleEvaluationPayload);
  }

  useEffect(() => {
    let cancelled = false;
    async function boot() {
      try {
        const res = await fetch("/api/quality-samples");
        const data = await res.json();
        if (!res.ok) throw new Error(data.error ?? "quality samples load failed");
        if (!cancelled) setPayload(data as QualitySampleEvaluationPayload);
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : String(err));
        }
      }
    }
    boot();
    return () => {
      cancelled = true;
    };
  }, []);

  async function runRegression(variants?: string[]) {
    setBusy(true);
    setError(null);
    try {
      const res = await fetch("/api/quality-samples", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ rounds: 2, variants }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error ?? "quality samples failed");
      setPayload(data as QualitySampleEvaluationPayload);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  }

  async function retryJob(jobId: string) {
    setBusy(true);
    setError(null);
    try {
      const res = await fetch(`/api/jobs/${jobId}/retry`, { method: "POST" });
      let data: { error?: string } | null = null;
      try {
        data = (await res.json()) as { error?: string };
      } catch {
        data = null;
      }
      if (!res.ok) throw new Error(data?.error ?? "任务重试失败");
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  }

  const samples = payload?.report?.samples ?? [];
  const variants = payload?.report?.variants ?? [];
  const latestJob = payload?.jobs[0] ?? null;
  const failedJobs = payload?.jobs.filter((job) => job.status === "failed") ?? [];
  const latestJobResult = parseJobResult(latestJob);
  const hasRunningJob =
    payload?.jobs.some(
      (job) =>
        (job.status === "queued" || job.status === "running") && !job.isStale
    ) ??
    false;
  const stats = useMemo(() => {
    const passed = samples.filter(samplePassed).length;
    const failed = samples.length - passed;
    const rounds = samples.reduce((count, sample) => count + sample.rounds.length, 0);
    const average = averageScores(samples.flatMap((sample) => sample.rounds));
    return { passed, failed, total: samples.length, rounds, average };
  }, [samples]);

  useEffect(() => {
    if (!hasRunningJob) return;
    const timer = window.setInterval(() => {
      load().catch((err) => {
        setError(err instanceof Error ? err.message : String(err));
      });
    }, 2000);
    return () => window.clearInterval(timer);
  }, [hasRunningJob]);

  return (
    <section className="page-shell">
      <header className="space-y-5">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div className="max-w-3xl space-y-3">
            <div className="flex flex-wrap items-center gap-2">
              <Badge variant="outline">内部工具</Badge>
              <Badge variant="secondary">低优先级 worker</Badge>
              <span className="text-sm text-gray-500">
                {payload
                  ? `${payload.mode} · 最近报告 ${formatDate(payload.updatedAt)}`
                  : "加载中..."}
              </span>
            </div>
            <div>
              <h1 className="page-title">
                模型 / Prompt 回归测试台
              </h1>
              <p className="page-description">
                用固定小说样本跑完整改编链路，检查换模型、改 prompt、改 workflow 后有没有质量退化。这里不是运营生成入口，也不会决定单个项目是否能继续。
              </p>
            </div>
          </div>
          <div className="flex flex-wrap gap-2">
            <Button variant="outline" onClick={load} disabled={busy}>
              <RefreshCw className="size-4" />
              刷新状态
            </Button>
            <Button onClick={() => runRegression()} disabled={busy || hasRunningJob}>
              <Play className="size-4" />
              {busy || hasRunningJob ? "回归运行中" : "运行内部回归"}
            </Button>
            <Button
              variant="outline"
              onClick={() =>
                runRegression([
                  "sop_full_stack",
                  "drama_engine_first",
                  "current_density",
                ])
              }
              disabled={busy || hasRunningJob}
            >
              <GitCompareArrows className="size-4" />
              三策略对比
            </Button>
            <Link href="/">
              <Button variant="outline">
                <ArrowLeft className="size-4" />
                回项目列表
              </Button>
            </Link>
          </div>
        </div>

        <section className="grid gap-3 md:grid-cols-3">
          <div className="soft-panel">
            <div className="mb-2 flex items-center gap-2 text-sm font-medium">
              <GitCompareArrows className="size-4" />
              用来比较版本
            </div>
            <p className="text-sm leading-5 text-gray-600">
              同一批样本反复跑，方便看 Gemini / Kimi / prompt 版本之间的质量变化。
            </p>
          </div>
          <div className="soft-panel">
            <div className="mb-2 flex items-center gap-2 text-sm font-medium">
              <ServerCog className="size-4" />
              不阻塞项目生成
            </div>
            <p className="text-sm leading-5 text-gray-600">
              回归测试由独立 quality worker 执行，正常短剧生成走 round worker。
            </p>
          </div>
          <div className="soft-panel">
            <div className="mb-2 flex items-center gap-2 text-sm font-medium">
              <Info className="size-4" />
              结果只看趋势
            </div>
            <p className="text-sm leading-5 text-gray-600">
              分数用于发现退化和异常，不是给运营交付的最终脚本评分页。
              {variants.length > 0 ? ` 当前报告：${variants.join(" / ")}` : ""}
            </p>
          </div>
        </section>
      </header>

      {error && (
        <div className="rounded-[var(--radius-md)] border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          {error}
        </div>
      )}

      <section className="grid gap-3 md:grid-cols-4">
        <Card className="gap-3 p-5">
          <div className="flex items-center justify-between gap-2 text-sm text-gray-500">
            <span className="inline-flex items-center gap-2">
              <CheckCircle2 className="size-4" />
              通过率
            </span>
            <Badge variant="outline">{stats.passed}/{stats.total}</Badge>
          </div>
          <div className="text-3xl font-semibold">{passRate(stats.passed, stats.total)}</div>
          <p className="text-xs text-gray-500">所有轮次无 warning 的样本占比</p>
        </Card>
        <Card className="gap-3 p-5">
          <div className="flex items-center gap-2 text-sm text-gray-500">
            <AlertTriangle className="size-4" />
            需关注样本
          </div>
          <div className="text-3xl font-semibold">{stats.failed}</div>
          <p className="text-xs text-gray-500">失败不代表线上不可用，代表需要看差异</p>
        </Card>
        <Card className="gap-3 p-5">
          <div className="flex items-center gap-2 text-sm text-gray-500">
            <Layers3 className="size-4" />
            已评估轮次
          </div>
          <div className="text-3xl font-semibold">{stats.rounds}</div>
          <p className="text-xs text-gray-500">样本数 × 每个样本跑的轮次</p>
        </Card>
        <Card className="gap-3 p-5">
          <div className="flex items-center gap-2 text-sm text-gray-500">
            <Gauge className="size-4" />
            平均维度分
          </div>
          <div className="text-3xl font-semibold">
            {stats.average == null ? "-" : stats.average.toFixed(1)}
          </div>
          <p className="text-xs text-gray-500">Hook / 冲突 / 断点 / 连续性 / 可拍性</p>
        </Card>
      </section>

      {payload && (
        <div className="status-line flex flex-wrap items-center gap-2">
          <FolderOpen className="size-4" />
          <span className="font-medium text-gray-700">报告目录</span>
          <span className="break-all">{payload.projectsDir}</span>
        </div>
      )}

      {latestJob && (
        <Card className="gap-4 p-5">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div className="space-y-1">
              <div className="flex flex-wrap items-center gap-2">
                <span className="font-medium">当前回归任务</span>
                <Badge variant={jobStatusVariant(latestJob)}>
                  {jobStatusLabel(latestJob)}
                </Badge>
                <span className="text-sm text-gray-500">{latestJob.title}</span>
              </div>
              <p className="text-sm text-gray-500">
                {latestJob.message ?? "等待状态更新"}
              </p>
            </div>
            <div className="flex items-center gap-3">
              {latestJob.retryable && (
                <Button
                  variant="outline"
                  size="sm"
                  disabled={busy}
                  onClick={() => retryJob(latestJob.id)}
                >
                  <RefreshCw className="size-4" />
                  {busy
                    ? "处理中"
                    : latestJob.isStale
                      ? "恢复队列"
                      : "重试"}
                </Button>
              )}
              <div className="text-right text-sm">
                <div className="font-medium">{latestJob.progress}%</div>
                <div className="text-xs text-gray-500">
                  {formatDate(latestJob.updatedAt)}
                </div>
              </div>
            </div>
          </div>
          {(latestJobResult?.runtimeMs != null ||
            latestJobResult?.passed != null ||
            latestJobResult?.total != null ||
            latestJobResult?.rounds != null) && (
            <div className="flex flex-wrap items-center gap-3 text-xs text-gray-500">
              {latestJobResult?.runtimeMs != null && (
                <span className="inline-flex items-center gap-1">
                  <Clock3 className="size-3.5" />
                  耗时 {formatDuration(latestJobResult.runtimeMs)}
                </span>
              )}
              {(latestJobResult?.passed != null ||
                latestJobResult?.total != null) && (
                <span>
                  通过 {latestJobResult.passed ?? "-"}/{latestJobResult.total ?? "-"}
                </span>
              )}
              {latestJobResult?.rounds != null && (
                <span>轮次 {latestJobResult.rounds}</span>
              )}
              {latestJobResult?.variants?.length ? (
                <span>策略 {latestJobResult.variants.join(" / ")}</span>
              ) : null}
            </div>
          )}
          <Progress value={latestJob.progress} className="h-2" />
          {latestJob.errorText && (
            <p className="text-sm text-red-600">{latestJob.errorText}</p>
          )}
          {(latestJob.statusReason || latestJob.operatorHint) && (
            <div className="rounded-[var(--radius-md)] border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-800">
              {latestJob.statusReason && <div>{latestJob.statusReason}</div>}
              {latestJob.operatorHint && (
                <div className="mt-1 text-xs text-amber-700">
                  {latestJob.operatorHint}
                </div>
              )}
            </div>
          )}
        </Card>
      )}

      {payload && samples.length === 0 && (
        <Card className="p-6">
          <div className="flex items-start gap-3">
            {failedJobs.length ? (
              <AlertTriangle className="mt-0.5 size-5 text-red-600" />
            ) : (
              <BarChart3 className="mt-0.5 size-5 text-gray-500" />
            )}
            <div>
              <div className="font-medium">
                {failedJobs.length
                  ? "最近回归失败，尚未生成可展示报告"
                  : "还没有可展示的回归报告"}
              </div>
              <p className="mt-1 text-sm text-gray-500">
                {failedJobs.length
                  ? failedJobs[0].errorText ??
                    failedJobs[0].statusReason ??
                    "请查看下方任务历史里的失败原因。"
                  : "点击“运行内部回归”后，系统会用固定样本跑完整链路，完成后这里会展示通过率、平均分和每个样本的 warning。"}
              </p>
              {failedJobs[0]?.operatorHint && (
                <p className="mt-2 text-sm text-amber-700">
                  {failedJobs[0].operatorHint}
                </p>
              )}
            </div>
          </div>
        </Card>
      )}

      {payload && payload.jobs.length > 1 && (
        <Card className="gap-3 p-5">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <h2 className="font-medium">最近任务历史</h2>
              <p className="text-sm text-gray-500">
                失败、等待过久和限额问题都会在这里保留，方便判断是不是模型配置或 worker 队列问题。
              </p>
            </div>
          </div>
          <div className="table-shell">
            <table className="w-full min-w-[760px] text-left text-sm">
              <thead className="text-xs text-gray-500">
                <tr className="border-b">
                  <th className="py-2 font-medium">状态</th>
                  <th className="py-2 font-medium">任务</th>
                  <th className="py-2 font-medium">进度</th>
                  <th className="py-2 font-medium">原因</th>
                  <th className="py-2 font-medium">更新时间</th>
                </tr>
              </thead>
              <tbody>
                {payload.jobs.slice(0, 8).map((job) => (
                  <tr key={job.id} className="border-b last:border-0">
                    <td className="py-2">
                      <Badge variant={jobStatusVariant(job)}>
                        {jobStatusLabel(job)}
                      </Badge>
                    </td>
                    <td className="max-w-[240px] py-2">
                      <div className="font-medium">{job.title}</div>
                      <div className="text-xs text-gray-500">
                        尝试 {job.attempts} 次
                        {job.failureCategory ? ` · ${job.failureCategory}` : ""}
                      </div>
                    </td>
                    <td className="py-2">{job.progress}%</td>
                    <td className="max-w-[360px] py-2 text-xs leading-5 text-gray-600">
                      {job.errorText ?? job.statusReason ?? job.message ?? "-"}
                      {job.operatorHint && (
                        <div className="mt-1 text-amber-700">
                          {job.operatorHint}
                        </div>
                      )}
                    </td>
                    <td className="py-2 text-xs text-gray-500">
                      {formatDate(job.updatedAt)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      )}

      <section className="space-y-3">
        {samples.length > 0 && (
          <div className="flex flex-wrap items-end justify-between gap-3">
            <div>
              <h2 className="text-lg font-semibold">样本明细</h2>
              <p className="text-sm text-gray-500">
                看 warning 就够了：它告诉我们新模型或新 prompt 主要在哪些类型上退化。
              </p>
            </div>
          </div>
        )}
        {samples.map((sample) => {
          const passed = samplePassed(sample);
          return (
            <Card
              key={`${sample.sample_id}:${sample.variant ?? "default"}`}
              className="gap-4 p-5"
            >
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div>
                  <div className="flex flex-wrap items-center gap-2">
                    <h2 className="font-medium">{sample.label}</h2>
                    <Badge variant={passed ? "default" : "destructive"}>
                      {passed ? "通过" : "需关注"}
                    </Badge>
                  </div>
                  <p className="text-xs text-gray-500">{sample.sample_id}</p>
                  {sample.variant && (
                    <p className="text-xs text-gray-500">
                      策略：{sample.variant}
                    </p>
                  )}
                </div>
                <span className="max-w-full break-all text-xs text-gray-500">
                  {sample.project_dir}
                </span>
              </div>

              <div className="table-shell">
                <table className="w-full min-w-[980px] text-left text-sm">
                  <thead className="text-xs text-gray-500">
                    <tr className="border-b">
                      <th className="py-2 font-medium">策略</th>
                      <th className="py-2 font-medium">轮次</th>
                      <th className="py-2 font-medium">集数</th>
                      <th className="py-2 font-medium">结论</th>
                      <th className="py-2 font-medium">Hook</th>
                      <th className="py-2 font-medium">冲突</th>
                      <th className="py-2 font-medium">断点</th>
                      <th className="py-2 font-medium">连续性</th>
                      <th className="py-2 font-medium">可拍性</th>
                      <th className="py-2 font-medium">源文</th>
                      <th className="py-2 font-medium">承接</th>
                      <th className="py-2 font-medium">需要看的问题</th>
                    </tr>
                  </thead>
                  <tbody>
                    {sample.rounds.map((round) => {
                      const warnings = combinedRoundWarnings(round);
                      return (
                      <tr key={round.round_number} className="border-b last:border-0">
                        <td className="py-2">
                          {round.generation_variant ?? sample.variant ?? "-"}
                        </td>
                        <td className="py-2">R{round.round_number}</td>
                        <td className="py-2">
                          {round.target_episode_range ?? "-"}
                        </td>
                        <td className="py-2">
                          <Badge
                            variant={
                              round.quality_status === "usable"
                                ? "default"
                                : "destructive"
                            }
                          >
                            {qualityStatusLabel(round.quality_status)}
                          </Badge>
                        </td>
                        <td className={`py-2 font-medium ${scoreTone(round.hook_score)}`}>
                          {round.hook_score ?? "-"}
                        </td>
                        <td className={`py-2 font-medium ${scoreTone(round.conflict_score)}`}>
                          {round.conflict_score ?? "-"}
                        </td>
                        <td className={`py-2 font-medium ${scoreTone(round.cliffhanger_score)}`}>
                          {round.cliffhanger_score ?? "-"}
                        </td>
                        <td className={`py-2 font-medium ${scoreTone(round.continuity_score)}`}>
                          {round.continuity_score ?? "-"}
                        </td>
                        <td className={`py-2 font-medium ${scoreTone(round.video_feasibility_score)}`}>
                          {round.video_feasibility_score ?? "-"}
                        </td>
                        <td className={`py-2 font-medium ${scoreTone(round.source_fidelity_score == null ? null : round.source_fidelity_score / 10)}`}>
                          {round.source_fidelity_score ?? "-"}
                        </td>
                        <td className={`py-2 font-medium ${scoreTone(round.continuity_audit_score == null ? null : round.continuity_audit_score / 10)}`}>
                          {round.continuity_audit_score ?? "-"}
                        </td>
                        <td className="max-w-[320px] py-2 text-xs leading-5 text-red-600">
                          {warnings.length
                            ? warnings.slice(0, 6).join("；")
                            : "-"}
                        </td>
                      </tr>
                    );
                    })}
                  </tbody>
                </table>
              </div>
            </Card>
          );
        })}
      </section>
    </section>
  );
}
