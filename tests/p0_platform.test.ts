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
process.env.NOVEL_DRAMA_TRUST_IDENTITY_HEADERS = "1";

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

test("credit settlement is idempotent for the same usage event", async () => {
  const { db, schema } = await import("../src/db/client");
  const { resolvePlatformContextFromInput } = await import(
    "../src/lib/platform-context"
  );
  const { settleUsageCredits } = await import("../src/lib/platform-credits");
  const context = await resolvePlatformContextFromInput({
    email: "credit-idempotency@example.com",
    tenantSlug: "credit-idempotency",
    tenantName: "Credit Idempotency",
  });
  const now = new Date();
  await db.insert(schema.usageEvents).values({
    id: "usage-credit-idempotency",
    tenantId: context.tenant.id,
    userId: context.user.id,
    eventType: "round_start",
    quantity: 1,
    billableUnits: 3,
    createdAt: now,
  });

  await settleUsageCredits({
    context,
    usageEventId: "usage-credit-idempotency",
    billableUnits: 3,
  });
  await settleUsageCredits({
    context,
    usageEventId: "usage-credit-idempotency",
    billableUnits: 3,
  });
  const rows = await db.query.creditLedger.findMany({
    where: (ledger, { eq }) =>
      eq(ledger.referenceKey, "usage:usage-credit-idempotency"),
  });

  assert.equal(rows.length, 1);
  assert.equal(rows[0].creditsDelta, -3);
});

test("checkout completion is idempotent and grants credits once", async () => {
  const { db, schema } = await import("../src/db/client");
  const { resolvePlatformContextFromInput } = await import(
    "../src/lib/platform-context"
  );
  const {
    completeCreditCheckoutSession,
    createCreditCheckoutSession,
  } = await import("../src/lib/platform-credits");
  const context = await resolvePlatformContextFromInput({
    email: "checkout-idempotency@example.com",
    tenantSlug: "checkout-idempotency",
    tenantName: "Checkout Idempotency",
  });
  const checkout = await createCreditCheckoutSession(
    context,
    "credits_100",
    "mock"
  );

  await Promise.all([
    completeCreditCheckoutSession(context, checkout.id),
    completeCreditCheckoutSession(context, checkout.id),
  ]);

  const invoices = await db.query.paymentInvoices.findMany({
    where: (invoice, { eq }) => eq(invoice.checkoutSessionId, checkout.id),
  });
  const ledger = await db.query.creditLedger.findMany({
    where: (entry, { eq }) =>
      eq(entry.referenceKey, `checkout:${checkout.id}:paid`),
  });
  assert.equal(invoices.length, 1);
  assert.equal(ledger.length, 1);
  assert.equal(ledger[0].creditsDelta, 100);
});

test("payment webhook replay reuses one event and one credit grant", async () => {
  const { db } = await import("../src/db/client");
  const { resolvePlatformContextFromInput } = await import(
    "../src/lib/platform-context"
  );
  const {
    createCreditCheckoutSession,
    processPaymentWebhook,
  } = await import("../src/lib/platform-credits");
  const context = await resolvePlatformContextFromInput({
    email: "webhook-idempotency@example.com",
    tenantSlug: "webhook-idempotency",
    tenantName: "Webhook Idempotency",
  });
  const checkout = await createCreditCheckoutSession(
    context,
    "credits_100",
    "mock"
  );
  const payload = {
    provider: "mock" as const,
    eventType: "checkout.paid",
    checkoutSessionId: checkout.id,
    externalEventId: "evt_checkout_idempotency",
    signatureVerified: true,
  };

  const [first, second] = await Promise.all([
    processPaymentWebhook(payload),
    processPaymentWebhook(payload),
  ]);
  const events = await db.query.paymentWebhookEvents.findMany({
    where: (event, { eq }) =>
      eq(event.externalEventId, "evt_checkout_idempotency"),
  });
  const ledger = await db.query.creditLedger.findMany({
    where: (entry, { eq }) =>
      eq(entry.referenceKey, `checkout:${checkout.id}:paid`),
  });

  assert.equal(first.webhookEventId, second.webhookEventId);
  assert.equal(events.length, 1);
  assert.equal(events[0].status, "processed");
  assert.equal(ledger.length, 1);
});

test("stale received payment webhook is reclaimed after an interrupted attempt", async () => {
  const { db, schema } = await import("../src/db/client");
  const { resolvePlatformContextFromInput } = await import(
    "../src/lib/platform-context"
  );
  const {
    createCreditCheckoutSession,
    processPaymentWebhook,
  } = await import("../src/lib/platform-credits");
  const context = await resolvePlatformContextFromInput({
    email: "webhook-reclaim@example.com",
    tenantSlug: "webhook-reclaim",
    tenantName: "Webhook Reclaim",
  });
  const checkout = await createCreditCheckoutSession(
    context,
    "credits_100",
    "mock"
  );
  await db.insert(schema.paymentWebhookEvents).values({
    id: "stale-received-webhook",
    tenantId: context.tenant.id,
    checkoutSessionId: checkout.id,
    provider: "mock",
    eventType: "checkout.paid",
    status: "received",
    externalEventId: "evt_stale_received",
    createdAt: new Date(Date.now() - 5 * 60 * 1000),
  });

  const result = await processPaymentWebhook({
    provider: "mock",
    eventType: "checkout.paid",
    checkoutSessionId: checkout.id,
    externalEventId: "evt_stale_received",
    signatureVerified: true,
  });
  const event = await db.query.paymentWebhookEvents.findFirst({
    where: (row, { eq }) => eq(row.id, "stale-received-webhook"),
  });
  const ledger = await db.query.creditLedger.findMany({
    where: (entry, { eq }) =>
      eq(entry.referenceKey, `checkout:${checkout.id}:paid`),
  });

  assert.equal(result.webhookEventId, "stale-received-webhook");
  assert.equal(event?.status, "processed");
  assert.equal(ledger.length, 1);
});

test("run-all schedules the next round when quality audit needs rewrite", async () => {
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

  assert.equal(next?.roundNum, 2);
  const project = await db.query.projects.findFirst({
    where: (projects, { eq }) => eq(projects.id, "project-p1-runall-quality"),
  });
  const jobs = await db.query.jobs.findMany({
    where: (jobs, { eq }) => eq(jobs.projectId, "project-p1-runall-quality"),
  });
  const meta = parseProjectMeta(project?.metaJson ?? null);
  assert.equal(project?.status, "running");
  assert.equal(meta.control?.runAll?.enabled, true);
  assert.equal(meta.control?.qualityGate?.status, "needs_rewrite");
  assert.equal(meta.control?.runAll?.pausedReason, undefined);
  assert.equal(jobs.length, 1);
  assert.equal(jobs[0]?.status, "queued");
});

test("run-all recovers a legacy quality-failed round and continues", async () => {
  const { db, schema } = await import("../src/db/client");
  const { scheduleNextRoundIfRunAll } = await import("../src/lib/engine-runner");
  const { parseProjectMeta } = await import("../src/lib/project-controls");
  const now = new Date();
  await db.insert(schema.projects).values({
    id: "project-p0-runall-failed-round",
    name: "RunAll Failed Round",
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
    id: "round-p0-runall-failed-round",
    projectId: "project-p0-runall-failed-round",
    roundNum: 1,
    epRange: "EP01-EP05",
    status: "failed",
    summaryJson: JSON.stringify({
      quality_report: {
        status: "needs_rewrite",
        rewrite_instruction: "EP01 原文资产未保留，先修复本轮。",
      },
      next_round_context: {
        current_episode: 5,
      },
    }),
    createdAt: now,
  });

  const next = await scheduleNextRoundIfRunAll("project-p0-runall-failed-round");

  assert.equal(next?.roundNum, 2);
  const project = await db.query.projects.findFirst({
    where: (projects, { eq }) => eq(projects.id, "project-p0-runall-failed-round"),
  });
  const round = await db.query.rounds.findFirst({
    where: (rounds, { eq }) => eq(rounds.id, "round-p0-runall-failed-round"),
  });
  const jobs = await db.query.jobs.findMany({
    where: (jobs, { eq }) => eq(jobs.projectId, "project-p0-runall-failed-round"),
  });
  const meta = parseProjectMeta(project?.metaJson ?? null);
  assert.equal(project?.status, "running");
  assert.equal(round?.status, "done");
  assert.equal(meta.control?.runAll?.enabled, true);
  assert.equal(meta.control?.qualityGate?.status, "needs_rewrite");
  assert.equal(jobs.length, 1);
  assert.equal(jobs[0]?.status, "queued");
});

test("quality audit preserves its report without stopping an enabled run-all chain", async () => {
  const { db, schema } = await import("../src/db/client");
  const { markProjectAfterRoundCompletion } = await import("../src/lib/engine-runner");
  const { parseProjectMeta } = await import("../src/lib/project-controls");
  const now = new Date();
  await db.insert(schema.projects).values({
    id: "project-p0-runall-quality-stop",
    name: "RunAll Quality Stop",
    novelText: "source",
    targetEpisodeCount: 25,
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

  await markProjectAfterRoundCompletion("project-p0-runall-quality-stop", {
    currentEpisode: 5,
    targetEpisodeCount: 25,
    qualityStatus: "needs_rewrite",
    roundNumber: 1,
    rewriteInstruction: "EP01 原文资产未保留，先修复本轮。",
  });

  const project = await db.query.projects.findFirst({
    where: (projects, { eq }) => eq(projects.id, "project-p0-runall-quality-stop"),
  });
  const meta = parseProjectMeta(project?.metaJson ?? null);
  assert.equal(project?.status, "running");
  assert.equal(meta.control?.runAll?.enabled, true);
  assert.equal(meta.control?.qualityGate?.status, "needs_rewrite");
  assert.equal(meta.control?.runAll?.pausedReason, undefined);
});

test("human-review quality is recorded as an audit while the project continues", async () => {
  const { db, schema } = await import("../src/db/client");
  const { markProjectAfterRoundCompletion } = await import("../src/lib/engine-runner");
  const now = new Date();
  await db.insert(schema.projects).values({
    id: "project-p0-human-review-stop",
    name: "Human Review Stop",
    novelText: "source",
    targetEpisodeCount: 25,
    status: "running",
    createdAt: now,
    updatedAt: now,
  });

  await markProjectAfterRoundCompletion("project-p0-human-review-stop", {
    currentEpisode: 5,
    targetEpisodeCount: 25,
    qualityStatus: "needs_human_review",
    roundNumber: 1,
    rewriteInstruction: "EP05 原文资产缺失，需要人工复核。",
  });

  const project = await db.query.projects.findFirst({
    where: (projects, { eq }) => eq(projects.id, "project-p0-human-review-stop"),
  });
  assert.equal(project?.status, "running");
  assert.match(project?.metaJson ?? "", /needs_human_review/);
  assert.match(project?.metaJson ?? "", /EP05 原文资产缺失/);
});

test("Doubao is the default model and legacy Gemini 3.1 aliases migrate to it", async () => {
  const {
    DEFAULT_LLM_MODEL,
    llmModelLabel,
    llmModelOptions,
    normalizeLlmModel,
  } = await import("../src/lib/llm-model-options");

  assert.equal(DEFAULT_LLM_MODEL, "bytedance-seed/seed-2.0-mini");
  assert.equal(normalizeLlmModel("doubao"), "bytedance-seed/seed-2.0-mini");
  assert.equal(normalizeLlmModel("gemini3.1f"), "bytedance-seed/seed-2.0-mini");
  assert.equal(
    normalizeLlmModel("bytedance-seed/seed-2.0-lite"),
    "bytedance-seed/seed-2.0-mini"
  );
  assert.equal(llmModelLabel(DEFAULT_LLM_MODEL), "豆包 Seed 2.0 Mini");
  assert.ok(
    llmModelOptions.some(
      (option) => option.value === "bytedance-seed/seed-2.0-mini"
    )
  );
  assert.ok(
    !llmModelOptions.some(
      (option) => String(option.value) === "google/gemini-3.1-flash-lite"
    )
  );
});

test("豆包使用顺序逐集首稿，Gemini 保留整轮首稿", async () => {
  const { shouldUseEpisodeFirstForModel } = await import(
    "../src/lib/engine-runner"
  );

  assert.equal(
    shouldUseEpisodeFirstForModel("bytedance-seed/seed-2.0-mini"),
    true
  );
  assert.equal(
    shouldUseEpisodeFirstForModel("bytedance-seed/seed-1.6-flash"),
    true
  );
  assert.equal(
    shouldUseEpisodeFirstForModel("google/gemini-3.5-flash"),
    false
  );
});

test("round generation job stores selected Gemini model in payload", async () => {
  const { db, schema } = await import("../src/db/client");
  const { startEngineRound } = await import("../src/lib/engine-runner");
  const now = new Date();
  await db.insert(schema.projects).values({
    id: "project-p0-model-select",
    name: "Model Select",
    novelText: "source",
    targetEpisodeCount: 5,
    status: "running",
    createdAt: now,
    updatedAt: now,
  });

  const started = await startEngineRound("project-p0-model-select", 1, {
    llmModel: "gemini_3_5_flash",
  });

  const job = await db.query.jobs.findFirst({
    where: (jobs, { eq }) => eq(jobs.id, started.jobId),
  });
  const payload = JSON.parse(job?.payloadJson ?? "{}") as { llmModel?: string };
  assert.equal(payload.llmModel, "google/gemini-3.5-flash");
});

test("engine run args include the selected model flag", async () => {
  const { buildEngineRunArgs } = await import("../src/lib/engine-runner");

  const args = buildEngineRunArgs({
    sourcePath: "/tmp/source.txt",
    engineDir: "/tmp/project",
    projectId: "project-model",
    roundNumber: 2,
    targetEpisodeCount: 25,
    episodesPerRound: 5,
    generationVariant: "drama_engine_first",
    repairBudget: "episode",
    llmModel: "google/gemini-3.5-flash",
    methodologyCardsPath: null,
    mock: false,
  });

  const modelIndex = args.indexOf("--model");
  assert.ok(modelIndex > -1);
  assert.equal(args[modelIndex + 1], "google/gemini-3.5-flash");
});

test("episode AI optimize prompt anchors on current draft, bible, and instruction", async () => {
  const { buildEpisodeOptimizationPrompt } = await import(
    "../src/lib/episode-ai-optimize"
  );

  const prompt = buildEpisodeOptimizationPrompt({
    project: {
      name: "名利双收",
      novelText: "原文：女主在颁奖礼后台被羞辱，随后提前放好的解约协议成为反击起点。",
    },
    episode: {
      epNum: 3,
      scriptTxt: "第3集 旧稿\n1-1 后台\n林挽清：我早就准备好了。",
    },
    bible: {
      charactersMd: "人物小传：林挽清克制、清醒，不歇斯底里。",
      episodePlanMd: "分集规划：第3集必须承接第2集结尾。",
      sixAssetsJson: "{\"核心钩子\":\"公开羞辱后的主动离开\"}",
      prevRoundSummaryJson: "{\"open_hooks\":[\"解约协议已埋\"]}",
    },
    round: {
      roundNum: 1,
      summaryJson: "{\"next_round_context\":{\"current_episode\":5}}",
    },
    episodes: [
      { epNum: 2, scriptTxt: "第2集 结尾：她把协议推到桌边。" },
      { epNum: 4, scriptTxt: "第4集 开头：路淮北发现她真的走了。" },
    ],
    instruction: "强化镜头和情绪递进，不要让女主突然全知全能。",
  });

  assert.match(prompt, /旧稿是唯一文本基准/);
  assert.match(prompt, /只优化第 3 集/);
  assert.match(prompt, /强化镜头和情绪递进/);
  assert.match(prompt, /人物小传/);
  assert.match(prompt, /第2集 结尾/);
  assert.match(prompt, /第4集 开头/);
});

test("edit impact applies user draft and optimizes impacted downstream episodes", async () => {
  const { db, schema } = await import("../src/db/client");
  const { applyEpisodeEditImpact } = await import("../src/lib/edit-impact-apply");
  const { parseProjectMeta } = await import("../src/lib/project-controls");
  const now = new Date();

  await db.insert(schema.projects).values({
    id: "project-p0-edit-impact",
    name: "Edit Impact Project",
    novelText: "原文：女主在颁奖礼被羞辱，解约协议提前埋下。",
    targetEpisodeCount: 5,
    status: "running",
    createdAt: now,
    updatedAt: now,
  });
  await db.insert(schema.rounds).values({
    id: "round-p0-edit-impact",
    projectId: "project-p0-edit-impact",
    roundNum: 1,
    epRange: "EP01-EP05",
    status: "done",
    summaryJson: JSON.stringify({
      next_round_context: {
        open_hooks: ["路淮北还不知道解约协议已经签好"],
        prop_states: ["解约协议在办公室抽屉"],
        foreshadowing_ledger: ["第2集开头要承接协议被推到桌边"],
      },
      story_state_ledger: {
        entries: [
          {
            episode: 1,
            kind: "prop",
            key: "解约协议",
            value: "提前准备",
            status: "open",
          },
        ],
      },
    }),
    createdAt: now,
  });
  await db.insert(schema.bibles).values({
    id: "bible-p0-edit-impact",
    projectId: "project-p0-edit-impact",
    charactersMd: "林挽清：克制、清醒，反击来自深思熟虑。",
    episodePlanMd: "第2集必须承接第1集结尾的解约协议。",
    sixAssetsJson: "{\"核心钩子\":\"公开羞辱后的主动离开\"}",
    prevRoundSummaryJson: "{}",
    updatedAt: now,
  });
  await db.insert(schema.episodes).values([
    {
      id: "episode-p0-impact-1",
      projectId: "project-p0-edit-impact",
      roundId: "round-p0-edit-impact",
      epNum: 1,
      scriptTxt: "第1集\n林挽清：我不要了。\n△结尾她转身离开。",
      draftMd: "第1集\n林挽清：我不要了。\n△结尾她转身离开。",
      status: "green",
      retryCount: 0,
      updatedAt: now,
    },
    {
      id: "episode-p0-impact-2",
      projectId: "project-p0-edit-impact",
      roundId: "round-p0-edit-impact",
      epNum: 2,
      scriptTxt: "第2集\n△开头路淮北看着空房间。\n路淮北：她人呢？",
      draftMd: "第2集\n△开头路淮北看着空房间。\n路淮北：她人呢？",
      status: "green",
      retryCount: 0,
      updatedAt: now,
    },
  ]);

  const project = await db.query.projects.findFirst({
    where: (projects, { eq }) => eq(projects.id, "project-p0-edit-impact"),
  });
  const round = await db.query.rounds.findFirst({
    where: (rounds, { eq }) => eq(rounds.id, "round-p0-edit-impact"),
  });
  const bible = await db.query.bibles.findFirst({
    where: (bibles, { eq }) => eq(bibles.projectId, "project-p0-edit-impact"),
  });
  const episodes = await db.query.episodes.findMany({
    where: (episodesTable, { eq }) =>
      eq(episodesTable.projectId, "project-p0-edit-impact"),
  });
  const episode = episodes.find((item) => item.epNum === 1);
  assert.ok(project);
  assert.ok(round);
  assert.ok(bible);
  assert.ok(episode);

  const editedScript =
    "第1集\n林挽清：（压低声音）协议，我昨晚就签好了。\n△结尾她把解约协议推到路淮北面前。";
  const result = await applyEpisodeEditImpact({
    project,
    round,
    bible,
    episode,
    episodes,
    editedScriptText: editedScript,
    optimizeImpacted: true,
    optimizer: async ({ instruction }) => ({
      scriptText: `第2集\n△开头特写解约协议，承接上集。\n林挽清OS：${(instruction ?? "").slice(0, 18)}`,
      llmModel: "fake-model",
    }),
  });

  assert.equal(result.report.changed, true);
  assert.equal(result.applied, true);
  assert.equal(result.optimizedEpisodes.length, 1);

  const updatedEp1 = await db.query.episodes.findFirst({
    where: (episodesTable, { eq }) => eq(episodesTable.id, "episode-p0-impact-1"),
  });
  const updatedEp2 = await db.query.episodes.findFirst({
    where: (episodesTable, { eq }) => eq(episodesTable.id, "episode-p0-impact-2"),
  });
  const updatedProject = await db.query.projects.findFirst({
    where: (projects, { eq }) => eq(projects.id, "project-p0-edit-impact"),
  });

  assert.equal(updatedEp1?.scriptTxt, editedScript);
  assert.match(updatedEp1?.reviewJson ?? "", /operator_script_edit/);
  assert.match(updatedEp2?.scriptTxt ?? "", /承接上集/);
  assert.match(updatedEp2?.reviewJson ?? "", /upstream_user_edit/);
  assert.match(
    JSON.stringify(parseProjectMeta(updatedProject?.metaJson ?? null)),
    /解约协议/
  );
});

test("legacy TypeScript generation chain is removed", () => {
  const removedFiles = [
    "src/lib/round-runner.ts",
    "src/lib/m1-normalize.ts",
    "src/lib/m2-bible.ts",
    "src/lib/m3-round.ts",
    "src/lib/m4-review.ts",
    "src/lib/m5-format.ts",
    "src/lib/anthropic.ts",
  ];
  for (const file of removedFiles) {
    assert.equal(existsSync(path.join(repoRoot, file)), false, file);
  }
  const pkg = readFileSync(path.join(repoRoot, "package.json"), "utf-8");
  assert.doesNotMatch(pkg, /@anthropic-ai\/sdk/);
});

test("round generation unique error classification only matches the named index", () => {
  const source = readFileSync(path.join(repoRoot, "src/lib/jobs.ts"), "utf-8");

  assert.match(source, /jobs_active_round_generation_unique/);
  assert.doesNotMatch(source, /jobs_active_round_generation_unique\|unique/);
});

test("round quality card stays compact and does not render issue lists", () => {
  const source = readFileSync(
    path.join(
      repoRoot,
      "src/app/projects/[id]/rounds/[n]/RoundClient.tsx"
    ),
    "utf-8"
  );
  const qualityStart = source.indexOf("质量审计");
  const sidePanelStart = source.indexOf("<aside className=\"round-inspector\">");
  const qualitySidePanelStart = source.indexOf("质量审计", sidePanelStart);
  const runtimeStart = source.indexOf("{hasGenerationMetrics", qualitySidePanelStart);
  assert.ok(qualityStart > -1);
  assert.ok(sidePanelStart > -1);
  assert.ok(qualitySidePanelStart > sidePanelStart);
  assert.ok(runtimeStart > qualitySidePanelStart);
  const qualityPanel = source.slice(qualitySidePanelStart, runtimeStart);

  assert.doesNotMatch(qualityPanel, /round-issue-list/);
  assert.match(qualityPanel, /源文/);
  assert.match(qualityPanel, /创作/);
  assert.match(qualityPanel, /门禁/);
  assert.match(qualityPanel, /承接/);
});

test("effective quality score is capped by final source evidence and drama gates", async () => {
  const { effectiveQualityScore } = await import("../src/lib/engine-types");

  const score = effectiveQualityScore({
    quality_report: {
      status: "needs_rewrite",
      scores: {
        hook: 9,
        conflict: 9,
        cliffhanger: 9,
        continuity: 9,
        video_feasibility: 9,
      },
      blocking_issues: [],
      rewrite_instruction: "source similarity below 5/10",
    },
    source_evidence_report: {
      coverage_score: 0,
      items: [],
      missing_items: ["EP05 缺少原文资产：霍雅偷拍照片"],
      rewrite_instruction: "原文证据未落到正片。",
    },
    drama_quality_report: {
      overall_score: 5,
      dimensions: [
        {
          name: "source_asset_preservation",
          score: 0,
          status: "blocking",
          evidence: ["source similarity below 5/10: 0/100"],
          suggestion: "恢复原文资产。",
        },
      ],
      blocking_issues: ["source_asset_preservation"],
      advisory_warnings: [],
      rewrite_instruction: "恢复原文资产。",
    },
  });

  assert.equal(score, 0);
});

test("episode quality score is not overwritten by round-level source gate", async () => {
  const {
    effectiveQualityScore,
    episodeQualityScore,
    sourceGateScore,
  } = await import("../src/lib/engine-types");
  const result = {
    quality_report: {
      status: "needs_human_review",
      scores: {
        hook: 10,
        conflict: 10,
        cliffhanger: 9,
        continuity: 10,
        video_feasibility: 9,
      },
      blocking_issues: [],
      rewrite_instruction: "source gate failed",
    },
    source_evidence_report: {
      coverage_score: 100,
      items: [
        {
          episode: 1,
          source_anchor: "EP01 source",
          adaptation_reason: "matched",
          retained_assets: ["hook"],
          script_evidence: ["hook"],
          status: "matched",
        },
        {
          episode: 2,
          source_anchor: "EP02 source",
          adaptation_reason: "missing specific anchor",
          retained_assets: ["VIP通道黄色炽热灯光"],
          script_evidence: [],
          status: "matched",
        },
      ],
      missing_items: [],
      rewrite_instruction: "",
    },
    adaptation_quality_report: {
      source_fidelity: {
        score: 10,
        preserved_original_hook: true,
        blocking_warnings: [
          "source anchor not evidenced in script: VIP通道黄色炽热灯光",
          "forbidden addition/reveal may have leaked into script: 严禁改变林挽清解约的主动性。",
        ],
        advisory_warnings: [],
        checks: [
          {
            category: "source_mapping",
            episode: 2,
            status: "blocking",
            warning: "source anchor not evidenced in script: VIP通道黄色炽热灯光",
          },
          {
            category: "C4_forbidden_addition",
            episode: null,
            status: "blocking",
            warning: "forbidden addition/reveal may have leaked into script",
          },
        ],
      },
      continuity: { score: 90, blocking_warnings: [], advisory_warnings: [] },
      story_state_ledger: {
        current_episode: 2,
        entries: [],
        open_hooks: [],
        forbidden_reveals: [],
        character_knowledge: {},
        relationship_changes: [],
        prop_states: [],
        foreshadowing_ledger: [],
        warnings: [],
      },
      blocking_warnings: [],
      advisory_warnings: [],
      rewrite_instruction: "",
    },
    drama_quality_report: {
      overall_score: 5,
      dimensions: [
        {
          name: "source_asset_preservation",
          score: 1,
          status: "blocking",
          evidence: ["source similarity below 5/10: 10/100"],
          suggestion: "restore source",
        },
      ],
      blocking_issues: [],
      advisory_warnings: [],
      rewrite_instruction: "",
    },
  } as never;

  assert.equal(effectiveQualityScore(result), 1);
  assert.equal(sourceGateScore(result), 1);
  assert.equal(episodeQualityScore(result, 1), 9.6);
  assert.equal(episodeQualityScore(result, 2), 4);
});

test("engine sync computes scores per episode instead of copying one round score", () => {
  const source = readFileSync(
    path.join(repoRoot, "src/lib/engine-runner.ts"),
    "utf-8"
  );

  assert.match(source, /episodeQualityScore\(result,\s*episode\.episode\)/);
  assert.doesNotMatch(source, /const score = effectiveQualityScore\(result\);/);
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

test("stale queued round generation is stopped instead of claimed days later", async () => {
  const { db, schema } = await import("../src/db/client");
  const { claimNextQueuedJob, STALE_QUEUED_JOB_MS } = await import("../src/lib/jobs");
  const stale = new Date(Date.now() - STALE_QUEUED_JOB_MS - 60_000);
  await db.insert(schema.projects).values({
    id: "project-p0-stale-queued",
    name: "Stale Queued Project",
    novelText: "source",
    targetEpisodeCount: 5,
    status: "running",
    createdAt: stale,
    updatedAt: stale,
  });
  await db.insert(schema.rounds).values({
    id: "round-p0-stale-queued",
    projectId: "project-p0-stale-queued",
    roundNum: 1,
    epRange: "EP01-EP05",
    status: "running",
    createdAt: stale,
  });
  await db.insert(schema.jobs).values({
    id: "job-p0-stale-queued",
    kind: "round_generation",
    title: "stale queued",
    projectId: "project-p0-stale-queued",
    roundId: "round-p0-stale-queued",
    status: "queued",
    progress: 0,
    createdAt: stale,
    updatedAt: stale,
  });

  const claimed = await claimNextQueuedJob({ kind: "round_generation" });

  const job = await db.query.jobs.findFirst({
    where: (jobs, { eq }) => eq(jobs.id, "job-p0-stale-queued"),
  });
  const project = await db.query.projects.findFirst({
    where: (projects, { eq }) => eq(projects.id, "project-p0-stale-queued"),
  });
  const round = await db.query.rounds.findFirst({
    where: (rounds, { eq }) => eq(rounds.id, "round-p0-stale-queued"),
  });
  assert.notEqual(claimed?.id, "job-p0-stale-queued");
  assert.equal(job?.status, "failed");
  assert.equal(project?.status, "failed");
  assert.equal(round?.status, "failed");
  assert.match(job?.errorText ?? "", /排队超过/);
});

test("retried queued round generation uses retry time for stale timeout", async () => {
  const { db, schema } = await import("../src/db/client");
  const { claimNextQueuedJob, STALE_QUEUED_JOB_MS } = await import("../src/lib/jobs");
  const staleCreatedAt = new Date(Date.now() - STALE_QUEUED_JOB_MS - 60_000);
  const retriedAt = new Date();
  await db.insert(schema.projects).values({
    id: "project-p0-retried-queued",
    name: "Retried Queued Project",
    novelText: "source",
    targetEpisodeCount: 5,
    status: "running",
    createdAt: staleCreatedAt,
    updatedAt: retriedAt,
  });
  await db.insert(schema.rounds).values({
    id: "round-p0-retried-queued",
    projectId: "project-p0-retried-queued",
    roundNum: 1,
    epRange: "EP01-EP05",
    status: "running",
    createdAt: staleCreatedAt,
  });
  await db.insert(schema.jobs).values({
    id: "job-p0-retried-queued",
    kind: "round_generation",
    title: "retried queued",
    projectId: "project-p0-retried-queued",
    roundId: "round-p0-retried-queued",
    status: "queued",
    progress: 0,
    attempts: 1,
    createdAt: staleCreatedAt,
    updatedAt: retriedAt,
    startedAt: null,
    finishedAt: null,
  });

  const claimed = await claimNextQueuedJob({ kind: "round_generation" });

  assert.equal(claimed?.id, "job-p0-retried-queued");
  assert.equal(claimed?.status, "running");
  assert.ok((claimed?.startedAt?.getTime() ?? 0) >= retriedAt.getTime());
  assert.equal(claimed?.attempts, 2);
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
    payloadJson: JSON.stringify({
      llmModel: "google/gemini-3.1-flash-lite",
      episodesPerRound: 5,
    }),
    createdAt: now,
    updatedAt: now,
    finishedAt: now,
  });

  const retried = await requeueRetryableJob("job-p1-retry", {
    payloadPatch: { llmModel: "bytedance-seed/seed-2.0-lite" },
  });

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
  assert.deepEqual(JSON.parse(retried.payloadJson ?? "{}"), {
    llmModel: "bytedance-seed/seed-2.0-lite",
    episodesPerRound: 5,
  });
});

test("quality gate failures are not presented as Engine execution failures", async () => {
  const { db, schema } = await import("../src/db/client");
  const { jobToView } = await import("../src/lib/jobs");
  const now = new Date();
  await db.insert(schema.jobs).values({
    id: "job-p0-quality-gate-classification",
    kind: "round_generation",
    title: "quality gate failure",
    status: "failed",
    progress: 100,
    message: "质量门禁未通过",
    errorText: "script quality error: EP03 与原文关键事件不一致",
    resultJson: JSON.stringify({
      failureCategory: "quality_gate",
      operatorHint: "脚本已生成，但未达到交付标准；请按问题定向修复或使用当前模型重试。",
      retryableNow: true,
    }),
    attempts: 1,
    createdAt: now,
    updatedAt: now,
    startedAt: now,
    finishedAt: now,
  });

  const job = await db.query.jobs.findFirst({
    where: (jobs, { eq }) => eq(jobs.id, "job-p0-quality-gate-classification"),
  });
  assert.ok(job);

  const view = jobToView(job);
  assert.equal(view.failureCategory, "quality_gate");
  assert.equal(view.statusReason, "质量门禁未通过");
  assert.match(view.operatorHint ?? "", /未达到交付标准/);
});

test("provider request timed out is classified as an Engine timeout", async () => {
  const { classifyJobFailureText } = await import("../src/lib/jobs");

  const failure = classifyJobFailureText(
    "OpenAI-compatible request failed while generating QualityReport: Request timed out."
  );

  assert.equal(failure?.category, "engine_timeout");
  assert.equal(failure?.userMessage, "生成超时，任务已停止");
});

test("succeeded jobs ignore stale failure diagnostics in result json", async () => {
  const { db, schema } = await import("../src/db/client");
  const { jobToView } = await import("../src/lib/jobs");
  const now = new Date();
  await db.insert(schema.jobs).values({
    id: "job-p0-succeeded-stale-failure-json",
    kind: "round_generation",
    title: "succeeded with stale diagnostics",
    status: "succeeded",
    progress: 100,
    message: "第 1 轮完成",
    resultJson: JSON.stringify({
      failureCategory: "engine_error",
      operatorHint: "旧失败提示不应污染成功态",
      notes: "previous error text kept for diagnosis",
    }),
    attempts: 1,
    createdAt: now,
    updatedAt: now,
    startedAt: now,
    finishedAt: now,
  });

  const job = await db.query.jobs.findFirst({
    where: (jobs, { eq }) => eq(jobs.id, "job-p0-succeeded-stale-failure-json"),
  });
  assert.ok(job);

  const view = jobToView(job);

  assert.equal(view.status, "succeeded");
  assert.equal(view.retryable, false);
  assert.equal(view.failureCategory, null);
  assert.equal(view.statusReason, null);
  assert.equal(view.operatorHint, null);
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

test("engine round succeeds when quality audit is red and continues scheduling", () => {
  const source = readFileSync(
    path.join(repoRoot, "src/lib/engine-runner.ts"),
    "utf-8"
  );
  const syncIndex = source.indexOf("await syncEngineRoundToDb(project, roundId, result);");
  const succeedIndex = source.indexOf("await succeedJob(jobId", syncIndex);
  const scheduleIndex = source.indexOf(
    "await scheduleNextRoundIfRunAll(project.id)",
    succeedIndex
  );
  const completionBlock = source.slice(syncIndex, succeedIndex);

  assert.ok(syncIndex > 0);
  assert.ok(succeedIndex > syncIndex);
  assert.ok(scheduleIndex > succeedIndex);
  assert.match(completionBlock, /质量审计待复核/);
  assert.doesNotMatch(completionBlock, /await failJob\(jobId/);
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

test("source evidence view type accepts source-unverified item status", () => {
  const item = {
    episode: 1,
    source_anchor: "EP01 原文资产",
    adaptation_reason: "上游资产未能回溯到原文",
    retained_assets: ["新增证据"],
    script_evidence: ["△新增证据被展示。"],
    evidence_spans: [],
    status: "source_unverified",
  } satisfies EngineSourceEvidenceItem;

  assert.equal(item.status, "source_unverified");
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

test("project list response redacts full novel text", async () => {
  const { GET } = await import("../src/app/api/projects/route");
  const { db, schema } = await import("../src/db/client");
  const { resolvePlatformContextFromInput } = await import(
    "../src/lib/platform-context"
  );
  const now = new Date();
  const context = await resolvePlatformContextFromInput({
    email: "redact-list@example.com",
    tenantSlug: "redact-list-tenant",
    tenantName: "Redact List Tenant",
  });
  const otherContext = await resolvePlatformContextFromInput({
    email: "other-redact-list@example.com",
    tenantSlug: "redact-list-tenant",
    tenantName: "Redact List Tenant",
  });
  const fullNovel = "这是一整本不应该出现在列表响应里的小说原文。";
  await db.insert(schema.projects).values({
    id: "project-p0-redact-list",
    tenantId: context.tenant.id,
    ownerUserId: context.user.id,
    name: "Redacted List",
    novelText: fullNovel,
    targetEpisodeCount: 5,
    status: "draft",
    createdAt: now,
    updatedAt: now,
  });
  await db.insert(schema.projects).values({
    id: "project-p0-redact-list-other-owner",
    tenantId: otherContext.tenant.id,
    ownerUserId: otherContext.user.id,
    name: "Other Owner Project",
    novelText: "同一个 workspace 里，其他 owner 的小说也不能出现在列表。",
    targetEpisodeCount: 5,
    status: "draft",
    createdAt: now,
    updatedAt: now,
  });

  const res = await GET(
    new Request("http://localhost/api/projects", {
      headers: {
        "x-novel-user-email": "redact-list@example.com",
        "x-novel-tenant": "redact-list-tenant",
        "x-novel-tenant-name": "Redact List Tenant",
      },
    }) as never
  );
  const body = (await res.json()) as Array<Record<string, unknown>>;
  const project = body.find((item) => item.id === "project-p0-redact-list");
  const otherProject = body.find(
    (item) => item.id === "project-p0-redact-list-other-owner"
  );

  assert.ok(project);
  assert.equal(otherProject, undefined);
  assert.equal(Object.prototype.hasOwnProperty.call(project, "novelText"), false);
  assert.equal(project.novelExcerpt, undefined);
  assert.equal(project.novelCharCount, fullNovel.length);
});

test("project workspace payload and server-rendered props redact full novel text", async () => {
  const { GET } = await import("../src/app/api/projects/[id]/route");
  const res = await GET(
    new Request("http://localhost/api/projects/project-p0-redact-list", {
      headers: {
        "x-novel-user-email": "redact-list@example.com",
        "x-novel-tenant": "redact-list-tenant",
        "x-novel-tenant-name": "Redact List Tenant",
      },
    }),
    { params: Promise.resolve({ id: "project-p0-redact-list" }) }
  );
  const body = (await res.json()) as {
    project: Record<string, unknown>;
  };
  const pageSource = readFileSync(
    path.join(repoRoot, "src/app/projects/[id]/rounds/[n]/page.tsx"),
    "utf-8"
  );

  assert.equal(res.status, 200);
  assert.equal(
    Object.prototype.hasOwnProperty.call(body.project, "novelText"),
    false
  );
  assert.match(pageSource, /project=\{projectWorkspaceView\(project\)\}/);
});

test("job list is isolated by project owner inside the same tenant", async () => {
  const { GET } = await import("../src/app/api/jobs/route");
  const { db, schema } = await import("../src/db/client");
  const { resolvePlatformContextFromInput } = await import(
    "../src/lib/platform-context"
  );
  const now = new Date();
  const ownerContext = await resolvePlatformContextFromInput({
    email: "job-owner@example.com",
    tenantSlug: "job-owner-tenant",
    tenantName: "Job Owner Tenant",
  });
  const otherContext = await resolvePlatformContextFromInput({
    email: "job-other@example.com",
    tenantSlug: "job-owner-tenant",
    tenantName: "Job Owner Tenant",
  });
  await db.insert(schema.projects).values([
    {
      id: "project-p0-job-owner-visible",
      tenantId: ownerContext.tenant.id,
      ownerUserId: ownerContext.user.id,
      name: "Visible Job Project",
      novelText: "source",
      targetEpisodeCount: 5,
      status: "running",
      createdAt: now,
      updatedAt: now,
    },
    {
      id: "project-p0-job-owner-hidden",
      tenantId: otherContext.tenant.id,
      ownerUserId: otherContext.user.id,
      name: "Hidden Job Project",
      novelText: "other source",
      targetEpisodeCount: 5,
      status: "running",
      createdAt: now,
      updatedAt: now,
    },
  ]);
  await db.insert(schema.jobs).values([
    {
      id: "job-p0-owner-visible",
      kind: "delivery_export",
      status: "queued",
      tenantId: ownerContext.tenant.id,
      projectId: "project-p0-job-owner-visible",
      title: "Visible delivery job",
      progress: 0,
      attempts: 0,
      createdAt: now,
      updatedAt: now,
    },
    {
      id: "job-p0-owner-hidden",
      kind: "delivery_export",
      status: "queued",
      tenantId: otherContext.tenant.id,
      projectId: "project-p0-job-owner-hidden",
      title: "Hidden delivery job",
      progress: 0,
      attempts: 0,
      createdAt: now,
      updatedAt: now,
    },
  ]);

  const res = await GET(
    new Request("http://localhost/api/jobs?limit=20", {
      headers: {
        "x-novel-user-email": "job-owner@example.com",
        "x-novel-tenant": "job-owner-tenant",
        "x-novel-tenant-name": "Job Owner Tenant",
      },
    }) as never
  );
  const body = (await res.json()) as Array<{ id: string }>;

  assert.equal(res.status, 200);
  assert.ok(body.some((job) => job.id === "job-p0-owner-visible"));
  assert.equal(body.some((job) => job.id === "job-p0-owner-hidden"), false);
});

test("delivery export request creates an async job instead of running export inline", async () => {
  const { POST } = await import("../src/app/api/projects/[id]/export/route");
  const { db, schema } = await import("../src/db/client");
  const { resolvePlatformContextFromInput } = await import(
    "../src/lib/platform-context"
  );
  const now = new Date();
  const context = await resolvePlatformContextFromInput({
    email: "async-export@example.com",
    tenantSlug: "async-export-tenant",
    tenantName: "Async Export Tenant",
  });
  await db.insert(schema.projects).values({
    id: "project-p0-async-export",
    tenantId: context.tenant.id,
    ownerUserId: context.user.id,
    name: "Async Export",
    novelText: "source",
    targetEpisodeCount: 5,
    status: "done",
    createdAt: now,
    updatedAt: now,
  });

  const previousAutoWorker = process.env.NOVEL_DRAMA_AUTO_WORKER;
  try {
    process.env.NOVEL_DRAMA_AUTO_WORKER = "0";
    const res = await POST(
      new Request(
        "http://localhost/api/projects/project-p0-async-export/export?round=1&allowIssues=1",
        {
          method: "POST",
          headers: {
            "x-novel-user-email": "async-export@example.com",
            "x-novel-tenant": "async-export-tenant",
            "x-novel-tenant-name": "Async Export Tenant",
            "idempotency-key": "delivery-export-once",
          },
        }
      ) as never,
      { params: Promise.resolve({ id: "project-p0-async-export" }) }
    );
    const body = (await res.json()) as { jobId?: string; status?: string };
    const jobs = await db.query.jobs.findMany({
      where: (jobsTable, { eq }) =>
        eq(jobsTable.projectId, "project-p0-async-export"),
    });

    assert.equal(res.status, 202);
    assert.equal(body.status, "queued");
    assert.ok(body.jobId);
    assert.equal(jobs.length, 1);
    assert.equal(jobs[0].kind, "delivery_export");
  } finally {
    setEnv("NOVEL_DRAMA_AUTO_WORKER", previousAutoWorker);
  }
});

test("project creation is deterministic, asynchronous, and idempotent", async () => {
  const { POST } = await import("../src/app/api/projects/route");
  const { db, schema } = await import("../src/db/client");
  const previousAutoWorker = process.env.NOVEL_DRAMA_AUTO_WORKER;
  process.env.NOVEL_DRAMA_AUTO_WORKER = "0";

  const createRequest = () => {
    const form = new FormData();
    form.set("name", "Idempotent Project");
    form.set("targetEpisodeCount", "5");
    form.set("file", new File(["第一章 她被当众赶出宴会。"], "source.txt"));
    return new Request("http://localhost/api/projects", {
      method: "POST",
      headers: {
        "x-novel-user-email": "project-create@example.com",
        "x-novel-tenant": "project-create-tenant",
        "x-novel-tenant-name": "Project Create Tenant",
        "idempotency-key": "create-project-once",
      },
      body: form,
    });
  };

  try {
    const first = await POST(createRequest() as never);
    const second = await POST(createRequest() as never);
    const firstBody = (await first.json()) as { id: string; jobId: string };
    const secondBody = (await second.json()) as { id: string; jobId: string };
    const projects = await db.query.projects.findMany({
      where: (projectsTable, { eq }) =>
        eq(projectsTable.name, "Idempotent Project"),
    });
    const jobs = await db.query.jobs.findMany({
      where: (jobsTable, { and, eq }) =>
        and(
          eq(jobsTable.kind, "round_generation"),
          eq(jobsTable.idempotencyKey, "project-create:create-project-once")
        ),
    });

    assert.equal(first.status, 202);
    assert.equal(second.status, 202);
    assert.equal(secondBody.id, firstBody.id);
    assert.equal(secondBody.jobId, firstBody.jobId);
    assert.equal(projects.length, 1);
    assert.equal(jobs.length, 1);
    assert.equal(jobs[0].status, "queued");
  } finally {
    setEnv("NOVEL_DRAMA_AUTO_WORKER", previousAutoWorker);
  }
});

test("project creation route never runs the legacy LLM upload judge inline", () => {
  const source = readFileSync(
    path.join(repoRoot, "src/app/api/projects/route.ts"),
    "utf-8"
  );

  assert.doesNotMatch(source, /normalizeNovel/);
  assert.match(source, /parseUpload/);
  assert.match(source, /extractRuleBasedMeta/);
});

test("episode optimization and edit application are queued instead of calling LLM inline", async () => {
  const optimizeRoute = await import(
    "../src/app/api/episodes/[id]/optimize/route"
  );
  const impactRoute = await import("../src/app/api/episodes/[id]/impact/route");
  const { db, schema } = await import("../src/db/client");
  const { resolvePlatformContextFromInput } = await import(
    "../src/lib/platform-context"
  );
  const context = await resolvePlatformContextFromInput({
    email: "async-edit@example.com",
    tenantSlug: "async-edit-tenant",
    tenantName: "Async Edit Tenant",
  });
  const now = new Date();
  await db.insert(schema.projects).values({
    id: "project-p0-async-edit",
    tenantId: context.tenant.id,
    ownerUserId: context.user.id,
    name: "Async Edit",
    novelText: "第一章 原文冲突。",
    targetEpisodeCount: 2,
    status: "done",
    createdAt: now,
    updatedAt: now,
  });
  await db.insert(schema.rounds).values({
    id: "round-p0-async-edit",
    projectId: "project-p0-async-edit",
    roundNum: 1,
    epRange: "EP01-EP02",
    status: "done",
    createdAt: now,
  });
  await db.insert(schema.episodes).values({
    id: "episode-p0-async-edit",
    projectId: "project-p0-async-edit",
    roundId: "round-p0-async-edit",
    epNum: 1,
    scriptTxt: "第1集 原稿",
    draftMd: "第1集 原稿",
    status: "green",
    updatedAt: now,
  });

  const headers = {
    "Content-Type": "application/json",
    "x-novel-user-email": "async-edit@example.com",
    "x-novel-tenant": "async-edit-tenant",
    "x-novel-tenant-name": "Async Edit Tenant",
  };
  const previousAutoWorker = process.env.NOVEL_DRAMA_AUTO_WORKER;
  process.env.NOVEL_DRAMA_AUTO_WORKER = "0";
  try {
    const optimizeResponse = await optimizeRoute.POST(
      new Request("http://localhost/api/episodes/episode-p0-async-edit/optimize", {
        method: "POST",
        headers,
        body: JSON.stringify({ instruction: "加强情绪递进" }),
      }),
      { params: Promise.resolve({ id: "episode-p0-async-edit" }) }
    );
    const impactResponse = await impactRoute.POST(
      new Request("http://localhost/api/episodes/episode-p0-async-edit/impact", {
        method: "POST",
        headers,
        body: JSON.stringify({
          editedScriptText: "第1集 用户改稿",
          applyEdit: true,
          optimizeDownstream: true,
        }),
      }),
      { params: Promise.resolve({ id: "episode-p0-async-edit" }) }
    );
    const jobs = await db.query.jobs.findMany({
      where: (jobsTable, { eq }) =>
        eq(jobsTable.projectId, "project-p0-async-edit"),
    });

    assert.equal(optimizeResponse.status, 202);
    assert.equal(impactResponse.status, 202);
    assert.deepEqual(
      jobs.map((job) => job.kind).sort(),
      ["edit_impact", "episode_optimize"]
    );
    assert.ok(jobs.every((job) => job.status === "queued"));
  } finally {
    setEnv("NOVEL_DRAMA_AUTO_WORKER", previousAutoWorker);
  }
});

test("ops worker setup consumes every async export job kind", () => {
  const workerSource = readFileSync(
    path.join(repoRoot, "src/scripts/job-worker.ts"),
    "utf-8"
  );
  const installSource = readFileSync(
    path.join(repoRoot, "scripts/install-ops-launchagent.sh"),
    "utf-8"
  );
  const expectedKinds = [
    "delivery_export",
    "video_brief_export",
    "localization_export",
    "episode_optimize",
    "edit_impact",
  ];

  for (const kind of expectedKinds) {
    assert.match(workerSource, new RegExp(kind));
  }
  assert.match(installSource, /ops-delivery-worker\.plist/);
  assert.match(installSource, /ops-video-brief-worker\.plist/);
  assert.match(installSource, /ops-localization-worker\.plist/);
  assert.match(installSource, /ops-episode-optimize-worker\.plist/);
  assert.match(installSource, /ops-edit-impact-worker\.plist/);
});

test("operational launch agents never force the mock engine", () => {
  const plistFiles = [
    "com.novel-to-drama.ops-web.plist",
    "com.novel-to-drama.ops-worker.plist",
    "com.novel-to-drama.ops-quality-worker.plist",
    "com.novel-to-drama.ops-delivery-worker.plist",
    "com.novel-to-drama.ops-video-brief-worker.plist",
    "com.novel-to-drama.ops-localization-worker.plist",
    "com.novel-to-drama.ops-episode-optimize-worker.plist",
    "com.novel-to-drama.ops-edit-impact-worker.plist",
  ];

  for (const file of plistFiles) {
    const source = readFileSync(path.join(repoRoot, "ops", file), "utf-8");
    assert.doesNotMatch(
      source,
      /<key>NOVEL_DRAMA_WEB_MOCK<\/key>\s*<string>1<\/string>/
    );
  }
});

test("round status is reconciled from episode status and cannot stay done with failed episode", async () => {
  const { db, schema } = await import("../src/db/client");
  const { reconcileRoundStatusFromEpisodes } = await import(
    "../src/lib/engine-runner"
  );
  const now = new Date();
  await db.insert(schema.projects).values({
    id: "project-p0-round-status-aggregate",
    name: "Round Aggregate",
    novelText: "source",
    targetEpisodeCount: 5,
    status: "done",
    createdAt: now,
    updatedAt: now,
  });
  await db.insert(schema.rounds).values({
    id: "round-p0-status-aggregate",
    projectId: "project-p0-round-status-aggregate",
    roundNum: 1,
    epRange: "EP01-EP05",
    status: "done",
    createdAt: now,
  });
  await db.insert(schema.episodes).values([
    {
      id: "episode-p0-status-green",
      projectId: "project-p0-round-status-aggregate",
      roundId: "round-p0-status-aggregate",
      epNum: 1,
      status: "green",
      retryCount: 0,
      updatedAt: now,
    },
    {
      id: "episode-p0-status-failed",
      projectId: "project-p0-round-status-aggregate",
      roundId: "round-p0-status-aggregate",
      epNum: 2,
      status: "failed",
      retryCount: 0,
      updatedAt: now,
    },
  ]);

  await reconcileRoundStatusFromEpisodes("round-p0-status-aggregate");

  const round = await db.query.rounds.findFirst({
    where: (rounds, { eq }) => eq(rounds.id, "round-p0-status-aggregate"),
  });
  assert.equal(round?.status, "failed");
});

test("round status stays done when episodes only need quality review", async () => {
  const { db, schema } = await import("../src/db/client");
  const { reconcileRoundStatusFromEpisodes } = await import(
    "../src/lib/engine-runner"
  );
  const now = new Date();
  await db.insert(schema.projects).values({
    id: "project-p0-round-status-red-audit",
    name: "Round Red Audit",
    novelText: "source",
    targetEpisodeCount: 5,
    status: "running",
    createdAt: now,
    updatedAt: now,
  });
  await db.insert(schema.rounds).values({
    id: "round-p0-status-red-audit",
    projectId: "project-p0-round-status-red-audit",
    roundNum: 1,
    epRange: "EP01-EP05",
    status: "running",
    createdAt: now,
  });
  await db.insert(schema.episodes).values([
    {
      id: "episode-p0-status-red-audit-1",
      projectId: "project-p0-round-status-red-audit",
      roundId: "round-p0-status-red-audit",
      epNum: 1,
      status: "red",
      retryCount: 0,
      updatedAt: now,
    },
    {
      id: "episode-p0-status-red-audit-2",
      projectId: "project-p0-round-status-red-audit",
      roundId: "round-p0-status-red-audit",
      epNum: 2,
      status: "green",
      retryCount: 0,
      updatedAt: now,
    },
  ]);

  await reconcileRoundStatusFromEpisodes("round-p0-status-red-audit");

  const round = await db.query.rounds.findFirst({
    where: (rounds, { eq }) => eq(rounds.id, "round-p0-status-red-audit"),
  });
  assert.equal(round?.status, "done");
});

test("core one-to-one artifacts have database uniqueness constraints", async () => {
  const { db, schema } = await import("../src/db/client");
  const now = new Date();
  await db.insert(schema.projects).values({
    id: "project-p0-unique-artifacts",
    name: "Unique Artifacts",
    novelText: "source",
    targetEpisodeCount: 5,
    status: "running",
    createdAt: now,
    updatedAt: now,
  });
  await db.insert(schema.bibles).values({
    id: "bible-p0-unique-1",
    projectId: "project-p0-unique-artifacts",
    updatedAt: now,
  });
  await assert.rejects(
    () =>
      db.insert(schema.bibles).values({
        id: "bible-p0-unique-2",
        projectId: "project-p0-unique-artifacts",
        updatedAt: now,
      }),
    /unique/i
  );

  await db.insert(schema.rounds).values({
    id: "round-p0-unique-1",
    projectId: "project-p0-unique-artifacts",
    roundNum: 1,
    epRange: "EP01-EP05",
    status: "done",
    createdAt: now,
  });
  await assert.rejects(
    () =>
      db.insert(schema.rounds).values({
        id: "round-p0-unique-2",
        projectId: "project-p0-unique-artifacts",
        roundNum: 1,
        epRange: "EP01-EP05 copy",
        status: "done",
        createdAt: now,
      }),
    /unique/i
  );

  await db.insert(schema.episodes).values({
    id: "episode-p0-unique-1",
    projectId: "project-p0-unique-artifacts",
    roundId: "round-p0-unique-1",
    epNum: 1,
    status: "green",
    retryCount: 0,
    updatedAt: now,
  });
  await assert.rejects(
    () =>
      db.insert(schema.episodes).values({
        id: "episode-p0-unique-2",
        projectId: "project-p0-unique-artifacts",
        roundId: "round-p0-unique-1",
        epNum: 1,
        status: "green",
        retryCount: 0,
        updatedAt: now,
      }),
    /unique/i
  );
});

test("round workspace requests are pinned to the server-resolved platform session", () => {
  const pageSource = readFileSync(
    path.join(repoRoot, "src/app/projects/[id]/rounds/[n]/page.tsx"),
    "utf-8"
  );
  const clientSource = readFileSync(
    path.join(repoRoot, "src/app/projects/[id]/rounds/[n]/RoundClient.tsx"),
    "utf-8"
  );

  assert.match(pageSource, /const \{ context, session \} = await resolvePlatformPageContext\(\)/);
  assert.match(pageSource, /platformSession=\{session\}/);
  assert.doesNotMatch(clientSource, /nextHeaders\.set\("x-novel-tenant/);
  assert.doesNotMatch(clientSource, /nextHeaders\.set\("x-novel-user-email/);
  assert.match(clientSource, /credentials:\s*"same-origin"/);
  assert.match(clientSource, /assertPlatformResponseContext/);
  const retryStart = clientSource.indexOf("async function retryJob");
  const retryEnd = clientSource.indexOf("async function cloneProject", retryStart);
  const retryBlock = clientSource.slice(retryStart, retryEnd);
  assert.match(retryBlock, /"Content-Type":\s*"application\/json"/);
  assert.match(retryBlock, /llmModel:\s*selectedLlmModel/);
  assert.equal(
    /(?<!platform)fetch\(\s*[`'"]\/api/.test(clientSource),
    false,
    "RoundClient API calls must use platformFetch so Web and Codex tests share the same tenant context"
  );
});

test("production platform context ignores forged browser identity headers", async () => {
  const previous = {
    trust: process.env.NOVEL_DRAMA_TRUST_IDENTITY_HEADERS,
    email: process.env.NOVEL_DRAMA_USER_EMAIL,
    tenant: process.env.NOVEL_DRAMA_TENANT_SLUG,
    tenantName: process.env.NOVEL_DRAMA_TENANT_NAME,
  };
  try {
    delete process.env.NOVEL_DRAMA_TRUST_IDENTITY_HEADERS;
    process.env.NOVEL_DRAMA_USER_EMAIL = "trusted-owner@example.com";
    process.env.NOVEL_DRAMA_TENANT_SLUG = "trusted-workspace";
    process.env.NOVEL_DRAMA_TENANT_NAME = "Trusted Workspace";
    const { resolvePlatformContext } = await import("../src/lib/platform-context");
    const context = await resolvePlatformContext(
      new Request("http://localhost/api/projects", {
        headers: {
          "x-novel-user-email": "forged@example.com",
          "x-novel-tenant": "forged-workspace",
        },
      }) as never
    );

    assert.equal(context.user.email, "trusted-owner@example.com");
    assert.equal(context.tenant.slug, "trusted-workspace");
  } finally {
    setEnv("NOVEL_DRAMA_TRUST_IDENTITY_HEADERS", previous.trust);
    setEnv("NOVEL_DRAMA_USER_EMAIL", previous.email);
    setEnv("NOVEL_DRAMA_TENANT_SLUG", previous.tenant);
    setEnv("NOVEL_DRAMA_TENANT_NAME", previous.tenantName);
  }
});

test("workspace session uses one signed HttpOnly cookie instead of raw identity cookies", async () => {
  const previousSecret = process.env.NOVEL_DRAMA_SESSION_SECRET;
  process.env.NOVEL_DRAMA_SESSION_SECRET = "test-session-secret";
  try {
    const { POST } = await import("../src/app/api/platform/session/route");
    const response = await POST(
      new Request("http://localhost/api/platform/session", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          email: "signed-session@example.com",
          tenantSlug: "signed-session",
          tenantName: "Signed Session",
        }),
      }) as never
    );
    const cookie = response.headers.get("set-cookie") ?? "";

    assert.equal(response.status, 200);
    assert.match(cookie, /novel_platform_session=/);
    assert.match(cookie, /HttpOnly/i);
    assert.match(cookie, /novel_user_email=;/);
    assert.doesNotMatch(cookie, /novel_user_email=[^;,]/);
  } finally {
    setEnv("NOVEL_DRAMA_SESSION_SECRET", previousSecret);
  }
});

test("round generation retries disable cached engine round_result reuse", () => {
  const source = readFileSync(
    path.join(repoRoot, "src/lib/engine-runner.ts"),
    "utf-8"
  );

  assert.match(source, /NOVEL_DRAMA_RESUME_ARTIFACTS/);
  assert.match(
    source,
    /await runNovelDrama\(args,\s*\{\s*resumeArtifacts:\s*false,\s*llmModel:\s*selectedModel,?\s*\}\s*\)/
  );
});
