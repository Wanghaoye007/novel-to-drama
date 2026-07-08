import { and, asc, desc, eq, inArray, isNull, lt, or, type SQL } from "drizzle-orm";
import { v4 as uuid } from "uuid";
import { db, schema } from "@/db/client";
import type { EngineJob } from "./engine-types";

type JobInsert = typeof schema.jobs.$inferInsert;
export type JobRow = typeof schema.jobs.$inferSelect;
export type JobKind = JobInsert["kind"];
export type JobStatus = NonNullable<JobInsert["status"]>;
export const STALE_RUNNING_JOB_MS = 30 * 60 * 1000;
export const STALE_QUEUED_JOB_MS = 15 * 60 * 1000;

export type JobFailureCategory =
  | "provider_quota"
  | "provider_auth"
  | "provider_rate_limit"
  | "provider_json"
  | "engine_timeout"
  | "worker_stale"
  | "engine_error"
  | "unknown";

export type JobFailureClassification = {
  category: JobFailureCategory;
  userMessage: string;
  operatorHint: string;
  retryableNow: boolean;
};

const failureDefaults: Record<JobFailureCategory, JobFailureClassification> = {
  provider_quota: {
    category: "provider_quota",
    userMessage: "LLM 额度或余额不足，任务已停止",
    operatorHint: "更换可用 key、提高 OpenRouter/模型额度，或先切到 mock 模式后再重试。",
    retryableNow: false,
  },
  provider_auth: {
    category: "provider_auth",
    userMessage: "LLM key 配置不可用，任务已停止",
    operatorHint: "检查 OPENAI_API_KEY、OPENAI_BASE_URL 和 OPENAI_MODEL 后再重试。",
    retryableNow: false,
  },
  provider_rate_limit: {
    category: "provider_rate_limit",
    userMessage: "LLM 触发限流，任务已停止",
    operatorHint: "等待限流窗口恢复，或切换备用模型/provider 后重试。",
    retryableNow: false,
  },
  provider_json: {
    category: "provider_json",
    userMessage: "模型返回格式不合格，任务已停止",
    operatorHint: "可直接重试；如果连续出现，降低单轮集数或切换 JSON 更稳定的模型。",
    retryableNow: true,
  },
  engine_timeout: {
    category: "engine_timeout",
    userMessage: "生成超时，任务已停止",
    operatorHint: "可重试；如果反复超时，降低单轮集数或检查当前模型响应速度。",
    retryableNow: true,
  },
  worker_stale: {
    category: "worker_stale",
    userMessage: "任务疑似中断，已停止",
    operatorHint: "确认 worker 进程、LLM key 和模型配置后，在页面点击重试。",
    retryableNow: true,
  },
  engine_error: {
    category: "engine_error",
    userMessage: "Engine 执行失败",
    operatorHint: "查看错误详情后重试；若连续失败，需要检查 prompt、模型或输入文本。",
    retryableNow: true,
  },
  unknown: {
    category: "unknown",
    userMessage: "任务失败",
    operatorHint: "查看错误详情后重试；若连续失败，需要检查 worker 日志。",
    retryableNow: true,
  },
};

function isJobFailureCategory(value: unknown): value is JobFailureCategory {
  return typeof value === "string" && value in failureDefaults;
}

function storedFailureFromResultJson(
  resultJson: string | null
): JobFailureClassification | null {
  if (!resultJson) return null;
  try {
    const parsed = JSON.parse(resultJson) as unknown;
    if (!parsed || typeof parsed !== "object") return null;
    const result = parsed as {
      failureCategory?: unknown;
      operatorHint?: unknown;
      retryableNow?: unknown;
    };
    if (!isJobFailureCategory(result.failureCategory)) return null;
    const base = failureDefaults[result.failureCategory];
    return {
      ...base,
      operatorHint:
        typeof result.operatorHint === "string" && result.operatorHint.trim()
          ? result.operatorHint
          : base.operatorHint,
      retryableNow:
        typeof result.retryableNow === "boolean" ? result.retryableNow : base.retryableNow,
    };
  } catch {
    return null;
  }
}

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

function ageMs(job: Pick<JobRow, "createdAt" | "updatedAt">, now = new Date()): number {
  return now.getTime() - job.updatedAt.getTime();
}

function formatAge(ms: number): string {
  const minutes = Math.max(1, Math.round(ms / 60000));
  if (minutes < 60) return `${minutes} 分钟`;
  const hours = Math.floor(minutes / 60);
  const rest = minutes % 60;
  return rest ? `${hours} 小时 ${rest} 分钟` : `${hours} 小时`;
}

function compactErrorText(value: string, limit = 1200): string {
  const compact = value.replace(/\s+/g, " ").trim();
  if (compact.length <= limit) return compact;
  return `${compact.slice(0, limit)}...`;
}

export function classifyJobFailureText(
  text: string | null | undefined
): JobFailureClassification | null {
  if (!text) return null;
  const normalized = text.toLowerCase();
  if (
    /key limit exceeded|daily limit|quota|insufficient_quota|credit balance|billing hard limit|limit exceeded/.test(
      normalized
    )
  ) {
    return failureDefaults.provider_quota;
  }
  if (
    /unauthorized|invalid api key|api key is not set|openai_api_key|\b401\b/.test(
      normalized
    )
  ) {
    return failureDefaults.provider_auth;
  }
  if (/rate limit|too many requests|\b429\b/.test(normalized)) {
    return failureDefaults.provider_rate_limit;
  }
  if (/invalid json|json that failed schema validation|response was truncated/.test(normalized)) {
    return failureDefaults.provider_json;
  }
  if (/timed out after|timeout|etimedout/.test(normalized)) {
    return failureDefaults.engine_timeout;
  }
  if (/novel-drama exited with code|traceback|exception|error/.test(normalized)) {
    return failureDefaults.engine_error;
  }
  return null;
}

export function isRunningJobStale(
  job: Pick<JobRow, "status" | "updatedAt">,
  now = new Date()
): boolean {
  return (
    job.status === "running" &&
    now.getTime() - job.updatedAt.getTime() > STALE_RUNNING_JOB_MS
  );
}

export function isQueuedJobWaitingTooLong(
  job: Pick<JobRow, "status" | "updatedAt">,
  now = new Date()
): boolean {
  return (
    job.status === "queued" &&
    now.getTime() - job.updatedAt.getTime() > STALE_QUEUED_JOB_MS
  );
}

export function isJobStale(
  job: Pick<JobRow, "status" | "createdAt" | "updatedAt">,
  now = new Date()
): boolean {
  return isRunningJobStale(job, now) || isQueuedJobWaitingTooLong(job, now);
}

export function isJobRetryable(job: Pick<JobRow, "status" | "updatedAt">): boolean {
  return job.status === "failed" || isRunningJobStale(job);
}

async function restoreRoundGenerationRetryState(job: JobRow): Promise<void> {
  if (job.kind !== "round_generation") return;
  const now = new Date();
  if (job.roundId) {
    await db
      .update(schema.rounds)
      .set({ status: "running", summaryJson: null })
      .where(eq(schema.rounds.id, job.roundId));
  }
  if (job.projectId) {
    await db
      .update(schema.projects)
      .set({ status: "running", updatedAt: now })
      .where(eq(schema.projects.id, job.projectId));
  }
}

export function jobToView(job: JobRow): EngineJob {
  const isRunningStale = isRunningJobStale(job);
  const isQueuedTooLong = isQueuedJobWaitingTooLong(job);
  const isStale = isRunningStale || isQueuedTooLong;
  const errorSource = [job.errorText, job.message, job.resultJson]
    .filter(Boolean)
    .join("\n");
  const failure = classifyJobFailureText(errorSource) ?? storedFailureFromResultJson(job.resultJson);
  const statusReason =
    failure?.userMessage ??
    (isRunningStale
      ? `worker 超过 ${formatAge(ageMs(job))} 没有心跳`
      : isQueuedTooLong
        ? `排队超过 ${formatAge(ageMs(job))}，可能没有可用 worker 或项目被暂停`
        : null);
  const operatorHint =
    failure?.operatorHint ??
    (isRunningStale
      ? "系统会把该任务标记为失败，确认 worker 和 LLM key 后可重试。"
      : isQueuedTooLong
        ? "确认 round worker/quality worker 正在运行；如果刚更换配置，可刷新后重试。"
        : null);
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
    isStale,
    isQueuedTooLong,
    retryable: job.status === "failed" || isRunningStale,
    failureCategory: failure?.category ?? null,
    statusReason,
    operatorHint,
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
  idempotencyKey,
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
  idempotencyKey?: string | null;
  message?: string | null;
  payload?: unknown;
  status?: JobStatus;
  progress?: number;
}): Promise<JobRow> {
  const normalizedIdempotencyKey = idempotencyKey?.trim() || null;
  if (normalizedIdempotencyKey) {
    const filters: SQL[] = [
      eq(schema.jobs.kind, kind),
      eq(schema.jobs.idempotencyKey, normalizedIdempotencyKey),
    ];
    if (tenantId) filters.push(eq(schema.jobs.tenantId, tenantId));
    else if (projectId) filters.push(eq(schema.jobs.projectId, projectId));
    const existingJob = await db.query.jobs.findFirst({
      where: and(...filters),
      orderBy: [desc(schema.jobs.createdAt)],
    });
    if (existingJob) return existingJob;
  }
  if (
    kind === "round_generation" &&
    roundId &&
    (status === "queued" || status === "running")
  ) {
    const activeJob = await db.query.jobs.findFirst({
      where: and(
        eq(schema.jobs.kind, kind),
        eq(schema.jobs.roundId, roundId),
        inArray(schema.jobs.status, ["queued", "running"])
      ),
    });
    if (activeJob) {
      throw new Error(
        `active job already exists for round ${roundId}: ${activeJob.id}`
      );
    }
  }
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
    idempotencyKey: normalizedIdempotencyKey,
    createdAt: now,
    updatedAt: now,
    startedAt: status === "running" ? now : null,
  };
  try {
    await db.insert(schema.jobs).values(row);
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    if (
      kind === "round_generation" &&
      roundId &&
      /jobs_active_round_generation_unique/i.test(message)
    ) {
      const activeJob = await db.query.jobs.findFirst({
        where: and(
          eq(schema.jobs.kind, kind),
          eq(schema.jobs.roundId, roundId),
          inArray(schema.jobs.status, ["queued", "running"])
        ),
      });
      throw new Error(
        `active job already exists for round ${roundId}: ${activeJob?.id ?? "unknown"}`
      );
    }
    if (
      normalizedIdempotencyKey &&
      /jobs_tenant_kind_idempotency_unique|unique/i.test(message)
    ) {
      const filters: SQL[] = [
        eq(schema.jobs.kind, kind),
        eq(schema.jobs.idempotencyKey, normalizedIdempotencyKey),
      ];
      if (tenantId) filters.push(eq(schema.jobs.tenantId, tenantId));
      else if (projectId) filters.push(eq(schema.jobs.projectId, projectId));
      const existingJob = await db.query.jobs.findFirst({
        where: and(...filters),
        orderBy: [desc(schema.jobs.createdAt)],
      });
      if (existingJob) return existingJob;
    }
    throw error;
  }
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

export async function findJob(jobId: string): Promise<JobRow | null> {
  const job = await db.query.jobs.findFirst({
    where: eq(schema.jobs.id, jobId),
  });
  return job ?? null;
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
  const queuedJobs = await db.query.jobs.findMany({
    where: and(...filters),
    orderBy: [asc(schema.jobs.createdAt)],
    limit: 25,
  });
  for (const candidate of queuedJobs) {
    const now = new Date();
    if (isQueuedJobWaitingTooLong(candidate, now)) {
      await stopStaleQueuedJob(candidate, now);
      continue;
    }

    if (candidate.kind === "round_generation" && candidate.projectId) {
      const project = await db.query.projects.findFirst({
        where: eq(schema.projects.id, candidate.projectId),
      });
      if (project?.status === "paused") continue;
    }

    const result = await db
      .update(schema.jobs)
      .set({
        status: "running",
        attempts: candidate.attempts + 1,
        progress: Math.max(candidate.progress, 5),
        message: candidate.message ?? "worker 已认领",
        startedAt: candidate.startedAt ?? now,
        updatedAt: now,
      })
      .where(and(eq(schema.jobs.id, candidate.id), eq(schema.jobs.status, "queued")));
    if (result.changes < 1) continue;

    const claimed = await db.query.jobs.findFirst({
      where: eq(schema.jobs.id, candidate.id),
    });
    if (claimed?.status === "running") return claimed;
  }
  return null;
}

async function stopStaleQueuedJob(job: JobRow, now = new Date()): Promise<void> {
  const age = now.getTime() - job.updatedAt.getTime();
  const errorText = `排队超过 ${formatAge(age)} 没有被 worker 认领，系统已停止任务。`;
  const result = {
    failureCategory: "worker_stale",
    operatorHint: "确认 worker 正常运行后，在页面点击重试。",
    recoveredAt: now.toISOString(),
    queuedSince: job.updatedAt.toISOString(),
  };

  await updateJob(job.id, {
    status: "failed",
    progress: 100,
    message: "排队超时，任务已停止",
    errorText,
    result,
    finishedAt: now,
  });

  if (job.roundId) {
    await db
      .update(schema.rounds)
      .set({
        status: "failed",
        summaryJson: JSON.stringify(
          {
            error: errorText,
            ...result,
          },
          null,
          2
        ),
      })
      .where(eq(schema.rounds.id, job.roundId));
  }
  if (job.projectId) {
    await db
      .update(schema.projects)
      .set({ status: "failed", updatedAt: now })
      .where(eq(schema.projects.id, job.projectId));
  }
}

export async function requeueRetryableJob(jobId: string): Promise<JobRow> {
  const job = await findJob(jobId);
  if (!job) throw new Error("job not found");
  if (!isJobRetryable(job)) {
    throw new Error(
      `only failed or stale running jobs can be retried; current status: ${job.status}`
    );
  }
  const reason = job.status === "failed" ? "重试" : "恢复队列";

  await restoreRoundGenerationRetryState(job);
  await updateJob(job.id, {
    status: "queued",
    progress: 0,
    message: `等待 worker ${reason} · 已尝试 ${job.attempts} 次`,
    errorText: null,
    result: null,
    startedAt: null,
    finishedAt: null,
  });

  const retried = await findJob(job.id);
  if (!retried) throw new Error("job retry failed");
  return retried;
}

export async function requeueInterruptedRunningJobs({
  kind,
  olderThanMs = 0,
}: {
  kind?: JobKind;
  olderThanMs?: number;
} = {}): Promise<{ requeued: number }> {
  const cutoff = new Date(Date.now() - Math.max(0, olderThanMs));
  const filters: SQL[] = [eq(schema.jobs.status, "running"), lt(schema.jobs.updatedAt, cutoff)];
  if (kind) filters.push(eq(schema.jobs.kind, kind));
  const runningJobs = await db.query.jobs.findMany({
    where: and(...filters),
    orderBy: [asc(schema.jobs.updatedAt)],
  });

  for (const job of runningJobs) {
    await updateJob(job.id, {
      status: "queued",
      progress: 0,
      message: `worker 启动后恢复队列 · 已尝试 ${job.attempts} 次`,
      errorText: null,
      result: null,
      startedAt: null,
      finishedAt: null,
    });

    if (job.roundId) {
      await db
        .update(schema.rounds)
        .set({ status: "running", summaryJson: null })
        .where(eq(schema.rounds.id, job.roundId));
    }
    if (job.projectId) {
      await db
        .update(schema.projects)
        .set({ status: "running", updatedAt: new Date() })
        .where(eq(schema.projects.id, job.projectId));
    }
  }

  return { requeued: runningJobs.length };
}

export async function reconcileStaleJobs({
  olderThanMs = STALE_RUNNING_JOB_MS,
}: {
  olderThanMs?: number;
} = {}): Promise<{ failedRunning: number }> {
  const cutoff = new Date(Date.now() - olderThanMs);
  const staleJobs = await db.query.jobs.findMany({
    where: and(eq(schema.jobs.status, "running"), lt(schema.jobs.updatedAt, cutoff)),
  });
  const now = new Date();

  for (const job of staleJobs) {
    const failure = classifyJobFailureText(
      [job.errorText, job.message, job.resultJson].filter(Boolean).join("\n")
    );
    const fallbackMessage = `worker 超过 ${formatAge(now.getTime() - job.updatedAt.getTime())} 没有心跳，系统已停止自动重排。`;
    const errorText = failure
      ? `${failure.userMessage}。${failure.operatorHint}`
      : fallbackMessage;
    const result = {
      failureCategory: failure?.category ?? "worker_stale",
      operatorHint:
        failure?.operatorHint ??
        "确认 worker 进程、LLM key 和模型配置后，在页面点击重试。",
      recoveredAt: now.toISOString(),
      staleSince: job.updatedAt.toISOString(),
    };

    await updateJob(job.id, {
      status: "failed",
      progress: 100,
      message: failure ? failure.userMessage : "任务疑似中断，已停止",
      errorText,
      result,
      finishedAt: now,
    });

    if (job.roundId) {
      await db
        .update(schema.rounds)
        .set({
          status: "failed",
          summaryJson: JSON.stringify(
            {
              error: errorText,
              ...result,
            },
            null,
            2
          ),
        })
        .where(eq(schema.rounds.id, job.roundId));
    }
    if (job.projectId) {
      await db
        .update(schema.projects)
        .set({ status: "failed", updatedAt: now })
        .where(eq(schema.projects.id, job.projectId));
    }
  }

  return { failedRunning: staleJobs.length };
}

export async function requeueStaleRunningJobs({
  olderThanMs = STALE_RUNNING_JOB_MS,
}: {
  olderThanMs?: number;
} = {}): Promise<void> {
  await reconcileStaleJobs({ olderThanMs });
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
  error: unknown,
  values: {
    message?: string | null;
    errorText?: string | null;
    result?: unknown;
  } = {}
): Promise<void> {
  const rawMessage = error instanceof Error ? error.message : String(error);
  const failure = classifyJobFailureText(rawMessage);
  const message = values.errorText ?? (
    failure
      ? `${failure.userMessage}。${failure.operatorHint}`
      : compactErrorText(rawMessage)
  );
  await updateJob(jobId, {
    status: "failed",
    progress: 100,
    message: values.message ?? failure?.userMessage ?? "失败",
    errorText: message,
    result:
      values.result ??
      (failure
        ? {
            failureCategory: failure.category,
            operatorHint: failure.operatorHint,
            retryableNow: failure.retryableNow,
          }
        : undefined),
    finishedAt: new Date(),
  });
}

export async function listJobs({
  projectId,
  tenantId,
  ownerUserId,
  kind,
  limit = 20,
}: {
  projectId?: string;
  tenantId?: string;
  ownerUserId?: string;
  kind?: JobKind;
  limit?: number;
} = {}): Promise<JobRow[]> {
  await reconcileStaleJobs();
  const filters: SQL[] = [];
  if (projectId) filters.push(eq(schema.jobs.projectId, projectId));
  if (tenantId) filters.push(eq(schema.jobs.tenantId, tenantId));
  if (ownerUserId && tenantId) {
    const ownedProjects = await db.query.projects.findMany({
      columns: { id: true },
      where: and(
        eq(schema.projects.tenantId, tenantId),
        eq(schema.projects.ownerUserId, ownerUserId)
      ),
    });
    const ownedProjectIds = ownedProjects.map((project) => project.id);
    if (projectId && !ownedProjectIds.includes(projectId)) return [];
    if (!projectId) {
      filters.push(
        ownedProjectIds.length > 0
          ? or(isNull(schema.jobs.projectId), inArray(schema.jobs.projectId, ownedProjectIds))!
          : isNull(schema.jobs.projectId)
      );
    }
  }
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
