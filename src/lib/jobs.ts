import { and, desc, eq, type SQL } from "drizzle-orm";
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
    roundId: job.roundId,
    title: job.title,
    progress: job.progress,
    message: job.message,
    errorText: job.errorText,
    resultJson: job.resultJson,
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
  roundId,
  message,
  status = "running",
  progress = 5,
}: {
  kind: JobKind;
  title: string;
  projectId?: string | null;
  roundId?: string | null;
  message?: string | null;
  status?: JobStatus;
  progress?: number;
}): Promise<JobRow> {
  const now = new Date();
  const row: JobInsert = {
    id: uuid(),
    kind,
    status,
    projectId,
    roundId,
    title,
    progress: boundedProgress(progress),
    message,
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
  if ("result" in values) update.resultJson = serializeResult(values.result);
  if ("startedAt" in values) update.startedAt = values.startedAt;
  if ("finishedAt" in values) update.finishedAt = values.finishedAt;

  await db.update(schema.jobs).set(update).where(eq(schema.jobs.id, jobId));
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
  kind,
  limit = 20,
}: {
  projectId?: string;
  kind?: JobKind;
  limit?: number;
} = {}): Promise<JobRow[]> {
  const filters: SQL[] = [];
  if (projectId) filters.push(eq(schema.jobs.projectId, projectId));
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
