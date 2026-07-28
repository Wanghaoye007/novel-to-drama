import { and, desc, eq, inArray, isNull, or } from "drizzle-orm";
import { db, schema } from "@/db/client";
import { deploymentReadiness } from "./deployment-readiness";
import {
  findJob,
  isJobRetryable,
  jobToView,
  requeueRetryableJob,
  type JobKind,
  type JobRow,
  type JobStatus,
} from "./jobs";
import {
  appendJobEvent,
  listJobEvents,
  listWorkerViews,
} from "./ops-observability";
import type { PlatformContext } from "./platform-context";

export class OpsConsoleError extends Error {
  constructor(
    message: string,
    readonly status: number
  ) {
    super(message);
    this.name = "OpsConsoleError";
  }
}

export type OpsJobListItem = {
  id: string;
  kind: JobKind;
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

export type OpsJobFilters = {
  status?: JobStatus;
  kind?: JobKind;
  query?: string;
  limit?: number;
};

async function ownedProjects(context: PlatformContext) {
  return db.query.projects.findMany({
    columns: { id: true, name: true },
    where: and(
      eq(schema.projects.tenantId, context.tenant.id),
      eq(schema.projects.ownerUserId, context.user.id)
    ),
  });
}

async function ownedJobRows(context: PlatformContext): Promise<{
  rows: JobRow[];
  projectNames: Map<string, string>;
}> {
  const projects = await ownedProjects(context);
  const projectIds = projects.map((project) => project.id);
  const projectScope = projectIds.length
    ? or(isNull(schema.jobs.projectId), inArray(schema.jobs.projectId, projectIds))!
    : isNull(schema.jobs.projectId);
  const rows = await db.query.jobs.findMany({
    where: and(eq(schema.jobs.tenantId, context.tenant.id), projectScope),
    orderBy: [desc(schema.jobs.createdAt)],
  });
  return {
    rows,
    projectNames: new Map(projects.map((project) => [project.id, project.name])),
  };
}

function toListItem(
  row: JobRow,
  projectNames: Map<string, string>
): OpsJobListItem {
  const view = jobToView(row);
  return {
    id: row.id,
    kind: row.kind,
    status: row.status,
    title: row.title,
    projectId: row.projectId,
    projectName: row.projectId ? projectNames.get(row.projectId) ?? null : null,
    roundId: row.roundId,
    workerId: row.workerId,
    progress: row.progress,
    attempts: row.attempts,
    failureCategory: view.failureCategory ?? null,
    statusReason: view.statusReason ?? null,
    message: row.message,
    retryable: view.retryable,
    isStale: view.isStale,
    createdAt: row.createdAt.toISOString(),
    startedAt: row.startedAt?.toISOString() ?? null,
    updatedAt: row.updatedAt.toISOString(),
    finishedAt: row.finishedAt?.toISOString() ?? null,
  };
}

function safeSummary(value: string | null): Record<string, unknown> | null {
  if (!value) return null;
  try {
    const parsed = JSON.parse(value) as unknown;
    if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) return null;
    const source = parsed as Record<string, unknown>;
    const allowed = [
      "llmModel",
      "generationVariant",
      "repairBudget",
      "episodesPerRound",
      "targetEpisodeCount",
      "roundNum",
      "variants",
      "format",
      "failureCategory",
      "operatorHint",
      "runtimeMs",
      "llmCalls",
      "qualityStatus",
      "targetEpisodeRange",
      "partialEpisodes",
      "resumeAttempt",
      "autoResume",
    ];
    return Object.fromEntries(
      allowed
        .filter((key) => Object.prototype.hasOwnProperty.call(source, key))
        .map((key) => [key, source[key]])
    );
  } catch {
    return null;
  }
}

function safeEventMetadata(value: string | null): Record<string, unknown> | null {
  if (!value) return null;
  try {
    const parsed = JSON.parse(value) as unknown;
    if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) return null;
    const source = parsed as Record<string, unknown>;
    const allowed = [
      "workerId",
      "attempts",
      "progress",
      "failureCategory",
      "reason",
    ];
    return Object.fromEntries(
      allowed
        .filter((key) => Object.prototype.hasOwnProperty.call(source, key))
        .map((key) => [key, source[key]])
    );
  } catch {
    return null;
  }
}

async function accessibleJob(
  context: PlatformContext,
  jobId: string
): Promise<JobRow> {
  const job = await findJob(jobId);
  if (!job || job.tenantId !== context.tenant.id) {
    throw new OpsConsoleError("not found", 404);
  }
  if (job.projectId) {
    const project = await db.query.projects.findFirst({
      columns: { id: true },
      where: and(
        eq(schema.projects.id, job.projectId),
        eq(schema.projects.tenantId, context.tenant.id),
        eq(schema.projects.ownerUserId, context.user.id)
      ),
    });
    if (!project) throw new OpsConsoleError("not found", 404);
  }
  return job;
}

export async function listOpsJobs(
  context: PlatformContext,
  filters: OpsJobFilters = {}
): Promise<OpsJobListItem[]> {
  const { rows, projectNames } = await ownedJobRows(context);
  const query = filters.query?.trim().toLocaleLowerCase("zh-CN") ?? "";
  const limit = Math.max(1, Math.min(100, Math.floor(filters.limit ?? 50)));
  return rows
    .filter((row) => !filters.status || row.status === filters.status)
    .filter((row) => !filters.kind || row.kind === filters.kind)
    .filter((row) => {
      if (!query) return true;
      return [
        row.id,
        row.title,
        row.projectId ? projectNames.get(row.projectId) : null,
      ]
        .filter(Boolean)
        .some((value) => String(value).toLocaleLowerCase("zh-CN").includes(query));
    })
    .slice(0, limit)
    .map((row) => toListItem(row, projectNames));
}

export async function getOpsOverview(context: PlatformContext) {
  const { rows, projectNames } = await ownedJobRows(context);
  const items = rows.map((row) => toListItem(row, projectNames));
  const counts: Record<JobStatus | "total", number> = {
    total: items.length,
    queued: 0,
    running: 0,
    succeeded: 0,
    failed: 0,
    cancelled: 0,
  };
  for (const item of items) counts[item.status] += 1;
  const readiness = deploymentReadiness();
  return {
    counts,
    workers: await listWorkerViews(),
    readiness: {
      status: readiness.status,
      checks: readiness.checks.map(({ key, status, message }) => ({
        key,
        status,
        message,
      })),
    },
    recentFailures: items.filter((item) => item.status === "failed").slice(0, 5),
    timestamp: new Date().toISOString(),
  };
}

export async function getOpsJobDetail(
  context: PlatformContext,
  jobId: string
) {
  const job = await accessibleJob(context, jobId);
  const project = job.projectId
    ? await db.query.projects.findFirst({
        columns: { name: true },
        where: eq(schema.projects.id, job.projectId),
      })
    : null;
  const events = await listJobEvents(job.id);
  return {
    job: toListItem(job, new Map(job.projectId ? [[job.projectId, project?.name ?? ""]] : [])),
    errorText: job.errorText?.slice(0, 4_000) ?? null,
    payloadSummary: safeSummary(job.payloadJson),
    resultSummary: safeSummary(job.resultJson),
    events: events.map((event) => ({
      id: event.id,
      eventType: event.eventType,
      message: event.message,
      metadata: safeEventMetadata(event.metadataJson),
      createdAt: event.createdAt.toISOString(),
    })),
  };
}

export function toOpsJobActionResult(job: JobRow) {
  return {
    id: job.id,
    status: job.status,
    progress: job.progress,
    attempts: job.attempts,
    updatedAt: job.updatedAt.toISOString(),
  };
}

export async function retryOpsJob(context: PlatformContext, jobId: string) {
  const job = await accessibleJob(context, jobId);
  if (!isJobRetryable(job)) {
    throw new OpsConsoleError(`当前状态 ${job.status} 不能重试`, 409);
  }
  return requeueRetryableJob(job.id);
}

export async function cancelQueuedJob(
  context: PlatformContext,
  jobId: string
) {
  const job = await accessibleJob(context, jobId);
  if (job.status !== "queued") {
    throw new OpsConsoleError("只能取消仍在排队的任务，运行中任务不会被强制终止", 409);
  }
  const now = new Date();
  const result = await db
    .update(schema.jobs)
    .set({
      status: "cancelled",
      message: "运营已取消排队任务",
      errorText: null,
      finishedAt: now,
      updatedAt: now,
    })
    .where(and(eq(schema.jobs.id, job.id), eq(schema.jobs.status, "queued")));
  if (result.changes !== 1) {
    throw new OpsConsoleError("任务状态已经变化，请刷新后重试", 409);
  }
  await appendJobEvent({
    jobId: job.id,
    eventType: "cancelled",
    message: "运营已取消排队任务",
    now,
  });
  if (job.kind === "round_generation") {
    if (job.roundId) {
      await db
        .update(schema.rounds)
        .set({
          status: "failed",
          summaryJson: JSON.stringify({ cancelled: true, jobId: job.id }),
        })
        .where(eq(schema.rounds.id, job.roundId));
    }
    if (job.projectId) {
      await db
        .update(schema.projects)
        .set({ status: "paused", updatedAt: now })
        .where(eq(schema.projects.id, job.projectId));
    }
  }
  return accessibleJob(context, job.id);
}
