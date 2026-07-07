import { execFileSync } from "node:child_process";
import { existsSync, mkdtempSync, mkdirSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import Database from "better-sqlite3";
import os from "node:os";
import path from "node:path";
import test from "node:test";
import assert from "node:assert/strict";
import type { EngineSourceEvidenceItem } from "../src/lib/engine-types";

const repoRoot = path.resolve(import.meta.dirname, "..");
const tempRoot = mkdtempSync(path.join(os.tmpdir(), "novel-drama-p0-"));
process.env.NOVEL_DRAMA_DB_PATH = path.join(tempRoot, "db.sqlite");
process.env.NOVEL_DRAMA_BACKFILL_LEGACY_TENANT = "0";

execFileSync("npx", ["drizzle-kit", "migrate"], {
  cwd: repoRoot,
  env: process.env,
  stdio: "ignore",
});

function setEnv(name: string, value: string | undefined): void {
  if (value === undefined) {
    delete process.env[name];
    return;
  }
  process.env[name] = value;
}

test.after(() => {
  rmSync(tempRoot, { recursive: true, force: true });
});

test("production-like deployment never silently falls back to mock engine", async () => {
  const previous = {
    webMock: process.env.NOVEL_DRAMA_WEB_MOCK,
    nodeEnv: process.env.NODE_ENV,
    target: process.env.NOVEL_DRAMA_DEPLOYMENT_TARGET,
    apiKey: process.env.OPENAI_API_KEY,
    model: process.env.OPENAI_MODEL,
  };
  try {
    delete process.env.NOVEL_DRAMA_WEB_MOCK;
    delete process.env.OPENAI_API_KEY;
    delete process.env.OPENAI_MODEL;
    setEnv("NODE_ENV", "production");
    process.env.NOVEL_DRAMA_DEPLOYMENT_TARGET = "production";

    const { resolveEngineMode, realEngineConfigProblem } = await import(
      "../src/lib/engine-runner"
    );

    assert.deepEqual(resolveEngineMode(), { mode: "real", explicitMock: false });
    assert.match(realEngineConfigProblem() ?? "", /OPENAI_API_KEY/);
  } finally {
    process.env.NOVEL_DRAMA_WEB_MOCK = previous.webMock;
    setEnv("NODE_ENV", previous.nodeEnv);
    process.env.NOVEL_DRAMA_DEPLOYMENT_TARGET = previous.target;
    process.env.OPENAI_API_KEY = previous.apiKey;
    process.env.OPENAI_MODEL = previous.model;
  }
});

test("round generation jobs are unique while a round already has an active job", async () => {
  const { db, schema } = await import("../src/db/client");
  const { createJob } = await import("../src/lib/jobs");
  const now = new Date();
  await db.insert(schema.projects).values({
    id: "project-p0",
    name: "P0 Project",
    novelText: "source",
    targetEpisodeCount: 5,
    status: "running",
    createdAt: now,
    updatedAt: now,
  });
  await db.insert(schema.rounds).values({
    id: "round-p0",
    projectId: "project-p0",
    roundNum: 1,
    epRange: "EP01-EP05",
    status: "running",
    createdAt: now,
  });

  const first = await createJob({
    kind: "round_generation",
    title: "first",
    projectId: "project-p0",
    roundId: "round-p0",
  });

  await assert.rejects(
    () =>
      createJob({
        kind: "round_generation",
        title: "duplicate",
        projectId: "project-p0",
        roundId: "round-p0",
      }),
    /active job already exists/
  );

  assert.equal(first.roundId, "round-p0");
});

test("payment webhook rejects unsigned requests even outside production", async () => {
  const previous = {
    nodeEnv: process.env.NODE_ENV,
    secretA: process.env.PLATFORM_PAYMENT_WEBHOOK_SECRET,
    secretB: process.env.NOVEL_DRAMA_PAYMENT_WEBHOOK_SECRET,
  };
  try {
    setEnv("NODE_ENV", "development");
    delete process.env.PLATFORM_PAYMENT_WEBHOOK_SECRET;
    delete process.env.NOVEL_DRAMA_PAYMENT_WEBHOOK_SECRET;

    const { POST } = await import("../src/app/api/platform/payments/webhook/route");
    const res = await POST(
      new Request("http://localhost/api/platform/payments/webhook", {
        method: "POST",
        body: JSON.stringify({
          provider: "mock",
          eventType: "checkout.paid",
          externalEventId: "evt_unsigned",
        }),
      }) as never
    );
    const body = (await res.json()) as { error?: string };

    assert.equal(res.status, 400);
    assert.match(body.error ?? "", /signature|secret|unsigned/i);
  } finally {
    setEnv("NODE_ENV", previous.nodeEnv);
    process.env.PLATFORM_PAYMENT_WEBHOOK_SECRET = previous.secretA;
    process.env.NOVEL_DRAMA_PAYMENT_WEBHOOK_SECRET = previous.secretB;
  }
});

test("payment webhook processor refuses unsigned direct calls", async () => {
  const { processPaymentWebhook } = await import("../src/lib/platform-credits");

  await assert.rejects(
    () =>
      processPaymentWebhook({
        provider: "mock",
        eventType: "checkout.paid",
        externalEventId: "direct_unsigned",
      }),
    /signature is required/
  );
});

test("payment webhook processor refuses unsigned mock bypass in production-like deployment", async () => {
  const previous = {
    nodeEnv: process.env.NODE_ENV,
    target: process.env.NOVEL_DRAMA_DEPLOYMENT_TARGET,
    allowUnsigned: process.env.NOVEL_DRAMA_ALLOW_UNSIGNED_MOCK_WEBHOOKS,
  };
  try {
    setEnv("NODE_ENV", "production");
    process.env.NOVEL_DRAMA_DEPLOYMENT_TARGET = "production";
    process.env.NOVEL_DRAMA_ALLOW_UNSIGNED_MOCK_WEBHOOKS = "1";
    const { processPaymentWebhook } = await import("../src/lib/platform-credits");

    await assert.rejects(
      () =>
        processPaymentWebhook({
          provider: "mock",
          eventType: "checkout.paid",
          externalEventId: "prod_unsigned_mock",
        }),
      /signature is required/
    );
  } finally {
    setEnv("NODE_ENV", previous.nodeEnv);
    process.env.NOVEL_DRAMA_DEPLOYMENT_TARGET = previous.target;
    process.env.NOVEL_DRAMA_ALLOW_UNSIGNED_MOCK_WEBHOOKS = previous.allowUnsigned;
  }
});

test("run-all pauses visibly when latest round quality is not usable", async () => {
  const { db, schema } = await import("../src/db/client");
  const { scheduleNextRoundIfRunAll } = await import("../src/lib/engine-runner");
  const { parseProjectMeta } = await import("../src/lib/project-controls");
  const now = new Date();
  await db.insert(schema.projects).values({
    id: "project-p1-runall-quality",
    name: "P1 RunAll Quality",
    novelText: "source",
    targetEpisodeCount: 20,
    status: "running",
    metaJson: JSON.stringify({
      control: {
        runAll: {
          enabled: true,
          generationVariant: "drama_engine_first",
          repairBudget: "episode",
        },
      },
    }),
    createdAt: now,
    updatedAt: now,
  });
  await db.insert(schema.rounds).values({
    id: "round-p1-runall-quality",
    projectId: "project-p1-runall-quality",
    roundNum: 1,
    epRange: "EP01-EP05",
    status: "done",
    summaryJson: JSON.stringify({
      quality_report: {
        status: "needs_rewrite",
        rewrite_instruction: "EP03 人物动机断裂，先修复再继续。",
      },
      next_round_context: {
        current_episode: 5,
      },
    }),
    createdAt: now,
  });

  const next = await scheduleNextRoundIfRunAll("project-p1-runall-quality");

  assert.equal(next, null);
  const project = await db.query.projects.findFirst({
    where: (projects, { eq }) => eq(projects.id, "project-p1-runall-quality"),
  });
  const jobs = await db.query.jobs.findMany({
    where: (jobs, { eq }) => eq(jobs.projectId, "project-p1-runall-quality"),
  });
  const meta = parseProjectMeta(project?.metaJson ?? null);
  assert.equal(project?.status, "failed");
  assert.equal(meta.control?.runAll?.enabled, false);
  assert.match(String(meta.control?.runAll?.pausedReason ?? ""), /needs_rewrite/);
  assert.equal(jobs.length, 0);
});

test("legacy per-episode retry helper is disabled instead of regenerating", async () => {
  const { retryEpisode } = await import("../src/lib/round-runner");

  await assert.rejects(
    () => retryEpisode("legacy-episode-id"),
    /legacy episode retry is disabled/i
  );
});

test("round generation unique error classification only matches the named index", () => {
  const source = readFileSync(path.join(repoRoot, "src/lib/jobs.ts"), "utf-8");

  assert.match(source, /jobs_active_round_generation_unique/);
  assert.doesNotMatch(source, /jobs_active_round_generation_unique\|unique/);
});

test("package exposes typecheck and test:ts avoids shell glob expansion", () => {
  const pkg = JSON.parse(
    readFileSync(path.join(repoRoot, "package.json"), "utf-8")
  ) as { scripts?: Record<string, string> };

  assert.equal(pkg.scripts?.typecheck, "tsc --noEmit");
  assert.equal(pkg.scripts?.["test:ts"], "node scripts/run-ts-tests.mjs");
});

test("active round generation migration deduplicates dirty queued and running jobs", () => {
  const dbPath = path.join(tempRoot, "dirty-migration.sqlite");
  const sqlite = new Database(dbPath);
  try {
    sqlite.exec(`
      create table jobs (
        id text primary key not null,
        kind text not null,
        status text not null,
        round_id text,
        progress integer not null default 0,
        error_text text,
        created_at integer not null,
        updated_at integer not null,
        finished_at integer
      );
      insert into jobs (id, kind, status, round_id, progress, created_at, updated_at)
      values
        ('old-running', 'round_generation', 'running', 'round-dirty', 30, 1000, 1000),
        ('new-queued', 'round_generation', 'queued', 'round-dirty', 0, 2000, 2000),
        ('other-round', 'round_generation', 'queued', 'round-clean', 0, 3000, 3000);
    `);
    const migration = readFileSync(
      path.join(repoRoot, "drizzle/migrations/0008_material_silvermane.sql"),
      "utf-8"
    );
    for (const statement of migration.split("--> statement-breakpoint")) {
      if (statement.trim()) sqlite.exec(statement);
    }

    const rows = sqlite
      .prepare("select id, status, error_text from jobs order by id")
      .all() as Array<{ id: string; status: string; error_text: string | null }>;
    const activeDirtyRows = rows.filter(
      (row) =>
        ["old-running", "new-queued"].includes(row.id) &&
        ["queued", "running"].includes(row.status)
    );
    assert.equal(activeDirtyRows.length, 1);
    assert.equal(activeDirtyRows[0].id, "new-queued");
    assert.match(
      rows.find((row) => row.id === "old-running")?.error_text ?? "",
      /dedup migration/
    );
  } finally {
    sqlite.close();
  }
});

test("stale round generation failure marks the project visibly failed", async () => {
  const { db, schema } = await import("../src/db/client");
  const { reconcileStaleJobs } = await import("../src/lib/jobs");
  const now = new Date();
  const stale = new Date(now.getTime() - 60_000);
  await db.insert(schema.projects).values({
    id: "project-p1-stale",
    name: "P1 Stale",
    novelText: "source",
    targetEpisodeCount: 10,
    status: "running",
    createdAt: now,
    updatedAt: now,
  });
  await db.insert(schema.rounds).values({
    id: "round-p1-stale",
    projectId: "project-p1-stale",
    roundNum: 1,
    epRange: "EP01-EP05",
    status: "running",
    createdAt: now,
  });
  await db.insert(schema.jobs).values({
    id: "job-p1-stale",
    kind: "round_generation",
    title: "stale round",
    projectId: "project-p1-stale",
    roundId: "round-p1-stale",
    status: "running",
    progress: 42,
    attempts: 1,
    createdAt: stale,
    updatedAt: stale,
    startedAt: stale,
  });

  const result = await reconcileStaleJobs({ olderThanMs: 1 });

  assert.equal(result.failedRunning, 1);
  const project = await db.query.projects.findFirst({
    where: (projects, { eq }) => eq(projects.id, "project-p1-stale"),
  });
  const round = await db.query.rounds.findFirst({
    where: (rounds, { eq }) => eq(rounds.id, "round-p1-stale"),
  });
  assert.equal(project?.status, "failed");
  assert.equal(round?.status, "failed");
});

test("direct retry requeues a round job and restores project and round running state", async () => {
  const { db, schema } = await import("../src/db/client");
  const { requeueRetryableJob } = await import("../src/lib/jobs");
  const now = new Date();
  await db.insert(schema.projects).values({
    id: "project-p1-retry",
    name: "P1 Retry",
    novelText: "source",
    targetEpisodeCount: 10,
    status: "failed",
    createdAt: now,
    updatedAt: now,
  });
  await db.insert(schema.rounds).values({
    id: "round-p1-retry",
    projectId: "project-p1-retry",
    roundNum: 1,
    epRange: "EP01-EP05",
    status: "failed",
    summaryJson: JSON.stringify({ error: "old failure" }),
    createdAt: now,
  });
  await db.insert(schema.jobs).values({
    id: "job-p1-retry",
    kind: "round_generation",
    title: "failed round",
    projectId: "project-p1-retry",
    roundId: "round-p1-retry",
    status: "failed",
    progress: 100,
    attempts: 1,
    errorText: "old failure",
    createdAt: now,
    updatedAt: now,
    finishedAt: now,
  });

  const retried = await requeueRetryableJob("job-p1-retry");

  const project = await db.query.projects.findFirst({
    where: (projects, { eq }) => eq(projects.id, "project-p1-retry"),
  });
  const round = await db.query.rounds.findFirst({
    where: (rounds, { eq }) => eq(rounds.id, "round-p1-retry"),
  });
  assert.equal(retried.status, "queued");
  assert.equal(project?.status, "running");
  assert.equal(round?.status, "running");
  assert.equal(round?.summaryJson, null);
});

test("round completion is marked succeeded before scheduling the next run-all round", () => {
  const source = readFileSync(
    path.join(repoRoot, "src/lib/engine-runner.ts"),
    "utf-8"
  );
  const syncIndex = source.indexOf("await syncEngineRoundToDb(project, roundId, result);");
  const successIndex = source.indexOf("await succeedJob(jobId", syncIndex);
  const scheduleIndex = source.indexOf(
    "await scheduleNextRoundIfRunAll(project.id)",
    syncIndex
  );

  assert.ok(syncIndex > 0);
  assert.ok(successIndex > syncIndex);
  assert.ok(scheduleIndex > successIndex);
});

test("engine round failure catch marks project failed instead of hiding it as running", () => {
  const source = readFileSync(
    path.join(repoRoot, "src/lib/engine-runner.ts"),
    "utf-8"
  );
  const catchIndex = source.indexOf("} catch (error) {");
  const failureProjectUpdate = source.indexOf(".update(schema.projects)", catchIndex);
  const failedStatusIndex = source.indexOf('.set({ status: "failed"', failureProjectUpdate);
  const runningStatusIndex = source.indexOf('.set({ status: "running"', failureProjectUpdate);

  assert.ok(catchIndex > 0);
  assert.ok(failureProjectUpdate > catchIndex);
  assert.ok(failedStatusIndex > failureProjectUpdate);
  assert.ok(runningStatusIndex === -1 || runningStatusIndex > failedStatusIndex);
});

test("quality sample worker runs direct baseline comparison by default", () => {
  const source = readFileSync(
    path.join(repoRoot, "src/lib/engine-runner.ts"),
    "utf-8"
  );
  const commandIndex = source.indexOf('"evaluate-samples"');
  const baselineFlagIndex = source.indexOf('"--direct-baseline"', commandIndex);

  assert.ok(commandIndex > 0);
  assert.ok(baselineFlagIndex > commandIndex);
});

test("source evidence view type accepts partial item status", () => {
  const item = {
    episode: 1,
    source_anchor: "EP01 原文资产",
    adaptation_reason: "部分保留，部分缺失",
    retained_assets: ["原文钩子", "情绪高潮"],
    script_evidence: ["△ 原文钩子被拍出来。"],
    evidence_spans: [],
    status: "partial",
  } satisfies EngineSourceEvidenceItem;

  assert.equal(item.status, "partial");
});

test("archived project control delete removes the project storage directory", async () => {
  const { POST } = await import("../src/app/api/projects/[id]/control/route");
  const { db, schema } = await import("../src/db/client");
  const { resolvePlatformContextFromInput } = await import("../src/lib/platform-context");
  const now = new Date();
  const context = await resolvePlatformContextFromInput({
    email: "delete-project@example.com",
    tenantSlug: "delete-project-tenant",
    tenantName: "Delete Project Tenant",
  });
  const projectId = "project-p1-archived-delete-storage";
  const storageDir = path.join(repoRoot, "storage", "projects", projectId);
  mkdirSync(storageDir, { recursive: true });
  writeFileSync(path.join(storageDir, "artifact.txt"), "source and prompt trace");
  await db.insert(schema.projects).values({
    id: projectId,
    tenantId: context.tenant.id,
    ownerUserId: context.user.id,
    name: "Archived Delete Storage",
    novelText: "source",
    targetEpisodeCount: 5,
    status: "paused",
    metaJson: JSON.stringify({ archivedAt: now.toISOString() }),
    createdAt: now,
    updatedAt: now,
  });

  try {
    const res = await POST(
      new Request(`http://localhost/api/projects/${projectId}/control`, {
        method: "POST",
        headers: {
          "x-novel-user-email": "delete-project@example.com",
          "x-novel-tenant": "delete-project-tenant",
          "x-novel-tenant-name": "Delete Project Tenant",
        },
        body: JSON.stringify({ action: "delete" }),
      }) as never,
      { params: Promise.resolve({ id: projectId }) }
    );

    assert.equal(res.status, 200);
    assert.equal(existsSync(storageDir), false);
  } finally {
    rmSync(storageDir, { recursive: true, force: true });
  }
});
