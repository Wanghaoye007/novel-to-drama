# Internal Ops Console Design

## Goal

Provide an internal operations surface that answers four questions without opening Zeabur logs:

1. Is the durable worker alive?
2. Which jobs are queued, running, failed, or completed?
3. Why did a job fail, and what happened before the failure?
4. Can an operator safely retry or cancel the job?

This is an internal single-tenant operations console, not a general SaaS administration system.

## Scope

### Included

- `/ops` overview with worker, queue, failure, and backup/readiness cards.
- Searchable and filterable job table with copyable job IDs.
- Job detail with a durable event timeline and redacted operational metadata.
- Retry failed or stale jobs through the existing retry contract.
- Cancel queued jobs. Running processes are never force-killed in this phase.
- Worker registration, independent heartbeat, current job, process start time, and build version.
- Tenant and owner isolation through the existing signed platform session.
- Compact list responses that do not include `payloadJson` or `resultJson`.

### Excluded

- New admin roles, organization management, billing administration, or public user controls.
- Streaming or storing full container logs in SQLite.
- Force-killing a running Python/LLM process.
- Multiple concurrent workers or cross-service queue coordination.

## Data Model

### `worker_instances`

- `id`: stable process instance ID.
- `status`: `online` or `offline`.
- `started_at`, `heartbeat_at`, `stopped_at`.
- `current_job_id`: nullable job being executed.
- `hostname`, `pid`, `version`: compact diagnostics.

A worker is shown as offline when its heartbeat is older than 30 seconds, even if the stored status is `online`.

### `job_events`

- `id`, `job_id`, `event_type`, `message`, `metadata_json`, `created_at`.
- Events are appended for creation, claim, progress milestones, retry, success, failure, cancellation, and stale recovery.
- Event metadata must remain compact and must not store full novel text, prompts, API keys, or raw provider responses.

### `jobs`

- Add nullable `worker_id` for attribution.
- Add `cancelled` to status. Cancellation is permitted only while queued.

## Runtime Flow

1. The durable worker registers an instance before queue recovery.
2. A timer updates heartbeat independently from long-running job execution.
3. Claiming a job records `worker_id`, sets `current_job_id`, and appends a claim event.
4. Job state helpers append compact events alongside state transitions.
5. Completion clears the worker's current job.
6. SIGTERM/SIGINT marks the instance offline before exit when possible. Stale heartbeat remains the crash fallback.

## API

- `GET /api/ops/overview`: compact counts, readiness, workers, recent failures.
- `GET /api/ops/jobs`: filters by status, kind, query, and bounded limit; no payload/result blobs.
- `GET /api/ops/jobs/[id]`: authorized detail, event timeline, compact payload/result summaries.
- `POST /api/ops/jobs/[id]/retry`: reuse current retry behavior.
- `POST /api/ops/jobs/[id]/cancel`: cancel queued jobs only.

All routes resolve the signed platform context and enforce tenant plus project-owner isolation. Global unscoped database access is not exposed.

## Interface

The page follows the existing restrained Reela-style operational UI:

- Compact status cards, not decorative dashboard cards.
- One dense task table optimized for scanning.
- Filters above the table; job detail opens as a focused dialog.
- Pink is reserved for primary actions and active state. Success, warning, and error retain semantic colors.
- Mobile stacks cards and converts the table to stable-width horizontal scrolling.

Automatic refresh runs every five seconds while the page is visible. It updates data without moving selected filters or closing the detail dialog.

## Error Handling

- A missing worker heartbeat is shown as offline; it does not rewrite job history.
- Failed heartbeat writes are logged and retried on the next interval.
- Retry uses the existing idempotent job ID and rejects non-retryable states.
- Cancel rejects running and terminal jobs with a clear conflict response.
- API errors return compact operator-safe messages; raw errors remain in the authorized detail response only.

## Verification

- Database migration and uniqueness tests.
- Worker heartbeat freshness and current-job attribution tests.
- Event append tests for create, claim, retry, fail, succeed, and cancel.
- Tenant/owner isolation tests for overview, list, detail, retry, and cancel.
- List redaction tests for `payloadJson` and `resultJson`.
- UI interaction tests for filters, detail, copy, retry, cancel, and automatic refresh.
- Full `npm run check`, production Docker build, and authenticated browser smoke test.
