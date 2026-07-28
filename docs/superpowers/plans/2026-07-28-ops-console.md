# Internal Ops Console Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an authenticated internal operations console with durable worker heartbeat, job history, safe job controls, and compact diagnostic APIs.

**Architecture:** SQLite remains the source of truth. A durable worker instance writes an independent heartbeat and job attribution, while every meaningful job transition appends a compact event. Server routes enforce the existing tenant/owner platform context; the client page polls compact overview/list endpoints and opens one authorized detail at a time.

**Tech Stack:** Next.js 16 App Router, React 19, TypeScript, Drizzle ORM, better-sqlite3, Lucide icons, Node test runner.

## Global Constraints

- This is an internal single-tenant operations console, not a general SaaS administration system.
- Reuse the signed platform context; do not add a second identity or role system.
- Do not store full novels, prompts, API keys, or raw provider responses in `job_events`.
- Compact list APIs must not return `payloadJson` or `resultJson`.
- Only queued jobs can be cancelled; running processes must never be force-killed in this phase.
- Worker heartbeat is stale after 30 seconds.
- Maintain `.superpowers/sdd/code-map.md` as files are added.

---

### Task 1: Durable Worker And Job Event Model

**Files:**
- Modify: `src/db/schema.ts`
- Create: `drizzle/migrations/0012_ops_observability.sql`
- Modify: `drizzle/migrations/meta/_journal.json`
- Create: `src/lib/ops-observability.ts`
- Modify: `src/lib/jobs.ts`
- Modify: `src/lib/job-worker.ts`
- Modify: `src/scripts/job-worker.ts`
- Test: `tests/ops_console.test.ts`

**Interfaces:**
- Produces: `registerWorkerInstance()`, `heartbeatWorkerInstance()`, `stopWorkerInstance()`, `appendJobEvent()`, `listWorkerViews()`.
- Extends: `claimNextQueuedJob({ kind, workerId })` and `runQueuedJobs({ workerId, ... })`.

- [ ] **Step 1: Write failing persistence tests**

Create tests that register a worker, heartbeat it, claim a queued job with its ID, and assert `worker_instances`, `jobs.worker_id`, and `job_events` are persisted. Add a 31-second-old heartbeat case that renders offline.

- [ ] **Step 2: Verify the tests fail**

Run: `node --import tsx --test tests/ops_console.test.ts`

Expected: FAIL because the schema tables and observability exports do not exist.

- [ ] **Step 3: Implement the schema and observability helpers**

Use these stable shapes:

```ts
type WorkerView = {
  id: string;
  status: "online" | "offline";
  currentJobId: string | null;
  startedAt: string;
  heartbeatAt: string;
  hostname: string;
  pid: number;
  version: string;
};

type JobEventType =
  | "created" | "claimed" | "progress" | "retried"
  | "succeeded" | "failed" | "cancelled" | "recovered";
```

Append events from job creation, claim, retry, success, failure, stale recovery, and cancellation. Pass a worker ID from the durable CLI worker into claim operations and update its current job before/after execution.

- [ ] **Step 4: Run focused tests**

Run: `node --import tsx --test tests/ops_console.test.ts tests/p0_platform.test.ts`

Expected: PASS with no regressions in existing job recovery behavior.

- [ ] **Step 5: Commit**

```bash
git add src/db/schema.ts drizzle/migrations src/lib/ops-observability.ts src/lib/jobs.ts src/lib/job-worker.ts src/scripts/job-worker.ts tests/ops_console.test.ts
git commit -m "feat: persist worker and job observability"
```

### Task 2: Authorized Operations APIs

**Files:**
- Create: `src/lib/ops-console.ts`
- Create: `src/app/api/ops/overview/route.ts`
- Create: `src/app/api/ops/jobs/route.ts`
- Create: `src/app/api/ops/jobs/[id]/route.ts`
- Create: `src/app/api/ops/jobs/[id]/retry/route.ts`
- Create: `src/app/api/ops/jobs/[id]/cancel/route.ts`
- Modify: `src/app/api/jobs/route.ts`
- Test: `tests/ops_console.test.ts`

**Interfaces:**
- Produces: `getOpsOverview(context)`, `listOpsJobs(context, filters)`, `getOpsJobDetail(context, jobId)`, `cancelQueuedJob(context, jobId)`.
- Consumes: worker/job event helpers from Task 1 and existing `requeueRetryableJob()`.

- [ ] **Step 1: Write failing API isolation and redaction tests**

Cover overview counts, worker freshness, owner filtering, job search, detail event ordering, retry, queued cancellation, and running-cancellation HTTP 409. Assert list responses omit `payloadJson` and `resultJson` while a detail returns only parsed compact diagnostics.

- [ ] **Step 2: Verify the tests fail**

Run: `node --import tsx --test tests/ops_console.test.ts`

Expected: FAIL with missing `/api/ops` modules.

- [ ] **Step 3: Implement server helpers and routes**

Use `resolvePlatformContext(req)`, `findTenantProject()`, and owner-scoped project IDs for every query. Return list rows with:

```ts
type OpsJobListItem = {
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
  createdAt: string;
  startedAt: string | null;
  updatedAt: string;
  finishedAt: string | null;
};
```

Cancel only `queued` rows and append a `cancelled` event. Reuse existing retry state restoration for failed or stale jobs.

- [ ] **Step 4: Run focused API tests**

Run: `node --import tsx --test tests/ops_console.test.ts tests/p0_platform.test.ts`

Expected: PASS, including legacy retry and tenant isolation tests.

- [ ] **Step 5: Commit**

```bash
git add src/lib/ops-console.ts src/app/api/ops src/app/api/jobs/route.ts tests/ops_console.test.ts
git commit -m "feat: expose protected operations APIs"
```

### Task 3: Operations Console Interface

**Files:**
- Create: `src/app/ops/page.tsx`
- Create: `src/app/ops/OpsConsoleClient.tsx`
- Modify: `src/components/app-shell.tsx`
- Modify: `src/app/globals.css`
- Test: `tests/ops_console_ui.test.ts`

**Interfaces:**
- Consumes: `GET /api/ops/overview`, `GET /api/ops/jobs`, detail, retry, and cancel routes.
- Produces: `/ops` page with five-second visible-page polling and stable filter/detail state.

- [ ] **Step 1: Write failing UI contract tests**

Assert navigation includes `/ops`; the page renders Worker, queue, failure, and readiness cards; filters include status/kind/query; job rows provide copy/detail/retry/cancel controls; polling checks `document.visibilityState` and uses a five-second interval.

- [ ] **Step 2: Verify the tests fail**

Run: `node --import tsx --test tests/ops_console_ui.test.ts`

Expected: FAIL because the page and navigation do not exist.

- [ ] **Step 3: Implement the compact operations UI**

Use existing `Card`, `Badge`, `Button`, `Dialog`, and `Input` components. Keep the layout full-width and dense: four summary cells, one filter row, one horizontally scrollable task table, and one focused detail dialog. Use Lucide icons for refresh, copy, search, retry, cancel, and activity.

- [ ] **Step 4: Run UI and type tests**

Run: `node --import tsx --test tests/ops_console_ui.test.ts && npm run typecheck`

Expected: PASS with no text overflow or missing accessible button labels.

- [ ] **Step 5: Commit**

```bash
git add src/app/ops src/components/app-shell.tsx src/app/globals.css tests/ops_console_ui.test.ts
git commit -m "feat: add internal operations console"
```

### Task 4: Deployment And End-To-End Verification

**Files:**
- Modify: `scripts/start-zeabur.sh`
- Modify: `deploy/zeabur.env.example`
- Modify: `docs/ZEABUR_DEPLOYMENT.md`
- Modify: `.superpowers/sdd/code-map.md`
- Test: `tests/zeabur_deployment.test.ts`

**Interfaces:**
- Consumes: durable worker CLI behavior and `/ops` health surfaces.
- Produces: documented heartbeat interval/version configuration and deploy verification steps.

- [ ] **Step 1: Write failing deployment assertions**

Assert the Zeabur entrypoint supplies `NOVEL_DRAMA_WORKER_VERSION`, heartbeat interval configuration, and graceful worker shutdown; assert the deployment runbook includes `/ops` verification.

- [ ] **Step 2: Verify the tests fail**

Run: `node --import tsx --test tests/zeabur_deployment.test.ts`

Expected: FAIL on missing worker observability deployment contract.

- [ ] **Step 3: Update deployment and code map**

Document `NOVEL_DRAMA_WORKER_HEARTBEAT_MS=5000`, `NOVEL_DRAMA_WORKER_STALE_MS=30000`, the `/ops` smoke test, and the single-worker capacity boundary. Keep secrets empty in the env example.

- [ ] **Step 4: Run complete verification**

Run:

```bash
npm run check
npm audit --omit=dev
docker build -t novel-to-drama:zeabur-ops-test .
```

Then launch the image with a named `/data` volume and verify `/api/health`, authorized `/ops`, worker heartbeat freshness, one queued cancellation, one retry, and persistence after container replacement.

Expected: all tests/builds pass; production audit has zero vulnerabilities; persisted worker/job events survive replacement.

- [ ] **Step 5: Commit**

```bash
git add scripts/start-zeabur.sh deploy/zeabur.env.example docs/ZEABUR_DEPLOYMENT.md .superpowers/sdd/code-map.md tests/zeabur_deployment.test.ts
git commit -m "docs: finish ops console deployment contract"
```
