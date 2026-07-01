"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import {
  AlertTriangle,
  CheckCircle2,
  Clock3,
  FolderOpen,
  Gauge,
  Play,
  RefreshCw,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import type {
  EngineJob,
  QualitySampleEvaluationPayload,
  QualitySampleRoundReport,
  QualitySampleResult,
} from "@/lib/engine-types";

function roundPassed(round: QualitySampleRoundReport): boolean {
  return round.warnings.length === 0;
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
  if (job.status === "queued") return "排队中";
  if (job.status === "running") return job.isStale ? "疑似中断" : "运行中";
  if (job.status === "succeeded") return "已完成";
  return "失败";
}

function jobStatusVariant(job: EngineJob): "default" | "destructive" | "outline" {
  if (job.status === "failed" || job.isStale) return "destructive";
  if (job.status === "succeeded") return "default";
  return "outline";
}

type QualityJobResult = {
  passed?: number | null;
  total?: number | null;
  rounds?: number | null;
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

  async function runGate() {
    setBusy(true);
    setError(null);
    try {
      const res = await fetch("/api/quality-samples", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ rounds: 2 }),
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
  const latestJob = payload?.jobs[0] ?? null;
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
    return { passed, failed, rounds, average };
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
    <main className="mx-auto max-w-5xl space-y-6 p-8">
      <header className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold">质量门禁</h1>
          <p className="text-sm text-gray-500">
            {payload ? `${payload.mode} · ${formatDate(payload.updatedAt)}` : "加载中..."}
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Button variant="outline" onClick={load} disabled={busy}>
            <RefreshCw className="size-4" />
            刷新
          </Button>
          <Button onClick={runGate} disabled={busy || hasRunningJob}>
            <Play className="size-4" />
            {busy || hasRunningJob ? "运行中..." : "运行样本质检"}
          </Button>
          <Link href="/">
            <Button variant="outline">项目列表</Button>
          </Link>
        </div>
      </header>

      {error && (
        <div className="rounded-md border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          {error}
        </div>
      )}

      <section className="grid gap-3 md:grid-cols-4">
        <Card className="gap-2 p-4">
          <div className="flex items-center gap-2 text-sm text-gray-500">
            <CheckCircle2 className="size-4" />
            通过样本
          </div>
          <div className="text-2xl font-semibold">{stats.passed}</div>
        </Card>
        <Card className="gap-2 p-4">
          <div className="flex items-center gap-2 text-sm text-gray-500">
            <AlertTriangle className="size-4" />
            失败样本
          </div>
          <div className="text-2xl font-semibold">{stats.failed}</div>
        </Card>
        <Card className="gap-2 p-4">
          <div className="flex items-center gap-2 text-sm text-gray-500">
            <RefreshCw className="size-4" />
            评估轮次
          </div>
          <div className="text-2xl font-semibold">{stats.rounds}</div>
        </Card>
        <Card className="gap-2 p-4">
          <div className="flex items-center gap-2 text-sm text-gray-500">
            <Gauge className="size-4" />
            平均分
          </div>
          <div className="text-2xl font-semibold">
            {stats.average == null ? "-" : stats.average.toFixed(1)}
          </div>
        </Card>
      </section>

      {payload && (
        <div className="flex flex-wrap items-center gap-2 text-xs text-gray-500">
          <FolderOpen className="size-4" />
          <span className="break-all">{payload.projectsDir}</span>
        </div>
      )}

      {latestJob && (
        <Card className="gap-3 p-4">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <div className="flex flex-wrap items-center gap-2">
                <span className="font-medium">{latestJob.title}</span>
                <Badge variant={jobStatusVariant(latestJob)}>
                  {jobStatusLabel(latestJob)}
                </Badge>
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
            </div>
          )}
          <div className="h-2 overflow-hidden rounded bg-gray-100">
            <div
              className="h-full bg-black transition-all"
              style={{ width: `${latestJob.progress}%` }}
            />
          </div>
          {latestJob.errorText && (
            <p className="text-sm text-red-600">{latestJob.errorText}</p>
          )}
        </Card>
      )}

      {payload && samples.length === 0 && (
        <Card className="p-4 text-sm text-gray-500">暂无样本报告</Card>
      )}

      <section className="space-y-3">
        {samples.map((sample) => {
          const passed = samplePassed(sample);
          return (
            <Card key={sample.sample_id} className="gap-4 p-4">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div>
                  <div className="flex flex-wrap items-center gap-2">
                    <h2 className="font-medium">{sample.label}</h2>
                    <Badge variant={passed ? "default" : "destructive"}>
                      {passed ? "passed" : "failed"}
                    </Badge>
                  </div>
                  <p className="text-xs text-gray-500">{sample.sample_id}</p>
                </div>
                <span className="max-w-full break-all text-xs text-gray-500">
                  {sample.project_dir}
                </span>
              </div>

              <div className="overflow-x-auto">
                <table className="w-full min-w-[760px] text-left text-sm">
                  <thead className="text-xs text-gray-500">
                    <tr className="border-b">
                      <th className="py-2 font-medium">轮次</th>
                      <th className="py-2 font-medium">集数</th>
                      <th className="py-2 font-medium">状态</th>
                      <th className="py-2 font-medium">Hook</th>
                      <th className="py-2 font-medium">冲突</th>
                      <th className="py-2 font-medium">钩子</th>
                      <th className="py-2 font-medium">连续性</th>
                      <th className="py-2 font-medium">可拍性</th>
                      <th className="py-2 font-medium">Warning</th>
                    </tr>
                  </thead>
                  <tbody>
                    {sample.rounds.map((round) => (
                      <tr key={round.round_number} className="border-b last:border-0">
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
                            {round.quality_status ?? "missing"}
                          </Badge>
                        </td>
                        <td className="py-2">{round.hook_score ?? "-"}</td>
                        <td className="py-2">{round.conflict_score ?? "-"}</td>
                        <td className="py-2">
                          {round.cliffhanger_score ?? "-"}
                        </td>
                        <td className="py-2">
                          {round.continuity_score ?? "-"}
                        </td>
                        <td className="py-2">
                          {round.video_feasibility_score ?? "-"}
                        </td>
                        <td className="max-w-[260px] py-2 text-xs text-red-600">
                          {round.warnings.length
                            ? round.warnings.join("；")
                            : "-"}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </Card>
          );
        })}
      </section>
    </main>
  );
}
