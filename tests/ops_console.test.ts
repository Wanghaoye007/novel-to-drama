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
