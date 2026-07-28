import { asc, desc, eq } from "drizzle-orm";
import { v4 as uuid } from "uuid";
import { db, schema } from "@/db/client";

export const DEFAULT_WORKER_STALE_MS = 30_000;

export type JobEventType =
  | "created"
  | "claimed"
  | "progress"
  | "retried"
  | "succeeded"
  | "failed"
  | "cancelled"
  | "recovered";

export type WorkerView = {
  id: string;
  status: "online" | "offline";
  currentJobId: string | null;
  startedAt: string;
  heartbeatAt: string;
  stoppedAt: string | null;
  hostname: string;
  pid: number;
  version: string;
};

function compactMetadata(value: unknown): string | null {
  if (value == null) return null;
  const serialized = JSON.stringify(value);
  return serialized.length <= 2_000
    ? serialized
    : JSON.stringify({ truncated: true });
}

export async function registerWorkerInstance({
  id,
  hostname,
  pid,
  version,
  now = new Date(),
}: {
  id: string;
  hostname: string;
  pid: number;
  version: string;
  now?: Date;
}): Promise<void> {
  await db
    .insert(schema.workerInstances)
    .values({
      id,
      status: "online",
      currentJobId: null,
      hostname,
      pid,
      version,
      startedAt: now,
      heartbeatAt: now,
      stoppedAt: null,
    })
    .onConflictDoUpdate({
      target: schema.workerInstances.id,
      set: {
        status: "online",
        currentJobId: null,
        hostname,
        pid,
        version,
        startedAt: now,
        heartbeatAt: now,
        stoppedAt: null,
      },
    });
}

export async function heartbeatWorkerInstance(
  workerId: string,
  options: { currentJobId?: string | null; now?: Date } = {}
): Promise<void> {
  const update: Partial<typeof schema.workerInstances.$inferInsert> = {
    status: "online",
    heartbeatAt: options.now ?? new Date(),
    stoppedAt: null,
  };
  if (Object.prototype.hasOwnProperty.call(options, "currentJobId")) {
    update.currentJobId = options.currentJobId ?? null;
  }
  await db
    .update(schema.workerInstances)
    .set(update)
    .where(eq(schema.workerInstances.id, workerId));
}

export async function stopWorkerInstance(
  workerId: string,
  now = new Date()
): Promise<void> {
  await db
    .update(schema.workerInstances)
    .set({
      status: "offline",
      currentJobId: null,
      heartbeatAt: now,
      stoppedAt: now,
    })
    .where(eq(schema.workerInstances.id, workerId));
}

export async function listWorkerViews({
  staleAfterMs = Number(
    process.env.NOVEL_DRAMA_WORKER_STALE_MS ?? DEFAULT_WORKER_STALE_MS
  ),
  now = new Date(),
}: {
  staleAfterMs?: number;
  now?: Date;
} = {}): Promise<WorkerView[]> {
  const rows = await db.query.workerInstances.findMany({
    orderBy: [desc(schema.workerInstances.heartbeatAt)],
  });
  const threshold = Number.isFinite(staleAfterMs)
    ? Math.max(1_000, staleAfterMs)
    : DEFAULT_WORKER_STALE_MS;
  return rows.map((row) => ({
    id: row.id,
    status:
      row.status === "online" &&
      now.getTime() - row.heartbeatAt.getTime() <= threshold
        ? "online"
        : "offline",
    currentJobId: row.currentJobId,
    startedAt: row.startedAt.toISOString(),
    heartbeatAt: row.heartbeatAt.toISOString(),
    stoppedAt: row.stoppedAt?.toISOString() ?? null,
    hostname: row.hostname,
    pid: row.pid,
    version: row.version,
  }));
}

export async function appendJobEvent({
  jobId,
  eventType,
  message,
  metadata,
  now = new Date(),
}: {
  jobId: string;
  eventType: JobEventType;
  message?: string | null;
  metadata?: unknown;
  now?: Date;
}): Promise<void> {
  await db.insert(schema.jobEvents).values({
    id: uuid(),
    jobId,
    eventType,
    message: message?.trim() || null,
    metadataJson: compactMetadata(metadata),
    createdAt: now,
  });
}

export async function listJobEvents(jobId: string) {
  return db.query.jobEvents.findMany({
    where: eq(schema.jobEvents.jobId, jobId),
    orderBy: [asc(schema.jobEvents.createdAt)],
  });
}
