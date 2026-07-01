import { and, asc, desc, eq, lt, type SQL } from "drizzle-orm";
import { v4 as uuid } from "uuid";
import { db, schema } from "@/db/client";
import type { EngineJob } from "./engine-types";

type JobInsert = typeof schema.jobs.$inferInsert;
export type JobRow = typeof schema.jobs.$inferSelect;
export type JobKind = JobInsert["kind"];
export type JobStatus = NonNullable<JobInsert["status"]>;

function boundedProgress(value: number): number {
  if (!Number.isFinite(value)) return 0;
  return Math.max(0, Math.min(100, Math.round(value)));
}

function serializeResult(result: unknown): string | null {
  if (result == null) return null;
  return JSON.stringify(result, null, 2);
}

function dateToIso(value: Date | null): string | null {
  return value ? value.toISOString() : null;
}

export function jobToView(job: JobRow): EngineJob {
  return {
    id: job.id,
    kind: job.kind,
    status: job.status,
    projectId: job.projectId,
    tenantId: job.tenantId,
    roundId: job.roundId,
    title: job.title,
    progress: job.progress,
    message: job.message,
    errorText: job.errorText,
    payloadJson: job.payloadJson,
    resultJson: job.resultJson,
    attempts: job.attempts,
    createdAt: job.createdAt.toISOString(),
    updatedAt: job.updatedAt.toISOString(),
    startedAt: dateToIso(job.startedAt),
    finishedAt: dateToIso(job.finishedAt),
  };
}

export async function createJob({
  kind,
  title,
  projectId,
  tenantId,
  roundId,
  message,
  payload,
  status = "queued",
  progress = 0,
}: {
  kind: JobKind;
  title: string;
  projectId?: string | null;
  tenantId?: string | null;
  roundId?: string | null;
  message?: string | null;
  payload?: unknown;
  status?: JobStatus;
  progress?: number;
}): Promise<JobRow> {
  const now = new Date();
  const row: JobInsert = {
    id: uuid(),
    kind,
    status,
    projectId,
    tenantId,
    roundId,
    title,
    progress: boundedProgress(progress),
    message,
    payloadJson: serializeResult(payload),
    createdAt: now,
    updatedAt: now,
    startedAt: status === "running" ? now : null,
  };
  await db.insert(schema.jobs).values(row);
  const created = await db.query.jobs.findFirst({
    where: eq(schema.jobs.id, row.id),
  });
  if (!created) throw new Error("job insert failed");
  return created;
}

export async function updateJob(
  jobId: string | null | undefined,
  values: {
    status?: JobStatus;
    progress?: number;
    message?: string | null;
    errorText?: string | null;
    payload?: unknown;
    result?: unknown;
    startedAt?: Date | null;
    finishedAt?: Date | null;
  }
): Promise<void> {
  if (!jobId) return;
  const update: Partial<JobInsert> = {
    updatedAt: new Date(),
  };
  if (values.status) update.status = values.status;
  if (values.progress != null) update.progress = boundedProgress(values.progress);
  if ("message" in values) update.message = values.message;
  if ("errorText" in values) update.errorText = values.errorText;
  if ("payload" in values) update.payloadJson = serializeResult(values.payload);
  if ("result" in values) update.resultJson = serializeResult(values.result);
  if ("startedAt" in values) update.startedAt = values.startedAt;
  if ("finishedAt" in values) update.finishedAt = values.finishedAt;

  await db.update(schema.jobs).set(update).where(eq(schema.jobs.id, jobId));
}

export function parseJobPayload<T>(job: JobRow): T {
  if (!job.payloadJson) {
    throw new Error(`job ${job.id} is missing payload`);
  }
  return JSON.parse(job.payloadJson) as T;
}

export async function claimNextQueuedJob({
  kind,
}: {
  kind?: JobKind;
} = {}): Promise<JobRow | null> {
  const filters: SQL[] = [eq(schema.jobs.status, "queued")];
  if (kind) filters.push(eq(schema.jobs.kind, kind));
  const job = await db.query.jobs.findFirst({
    where: and(...filters),
    orderBy: [asc(schema.jobs.createdAt)],
  });
  if (!job) return null;

  const now = new Date();
  await db
    .update(schema.jobs)
    .set({
      status: "running",
      attempts: job.attempts + 1,
      progress: Math.max(job.progress, 5),
      message: job.message ?? "worker 已认领",
      startedAt: job.startedAt ?? now,
      updatedAt: now,
    })
    .where(and(eq(schema.jobs.id, job.id), eq(schema.jobs.status, "queued")));

  const claimed = await db.query.jobs.findFirst({
    where: eq(schema.jobs.id, job.id),
  });
  return claimed?.status === "running" ? claimed : null;
}

export async function requeueStaleRunningJobs({
  olderThanMs = 30 * 60 * 1000,
}: {
  olderThanMs?: number;
} = {}): Promise<void> {
  const cutoff = new Date(Date.now() - olderThanMs);
  await db
    .update(schema.jobs)
    .set({
      status: "queued",
      progress: 0,
      message: "worker interrupted; requeued",
      updatedAt: new Date(),
      startedAt: null,
    })
    .where(
      and(eq(schema.jobs.status, "running"), lt(schema.jobs.updatedAt, cutoff))
    );
}

export async function succeedJob(
  jobId: string | null | undefined,
  values: { message?: string | null; result?: unknown } = {}
): Promise<void> {
  await updateJob(jobId, {
    status: "succeeded",
    progress: 100,
    message: values.message ?? "完成",
    errorText: null,
    result: values.result,
    finishedAt: new Date(),
  });
}

export async function failJob(
  jobId: string | null | undefined,
  error: unknown
): Promise<void> {
  const message = error instanceof Error ? error.message : String(error);
  await updateJob(jobId, {
    status: "failed",
    progress: 100,
    message: "失败",
    errorText: message,
    finishedAt: new Date(),
  });
}

export async function listJobs({
  projectId,
  tenantId,
  kind,
  limit = 20,
}: {
  projectId?: string;
  tenantId?: string;
  kind?: JobKind;
  limit?: number;
} = {}): Promise<JobRow[]> {
  const filters: SQL[] = [];
  if (projectId) filters.push(eq(schema.jobs.projectId, projectId));
  if (tenantId) filters.push(eq(schema.jobs.tenantId, tenantId));
  if (kind) filters.push(eq(schema.jobs.kind, kind));
  return db.query.jobs.findMany({
    where: filters.length ? and(...filters) : undefined,
    orderBy: [desc(schema.jobs.createdAt)],
    limit: Math.max(1, Math.min(100, Math.floor(limit))),
  });
}

export async function listJobViews(
  options: Parameters<typeof listJobs>[0] = {}
): Promise<EngineJob[]> {
  const rows = await listJobs(options);
  return rows.map(jobToView);
}
