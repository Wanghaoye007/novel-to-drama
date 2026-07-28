import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import { mkdtempSync, rmSync } from "node:fs";
import os from "node:os";
import path from "node:path";
import test from "node:test";

const repoRoot = path.resolve(import.meta.dirname, "..");
const tempRoot = mkdtempSync(path.join(os.tmpdir(), "novel-drama-ops-console-"));
process.env.NOVEL_DRAMA_DB_PATH = path.join(tempRoot, "db.sqlite");
process.env.NOVEL_DRAMA_BACKFILL_LEGACY_TENANT = "0";
process.env.NOVEL_DRAMA_TRUST_IDENTITY_HEADERS = "1";

execFileSync("npx", ["drizzle-kit", "migrate"], {
  cwd: repoRoot,
  env: process.env,
  stdio: "ignore",
});

test.after(() => {
  rmSync(tempRoot, { recursive: true, force: true });
});

test("worker heartbeat records process identity and current job", async () => {
  const { db, schema } = await import("../src/db/client");
  const {
    heartbeatWorkerInstance,
    listWorkerViews,
    registerWorkerInstance,
  } = await import("../src/lib/ops-observability");
  const startedAt = new Date("2026-07-28T04:00:00.000Z");
  const heartbeatAt = new Date("2026-07-28T04:00:05.000Z");

  await registerWorkerInstance({
    id: "worker-ops-1",
    hostname: "zeabur-node",
    pid: 4321,
    version: "commit-abc",
    now: startedAt,
  });
  await heartbeatWorkerInstance("worker-ops-1", {
    currentJobId: "job-ops-current",
    now: heartbeatAt,
  });

  const stored = await db.query.workerInstances.findFirst({
    where: (table, { eq }) => eq(table.id, "worker-ops-1"),
  });
  const views = await listWorkerViews({ now: heartbeatAt });

  assert.equal(stored?.hostname, "zeabur-node");
  assert.equal(stored?.pid, 4321);
  assert.equal(stored?.version, "commit-abc");
  assert.equal(stored?.currentJobId, "job-ops-current");
  assert.equal(views[0]?.status, "online");
  assert.equal(views[0]?.heartbeatAt, heartbeatAt.toISOString());
  assert.ok(schema.workerInstances);
});

test("worker view marks a heartbeat older than 30 seconds offline", async () => {
  const { listWorkerViews, registerWorkerInstance } = await import(
    "../src/lib/ops-observability"
  );
  const heartbeatAt = new Date("2026-07-28T05:00:00.000Z");
  await registerWorkerInstance({
    id: "worker-ops-stale",
    hostname: "zeabur-node",
    pid: 9876,
    version: "commit-def",
    now: heartbeatAt,
  });

  const views = await listWorkerViews({
    now: new Date(heartbeatAt.getTime() + 31_000),
  });
  const stale = views.find((worker) => worker.id === "worker-ops-stale");

  assert.equal(stale?.status, "offline");
});

test("claiming and finishing a job records worker attribution and event history", async () => {
  const { db, schema } = await import("../src/db/client");
  const { registerWorkerInstance } = await import("../src/lib/ops-observability");
  const {
    claimNextQueuedJob,
    createJob,
    listJobEvents,
    succeedJob,
  } = await import("../src/lib/jobs");

  await registerWorkerInstance({
    id: "worker-ops-claim",
    hostname: "zeabur-node",
    pid: 777,
    version: "commit-ghi",
  });
  const job = await createJob({
    kind: "delivery_export",
    title: "运维事件测试",
    message: "等待 worker",
  });
  const claimed = await claimNextQueuedJob({ workerId: "worker-ops-claim" });
  await succeedJob(job.id, { message: "导出完成" });

  const stored = await db.query.jobs.findFirst({
    where: (table, { eq }) => eq(table.id, job.id),
  });
  const events = await listJobEvents(job.id);

  assert.equal(claimed?.id, job.id);
  assert.equal(stored?.workerId, "worker-ops-claim");
  assert.deepEqual(
    events.map((event) => event.eventType),
    ["created", "claimed", "succeeded"]
  );
  assert.ok(schema.jobEvents);
});

test("progress milestones append one compact event", async () => {
  const {
    claimNextQueuedJob,
    createJob,
    listJobEvents,
    updateJob,
  } = await import("../src/lib/jobs");
  const job = await createJob({
    kind: "video_brief_export",
    title: "进度事件测试",
  });
  await claimNextQueuedJob();
  await updateJob(job.id, { progress: 34, message: "生成中" });
  await updateJob(job.id, { progress: 39, message: "仍在生成" });

  const events = await listJobEvents(job.id);
  assert.deepEqual(
    events.map((event) => event.eventType),
    ["created", "claimed", "progress"]
  );
});

test("stale queued jobs append a failure event when the worker rejects them", async () => {
  const { db, schema } = await import("../src/db/client");
  const { claimNextQueuedJob, listJobEvents } = await import("../src/lib/jobs");
  const stale = new Date(Date.now() - 16 * 60 * 1000);
  await db.insert(schema.jobs).values({
    id: "job-ops-stale-queued",
    kind: "localization_export",
    status: "queued",
    title: "过期排队任务",
    progress: 0,
    attempts: 0,
    createdAt: stale,
    updatedAt: stale,
  });

  await claimNextQueuedJob({ kind: "localization_export" });
  const events = await listJobEvents("job-ops-stale-queued");

  assert.equal(events.at(-1)?.eventType, "failed");
  assert.match(events.at(-1)?.message ?? "", /排队超时/);
});

function opsRequest(pathname: string, email: string, tenantSlug: string): Request {
  return new Request(`http://localhost${pathname}`, {
    headers: {
      "x-novel-user-email": email,
      "x-novel-tenant": tenantSlug,
      "x-novel-tenant-name": "Ops Console Tenant",
    },
  });
}

test("ops overview and job list are owner-scoped and redact job blobs", async () => {
  const { db, schema } = await import("../src/db/client");
  const { createJob, failJob, updateJob } = await import("../src/lib/jobs");
  const { resolvePlatformContextFromInput } = await import(
    "../src/lib/platform-context"
  );
  const { registerWorkerInstance } = await import("../src/lib/ops-observability");
  const overviewRoute = await import("../src/app/api/ops/overview/route");
  const jobsRoute = await import("../src/app/api/ops/jobs/route");
  const owner = await resolvePlatformContextFromInput({
    email: "ops-owner@example.com",
    tenantSlug: "ops-console-tenant",
    tenantName: "Ops Console Tenant",
  });
  const other = await resolvePlatformContextFromInput({
    email: "ops-other@example.com",
    tenantSlug: "ops-console-tenant",
    tenantName: "Ops Console Tenant",
  });
  const now = new Date();
  await db.insert(schema.projects).values([
    {
      id: "project-ops-visible",
      tenantId: owner.tenant.id,
      ownerUserId: owner.user.id,
      name: "可见项目",
      novelText: "可见原文",
      targetEpisodeCount: 5,
      status: "running",
      createdAt: now,
      updatedAt: now,
    },
    {
      id: "project-ops-hidden",
      tenantId: other.tenant.id,
      ownerUserId: other.user.id,
      name: "隐藏项目",
      novelText: "隐藏原文",
      targetEpisodeCount: 5,
      status: "running",
      createdAt: now,
      updatedAt: now,
    },
  ]);
  const visible = await createJob({
    kind: "round_generation",
    tenantId: owner.tenant.id,
    projectId: "project-ops-visible",
    title: "可见生成任务",
    payload: { novelText: "绝不能出现在列表", llmModel: "safe-model" },
  });
  await updateJob(visible.id, {
    result: { rawProviderResponse: "绝不能出现在列表", runtimeMs: 1234 },
  });
  const failed = await createJob({
    kind: "delivery_export",
    tenantId: owner.tenant.id,
    projectId: "project-ops-visible",
    title: "可见失败任务",
  });
  await failJob(failed.id, new Error("provider request timed out"));
  await createJob({
    kind: "delivery_export",
    tenantId: other.tenant.id,
    projectId: "project-ops-hidden",
    title: "隐藏任务",
  });
  await registerWorkerInstance({
    id: "worker-ops-api",
    hostname: "zeabur-node",
    pid: 2468,
    version: "api-test",
  });

  const listResponse = await jobsRoute.GET(
    opsRequest("/api/ops/jobs?limit=50", owner.user.email, owner.tenant.slug) as never
  );
  const listBody = (await listResponse.json()) as {
    jobs: Array<Record<string, unknown>>;
  };
  const overviewResponse = await overviewRoute.GET(
    opsRequest("/api/ops/overview", owner.user.email, owner.tenant.slug) as never
  );
  const overview = (await overviewResponse.json()) as {
    counts: Record<string, number>;
    workers: Array<{ id: string; status: string }>;
  };

  assert.equal(listResponse.status, 200);
  assert.ok(listBody.jobs.some((job) => job.id === visible.id));
  assert.equal(listBody.jobs.some((job) => job.title === "隐藏任务"), false);
  assert.equal("payloadJson" in listBody.jobs[0]!, false);
  assert.equal("resultJson" in listBody.jobs[0]!, false);
  assert.equal(JSON.stringify(listBody).includes("绝不能出现在列表"), false);
  assert.equal(overview.counts.failed, 1);
  assert.ok(overview.workers.some((worker) => worker.id === "worker-ops-api"));
});

test("ops detail, retry, and queued cancellation enforce safe state transitions", async () => {
  const { db, schema } = await import("../src/db/client");
  const { claimNextQueuedJob, createJob, failJob } = await import(
    "../src/lib/jobs"
  );
  const { resolvePlatformContextFromInput } = await import(
    "../src/lib/platform-context"
  );
  const owner = await resolvePlatformContextFromInput({
    email: "ops-control@example.com",
    tenantSlug: "ops-control-tenant",
    tenantName: "Ops Control Tenant",
  });
  const other = await resolvePlatformContextFromInput({
    email: "ops-control-other@example.com",
    tenantSlug: "ops-control-tenant",
    tenantName: "Ops Control Tenant",
  });
  const now = new Date();
  await db.insert(schema.projects).values([
    {
      id: "project-ops-control",
      tenantId: owner.tenant.id,
      ownerUserId: owner.user.id,
      name: "控制项目",
      novelText: "原文",
      targetEpisodeCount: 3,
      status: "running",
      createdAt: now,
      updatedAt: now,
    },
    {
      id: "project-ops-control-hidden",
      tenantId: other.tenant.id,
      ownerUserId: other.user.id,
      name: "隐藏控制项目",
      novelText: "原文",
      targetEpisodeCount: 3,
      status: "running",
      createdAt: now,
      updatedAt: now,
    },
  ]);
  const queued = await createJob({
    kind: "localization_export",
    tenantId: owner.tenant.id,
    projectId: "project-ops-control",
    title: "等待取消",
  });
  const running = await createJob({
    kind: "video_brief_export",
    tenantId: owner.tenant.id,
    projectId: "project-ops-control",
    title: "运行中不可强杀",
  });
  await claimNextQueuedJob({ kind: "video_brief_export" });
  const failed = await createJob({
    kind: "delivery_export",
    tenantId: owner.tenant.id,
    projectId: "project-ops-control",
    title: "等待重试",
  });
  await failJob(failed.id, new Error("provider request timed out"));
  const hidden = await createJob({
    kind: "delivery_export",
    tenantId: other.tenant.id,
    projectId: "project-ops-control-hidden",
    title: "不可访问",
  });

  const detailRoute = await import("../src/app/api/ops/jobs/[id]/route");
  const cancelRoute = await import("../src/app/api/ops/jobs/[id]/cancel/route");
  const retryRoute = await import("../src/app/api/ops/jobs/[id]/retry/route");
  const routeContext = (id: string) => ({ params: Promise.resolve({ id }) });
  const visibleDetail = await detailRoute.GET(
    opsRequest(`/api/ops/jobs/${queued.id}`, owner.user.email, owner.tenant.slug) as never,
    routeContext(queued.id)
  );
  const hiddenDetail = await detailRoute.GET(
    opsRequest(`/api/ops/jobs/${hidden.id}`, owner.user.email, owner.tenant.slug) as never,
    routeContext(hidden.id)
  );
  const cancelledResponse = await cancelRoute.POST(
    opsRequest(`/api/ops/jobs/${queued.id}/cancel`, owner.user.email, owner.tenant.slug) as never,
    routeContext(queued.id)
  );
  const runningCancelResponse = await cancelRoute.POST(
    opsRequest(`/api/ops/jobs/${running.id}/cancel`, owner.user.email, owner.tenant.slug) as never,
    routeContext(running.id)
  );
  const retriedResponse = await retryRoute.POST(
    opsRequest(`/api/ops/jobs/${failed.id}/retry`, owner.user.email, owner.tenant.slug) as never,
    routeContext(failed.id)
  );
  const retriedBody = (await retriedResponse.json()) as {
    job: Record<string, unknown> & { status: string };
  };
  const detail = (await visibleDetail.json()) as {
    events: Array<{ eventType: string }>;
  };
  const cancelled = await db.query.jobs.findFirst({
    where: (table, { eq }) => eq(table.id, queued.id),
  });
  const retried = await db.query.jobs.findFirst({
    where: (table, { eq }) => eq(table.id, failed.id),
  });

  assert.equal(visibleDetail.status, 200);
  assert.ok(detail.events.some((event) => event.eventType === "created"));
  assert.equal(hiddenDetail.status, 404);
  assert.equal(cancelledResponse.status, 200);
  assert.equal(cancelled?.status, "cancelled");
  assert.equal(runningCancelResponse.status, 409);
  assert.equal(retriedResponse.status, 200);
  assert.equal(retriedBody.job.status, "queued");
  assert.equal("payloadJson" in retriedBody.job, false);
  assert.equal("resultJson" in retriedBody.job, false);
  assert.equal(retried?.status, "queued");
});
