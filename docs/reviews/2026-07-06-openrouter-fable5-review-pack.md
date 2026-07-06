# OpenRouter Fable 5 Review Pack

- Generated: 2026-07-06T20:53:06
- Repo: `/Users/wangzipeng/Documents/小说转剧本`
- Branch: `codex/unify-platform-flow`
- HEAD: `ce8664e0503ba0e84a5650903f0cedc2f6ba9192`
- Review model requested: `anthropic/claude-fable-5`

## Product Contract

This is a novel-to-vertical-short-drama platform, not a one-shot rewrite tool. The stable product spine is:

`source analysis -> round/context resolver -> system-owned Story Bible -> episode plan -> script generation -> quality gates -> state ledger/writeback -> exports/web jobs`

Key product constraints:

- Story Bible is internal/system-owned; no user confirmation gate in MVP.
- Later rounds automatically derive source episode range and context from original source + prior state.
- Strong source material should be lightly adapted: preserve C0 facts, C1 hooks/signature scenes/emotional sequence; enhance visuals/pace, do not rewrite away the original hit assets.
- The platform must support replayable A/B and traceability: prompts, model, input package, cache fingerprint, raw output, rendered output, quality reports.
- Separate human-facing creative scripts from AI-video shooting/execution script requirements.

## Current Change Bundle To Review

This bundle contains the latest P0/P1/P2 platform-chain fixes:

### P0

- Production-like deployments default to real engine unless mock is explicit.
- Ops scripts default mock off.
- Round-generation jobs are unique while a round has queued/running job.
- Payment webhooks require verified signature unless explicit mock bypass is enabled.
- Low/no-blocking drama-quality advisory no longer forces rewrite by itself.
- Episode repair fallback defaults to no speculative repair.

### P1

- Stale/failed round job does not mark whole project failed.
- Retry restores round/project to running state from any requeue path.
- Successful current job is marked succeeded before scheduling the next batch round.
- Hook/source evidence matching requires specific event/asset overlap, not just shared character names.
- LLM quality prompt now judges drama/continuity/source fidelity from digest only; deterministic local gates own line-level metrics.
- Run manifest includes repair fallback env and prior-round artifact reuse now requires compatible manifest.

### P2

- Source evidence report now emits source-span evidence per retained asset: source excerpt/line/index, script line/index, adaptation reason, matched/missing.
- Source span selection uses best-hit matching instead of first weak match.
- Frontend engine types include span fields.
- README/architecture docs mention source-span evidence as A/B/review artifact.

## Verification Already Run

- `python3 -m pytest -q` passed.
- `npm run test:ts` passed.
- `npm run build` passed.
- `git diff --check` passed.

## Reviewer Instructions

You are an external senior architecture/process reviewer. Review the new chain for production readiness and whether it satisfies the product contract above.

Output in Chinese, with this exact structure:

1. Overall verdict: one of `ready`, `ready_with_followups`, `not_ready`.
2. P0 blockers: bullets with severity, exact file path, function/class/area, why it matters, and concrete fix.
3. P1 important fixes: same format.
4. P2 followups: same format.
5. Quality-chain risks: whether this chain can prove it beats direct LLM rewrite; mention missing evidence if any.
6. Files to inspect/change next: exact file list grouped by priority.
7. Minimal next action plan: 5-8 steps, test command for each major step.

Focus on real bugs, architecture holes, replayability, cache correctness, job state correctness, source fidelity, and quality evaluation. Do not spend time on generic style nits.

## Git Status

```text
 M README.md
 M docs/PROMPT_SKILL_ARCHITECTURE.md
 M drizzle/migrations/meta/_journal.json
 M package.json
 M scripts/start-ops-server.sh
 M scripts/start-ops-worker.sh
 M src/app/api/health/route.ts
 M src/app/api/platform/payments/webhook/route.ts
 M src/db/schema.ts
 M src/lib/engine-runner.ts
 M src/lib/engine-types.ts
 M src/lib/jobs.ts
 M src/lib/platform-credits.ts
 M src/novel_drama_engine/adaptation_quality.py
 M src/novel_drama_engine/drama_quality.py
 M src/novel_drama_engine/models.py
 M src/novel_drama_engine/pipeline.py
 M src/novel_drama_engine/prompts.py
 M src/novel_drama_engine/source_evidence.py
 M tests/test_adaptation_quality.py
 M tests/test_drama_quality.py
 M tests/test_pipeline.py
 M tests/test_prompt_script_quality_contract.py
 M tests/test_source_evidence.py
?? drizzle/migrations/0008_material_silvermane.sql
?? drizzle/migrations/meta/0008_snapshot.json
?? tests/p0_platform.test.ts

```

## Diff Stat

```text
 README.md                                      |   1 +
 docs/PROMPT_SKILL_ARCHITECTURE.md              |   1 +
 drizzle/migrations/meta/_journal.json          |   7 +
 package.json                                   |   1 +
 scripts/start-ops-server.sh                    |   2 +-
 scripts/start-ops-worker.sh                    |   2 +-
 src/app/api/health/route.ts                    |   7 +-
 src/app/api/platform/payments/webhook/route.ts |   6 +-
 src/db/schema.ts                               |  73 +++++++----
 src/lib/engine-runner.ts                       |  90 +++++++++----
 src/lib/engine-types.ts                        |  13 ++
 src/lib/jobs.ts                                |  63 ++++++++-
 src/lib/platform-credits.ts                    |   7 +
 src/novel_drama_engine/adaptation_quality.py   |  26 +++-
 src/novel_drama_engine/drama_quality.py        |  16 +++
 src/novel_drama_engine/models.py               |  13 ++
 src/novel_drama_engine/pipeline.py             |  43 +++++--
 src/novel_drama_engine/prompts.py              |  28 ++--
 src/novel_drama_engine/source_evidence.py      | 169 ++++++++++++++++++++++---
 tests/test_adaptation_quality.py               |  12 ++
 tests/test_drama_quality.py                    |  41 ++----
 tests/test_pipeline.py                         |  92 +++++++++++++-
 tests/test_prompt_script_quality_contract.py   |  15 ++-
 tests/test_source_evidence.py                  | 112 +++++++++++++++-
 24 files changed, 688 insertions(+), 152 deletions(-)

```

## Changed Tracked Files

```text
README.md
docs/PROMPT_SKILL_ARCHITECTURE.md
drizzle/migrations/meta/_journal.json
package.json
scripts/start-ops-server.sh
scripts/start-ops-worker.sh
src/app/api/health/route.ts
src/app/api/platform/payments/webhook/route.ts
src/db/schema.ts
src/lib/engine-runner.ts
src/lib/engine-types.ts
src/lib/jobs.ts
src/lib/platform-credits.ts
src/novel_drama_engine/adaptation_quality.py
src/novel_drama_engine/drama_quality.py
src/novel_drama_engine/models.py
src/novel_drama_engine/pipeline.py
src/novel_drama_engine/prompts.py
src/novel_drama_engine/source_evidence.py
tests/test_adaptation_quality.py
tests/test_drama_quality.py
tests/test_pipeline.py
tests/test_prompt_script_quality_contract.py
tests/test_source_evidence.py

```

## Full Tracked Diff

```diff
diff --git a/README.md b/README.md
index 4144277..2741cf1 100644
--- a/README.md
+++ b/README.md
@@ -344,6 +344,7 @@ The command writes:
 - `.drama_project/round_001/raw_llm_output.jsonl` for raw model responses
 - `.drama_project/round_001/prompt_trace_analysis.md` for cache/prompt/raw-output diagnosis
 - `.drama_project/round_001/script_novelty_report.md` for cross-episode repetition and novelty diagnosis
+- `.drama_project/round_001/source_evidence_report.md` for source-span evidence that links retained source assets to source lines, script lines, and adaptation reasons
 
 To regenerate the diagnosis report for an existing round:
 
diff --git a/docs/PROMPT_SKILL_ARCHITECTURE.md b/docs/PROMPT_SKILL_ARCHITECTURE.md
index f4b1b9a..b4f5b8f 100644
--- a/docs/PROMPT_SKILL_ARCHITECTURE.md
+++ b/docs/PROMPT_SKILL_ARCHITECTURE.md
@@ -106,6 +106,7 @@ source analysis -> viral asset extraction -> episode/context resolver
 - `NOVEL_DRAMA_SCRIPT_EPISODE_FIRST=0` 的整轮首稿路径；设为 `1` 可测试逐集生成/失败修复，但要重点检查上下集承接
 - `NOVEL_DRAMA_EXPERIMENT_MODE=1` 的无缓存追踪路径；每次 A/B 都要保留 `prompt_trace.json`、`raw_llm_output.jsonl`、`prompt_trace_analysis.md`
 - `creative_script.md` vs `shooting_script.md` 的分离产物；前者评戏，后者评 AI 视频执行可拍性，不能混成一个门槛
+- `source_evidence_report.md` 的 source span evidence；每个 retained asset 要能追到原文行、脚本行和改写原因，用来判断强原文轻改是否真的执行
 - `quality_user` / `state_user` 默认消费 `script_batch_digest`，只给集数摘要、场景骨架、开头/结尾关键行和状态更新；完整剧本文本留在 artifact 与本地确定性 gate，避免 QA/状态回写 prompt 过载
 - Story State Ledger 会把 previous_context 的 open hook 和同轮 episode cliffhanger 标为 open/closed：如果下一轮开头或下一集开头已承接则关闭；如果 next_round_context 没带最终钩子，会写 warning，防止下一轮开头丢承接
 
diff --git a/package.json b/package.json
index 6575dd8..0eed5d5 100644
--- a/package.json
+++ b/package.json
@@ -7,6 +7,7 @@
     "build": "next build",
     "start": "next start",
     "engine": "python3 -m novel_drama_engine.cli",
+    "test:ts": "node --test --import tsx tests/*.test.ts",
     "ops:start": "scripts/start-ops-server.sh",
     "ops:install": "scripts/install-ops-launchagent.sh",
     "ops:health": "scripts/ops-health-check.sh",
diff --git a/scripts/start-ops-server.sh b/scripts/start-ops-server.sh
index df41a32..25525e1 100755
--- a/scripts/start-ops-server.sh
+++ b/scripts/start-ops-server.sh
@@ -15,7 +15,7 @@ export PATH="/usr/local/bin:/opt/homebrew/bin:/Library/Frameworks/Python.framewo
 export NODE_ENV="${NODE_ENV:-production}"
 export PORT="${PORT:-3000}"
 export OPS_HOST="${OPS_HOST:-::}"
-export NOVEL_DRAMA_WEB_MOCK="${NOVEL_DRAMA_WEB_MOCK:-1}"
+export NOVEL_DRAMA_WEB_MOCK="${NOVEL_DRAMA_WEB_MOCK:-0}"
 export NOVEL_DRAMA_AUTO_WORKER="${NOVEL_DRAMA_AUTO_WORKER:-0}"
 export NOVEL_DRAMA_DB_PATH="${NOVEL_DRAMA_DB_PATH:-$ROOT_DIR/db.sqlite}"
 export NOVEL_DRAMA_USER_EMAIL="${NOVEL_DRAMA_USER_EMAIL:-ops@novel-drama.local}"
diff --git a/scripts/start-ops-worker.sh b/scripts/start-ops-worker.sh
index a213d5a..7540795 100644
--- a/scripts/start-ops-worker.sh
+++ b/scripts/start-ops-worker.sh
@@ -13,7 +13,7 @@ fi
 
 export PATH="/usr/local/bin:/opt/homebrew/bin:/Library/Frameworks/Python.framework/Versions/3.14/bin:/usr/bin:/bin:/usr/sbin:/sbin"
 export NODE_ENV="${NODE_ENV:-production}"
-export NOVEL_DRAMA_WEB_MOCK="${NOVEL_DRAMA_WEB_MOCK:-1}"
+export NOVEL_DRAMA_WEB_MOCK="${NOVEL_DRAMA_WEB_MOCK:-0}"
 export NOVEL_DRAMA_AUTO_WORKER="0"
 export NOVEL_DRAMA_DB_PATH="${NOVEL_DRAMA_DB_PATH:-$ROOT_DIR/db.sqlite}"
 export NOVEL_DRAMA_USER_EMAIL="${NOVEL_DRAMA_USER_EMAIL:-ops@novel-drama.local}"
diff --git a/src/app/api/health/route.ts b/src/app/api/health/route.ts
index 2e2cdd6..dc4a6ed 100644
--- a/src/app/api/health/route.ts
+++ b/src/app/api/health/route.ts
@@ -2,9 +2,11 @@ import {
   deploymentReadiness,
   resolveDatabasePath,
 } from "@/lib/deployment-readiness";
+import { resolveEngineMode } from "@/lib/engine-runner";
 
 export async function GET() {
-  const mockMode = process.env.NOVEL_DRAMA_WEB_MOCK === "1";
+  const engineMode = resolveEngineMode();
+  const mockMode = engineMode.mode === "mock";
   let baseUrlHost: string | null = null;
   if (process.env.OPENAI_BASE_URL) {
     try {
@@ -16,7 +18,8 @@ export async function GET() {
   return Response.json({
     ok: true,
     app: "novel-to-drama",
-    mode: mockMode ? "mock" : "real",
+    mode: engineMode.mode,
+    explicitMock: engineMode.explicitMock,
     autoWorker: process.env.NOVEL_DRAMA_AUTO_WORKER ?? "default",
     db: {
       path: resolveDatabasePath(),
diff --git a/src/app/api/platform/payments/webhook/route.ts b/src/app/api/platform/payments/webhook/route.ts
index 566a8a1..b286445 100644
--- a/src/app/api/platform/payments/webhook/route.ts
+++ b/src/app/api/platform/payments/webhook/route.ts
@@ -33,10 +33,7 @@ function normalizeSignature(value: string | null): string | null {
 function verifyWebhookSignature(req: NextRequest, rawBody: string): boolean {
   const secret = webhookSecret();
   if (!secret) {
-    if (process.env.NODE_ENV === "production") {
-      throw new Error("payment webhook secret is not configured");
-    }
-    return false;
+    throw new Error("payment webhook secret is not configured; unsigned webhooks are rejected");
   }
   const provided = normalizeSignature(signatureHeader(req));
   if (!provided) {
@@ -67,6 +64,7 @@ export async function POST(req: NextRequest) {
     return NextResponse.json(
       await processPaymentWebhook({
         ...body,
+        signatureVerified,
         raw: {
           ...body,
           signatureVerified,
diff --git a/src/db/schema.ts b/src/db/schema.ts
index 89731a1..01292ba 100644
--- a/src/db/schema.ts
+++ b/src/db/schema.ts
@@ -1,4 +1,11 @@
-import { sqliteTable, text, integer, real } from "drizzle-orm/sqlite-core";
+import { sql } from "drizzle-orm";
+import {
+  sqliteTable,
+  text,
+  integer,
+  real,
+  uniqueIndex,
+} from "drizzle-orm/sqlite-core";
 
 export const users = sqliteTable("users", {
   id: text("id").primaryKey(),
@@ -180,33 +187,43 @@ export const rounds = sqliteTable("rounds", {
   createdAt: integer("created_at", { mode: "timestamp_ms" }).notNull(),
 });
 
-export const jobs = sqliteTable("jobs", {
-  id: text("id").primaryKey(),
-  kind: text("kind", {
-    enum: ["round_generation", "quality_samples"],
-  }).notNull(),
-  status: text("status", {
-    enum: ["queued", "running", "succeeded", "failed"],
-  })
-    .notNull()
-    .default("queued"),
-  projectId: text("project_id").references(() => projects.id, {
-    onDelete: "cascade",
-  }),
-  tenantId: text("tenant_id").references(() => tenants.id, { onDelete: "cascade" }),
-  roundId: text("round_id").references(() => rounds.id, { onDelete: "set null" }),
-  title: text("title").notNull(),
-  progress: integer("progress").notNull().default(0),
-  message: text("message"),
-  errorText: text("error_text"),
-  payloadJson: text("payload_json"),
-  resultJson: text("result_json"),
-  attempts: integer("attempts").notNull().default(0),
-  createdAt: integer("created_at", { mode: "timestamp_ms" }).notNull(),
-  updatedAt: integer("updated_at", { mode: "timestamp_ms" }).notNull(),
-  startedAt: integer("started_at", { mode: "timestamp_ms" }),
-  finishedAt: integer("finished_at", { mode: "timestamp_ms" }),
-});
+export const jobs = sqliteTable(
+  "jobs",
+  {
+    id: text("id").primaryKey(),
+    kind: text("kind", {
+      enum: ["round_generation", "quality_samples"],
+    }).notNull(),
+    status: text("status", {
+      enum: ["queued", "running", "succeeded", "failed"],
+    })
+      .notNull()
+      .default("queued"),
+    projectId: text("project_id").references(() => projects.id, {
+      onDelete: "cascade",
+    }),
+    tenantId: text("tenant_id").references(() => tenants.id, { onDelete: "cascade" }),
+    roundId: text("round_id").references(() => rounds.id, { onDelete: "set null" }),
+    title: text("title").notNull(),
+    progress: integer("progress").notNull().default(0),
+    message: text("message"),
+    errorText: text("error_text"),
+    payloadJson: text("payload_json"),
+    resultJson: text("result_json"),
+    attempts: integer("attempts").notNull().default(0),
+    createdAt: integer("created_at", { mode: "timestamp_ms" }).notNull(),
+    updatedAt: integer("updated_at", { mode: "timestamp_ms" }).notNull(),
+    startedAt: integer("started_at", { mode: "timestamp_ms" }),
+    finishedAt: integer("finished_at", { mode: "timestamp_ms" }),
+  },
+  (table) => [
+    uniqueIndex("jobs_active_round_generation_unique")
+      .on(table.roundId)
+      .where(
+        sql`${table.kind} = 'round_generation' and ${table.roundId} is not null and ${table.status} in ('queued', 'running')`
+      ),
+  ]
+);
 
 export const usageEvents = sqliteTable("usage_events", {
   id: text("id").primaryKey(),
diff --git a/src/lib/engine-runner.ts b/src/lib/engine-runner.ts
index 4a0fb37..799a348 100644
--- a/src/lib/engine-runner.ts
+++ b/src/lib/engine-runner.ts
@@ -111,16 +111,35 @@ function novelDramaCommand(args: string[]): { command: string; args: string[] }
   };
 }
 
+export function isProductionLikeDeployment(): boolean {
+  return (
+    process.env.NODE_ENV === "production" ||
+    process.env.NOVEL_DRAMA_ONLINE_MODE === "1" ||
+    process.env.NOVEL_DRAMA_DEPLOYMENT_TARGET === "production"
+  );
+}
+
+export function resolveEngineMode(): { mode: "mock" | "real"; explicitMock: boolean } {
+  if (process.env.NOVEL_DRAMA_WEB_MOCK === "1") {
+    return { mode: "mock", explicitMock: true };
+  }
+  if (process.env.NOVEL_DRAMA_WEB_MOCK === "0") {
+    return { mode: "real", explicitMock: false };
+  }
+  if (isProductionLikeDeployment()) {
+    return { mode: "real", explicitMock: false };
+  }
+  return { mode: process.env.OPENAI_API_KEY ? "real" : "mock", explicitMock: false };
+}
+
 function shouldUseMockEngine(): boolean {
-  if (process.env.NOVEL_DRAMA_WEB_MOCK === "1") return true;
-  if (process.env.NOVEL_DRAMA_WEB_MOCK === "0") return false;
-  return !process.env.OPENAI_API_KEY;
+  return resolveEngineMode().mode === "mock";
 }
 
-function realEngineConfigProblem(): string | null {
+export function realEngineConfigProblem(): string | null {
   if (shouldUseMockEngine()) return null;
   if (!process.env.OPENAI_API_KEY) {
-    return "OPENAI_API_KEY is not set while NOVEL_DRAMA_WEB_MOCK=0";
+    return "OPENAI_API_KEY is not set while real Engine mode is enabled";
   }
   if (!process.env.OPENAI_MODEL) {
     return "OPENAI_MODEL is not set while real Engine mode is enabled";
@@ -129,6 +148,7 @@ function realEngineConfigProblem(): string | null {
 }
 
 function redactedProviderConfig(): Record<string, unknown> {
+  const engineMode = resolveEngineMode();
   let baseUrlHost: string | null = null;
   if (process.env.OPENAI_BASE_URL) {
     try {
@@ -138,7 +158,8 @@ function redactedProviderConfig(): Record<string, unknown> {
     }
   }
   return {
-    mode: shouldUseMockEngine() ? "mock" : "real",
+    mode: engineMode.mode,
+    explicitMock: engineMode.explicitMock,
     provider: process.env.NOVEL_DRAMA_LLM_PROVIDER ?? null,
     model: process.env.OPENAI_MODEL ?? null,
     baseUrlHost,
@@ -1016,28 +1037,45 @@ async function executeEngineRound(
     });
     const result = await readEngineRoundResult(project.id, roundNumber);
     await syncEngineRoundToDb(project, roundId, result);
-    const nextJob = await scheduleNextRoundIfRunAll(project.id);
+    const completionResult = {
+      projectId: project.id,
+      roundId,
+      roundNumber,
+      targetEpisodeRange: result.episode_context.target_episode_range,
+      qualityStatus: result.quality_report.status,
+      generationVariant: selectedGenerationVariant,
+      repairBudget: selectedRepairBudget,
+      episodesPerRound: selectedEpisodesPerRound,
+      runtimeMs: result.runtime_report?.total_duration_ms,
+      llmCalls: result.runtime_report?.llm_calls.length,
+      sourceStrength: result.source_strength_profile?.overall_level ?? null,
+      adaptationIntensity:
+        result.source_strength_profile?.recommended_intensity ?? null,
+      methodologyCards:
+        result.methodology_context?.cards?.map((card) => card.name) ?? [],
+      nextJobId: null as string | null,
+      nextRoundScheduleError: null as string | null,
+    };
     await succeedJob(jobId, {
       message: `第 ${roundNumber} 轮完成`,
-      result: {
-        projectId: project.id,
-        roundId,
-        roundNumber,
-        targetEpisodeRange: result.episode_context.target_episode_range,
-        qualityStatus: result.quality_report.status,
-        generationVariant: selectedGenerationVariant,
-        repairBudget: selectedRepairBudget,
-        episodesPerRound: selectedEpisodesPerRound,
-        runtimeMs: result.runtime_report?.total_duration_ms,
-        llmCalls: result.runtime_report?.llm_calls.length,
-        sourceStrength: result.source_strength_profile?.overall_level ?? null,
-        adaptationIntensity:
-          result.source_strength_profile?.recommended_intensity ?? null,
-        methodologyCards:
-          result.methodology_context?.cards?.map((card) => card.name) ?? [],
-        nextJobId: nextJob?.jobId ?? null,
-      },
+      result: completionResult,
     });
+    try {
+      const nextJob = await scheduleNextRoundIfRunAll(project.id);
+      if (nextJob) {
+        completionResult.nextJobId = nextJob.jobId;
+        await updateJob(jobId, { result: completionResult });
+      }
+    } catch (scheduleError) {
+      const scheduleMessage =
+        scheduleError instanceof Error ? scheduleError.message : String(scheduleError);
+      completionResult.nextRoundScheduleError = scheduleMessage;
+      await updateJob(jobId, {
+        message: `第 ${roundNumber} 轮完成；下一轮调度失败`,
+        result: completionResult,
+      });
+      console.error("[engine-runner] next round schedule failed:", scheduleError);
+    }
   } catch (error) {
     const message = error instanceof Error ? error.message : String(error);
     const failure = classifyJobFailureText(message);
@@ -1083,7 +1121,7 @@ async function executeEngineRound(
       .where(eq(schema.rounds.id, roundId));
     await db
       .update(schema.projects)
-      .set({ status: "failed", updatedAt: new Date() })
+      .set({ status: "running", updatedAt: new Date() })
       .where(eq(schema.projects.id, project.id));
     await failJob(jobId, error, {
       message: failure?.userMessage ?? "生成失败",
diff --git a/src/lib/engine-types.ts b/src/lib/engine-types.ts
index cf0a33f..f779d7f 100644
--- a/src/lib/engine-types.ts
+++ b/src/lib/engine-types.ts
@@ -311,6 +311,19 @@ export interface EngineSourceEvidenceItem {
   adaptation_reason: string;
   retained_assets: string[];
   script_evidence: string[];
+  evidence_spans?: EngineSourceEvidenceSpan[];
+  status: "matched" | "missing";
+}
+
+export interface EngineSourceEvidenceSpan {
+  asset: string;
+  source_anchor: string;
+  source_excerpt: string;
+  source_line?: string | null;
+  source_line_index?: number | null;
+  script_line?: string | null;
+  script_line_index?: number | null;
+  adaptation_reason: string;
   status: "matched" | "missing";
 }
 
diff --git a/src/lib/jobs.ts b/src/lib/jobs.ts
index c6115a9..5d1491c 100644
--- a/src/lib/jobs.ts
+++ b/src/lib/jobs.ts
@@ -1,4 +1,4 @@
-import { and, asc, desc, eq, lt, type SQL } from "drizzle-orm";
+import { and, asc, desc, eq, inArray, lt, type SQL } from "drizzle-orm";
 import { v4 as uuid } from "uuid";
 import { db, schema } from "@/db/client";
 import type { EngineJob } from "./engine-types";
@@ -207,6 +207,23 @@ export function isJobRetryable(job: Pick<JobRow, "status" | "updatedAt">): boole
   return job.status === "failed" || isRunningJobStale(job);
 }
 
+async function restoreRoundGenerationRetryState(job: JobRow): Promise<void> {
+  if (job.kind !== "round_generation") return;
+  const now = new Date();
+  if (job.roundId) {
+    await db
+      .update(schema.rounds)
+      .set({ status: "running", summaryJson: null })
+      .where(eq(schema.rounds.id, job.roundId));
+  }
+  if (job.projectId) {
+    await db
+      .update(schema.projects)
+      .set({ status: "running", updatedAt: now })
+      .where(eq(schema.projects.id, job.projectId));
+  }
+}
+
 export function jobToView(job: JobRow): EngineJob {
   const isRunningStale = isRunningJobStale(job);
   const isQueuedTooLong = isQueuedJobWaitingTooLong(job);
@@ -277,6 +294,24 @@ export async function createJob({
   status?: JobStatus;
   progress?: number;
 }): Promise<JobRow> {
+  if (
+    kind === "round_generation" &&
+    roundId &&
+    (status === "queued" || status === "running")
+  ) {
+    const activeJob = await db.query.jobs.findFirst({
+      where: and(
+        eq(schema.jobs.kind, kind),
+        eq(schema.jobs.roundId, roundId),
+        inArray(schema.jobs.status, ["queued", "running"])
+      ),
+    });
+    if (activeJob) {
+      throw new Error(
+        `active job already exists for round ${roundId}: ${activeJob.id}`
+      );
+    }
+  }
   const now = new Date();
   const row: JobInsert = {
     id: uuid(),
@@ -293,7 +328,28 @@ export async function createJob({
     updatedAt: now,
     startedAt: status === "running" ? now : null,
   };
-  await db.insert(schema.jobs).values(row);
+  try {
+    await db.insert(schema.jobs).values(row);
+  } catch (error) {
+    const message = error instanceof Error ? error.message : String(error);
+    if (
+      kind === "round_generation" &&
+      roundId &&
+      /jobs_active_round_generation_unique|unique/i.test(message)
+    ) {
+      const activeJob = await db.query.jobs.findFirst({
+        where: and(
+          eq(schema.jobs.kind, kind),
+          eq(schema.jobs.roundId, roundId),
+          inArray(schema.jobs.status, ["queued", "running"])
+        ),
+      });
+      throw new Error(
+        `active job already exists for round ${roundId}: ${activeJob?.id ?? "unknown"}`
+      );
+    }
+    throw error;
+  }
   const created = await db.query.jobs.findFirst({
     where: eq(schema.jobs.id, row.id),
   });
@@ -396,6 +452,7 @@ export async function requeueRetryableJob(jobId: string): Promise<JobRow> {
   }
   const reason = job.status === "failed" ? "重试" : "恢复队列";
 
+  await restoreRoundGenerationRetryState(job);
   await updateJob(job.id, {
     status: "queued",
     progress: 0,
@@ -507,7 +564,7 @@ export async function reconcileStaleJobs({
         })
         .where(eq(schema.rounds.id, job.roundId));
     }
-    if (job.projectId) {
+    if (job.projectId && job.kind !== "round_generation") {
       await db
         .update(schema.projects)
         .set({ status: "failed", updatedAt: now })
diff --git a/src/lib/platform-credits.ts b/src/lib/platform-credits.ts
index 11d300a..69269a5 100644
--- a/src/lib/platform-credits.ts
+++ b/src/lib/platform-credits.ts
@@ -446,8 +446,15 @@ export async function processPaymentWebhook(payload: {
   eventType?: string;
   checkoutSessionId?: string;
   externalEventId?: string;
+  signatureVerified?: boolean;
   raw?: unknown;
 }): Promise<{ ok: boolean; webhookEventId: string }> {
+  if (
+    payload.signatureVerified !== true &&
+    process.env.NOVEL_DRAMA_ALLOW_UNSIGNED_MOCK_WEBHOOKS !== "1"
+  ) {
+    throw new Error("payment webhook signature is required before processing");
+  }
   const eventId = uuid();
   let tenantId: string | null = null;
   let session: CheckoutSessionRow | undefined;
diff --git a/src/novel_drama_engine/adaptation_quality.py b/src/novel_drama_engine/adaptation_quality.py
index 8db18a7..11aee1b 100644
--- a/src/novel_drama_engine/adaptation_quality.py
+++ b/src/novel_drama_engine/adaptation_quality.py
@@ -897,6 +897,21 @@ def _token_overlap(left: str, right: str) -> int:
     return sum((left_tokens & right_tokens).values())
 
 
+def _token_match_strength(needle: str, haystack: str) -> tuple[int, int]:
+    normalized_haystack = normalize_text(haystack)
+    tokens = [token for token in _tokens(needle) if len(token) >= 2]
+    matched = sum(1 for token in tokens if normalize_text(token) in normalized_haystack)
+    return matched, len(tokens)
+
+
+def _has_late_event_overlap(needle: str, haystack: str) -> bool:
+    compact = normalize_text(needle)
+    if len(compact) <= 4:
+        return True
+    late_segment = compact[4:]
+    return any(normalize_text(token) in normalize_text(haystack) for token in _tokens(late_segment))
+
+
 def build_continuity_audit_report(
     *,
     episode_context: EpisodeContext,
@@ -969,9 +984,14 @@ def _entry_value(value: Any) -> str:
 
 
 def _hook_acknowledged(hook: str, text: str) -> bool:
-    return bool(hook.strip() and text.strip()) and (
-        _loose_contains(text, hook) or _token_overlap(hook, text) > 0
-    )
+    if not (hook.strip() and text.strip()):
+        return False
+    if normalize_text(hook) in normalize_text(text):
+        return True
+    matched, total = _token_match_strength(hook, text)
+    if total <= 2:
+        return matched == total and matched > 0
+    return matched >= 3 and (matched / total) >= 0.25 and _has_late_event_overlap(hook, text)
 
 
 def build_story_state_ledger(
diff --git a/src/novel_drama_engine/drama_quality.py b/src/novel_drama_engine/drama_quality.py
index e014ad5..cccec21 100644
--- a/src/novel_drama_engine/drama_quality.py
+++ b/src/novel_drama_engine/drama_quality.py
@@ -318,6 +318,22 @@ def merge_drama_quality_into_report(
 ) -> QualityReport:
     if not drama_quality_report.blocking_issues and drama_quality_report.overall_score >= 7:
         return quality_report
+    if not drama_quality_report.blocking_issues:
+        advisory_instruction = "；".join(
+            part
+            for part in [
+                quality_report.rewrite_instruction,
+                (
+                    "drama_quality advisory: "
+                    f"overall {drama_quality_report.overall_score}/10；"
+                    f"{drama_quality_report.rewrite_instruction}"
+                ),
+            ]
+            if part.strip()
+        )
+        return quality_report.model_copy(
+            update={"rewrite_instruction": advisory_instruction}
+        )
     issues = [*quality_report.blocking_issues]
     issues.extend(
         f"drama_quality: {issue}"
diff --git a/src/novel_drama_engine/models.py b/src/novel_drama_engine/models.py
index d745e81..d053f6f 100644
--- a/src/novel_drama_engine/models.py
+++ b/src/novel_drama_engine/models.py
@@ -827,12 +827,25 @@ class ScriptNoveltyReport(BaseModel):
     rewrite_instruction: str = ""
 
 
+class SourceEvidenceSpan(BaseModel):
+    asset: str
+    source_anchor: str
+    source_excerpt: str
+    source_line: str | None = None
+    source_line_index: int | None = Field(default=None, ge=1)
+    script_line: str | None = None
+    script_line_index: int | None = Field(default=None, ge=1)
+    adaptation_reason: str
+    status: Literal["matched", "missing"]
+
+
 class SourceEvidenceItem(BaseModel):
     episode: int = Field(ge=1)
     source_anchor: str
     adaptation_reason: str
     retained_assets: list[str] = Field(default_factory=list)
     script_evidence: list[str] = Field(default_factory=list)
+    evidence_spans: list[SourceEvidenceSpan] = Field(default_factory=list)
     status: Literal["matched", "missing"]
 
 
diff --git a/src/novel_drama_engine/pipeline.py b/src/novel_drama_engine/pipeline.py
index 886a9c9..d1342d4 100644
--- a/src/novel_drama_engine/pipeline.py
+++ b/src/novel_drama_engine/pipeline.py
@@ -110,6 +110,7 @@ CACHE_RELEVANT_ENV = (
     "NOVEL_DRAMA_LLM_PROVIDER",
     "NOVEL_DRAMA_GENERATION_VARIANT",
     "NOVEL_DRAMA_REPAIR_BUDGET",
+    "NOVEL_DRAMA_EPISODE_REPAIR_FALLBACK",
     "NOVEL_DRAMA_SCRIPT_EPISODE_FIRST",
     "NOVEL_DRAMA_SCRIPT_PROMPT_MODE",
     "NOVEL_DRAMA_STRICT_SHOOTING_QUALITY",
@@ -503,7 +504,7 @@ def strong_source_light_adaptation(
 
 
 def fallback_episode_repair_targets(episode_numbers: list[int]) -> set[int]:
-    raw = os.environ.get("NOVEL_DRAMA_EPISODE_REPAIR_FALLBACK", "first")
+    raw = os.environ.get("NOVEL_DRAMA_EPISODE_REPAIR_FALLBACK", "none")
     normalized = raw.strip().lower().replace("-", "_")
     if normalized in {"all", "full", "every", "全部"}:
         return set(episode_numbers)
@@ -853,6 +854,8 @@ class RoundPipeline:
                 if candidate < round_number
             ]
             for prior_round_number in reversed(prior_round_numbers):
+                if not prior_run_manifest_compatible(prior_round_number):
+                    continue
                 artifact = self.store.read_round_artifact(
                     prior_round_number,
                     name,
@@ -862,6 +865,36 @@ class RoundPipeline:
                     return artifact
             return None
 
+        def prior_run_manifest_compatible(prior_round_number: int) -> bool:
+            path = self.store.project_dir / f"round_{prior_round_number:03d}" / "run_manifest.json"
+            if not path.exists():
+                return False
+            try:
+                prior_manifest = json.loads(path.read_text(encoding="utf-8"))
+            except json.JSONDecodeError:
+                return False
+
+            comparable_keys = (
+                "schema_version",
+                "project_id",
+                "source_sha256",
+                "source_chars",
+                "target_episode_count",
+                "generation_variant",
+                "repair_budget",
+                "llm_class",
+                "llm_model",
+                "llm_provider",
+                "openai_base_url",
+                "env",
+                "code",
+                "methodology_cards_path",
+            )
+            return all(
+                prior_manifest.get(key) == expected_manifest.get(key)
+                for key in comparable_keys
+            )
+
         def record_cached_stage(name: str) -> None:
             stages.append(
                 PipelineStageMetric(
@@ -1443,13 +1476,7 @@ class RoundPipeline:
                         else "No local, reported, missing, or fallback episode targets.",
                     )
                     repaired_batch = current_script_batch
-                    repaired_quality = run_stage(
-                        "mark_human_review_without_repair_targets",
-                        lambda: current_quality_report.model_copy(
-                            update={"status": QualityStatus.NEEDS_HUMAN_REVIEW},
-                        ),
-                    )
-                    return repaired_batch, repaired_quality
+                    return repaired_batch, current_quality_report
                 self.store.write_round_artifact(
                     round_number,
                     "script_batch_episode_repair",
diff --git a/src/novel_drama_engine/prompts.py b/src/novel_drama_engine/prompts.py
index 78023af..6b05856 100644
--- a/src/novel_drama_engine/prompts.py
+++ b/src/novel_drama_engine/prompts.py
@@ -1140,34 +1140,30 @@ def quality_user(
         stage_instruction(
             "检查 script_batch 是否达到可交付短剧正片标准。只要出现任一硬伤，status=needs_rewrite，并在 rewrite_instruction 中逐集说明怎么补足。",
             (
-                "按集检查：结构体量 -> 前 8 beat 冲突 -> EpisodeDramaPlan 执行度 -> "
-                "SeriesEpisodeOutline 信息增量 -> C0/C1/C4 原著保真 -> 镜头可执行度 -> 台词效率 -> 最后 2 行追更钩子 -> "
-                "状态连续性和题材模板一致性。"
+                "本地确定性质检已经负责逐行硬指标：字数、行数、scene 数、action/dialogue 数量、"
+                "action 格式、景别运镜、对白长度、最后两行模板和 metadata 泄漏。"
+                "不要凭摘要声称逐行检查了每条 action 或每句对白，也不要把这些硬指标当成你的主要评分依据。"
             ),
             (
-                "硬性拒绝以下问题：单集少于 800 字、少于 2 场、少于 8 条镜头动作、"
-                "少于 16 条对白/OS/VO、开头 8 个 beat 没有爆冲突、"
-                "scene.heading 不是 集数-场次 日/夜-内/外-具体地点、OS 后没有动作承接、"
-                "结尾钩子太软、题材模板错配。rewrite_instruction 必须指出第几集、哪个硬伤、"
-                "应该补哪些场面、镜头、动作、短台词或结尾钩子。"
+                "只基于 script_batch_digest 可见内容判断：戏剧质量、跨集连续性、人物动机、"
+                "原著保真和题材模板一致性。重点看 opening_lines/tail_lines/scene_skeleton 是否显示"
+                "冲突递进、信息增量、真实人物反应、原文 C0/C1 资产和可理解的关系状态。"
+                "rewrite_instruction 必须指出第几集、哪个戏剧硬伤、回到哪条原文资产或哪段人物逻辑补救。"
                 f"{SOURCE_FIDELITY_QUALITY_RULE}"
             ),
             (
                 "如果 series_structure_plan 不为空，还要检查每集是否有信息增量、是否匹配对应 ending_hook_type、"
-                "是否连续水集、是否偏离人物标签和全局节奏。逐集检查最后一场最后 2 行是否把 cliffhanger 演成动作、对白或道具特写；"
-                "只在字段里写 cliffhanger、另起说明行或营销看点行都不合格。"
-                "cliffhanger 字段必须能在最后一场最后 4 行中找到相同台词或动作；"
+                "是否连续水集、是否偏离人物标签和全局节奏。"
+                "cliffhanger 字段必须能在摘要中的 tail_lines 里找到可见承接；"
                 "“留下悬念/关于身份的悬念/气氛紧张”等说明句不合格。"
                 "必须检查第一场：原文有 C1 天然钩子但脚本删除/降级，或原文无天然钩子但脚本没有事实兼容型钩子，都不合格。"
                 "必须检查人物：台词或动作若改变 Story Bible 中的人物动机、说话方式、关系状态，或把 C0 决策时机改掉，都不合格。"
-                "必须检查 action 是否包含景别、运镜、构图/光线、道具、表情、音效/BGM 和镜头衔接；"
-                f"{ACTION_LINE_TEMPLATE_RULE}{SHOT_LINKAGE_RULE}{FINAL_TWO_LINE_RULE}{INFO_INCREMENT_RULE}"
-                "对白是否超过 22 字、是否解释价值观、是否一行塞多个信息。"
+                "如果摘要显示台词在解释价值观、同一情绪反复打转、上一集结尾和下一集开头不照应，必须指出。"
             ),
             (
                 "如果用户可见剧本文本里把 hook/主情绪/watch_reason 当成独立说明展示，"
-                "或出现“消费理由/观众要看/本集看点”等分析词，或 action 缺少景别/运镜/构图/衔接，"
-                "或 action 只是“众人震惊/气氛凝固/他很害怕”这种抽象描述，或对白显著啰嗦，也必须重写。"
+                "或出现“消费理由/观众要看/本集看点”等分析词，或摘要显示动作只是"
+                "“众人震惊/气氛凝固/他很害怕”这种抽象描述，或对白显著啰嗦，也必须重写。"
                 "题材模板错配必须拦截：男频穿越/大宋/武大郎/金莲/西门庆类不得混入"
                 "真假千金/豪门宴会/总裁/亲子鉴定/大小姐模板，反向也不得串戏。"
             ),
diff --git a/src/novel_drama_engine/source_evidence.py b/src/novel_drama_engine/source_evidence.py
index ed96b25..b625224 100644
--- a/src/novel_drama_engine/source_evidence.py
+++ b/src/novel_drama_engine/source_evidence.py
@@ -11,8 +11,9 @@ from novel_drama_engine.models import (
     ScriptBatch,
     SourceEvidenceItem,
     SourceEvidenceReport,
+    SourceEvidenceSpan,
 )
-from novel_drama_engine.renderer import render_line
+from novel_drama_engine.renderer import render_shooting_episode
 
 
 def _compact(text: str) -> str:
@@ -47,27 +48,127 @@ def _asset_needles(asset: str) -> list[str]:
     return list(dict.fromkeys(needles))
 
 
+def _asset_tokens(asset: str) -> list[str]:
+    compact = _compact(asset)
+    tokens: list[str] = []
+    for run in re.findall(r"[\u4e00-\u9fffA-Za-z0-9]{2,}", compact):
+        tokens.append(run)
+        if re.fullmatch(r"[\u4e00-\u9fff]{4,}", run):
+            tokens.extend(run[index : index + 2] for index in range(0, len(run) - 1))
+    return list(dict.fromkeys(token for token in tokens if len(token) >= 2))
+
+
+def _has_specific_asset_overlap(line: str, asset: str) -> bool:
+    compact_asset = _compact(asset)
+    if len(compact_asset) <= 4:
+        return False
+    compact_line = _compact(line)
+    late_tokens = _asset_tokens(compact_asset[4:])
+    return any(token in compact_line for token in late_tokens)
+
+
 def _line_matches_asset(line: str, asset: str) -> bool:
     compact_line = _compact(line)
     if not compact_line:
         return False
-    return any(needle in compact_line for needle in _asset_needles(asset))
+    compact_asset = _compact(asset)
+    if compact_asset and compact_asset in compact_line:
+        return True
+    if len(compact_asset) <= 4:
+        return any(needle in compact_line for needle in _asset_needles(asset))
+
+    tokens = _asset_tokens(asset)
+    if not tokens:
+        return False
+    matched = sum(1 for token in tokens if token in compact_line)
+    coverage = matched / max(1, len(tokens))
+    return matched >= 3 and coverage >= 0.25 and _has_specific_asset_overlap(line, asset)
+
+
+def _asset_match_score(line: str, asset: str) -> float:
+    compact_line = _compact(line)
+    compact_asset = _compact(asset)
+    if not compact_line:
+        return 0
+    if compact_asset and compact_asset in compact_line:
+        return 1000 + len(compact_asset)
+    tokens = _asset_tokens(asset)
+    if not tokens:
+        return 0
+    matched = sum(1 for token in tokens if token in compact_line)
+    coverage = matched / max(1, len(tokens))
+    if not _line_matches_asset(line, asset):
+        return 0
+    late_bonus = 2 if _has_specific_asset_overlap(line, asset) else 0
+    return matched + coverage + late_bonus
+
+
+def _script_line_entries(script: EpisodeScript) -> list[tuple[int, str]]:
+    rendered = render_shooting_episode(script)
+    return [
+        (index, line.strip())
+        for index, line in enumerate(rendered.splitlines(), start=1)
+        if line.strip()
+    ]
 
 
 def _script_lines(script: EpisodeScript) -> list[str]:
-    lines: list[str] = [script.title, script.hook_3s, script.cliffhanger]
-    for scene in script.scenes:
-        lines.append(scene.heading)
-        lines.append("、".join(scene.characters))
-        lines.extend(render_line(line) for line in scene.lines)
-    return [line.strip() for line in lines if line and line.strip()]
-
-
-def _evidence_for_asset(lines: list[str], asset: str) -> str | None:
-    for line in lines:
-        if _line_matches_asset(line, asset):
-            return line
-    return None
+    return [line for _, line in _script_line_entries(script)]
+
+
+def _line_entry_for_asset(
+    entries: list[tuple[int, str]],
+    asset: str,
+) -> tuple[int | None, str | None]:
+    candidates = [
+        (_asset_match_score(line, asset), index, line)
+        for index, line in entries
+    ]
+    candidates = [candidate for candidate in candidates if candidate[0] > 0]
+    if not candidates:
+        return None, None
+    _, index, line = max(candidates, key=lambda item: item[0])
+    return index, line
+
+
+def _source_line_for_asset(
+    packet: EpisodeSourcePacket,
+    asset: str,
+) -> tuple[int | None, str | None]:
+    lines = [line.strip() for line in packet.source_excerpt.splitlines() if line.strip()]
+    candidates = [
+        (_asset_match_score(line, asset), index, line)
+        for index, line in enumerate(lines, start=1)
+    ]
+    candidates = [candidate for candidate in candidates if candidate[0] > 0]
+    if candidates:
+        _, index, line = max(candidates, key=lambda item: item[0])
+        return index, line
+    anchor = packet.source_anchor.strip()
+    if anchor and _line_matches_asset(anchor, asset):
+        return 1, anchor
+    return None, None
+
+
+def _evidence_span_for_asset(
+    packet: EpisodeSourcePacket,
+    asset: str,
+    script_entries: list[tuple[int, str]],
+    adaptation_reason: str,
+) -> SourceEvidenceSpan:
+    source_line_index, source_line = _source_line_for_asset(packet, asset)
+    script_line_index, script_line = _line_entry_for_asset(script_entries, asset)
+    return SourceEvidenceSpan(
+        asset=asset,
+        source_anchor=packet.source_anchor,
+        source_excerpt=packet.source_excerpt,
+        source_line=source_line,
+        source_line_index=source_line_index,
+        script_line=script_line,
+        script_line_index=script_line_index,
+        adaptation_reason=adaptation_reason,
+        status="matched" if script_line else "missing",
+    )
 
 
 def _packet_assets(packet: EpisodeSourcePacket) -> list[str]:
@@ -144,18 +245,27 @@ def build_source_evidence_report(
         if script is None:
             continue
 
-        lines = _script_lines(script)
+        line_entries = _script_line_entries(script)
         assets = _packet_assets(packet)
         if not assets:
             assets = [packet.source_anchor]
 
-        script_evidence: list[str] = []
+        adaptation_reason = _packet_reason(packet)
+        evidence_spans: list[SourceEvidenceSpan] = []
         for asset in assets:
-            evidence = _evidence_for_asset(lines, asset)
-            if evidence:
-                script_evidence.append(evidence)
+            evidence_spans.append(
+                _evidence_span_for_asset(
+                    packet,
+                    asset,
+                    line_entries,
+                    adaptation_reason,
+                )
+            )
 
         total_count += 1
+        script_evidence = [
+            span.script_line for span in evidence_spans if span.script_line
+        ]
         unique_evidence = list(dict.fromkeys(script_evidence))[:6]
         if unique_evidence:
             matched_count += 1
@@ -170,9 +280,10 @@ def build_source_evidence_report(
             SourceEvidenceItem(
                 episode=packet.episode,
                 source_anchor=packet.source_anchor,
-                adaptation_reason=_packet_reason(packet),
+                adaptation_reason=adaptation_reason,
                 retained_assets=assets,
                 script_evidence=unique_evidence,
+                evidence_spans=evidence_spans,
                 status=status,
             )
         )
@@ -215,6 +326,22 @@ def render_source_evidence_report(report: SourceEvidenceReport) -> str:
         if item.script_evidence:
             parts.append("- Script Evidence:")
             parts.extend(f"  - {line}" for line in item.script_evidence)
+        if item.evidence_spans:
+            parts.append("- Source Span Evidence:")
+            for span in item.evidence_spans:
+                source_ref = (
+                    f"source L{span.source_line_index}: {span.source_line}"
+                    if span.source_line_index and span.source_line
+                    else "source missing"
+                )
+                script_ref = (
+                    f"script L{span.script_line_index}: {span.script_line}"
+                    if span.script_line_index and span.script_line
+                    else "script missing"
+                )
+                parts.append(
+                    f"  - {span.status} · {span.asset} · {source_ref} -> {script_ref}"
+                )
     if report.missing_items:
         parts.extend(["", "## Missing Items"])
         parts.extend(f"- {item}" for item in report.missing_items)
diff --git a/tests/test_adaptation_quality.py b/tests/test_adaptation_quality.py
index 06bc0ee..8f998e3 100644
--- a/tests/test_adaptation_quality.py
+++ b/tests/test_adaptation_quality.py
@@ -3,6 +3,7 @@ from novel_drama_engine.adaptation_quality import (
     build_story_state_ledger,
     build_methodology_quality_report,
     merge_methodology_quality_into_report,
+    _hook_acknowledged,
 )
 from novel_drama_engine.models import (
     AdaptationIntensity,
@@ -224,6 +225,17 @@ def test_adaptation_quality_blocks_dropped_original_hook():
     assert report.source_fidelity.score < 100
 
 
+def test_hook_acknowledgement_requires_specific_event_overlap_not_only_shared_name():
+    assert not _hook_acknowledged(
+        "许念念举起提前准备好的解约协议",
+        "许念念低头喝水，镜头扫过桌面。",
+    )
+    assert _hook_acknowledged(
+        "许念念举起提前准备好的解约协议",
+        "许念念从包里抽出解约协议，举到镜头前。",
+    )
+
+
 def test_forbidden_reveal_allows_investigation_before_identity_result():
     report = build_adaptation_quality_report(
         source_text="林晚生日宴被羞辱，旧木盒出现。",
diff --git a/tests/test_drama_quality.py b/tests/test_drama_quality.py
index 9e4fcc4..43b096f 100644
--- a/tests/test_drama_quality.py
+++ b/tests/test_drama_quality.py
@@ -4,6 +4,7 @@ from novel_drama_engine.drama_quality import (
     merge_drama_quality_into_report,
 )
 from novel_drama_engine.models import (
+    DramaQualityReport,
     EpisodeScript,
     QualityReport,
     QualityScores,
@@ -49,31 +50,7 @@ def test_drama_quality_comparison_requires_pipeline_to_beat_baseline():
     assert any("direct LLM baseline" in issue for issue in report.blocking_issues)
 
 
-def test_merge_drama_quality_marks_usable_report_for_review_when_drama_fails():
-    weak_batch = ScriptBatch(
-        episodes=[
-            EpisodeScript(
-                episode=1,
-                title="弱戏",
-                hook_3s="她来了。",
-                main_emotion="平",
-                watch_reason="信息不足。",
-                scenes=[
-                    Scene(
-                        heading="1-1 日-内-屋内",
-                        characters=["甲", "乙"],
-                        lines=[
-                            SceneLine(kind="action", text="△甲站着。"),
-                            SceneLine(kind="dialogue", speaker="甲", text="你好。"),
-                            SceneLine(kind="dialogue", speaker="乙", text="嗯。"),
-                        ],
-                    )
-                ],
-                cliffhanger="她来了。",
-                state_update={},
-            )
-        ]
-    )
+def test_merge_drama_quality_keeps_usable_report_when_only_drama_score_is_low():
     quality_report = QualityReport(
         status=QualityStatus.USABLE,
         scores=QualityScores(
@@ -86,12 +63,14 @@ def test_merge_drama_quality_marks_usable_report_for_review_when_drama_fails():
         blocking_issues=[],
         rewrite_instruction="",
     )
-
-    drama_report = build_drama_quality_report(
-        script_batch=weak_batch,
-        quality_report=quality_report,
+    drama_report = DramaQualityReport(
+        overall_score=6,
+        blocking_issues=[],
+        advisory_warnings=["情绪递进偏弱"],
+        rewrite_instruction="加强情绪递进，但不阻断交付。",
     )
     merged = merge_drama_quality_into_report(quality_report, drama_report)
 
-    assert merged.status == QualityStatus.NEEDS_HUMAN_REVIEW
-    assert any("drama_quality" in issue for issue in merged.blocking_issues)
+    assert merged.status == QualityStatus.USABLE
+    assert merged.blocking_issues == []
+    assert "drama_quality advisory" in merged.rewrite_instruction
diff --git a/tests/test_pipeline.py b/tests/test_pipeline.py
index d930f0c..935f475 100644
--- a/tests/test_pipeline.py
+++ b/tests/test_pipeline.py
@@ -26,6 +26,7 @@ from novel_drama_engine.pipeline import (
     RepairBudget,
     RoundPipeline,
     build_run_manifest,
+    fallback_episode_repair_targets,
     normalize_repair_budget,
 )
 from novel_drama_engine.rounds import (
@@ -323,6 +324,7 @@ def test_pipeline_persists_artifacts(tmp_path, happy_round_outputs):
     assert result.script_novelty_report.overall_score >= 7
     assert result.source_evidence_report is not None
     assert result.source_evidence_report.coverage_score >= 0
+    assert any(item.evidence_spans for item in result.source_evidence_report.items)
     assert result.source_strength_profile is not None
     assert result.story_state_ledger is not None
     assert result.runtime_report is not None
@@ -429,6 +431,25 @@ def test_pipeline_resumes_from_cached_round_artifacts(tmp_path, happy_round_outp
     )
 
 
+def test_run_manifest_tracks_episode_repair_fallback_env(monkeypatch):
+    monkeypatch.setenv("NOVEL_DRAMA_EPISODE_REPAIR_FALLBACK", "first")
+    llm = StaticJsonLLM([])
+
+    manifest = build_run_manifest(
+        project_id="demo",
+        round_number=1,
+        source_text="林晚被赶出生日宴。",
+        target_episode_count=None,
+        episodes_per_round=5,
+        generation_variant=GenerationVariant.CURRENT_DENSITY,
+        repair_budget=RepairBudget.EPISODE,
+        llm=llm,
+        methodology_cards_path=None,
+    )
+
+    assert manifest["env"]["NOVEL_DRAMA_EPISODE_REPAIR_FALLBACK"] == "first"
+
+
 def test_pipeline_ignores_cached_round_without_matching_manifest(tmp_path, happy_round_outputs):
     source, context, bible, scripts, stale_quality, stale_next_context = happy_round_outputs
     fresh_outputs = demo_round_outputs()
@@ -473,6 +494,22 @@ def test_pipeline_reuses_prior_round_story_bible(tmp_path, happy_round_outputs):
     store = ProjectStore(tmp_path)
     store.write_round_artifact(1, "story_bible", prior_bible)
     llm = RecordingLLM(round_two_outputs)
+    prior_manifest = build_run_manifest(
+        project_id="demo",
+        round_number=1,
+        source_text="林晚被赶出生日宴。",
+        target_episode_count=None,
+        episodes_per_round=5,
+        generation_variant=GenerationVariant.CURRENT_DENSITY,
+        repair_budget=RepairBudget.EPISODE,
+        llm=llm,
+        methodology_cards_path=None,
+    )
+    store.write_text_artifact(
+        1,
+        "run_manifest.json",
+        json.dumps(prior_manifest, ensure_ascii=False, indent=2),
+    )
     pipeline = RoundPipeline(llm=llm, store=store)
 
     result = pipeline.run(
@@ -493,6 +530,38 @@ def test_pipeline_reuses_prior_round_story_bible(tmp_path, happy_round_outputs):
     )
 
 
+def test_pipeline_skips_prior_round_story_bible_without_compatible_manifest(
+    tmp_path,
+    happy_round_outputs,
+):
+    _, _, prior_bible, _, _, previous_context = happy_round_outputs
+    stale_bible = prior_bible.model_copy(update={"mainline": "STALE OLD BIBLE"})
+    round_two_outputs = demo_round_outputs(
+        round_number=2,
+        previous_context=previous_context,
+    )
+    store = ProjectStore(tmp_path)
+    store.write_round_artifact(1, "story_bible", stale_bible)
+    llm = RecordingLLM(round_two_outputs)
+    pipeline = RoundPipeline(llm=llm, store=store)
+
+    result = pipeline.run(
+        project_id="demo",
+        round_number=2,
+        source_text="林晚被赶出生日宴。",
+        previous_context=previous_context,
+    )
+
+    assert result.story_bible.mainline != "STALE OLD BIBLE"
+    assert "StoryBible" in [
+        call["response_model"].__name__ for call in llm.calls
+    ]
+    assert any(
+        stage.name == "story_bible" and stage.status == "succeeded"
+        for stage in result.runtime_report.stages
+    )
+
+
 def test_pipeline_drama_engine_variant_persists_episode_plan(tmp_path):
     outputs = demo_round_outputs(include_episode_plan=True)
     pipeline = RoundPipeline(llm=StaticJsonLLM(outputs), store=ProjectStore(tmp_path))
@@ -723,7 +792,9 @@ def test_pipeline_default_repair_targets_episode_without_batch_rewrite(
 def test_pipeline_pre_adaptation_gate_rewrites_source_intent_drift(
     tmp_path,
     happy_round_outputs,
+    monkeypatch,
 ):
+    monkeypatch.setenv("NOVEL_DRAMA_EPISODE_REPAIR_FALLBACK", "first")
     outputs = list(happy_round_outputs)
     source_analysis = outputs[0].model_copy(
         update={"candidate_hooks": [], "visual_moments": []}
@@ -937,7 +1008,7 @@ def test_pipeline_strong_source_cost_control_blocks_fallback_repair(tmp_path):
         if stage.status == "skipped"
     }
 
-    assert result.quality_report.status == QualityStatus.NEEDS_HUMAN_REVIEW
+    assert result.quality_report.status == QualityStatus.NEEDS_REWRITE
     assert result.runtime_report.repair_budget == RepairBudget.EPISODE
     assert len(script_calls) == 1
     assert episode_calls == []
@@ -953,6 +1024,12 @@ def test_pipeline_strong_source_cost_control_blocks_fallback_repair(tmp_path):
     assert not (tmp_path / "round_001" / "script_batch_episode_repair.json").exists()
 
 
+def test_episode_repair_fallback_defaults_to_no_speculative_repair(monkeypatch):
+    monkeypatch.delenv("NOVEL_DRAMA_EPISODE_REPAIR_FALLBACK", raising=False)
+
+    assert fallback_episode_repair_targets([1, 2, 3]) == set()
+
+
 def test_pipeline_strong_source_cost_control_repairs_named_episode_only(tmp_path):
     outputs = demo_round_outputs(include_sop_stack=True)
     source = outputs[0]
@@ -1033,7 +1110,12 @@ def test_pipeline_strong_source_cost_control_repairs_named_episode_only(tmp_path
     assert not (tmp_path / "round_001" / "script_batch_rewrite.json").exists()
 
 
-def test_pipeline_escalates_second_rewrite_to_human_review(tmp_path, happy_round_outputs):
+def test_pipeline_escalates_second_rewrite_to_human_review(
+    tmp_path,
+    happy_round_outputs,
+    monkeypatch,
+):
+    monkeypatch.setenv("NOVEL_DRAMA_EPISODE_REPAIR_FALLBACK", "first")
     outputs = list(happy_round_outputs)
     first_script = outputs[3]
     repaired_episode = first_script.episodes[0].model_copy(deep=True)
@@ -1157,6 +1239,7 @@ def test_pipeline_polishes_episode_repair_when_local_quality_still_fails(
     happy_round_outputs,
     monkeypatch,
 ):
+    monkeypatch.setenv("NOVEL_DRAMA_EPISODE_REPAIR_FALLBACK", "first")
     monkeypatch.setenv("NOVEL_DRAMA_BLOCKING_OPTIONAL_POLISH", "1")
     outputs = list(happy_round_outputs)
     first_script = outputs[3]
@@ -1231,7 +1314,9 @@ def test_pipeline_polishes_episode_repair_when_local_quality_still_fails(
 def test_pipeline_skips_optional_polish_by_default(
     tmp_path,
     happy_round_outputs,
+    monkeypatch,
 ):
+    monkeypatch.setenv("NOVEL_DRAMA_EPISODE_REPAIR_FALLBACK", "first")
     outputs = list(happy_round_outputs)
     first_script = outputs[3]
     bad_episode = first_script.episodes[0].model_copy(
@@ -1306,6 +1391,7 @@ def test_pipeline_keeps_previous_episode_when_optional_polish_fails(
     happy_round_outputs,
     monkeypatch,
 ):
+    monkeypatch.setenv("NOVEL_DRAMA_EPISODE_REPAIR_FALLBACK", "first")
     monkeypatch.setenv("NOVEL_DRAMA_BLOCKING_OPTIONAL_POLISH", "1")
     outputs = list(happy_round_outputs)
     first_script = outputs[3]
@@ -1384,6 +1470,7 @@ def test_pipeline_runs_hook_dialogue_polish_for_soft_tail_after_quality_polish(
     happy_round_outputs,
     monkeypatch,
 ):
+    monkeypatch.setenv("NOVEL_DRAMA_EPISODE_REPAIR_FALLBACK", "first")
     monkeypatch.setenv("NOVEL_DRAMA_BLOCKING_OPTIONAL_POLISH", "1")
     outputs = list(happy_round_outputs)
     first_script = outputs[3]
@@ -1448,6 +1535,7 @@ def test_pipeline_keeps_quality_polished_episode_when_hook_polish_fails(
     happy_round_outputs,
     monkeypatch,
 ):
+    monkeypatch.setenv("NOVEL_DRAMA_EPISODE_REPAIR_FALLBACK", "first")
     monkeypatch.setenv("NOVEL_DRAMA_BLOCKING_OPTIONAL_POLISH", "1")
     outputs = list(happy_round_outputs)
     first_script = outputs[3]
diff --git a/tests/test_prompt_script_quality_contract.py b/tests/test_prompt_script_quality_contract.py
index c6c183c..e001389 100644
--- a/tests/test_prompt_script_quality_contract.py
+++ b/tests/test_prompt_script_quality_contract.py
@@ -77,11 +77,16 @@ def test_script_and_quality_prompts_lock_user_visible_script_contract():
     assert "转身离开、我需要时间、明天再说" in hook_dialogue_prompt
     assert "cliffhanger 字段必须直接填写最后 4 行里已经演出来的钩子台词或动作" in hook_dialogue_prompt
     assert "action 行硬格式" in hook_dialogue_prompt
-    assert "逐集检查最后一场最后 2 行是否把 cliffhanger 演成动作、对白或道具特写" in quality_prompt
-    assert "cliffhanger 字段必须能在最后一场最后 4 行中找到相同台词或动作" in quality_prompt
-    assert "action 行硬格式" in quality_prompt
-    assert "镜头衔接硬验收" in quality_prompt
-    assert "最后两行硬模板" in quality_prompt
+    assert "本地确定性质检已经负责逐行硬指标" in quality_prompt
+    assert "不要凭摘要声称逐行检查了每条 action 或每句对白" in quality_prompt
+    assert "只基于 script_batch_digest 可见内容判断" in quality_prompt
+    assert "戏剧质量、跨集连续性、人物动机、原著保真和题材模板一致性" in quality_prompt
+    assert "cliffhanger 字段必须能在摘要中的 tail_lines 里找到可见承接" in quality_prompt
+    assert "action 行硬格式" not in quality_prompt
+    assert "镜头衔接硬验收" not in quality_prompt
+    assert "最后两行硬模板" not in quality_prompt
+    assert "必须检查 action 是否包含景别" not in quality_prompt
+    assert "对白是否超过 22 字" not in quality_prompt
     assert "题材模板错配必须拦截" in quality_prompt
     assert "真假千金/豪门宴会/总裁/亲子鉴定/大小姐模板" in quality_prompt
 
diff --git a/tests/test_source_evidence.py b/tests/test_source_evidence.py
index cfa67be..703be96 100644
--- a/tests/test_source_evidence.py
+++ b/tests/test_source_evidence.py
@@ -1,5 +1,12 @@
 from novel_drama_engine.demo import demo_round_outputs
-from novel_drama_engine.models import EpisodeSourcePacket, EpisodeSourcePackets
+from novel_drama_engine.models import (
+    EpisodeScript,
+    EpisodeSourcePacket,
+    EpisodeSourcePackets,
+    Scene,
+    SceneLine,
+    ScriptBatch,
+)
 from novel_drama_engine.source_evidence import (
     build_source_evidence_report,
     render_source_evidence_report,
@@ -60,3 +67,106 @@ def test_source_evidence_report_flags_missing_source_assets():
     assert report.items[0].script_evidence == []
     assert report.missing_items == ["EP01 缺少原文资产：亲哥哥救场"]
     assert "原文证据未落到正片" in report.rewrite_instruction
+
+
+def test_source_evidence_requires_specific_asset_not_only_character_name():
+    packet = EpisodeSourcePacket(
+        episode=1,
+        source_anchor="许念念早已把解约协议放进包里。",
+        source_excerpt="许念念走进办公室，举起提前准备好的解约协议。",
+        c1_must_keep_assets=["许念念举起提前准备好的解约协议"],
+    )
+    script = EpisodeScript(
+        episode=1,
+        title="办公室对峙",
+        hook_3s="门被推开。",
+        main_emotion="压迫",
+        watch_reason="系统内部看点",
+        scenes=[
+            Scene(
+                heading="1-1 日-内-办公室",
+                characters=["许念念"],
+                lines=[
+                    SceneLine(
+                        kind="action",
+                        text="△中景推近许念念低头喝水，桌面没有任何文件。",
+                    )
+                ],
+            )
+        ],
+        cliffhanger="门外传来脚步声。",
+        state_update={},
+    )
+
+    report = build_source_evidence_report(
+        ScriptBatch(episodes=[script]),
+        episode_source_packets=EpisodeSourcePackets(packets=[packet]),
+    )
+
+    assert report.coverage_score == 0
+    assert report.items[0].status == "missing"
+    assert report.items[0].script_evidence == []
+
+    script.scenes[0].lines[0].text = "△中景推近许念念从包里抽出解约协议，举到镜头前。"
+    matched_report = build_source_evidence_report(
+        ScriptBatch(episodes=[script]),
+        episode_source_packets=EpisodeSourcePackets(packets=[packet]),
+    )
+
+    assert matched_report.coverage_score == 100
+    assert matched_report.items[0].status == "matched"
+
+
+def test_source_evidence_records_source_span_script_line_and_reason_per_asset():
+    packet = EpisodeSourcePacket(
+        episode=1,
+        source_anchor="办公室解约",
+        source_excerpt=(
+            "许念念早已把解约协议放进包里。\n"
+            "她走进办公室，举起提前准备好的解约协议。"
+        ),
+        c1_must_keep_assets=["许念念举起提前准备好的解约协议"],
+    )
+    script = EpisodeScript(
+        episode=1,
+        title="办公室对峙",
+        hook_3s="门被推开。",
+        main_emotion="压迫",
+        watch_reason="系统内部看点",
+        scenes=[
+            Scene(
+                heading="1-1 日-内-办公室",
+                characters=["许念念"],
+                lines=[
+                    SceneLine(kind="dialogue", speaker="路淮北", emotion="冷", text="你想清楚。"),
+                    SceneLine(
+                        kind="action",
+                        text="△中景推近许念念从包里抽出解约协议，举到镜头前。",
+                    ),
+                ],
+            )
+        ],
+        cliffhanger="她把笔压在纸上。",
+        state_update={},
+    )
+
+    report = build_source_evidence_report(
+        ScriptBatch(episodes=[script]),
+        episode_source_packets=EpisodeSourcePackets(packets=[packet]),
+    )
+
+    span = report.items[0].evidence_spans[0]
+    assert span.asset == "许念念举起提前准备好的解约协议"
+    assert span.status == "matched"
+    assert span.source_anchor == "办公室解约"
+    assert span.source_excerpt == packet.source_excerpt
+    assert span.source_line == "她走进办公室，举起提前准备好的解约协议。"
+    assert span.source_line_index == 2
+    assert span.script_line == "△中景推近许念念从包里抽出解约协议，举到镜头前。"
+    assert span.script_line_index == 7
+    assert span.adaptation_reason.startswith("保留原文必留资产")
+
+    markdown = render_source_evidence_report(report)
+    assert "Source Span Evidence" in markdown
+    assert "source L2" in markdown
+    assert "script L7" in markdown

```

## Untracked Files Included

### drizzle/migrations/0008_material_silvermane.sql

```
CREATE UNIQUE INDEX `jobs_active_round_generation_unique` ON `jobs` (`round_id`) WHERE "jobs"."kind" = 'round_generation' and "jobs"."round_id" is not null and "jobs"."status" in ('queued', 'running');
```
### drizzle/migrations/meta/0008_snapshot.json

```
{
  "version": "6",
  "dialect": "sqlite",
  "id": "e3cfd433-3185-4dfa-a65b-a4241cdde5c2",
  "prevId": "e9375dfd-0e78-41b1-9700-f4d9b0b4bfc8",
  "tables": {
    "api_keys": {
      "name": "api_keys",
      "columns": {
        "id": {
          "name": "id",
          "type": "text",
          "primaryKey": true,
          "notNull": true,
          "autoincrement": false
        },
        "tenant_id": {
          "name": "tenant_id",
          "type": "text",
          "primaryKey": false,
          "notNull": true,
          "autoincrement": false
        },
        "created_by_user_id": {
          "name": "created_by_user_id",
          "type": "text",
          "primaryKey": false,
          "notNull": false,
          "autoincrement": false
        },
        "name": {
          "name": "name",
          "type": "text",
          "primaryKey": false,
          "notNull": true,
          "autoincrement": false
        },
        "key_prefix": {
          "name": "key_prefix",
          "type": "text",
          "primaryKey": false,
          "notNull": true,
          "autoincrement": false
        },
        "key_hash": {
          "name": "key_hash",
          "type": "text",
          "primaryKey": false,
          "notNull": true,
          "autoincrement": false
        },
        "last_used_at": {
          "name": "last_used_at",
          "type": "integer",
          "primaryKey": false,
          "notNull": false,
          "autoincrement": false
        },
        "revoked_at": {
          "name": "revoked_at",
          "type": "integer",
          "primaryKey": false,
          "notNull": false,
          "autoincrement": false
        },
        "created_at": {
          "name": "created_at",
          "type": "integer",
          "primaryKey": false,
          "notNull": true,
          "autoincrement": false
        },
        "updated_at": {
          "name": "updated_at",
          "type": "integer",
          "primaryKey": false,
          "notNull": true,
          "autoincrement": false
        }
      },
      "indexes": {},
      "foreignKeys": {
        "api_keys_tenant_id_tenants_id_fk": {
          "name": "api_keys_tenant_id_tenants_id_fk",
          "tableFrom": "api_keys",
          "tableTo": "tenants",
          "columnsFrom": [
            "tenant_id"
          ],
          "columnsTo": [
            "id"
          ],
          "onDelete": "cascade",
          "onUpdate": "no action"
        },
        "api_keys_created_by_user_id_users_id_fk": {
          "name": "api_keys_created_by_user_id_users_id_fk",
          "tableFrom": "api_keys",
          "tableTo": "users",
          "columnsFrom": [
            "created_by_user_id"
          ],
          "columnsTo": [
            "id"
          ],
          "onDelete": "set null",
          "onUpdate": "no action"
        }
      },
      "compositePrimaryKeys": {},
      "uniqueConstraints": {},
      "checkConstraints": {}
    },
    "bibles": {
      "name": "bibles",
      "columns": {
        "id": {
          "name": "id",
          "type": "text",
          "primaryKey": true,
          "notNull": true,
          "autoincrement": false
        },
        "project_id": {
          "name": "project_id",
          "type": "text",
          "primaryKey": false,
          "notNull": true,
          "autoincrement": false
        },
        "channel": {
          "name": "channel",
          "type": "text",
          "primaryKey": false,
          "notNull": false,
          "autoincrement": false
        },
        "six_assets_json": {
          "name": "six_assets_json",
          "type": "text",
          "primaryKey": false,
          "notNull": false,
          "autoincrement": false
        },
        "characters_md": {
          "name": "characters_md",
          "type": "text",
          "primaryKey": false,
          "notNull": false,
          "autoincrement": false
        },
        "episode_plan_md": {
          "name": "episode_plan_md",
          "type": "text",
          "primaryKey": false,
          "notNull": false,
          "autoincrement": false
        },
        "prev_round_summary_json": {
          "name": "prev_round_summary_json",
          "type": "text",
          "primaryKey": false,
          "notNull": false,
          "autoincrement": false
        },
        "name_mapping_json": {
          "name": "name_mapping_json",
          "type": "text",
          "primaryKey": false,
          "notNull": false,
          "autoincrement": false
        },
        "culture_mapping_json": {
          "name": "culture_mapping_json",
          "type": "text",
          "primaryKey": false,
          "notNull": false,
          "autoincrement": false
        },
        "updated_at": {
          "name": "updated_at",
          "type": "integer",
          "primaryKey": false,
          "notNull": true,
          "autoincrement": false
        }
      },
      "indexes": {},
      "foreignKeys": {
        "bibles_project_id_projects_id_fk": {
          "name": "bibles_project_id_projects_id_fk",
          "tableFrom": "bibles",
          "tableTo": "projects",
          "columnsFrom": [
            "project_id"
          ],
          "columnsTo": [
            "id"
          ],
          "onDelete": "cascade",
          "onUpdate": "no action"
        }
      },
      "compositePrimaryKeys": {},
      "uniqueConstraints": {},
      "checkConstraints": {}
    },
    "billing_plans": {
      "name": "billing_plans",
      "columns": {
        "id": {
          "name": "id",
          "type": "text",
          "primaryKey": true,
          "notNull": true,
          "autoincrement": false
        },
        "slug": {
          "name": "slug",
          "type": "text",
          "primaryKey": false,
          "notNull": true,
          "autoincrement": false
        },
        "name": {
          "name": "name",
          "type": "text",
          "primaryKey": false,
          "notNull": true,
          "autoincrement": false
        },
        "monthly_price_cents": {
          "name": "monthly_price_cents",
          "type": "integer",
          "primaryKey": false,
          "notNull": true,
          "autoincrement": false,
          "default": 0
        },
        "currency": {
          "name": "currency",
          "type": "text",
          "primaryKey": false,
          "notNull": true,
          "autoincrement": false,
          "default": "'USD'"
        },
        "project_limit": {
          "name": "project_limit",
          "type": "integer",
          "primaryKey": false,
          "notNull": true,
          "autoincrement": false,
          "default": 25
        },
        "monthly_job_limit": {
          "name": "monthly_job_limit",
          "type": "integer",
          "primaryKey": false,
          "notNull": true,
          "autoincrement": false,
          "default": 200
        },
        "included_billable_units": {
          "name": "included_billable_units",
          "type": "integer",
          "primaryKey": false,
          "notNull": true,
          "autoincrement": false,
          "default": 100
        },
        "overage_unit_price_cents": {
          "name": "overage_unit_price_cents",
          "type": "integer",
          "primaryKey": false,
          "notNull": true,
          "autoincrement": false,
          "default": 0
        },
        "features_json": {
          "name": "features_json",
          "type": "text",
          "primaryKey": false,
          "notNull": false,
          "autoincrement": false
        },
        "created_at": {
          "name": "created_at",
          "type": "integer",
          "primaryKey": false,
          "notNull": true,
          "autoincrement": false
        },
        "updated_at": {
          "name": "updated_at",
          "type": "integer",
          "primaryKey": false,
          "notNull": true,
          "autoincrement": false
        }
      },
      "indexes": {},
      "foreignKeys": {},
      "compositePrimaryKeys": {},
      "uniqueConstraints": {},
      "checkConstraints": {}
    },
    "credit_ledger": {
      "name": "credit_ledger",
      "columns": {
        "id": {
          "name": "id",
          "type": "text",
          "primaryKey": true,
          "notNull": true,
          "autoincrement": false
        },
        "tenant_id": {
          "name": "tenant_id",
          "type": "text",
          "primaryKey": false,
          "notNull": true,
          "autoincrement": false
        },
        "user_id": {
          "name": "user_id",
          "type": "text",
          "primaryKey": false,
          "notNull": false,
          "autoincrement": false
        },
        "source_type": {
          "name": "source_type",
          "type": "text",
          "primaryKey": false,
          "notNull": true,
          "autoincrement": false
        },
        "credits_delta": {
          "name": "credits_delta",
          "type": "integer",
          "primaryKey": false,
          "notNull": true,
          "autoincrement": false
        },
        "balance_after": {
          "name": "balance_after",
          "type": "integer",
          "primaryKey": false,
          "notNull": true,
          "autoincrement": false
        },
        "usage_event_id": {
          "name": "usage_event_id",
          "type": "text",
          "primaryKey": false,
          "notNull": false,
          "autoincrement": false
        },
        "checkout_session_id": {
          "name": "checkout_session_id",
          "type": "text",
          "primaryKey": false,
          "notNull": false,
          "autoincrement": false
        },
        "invoice_id": {
          "name": "invoice_id",
          "type": "text",
          "primaryKey": false,
          "notNull": false,
          "autoincrement": false
        },
        "reference_key": {
          "name": "reference_key",
          "type": "text",
          "primaryKey": false,
          "notNull": false,
          "autoincrement": false
        },
        "metadata_json": {
          "name": "metadata_json",
          "type": "text",
          "primaryKey": false,
          "notNull": false,
          "autoincrement": false
        },
        "created_at": {
          "name": "created_at",
          "type": "integer",
          "primaryKey": false,
          "notNull": true,
          "autoincrement": false
        }
      },
      "indexes": {},
      "foreignKeys": {
        "credit_ledger_tenant_id_tenants_id_fk": {
          "name": "credit_ledger_tenant_id_tenants_id_fk",
          "tableFrom": "credit_ledger",
          "tableTo": "tenants",
          "columnsFrom": [
            "tenant_id"
          ],
          "columnsTo": [
            "id"
          ],
          "onDelete": "cascade",
          "onUpdate": "no action"
        },
        "credit_ledger_user_id_users_id_fk": {
          "name": "credit_ledger_user_id_users_id_fk",
          "tableFrom": "credit_ledger",
          "tableTo": "users",
          "columnsFrom": [
            "user_id"
          ],
          "columnsTo": [
            "id"
          ],
          "onDelete": "set null",
          "onUpdate": "no action"
        },
        "credit_ledger_usage_event_id_usage_events_id_fk": {
          "name": "credit_ledger_usage_event_id_usage_events_id_fk",
          "tableFrom": "credit_ledger",
          "tableTo": "usage_events",
          "columnsFrom": [
            "usage_event_id"
          ],
          "columnsTo": [
            "id"
          ],
          "onDelete": "set null",
          "onUpdate": "no action"
        },
        "credit_ledger_checkout_session_id_payment_checkout_sessions_id_fk": {
          "name": "credit_ledger_checkout_session_id_payment_checkout_sessions_id_fk",
          "tableFrom": "credit_ledger",
          "tableTo": "payment_checkout_sessions",
          "columnsFrom": [
            "checkout_session_id"
          ],
          "columnsTo": [
            "id"
          ],
          "onDelete": "set null",
          "onUpdate": "no action"
        },
        "credit_ledger_invoice_id_payment_invoices_id_fk": {
          "name": "credit_ledger_invoice_id_payment_invoices_id_fk",
          "tableFrom": "credit_ledger",
          "tableTo": "payment_invoices",
          "columnsFrom": [
            "invoice_id"
          ],
          "columnsTo": [
            "id"
          ],
          "onDelete": "set null",
          "onUpdate": "no action"
        }
      },
      "compositePrimaryKeys": {},
      "uniqueConstraints": {},
      "checkConstraints": {}
    },
    "credit_packages": {
      "name": "credit_packages",
      "columns": {
        "id": {
          "name": "id",
          "type": "text",
          "primaryKey": true,
          "notNull": true,
          "autoincrement": false
        },
        "slug": {
          "name": "slug",
          "type": "text",
          "primaryKey": false,
          "notNull": true,
          "autoincrement": false
        },
        "name": {
          "name": "name",
          "type": "text",
          "primaryKey": false,
          "notNull": true,
          "autoincrement": false
        },
        "credits": {
          "name": "credits",
          "type": "integer",
          "primaryKey": false,
          "notNull": true,
          "autoincrement": false
        },
        "price_cents": {
          "name": "price_cents",
          "type": "integer",
          "primaryKey": false,
          "notNull": true,
          "autoincrement": false
        },
        "currency": {
          "name": "currency",
          "type": "text",
          "primaryKey": false,
          "notNull": true,
          "autoincrement": false,
          "default": "'USD'"
        },
        "active": {
          "name": "active",
          "type": "integer",
          "primaryKey": false,
          "notNull": true,
          "autoincrement": false,
          "default": true
        },
        "sort_order": {
          "name": "sort_order",
          "type": "integer",
          "primaryKey": false,
          "notNull": true,
          "autoincrement": false,
          "default": 0
        },
        "metadata_json": {
          "name": "metadata_json",
          "type": "text",
          "primaryKey": false,
          "notNull": false,
          "autoincrement": false
        },
        "created_at": {
          "name": "created_at",
          "type": "integer",
          "primaryKey": false,
          "notNull": true,
          "autoincrement": false
        },
        "updated_at": {
          "name": "updated_at",
          "type": "integer",
          "primaryKey": false,
          "notNull": true,
          "autoincrement": false
        }
      },
      "indexes": {},
      "foreignKeys": {},
      "compositePrimaryKeys": {},
      "uniqueConstraints": {},
      "checkConstraints": {}
    },
    "episodes": {
      "name": "episodes",
      "columns": {
        "id": {
          "name": "id",
          "type": "text",
          "primaryKey": true,
          "notNull": true,
          "autoincrement": false
        },
        "project_id": {
          "name": "project_id",
          "type": "text",
          "primaryKey": false,
          "notNull": true,
          "autoincrement": false
        },
        "round_id": {
          "name": "round_id",
          "type": "text",
          "primaryKey": false,
          "notNull": true,
          "autoincrement": false
        },
        "ep_num": {
          "name": "ep_num",
          "type": "integer",
          "primaryKey": false,
          "notNull": true,
          "autoincrement": false
        },
        "draft_md": {
          "name": "draft_md",
          "type": "text",
          "primaryKey": false,
          "notNull": false,
          "autoincrement": false
        },
        "script_txt": {
          "name": "script_txt",
          "type": "text",
          "primaryKey": false,
          "notNull": false,
          "autoincrement": false
        },
        "score": {
          "name": "score",
          "type": "real",
          "primaryKey": false,
          "notNull": false,
          "autoincrement": false
        },
        "review_json": {
          "name": "review_json",
          "type": "text",
          "primaryKey": false,
          "notNull": false,
          "autoincrement": false
        },
        "ep_summary_json": {
          "name": "ep_summary_json",
          "type": "text",
          "primaryKey": false,
          "notNull": false,
          "autoincrement": false
        },
        "retry_count": {
          "name": "retry_count",
          "type": "integer",
          "primaryKey": false,
          "notNull": true,
          "autoincrement": false,
          "default": 0
        },
        "status": {
          "name": "status",
          "type": "text",
          "primaryKey": false,
          "notNull": true,
          "autoincrement": false,
          "default": "'pending'"
        },
        "updated_at": {
          "name": "updated_at",
          "type": "integer",
          "primaryKey": false,
          "notNull": true,
          "autoincrement": false
        }
      },
      "indexes": {},
      "foreignKeys": {
        "episodes_project_id_projects_id_fk": {
          "name": "episodes_project_id_projects_id_fk",
          "tableFrom": "episodes",
          "tableTo": "projects",
          "columnsFrom": [
            "project_id"
          ],
          "columnsTo": [
            "id"
          ],
          "onDelete": "cascade",
          "onUpdate": "no action"
        },
        "episodes_round_id_rounds_id_fk": {
          "name": "episodes_round_id_rounds_id_fk",
          "tableFrom": "episodes",
          "tableTo": "rounds",
          "columnsFrom": [
            "round_id"
          ],
          "columnsTo": [
            "id"
          ],
          "onDelete": "cascade",
          "onUpdate": "no action"
        }
      },
      "compositePrimaryKeys": {},
      "uniqueConstraints": {},
      "checkConstraints": {}
    },
    "jobs": {
      "name": "jobs",
      "columns": {
        "id": {
          "name": "id",
          "type": "text",
          "primaryKey": true,
          "notNull": true,
          "autoincrement": false
        },
        "kind": {
          "name": "kind",
          "type": "text",
          "primaryKey": false,
          "notNull": true,
          "autoincrement": false
        },
        "status": {
          "name": "status",
          "type": "text",
          "primaryKey": false,
          "notNull": true,
          "autoincrement": false,
          "default": "'queued'"
        },
        "project_id": {
          "name": "project_id",
          "type": "text",
          "primaryKey": false,
          "notNull": false,
          "autoincrement": false
        },
        "tenant_id": {
          "name": "tenant_id",
          "type": "text",
          "primaryKey": false,
          "notNull": false,
          "autoincrement": false
        },
        "round_id": {
          "name": "round_id",
          "type": "text",
          "primaryKey": false,
          "notNull": false,
          "autoincrement": false
        },
        "title": {
          "name": "title",
          "type": "text",
          "primaryKey": false,
          "notNull": true,
          "autoincrement": false
        },
        "progress": {
          "name": "progress",
          "type": "integer",
          "primaryKey": false,
          "notNull": true,
          "autoincrement": false,
          "default": 0
        },
        "message": {
          "name": "message",
          "type": "text",
          "primaryKey": false,
          "notNull": false,
          "autoincrement": false
        },
        "error_text": {
          "name": "error_text",
          "type": "text",
          "primaryKey": false,
          "notNull": false
... [truncated]

```
### tests/p0_platform.test.ts

```
import { execFileSync } from "node:child_process";
import { mkdtempSync, readFileSync, rmSync } from "node:fs";
import os from "node:os";
import path from "node:path";
import test from "node:test";
import assert from "node:assert/strict";

const repoRoot = path.resolve(import.meta.dirname, "..");
const tempRoot = mkdtempSync(path.join(os.tmpdir(), "novel-drama-p0-"));
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
    process.env.NODE_ENV = "production";
    process.env.NOVEL_DRAMA_DEPLOYMENT_TARGET = "production";

    const { resolveEngineMode, realEngineConfigProblem } = await import(
      "../src/lib/engine-runner"
    );

    assert.deepEqual(resolveEngineMode(), { mode: "real", explicitMock: false });
    assert.match(realEngineConfigProblem() ?? "", /OPENAI_API_KEY/);
  } finally {
    process.env.NOVEL_DRAMA_WEB_MOCK = previous.webMock;
    process.env.NODE_ENV = previous.nodeEnv;
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
    process.env.NODE_ENV = "development";
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
    process.env.NODE_ENV = previous.nodeEnv;
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

test("stale round generation failure does not mark the whole project failed", async () => {
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
    maxAttempts: 3,
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
  assert.equal(project?.status, "running");
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
    maxAttempts: 3,
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

```
