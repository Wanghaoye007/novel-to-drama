"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import {
  Activity,
  AlertTriangle,
  Ban,
  CheckCircle2,
  Clipboard,
  Clock3,
  Copy,
  Eye,
  LoaderCircle,
  RefreshCw,
  RotateCcw,
  Search,
  Server,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";

type JobStatus = "queued" | "running" | "succeeded" | "failed" | "cancelled";

type OpsJob = {
  id: string;
  kind: string;
  status: JobStatus;
  title: string;
  projectId: string | null;
  projectName: string | null;
  roundId: string | null;
  workerId: string | null;
  progress: number;
  attempts: number;
  failureCategory: string | null;
  statusReason: string | null;
  message: string | null;
  retryable: boolean;
  isStale: boolean;
  createdAt: string;
  startedAt: string | null;
  updatedAt: string;
  finishedAt: string | null;
};

type WorkerView = {
  id: string;
  status: "online" | "offline";
  currentJobId: string | null;
  startedAt: string;
  heartbeatAt: string;
  hostname: string;
  pid: number;
  version: string;
};

type OpsOverview = {
  counts: Record<JobStatus | "total", number>;
  workers: WorkerView[];
  readiness: {
    status: "ready" | "warning" | "blocked";
    checks: Array<{ key: string; status: string; message: string }>;
  };
  recentFailures: OpsJob[];
  timestamp: string;
};

type JobDetail = {
  job: OpsJob;
  errorText: string | null;
  payloadSummary: Record<string, unknown> | null;
  resultSummary: Record<string, unknown> | null;
  events: Array<{
    id: string;
    eventType: string;
    message: string | null;
    metadata: Record<string, unknown> | null;
    createdAt: string;
  }>;
};

const kindLabels: Record<string, string> = {
  round_generation: "轮次生成",
  quality_samples: "质量回归",
  delivery_export: "剧本导出",
  video_brief_export: "视频执行稿",
  localization_export: "本地化导出",
  episode_optimize: "单集优化",
  edit_impact: "改编影响",
};

const statusLabels: Record<JobStatus, string> = {
  queued: "排队中",
  running: "运行中",
  succeeded: "已完成",
  failed: "失败",
  cancelled: "已取消",
};

function formatDate(value: string | null): string {
  if (!value) return "-";
  return new Date(value).toLocaleString("zh-CN", {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: false,
  });
}

function formatDuration(job: OpsJob): string {
  const start = new Date(job.startedAt ?? job.createdAt).getTime();
  const end = new Date(job.finishedAt ?? job.updatedAt).getTime();
  const seconds = Math.max(0, Math.round((end - start) / 1000));
  if (seconds < 60) return `${seconds}s`;
  const minutes = Math.floor(seconds / 60);
  return `${minutes}m ${seconds % 60}s`;
}

function statusVariant(status: JobStatus): "default" | "destructive" | "outline" | "secondary" {
  if (status === "failed") return "destructive";
  if (status === "succeeded") return "default";
  if (status === "cancelled") return "secondary";
  return "outline";
}

async function parseResponse<T>(response: Response): Promise<T> {
  const body = (await response.json()) as T & { error?: string };
  if (!response.ok) {
    throw new Error(body.error ?? `请求失败 (${response.status})`);
  }
  return body;
}

function jobActionPath(jobId: string, action: "retry" | "cancel"): string {
  if (action === "retry") return `/api/ops/jobs/${jobId}/retry`;
  return `/api/ops/jobs/${jobId}/cancel`;
}

export function OpsConsoleClient() {
  const [overview, setOverview] = useState<OpsOverview | null>(null);
  const [jobs, setJobs] = useState<OpsJob[]>([]);
  const [query, setQuery] = useState("");
  const [status, setStatus] = useState("");
  const [kind, setKind] = useState("");
  const [detailId, setDetailId] = useState<string | null>(null);
  const [detail, setDetail] = useState<JobDetail | null>(null);
  const [busyId, setBusyId] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const listUrl = useMemo(() => {
    const params = new URLSearchParams({ limit: "100" });
    if (query.trim()) params.set("query", query.trim());
    if (status) params.set("status", status);
    if (kind) params.set("kind", kind);
    return `/api/ops/jobs?${params.toString()}`;
  }, [kind, query, status]);

  const loadOverview = useCallback(async () => {
    const data = await parseResponse<OpsOverview>(
      await fetch("/api/ops/overview", { cache: "no-store" })
    );
    setOverview(data);
  }, []);

  const loadJobs = useCallback(async () => {
    const data = await parseResponse<{ jobs: OpsJob[] }>(
      await fetch(listUrl, { cache: "no-store" })
    );
    setJobs(data.jobs);
  }, [listUrl]);

  const loadDetail = useCallback(async (jobId: string) => {
    const data = await parseResponse<JobDetail>(
      await fetch(`/api/ops/jobs/${jobId}`, { cache: "no-store" })
    );
    setDetail(data);
  }, []);

  const refresh = useCallback(
    async (silent = false) => {
      if (!silent) setLoading(true);
      try {
        await Promise.all([
          loadOverview(),
          loadJobs(),
          detailId ? loadDetail(detailId) : Promise.resolve(),
        ]);
        setError(null);
      } catch (cause) {
        setError(cause instanceof Error ? cause.message : String(cause));
      } finally {
        if (!silent) setLoading(false);
      }
    },
    [detailId, loadDetail, loadJobs, loadOverview]
  );

  useEffect(() => {
    const timer = window.setTimeout(() => void refresh(), 200);
    return () => window.clearTimeout(timer);
  }, [refresh]);

  useEffect(() => {
    const poll = () => {
      if (document.visibilityState !== "visible") return;
      void refresh(true);
    };
    const timer = window.setInterval(poll, 5_000);
    document.addEventListener("visibilitychange", poll);
    return () => {
      window.clearInterval(timer);
      document.removeEventListener("visibilitychange", poll);
    };
  }, [refresh]);

  async function openDetail(jobId: string) {
    setDetailId(jobId);
    setDetail(null);
    try {
      await loadDetail(jobId);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : String(cause));
    }
  }

  async function copyJobId(jobId: string) {
    try {
      await navigator.clipboard.writeText(jobId);
    } catch {
      setError("复制失败，请手动选择任务 ID");
    }
  }

  async function runAction(jobId: string, action: "retry" | "cancel") {
    setBusyId(jobId);
    setError(null);
    try {
      await parseResponse(
        await fetch(jobActionPath(jobId, action), { method: "POST" })
      );
      await refresh(true);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : String(cause));
    } finally {
      setBusyId(null);
    }
  }

  const onlineWorkers = overview?.workers.filter((worker) => worker.status === "online") ?? [];
  const queueCount = (overview?.counts.queued ?? 0) + (overview?.counts.running ?? 0);

  return (
    <section className="page-shell ops-console">
      <header className="flex flex-wrap items-start justify-between gap-4">
        <div className="space-y-2">
          <div className="flex items-center gap-2 text-sm text-gray-500">
            <Activity className="size-4 text-[color:var(--reela-pink)]" />
            <span>内部运营</span>
            <span aria-hidden="true">·</span>
            <span>{overview ? `更新 ${formatDate(overview.timestamp)}` : "正在连接"}</span>
          </div>
          <div>
            <h1 className="page-title">任务运维</h1>
            <p className="page-description">查看 worker、任务状态和失败原因，安全重试或取消排队任务。</p>
          </div>
        </div>
        <Button variant="outline" onClick={() => void refresh()} disabled={loading}>
          <RefreshCw className={loading ? "size-4 animate-spin" : "size-4"} />
          刷新
        </Button>
      </header>

      {error ? (
        <div role="alert" className="rounded-[var(--radius-md)] border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          {error}
        </div>
      ) : null}

      <section className="ops-summary-grid" aria-label="运维摘要">
        <Card className="ops-summary-cell">
          <div className="ops-summary-label"><Server className="size-4" />Worker</div>
          <div className="ops-summary-value">{onlineWorkers.length}/{overview?.workers.length ?? 0}</div>
          <div className="ops-summary-note">{onlineWorkers.length ? `${onlineWorkers[0]?.hostname} · 在线` : "无在线 worker"}</div>
        </Card>
        <Card className="ops-summary-cell">
          <div className="ops-summary-label"><Clock3 className="size-4" />排队 / 运行</div>
          <div className="ops-summary-value">{queueCount}</div>
          <div className="ops-summary-note">{overview?.counts.queued ?? 0} 排队 · {overview?.counts.running ?? 0} 运行</div>
        </Card>
        <Card className="ops-summary-cell">
          <div className="ops-summary-label"><AlertTriangle className="size-4" />失败任务</div>
          <div className="ops-summary-value">{overview?.counts.failed ?? 0}</div>
          <div className="ops-summary-note">当前账号可见范围</div>
        </Card>
        <Card className="ops-summary-cell">
          <div className="ops-summary-label"><CheckCircle2 className="size-4" />上线准备度</div>
          <div className="ops-summary-value ops-summary-value-text">{!overview ? "-" : overview.readiness.status === "ready" ? "可用" : overview.readiness.status === "warning" ? "警告" : "阻断"}</div>
          <div className="ops-summary-note">{overview?.readiness.checks.find((check) => check.status !== "ready")?.message ?? "关键检查通过"}</div>
        </Card>
      </section>

      <Card className="gap-0 overflow-hidden p-0">
        <div className="ops-filter-row">
          <label className="ops-search-field">
            <Search aria-hidden="true" className="size-4" />
            <Input
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="任务 ID / 项目"
              aria-label="搜索任务 ID 或项目"
            />
          </label>
          <select value={status} onChange={(event) => setStatus(event.target.value)} aria-label="按状态筛选" className="ops-select">
            <option value="">全部状态</option>
            {Object.entries(statusLabels).map(([value, label]) => <option key={value} value={value}>{label}</option>)}
          </select>
          <select value={kind} onChange={(event) => setKind(event.target.value)} aria-label="按类型筛选" className="ops-select">
            <option value="">全部类型</option>
            {Object.entries(kindLabels).map(([value, label]) => <option key={value} value={value}>{label}</option>)}
          </select>
          <span className="ml-auto text-xs text-gray-500">{jobs.length} 条任务</span>
        </div>

        <div className="overflow-x-auto">
          <table className="ops-job-table">
            <thead>
              <tr>
                <th>任务</th><th>项目</th><th>状态</th><th>进度</th><th>Worker</th><th>耗时</th><th>更新时间</th><th aria-label="操作" />
              </tr>
            </thead>
            <tbody>
              {jobs.map((job) => (
                <tr key={job.id}>
                  <td>
                    <button type="button" className="ops-job-title" onClick={() => void openDetail(job.id)}>{job.title}</button>
                    <div className="ops-mono">{job.id}</div>
                    <div className="text-xs text-gray-500">{kindLabels[job.kind] ?? job.kind}</div>
                  </td>
                  <td>{job.projectId ? <Link className="ops-project-link" href={`/projects/${job.projectId}`}>{job.projectName ?? job.projectId}</Link> : "系统任务"}</td>
                  <td><Badge variant={statusVariant(job.status)}>{job.isStale ? "疑似中断" : statusLabels[job.status]}</Badge></td>
                  <td><div className="ops-progress"><span style={{ width: `${job.progress}%` }} /></div><span className="text-xs text-gray-500">{job.progress}%</span></td>
                  <td><span className="ops-mono">{job.workerId ? job.workerId.slice(0, 8) : "-"}</span></td>
                  <td>{formatDuration(job)}</td>
                  <td>{formatDate(job.updatedAt)}</td>
                  <td>
                    <div className="flex justify-end gap-1">
                      <Button size="icon-xs" variant="ghost" title="复制任务 ID" aria-label={`复制任务 ID ${job.id}`} onClick={() => void copyJobId(job.id)}><Copy /></Button>
                      <Button size="icon-xs" variant="ghost" title="查看详情" aria-label={`查看任务 ${job.id}`} onClick={() => void openDetail(job.id)}><Eye /></Button>
                      {job.retryable ? <Button size="icon-xs" variant="ghost" title="重试任务" aria-label={`重试任务 ${job.id}`} disabled={busyId === job.id} onClick={() => void runAction(job.id, "retry")}><RotateCcw /></Button> : null}
                      {job.status === "queued" ? <Button size="icon-xs" variant="ghost" title="取消排队" aria-label={`取消排队 ${job.id}`} disabled={busyId === job.id} onClick={() => void runAction(job.id, "cancel")}><Ban /></Button> : null}
                    </div>
                  </td>
                </tr>
              ))}
              {!loading && jobs.length === 0 ? <tr><td colSpan={8} className="py-14 text-center text-sm text-gray-500">没有符合筛选条件的任务</td></tr> : null}
              {loading && jobs.length === 0 ? <tr><td colSpan={8} className="py-14 text-center text-sm text-gray-500"><LoaderCircle className="mr-2 inline size-4 animate-spin" />正在加载任务</td></tr> : null}
            </tbody>
          </table>
        </div>
      </Card>

      <Dialog open={Boolean(detailId)} onOpenChange={(open) => { if (!open) { setDetailId(null); setDetail(null); } }}>
        <DialogContent className="max-h-[86vh] max-w-3xl overflow-y-auto p-0 sm:max-w-3xl">
          <DialogHeader className="border-b px-6 py-5 pr-14">
            <DialogTitle>{detail?.job.title ?? "任务详情"}</DialogTitle>
            <DialogDescription className="ops-mono break-all">{detailId}</DialogDescription>
          </DialogHeader>
          {!detail ? <div className="p-8 text-center text-sm text-gray-500"><LoaderCircle className="mr-2 inline size-4 animate-spin" />读取任务记录</div> : (
            <div className="space-y-6 px-6 py-5">
              <div className="grid gap-3 sm:grid-cols-4">
                <div><div className="ops-detail-label">状态</div><Badge variant={statusVariant(detail.job.status)}>{statusLabels[detail.job.status]}</Badge></div>
                <div><div className="ops-detail-label">进度</div><div className="font-semibold">{detail.job.progress}%</div></div>
                <div><div className="ops-detail-label">尝试次数</div><div className="font-semibold">{detail.job.attempts}</div></div>
                <div><div className="ops-detail-label">耗时</div><div className="font-semibold">{formatDuration(detail.job)}</div></div>
              </div>

              {detail.errorText ? <section><h3 className="ops-detail-heading">错误详情</h3><pre className="ops-error-block">{detail.errorText}</pre></section> : null}

              <section>
                <h3 className="ops-detail-heading">事件时间线</h3>
                <ol className="ops-timeline">
                  {detail.events.map((event) => <li key={event.id}><span className="ops-timeline-dot" /><div><div className="flex flex-wrap items-center gap-2"><strong>{event.eventType}</strong><span className="text-xs text-gray-500">{formatDate(event.createdAt)}</span></div>{event.message ? <p>{event.message}</p> : null}{event.metadata && Object.keys(event.metadata).length ? <code>{JSON.stringify(event.metadata)}</code> : null}</div></li>)}
                </ol>
              </section>

              {(detail.payloadSummary || detail.resultSummary) ? <section><h3 className="ops-detail-heading">运行摘要</h3><pre className="ops-summary-block">{JSON.stringify({ input: detail.payloadSummary, result: detail.resultSummary }, null, 2)}</pre></section> : null}

              <div className="flex flex-wrap justify-end gap-2 border-t pt-4">
                <Button variant="outline" onClick={() => void copyJobId(detail.job.id)}><Clipboard className="size-4" />复制任务 ID</Button>
                {detail.job.retryable ? <Button onClick={() => void runAction(detail.job.id, "retry")} disabled={busyId === detail.job.id}><RotateCcw className="size-4" />重试任务</Button> : null}
                {detail.job.status === "queued" ? <Button variant="destructive" onClick={() => void runAction(detail.job.id, "cancel")} disabled={busyId === detail.job.id}><Ban className="size-4" />取消排队</Button> : null}
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>
    </section>
  );
}
