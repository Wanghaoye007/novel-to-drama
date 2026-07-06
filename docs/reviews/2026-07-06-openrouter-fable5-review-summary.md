# OpenRouter Fable 5 Review Summary

- Review model: `anthropic/claude-fable-5`
- Pack: `2026-07-06-openrouter-fable5-review-pack.md`
- First response: `2026-07-06-openrouter-fable5-review.md`
- Continuation: `2026-07-06-openrouter-fable5-review-continuation.md`
- Total cost: `$1.59629`
- Verdict: `not_ready`

## P0 Blockers

1. `src/novel_drama_engine/pipeline.py`
   - `prior_run_manifest_compatible` compares full `code` and `env`, so after this deploy all old manifests become incompatible and prior Story Bible reuse is silently skipped.
   - Fix: compare a semantic compatibility set only, normalize missing env defaults, and record a warning when reuse is skipped.

2. `drizzle/migrations/0008_material_silvermane.sql`
   - Unique active round-generation job index can fail on existing databases that already contain duplicate queued/running jobs.
   - Fix: clean duplicate active jobs in the migration before creating the unique partial index.

3. `src/lib/engine-runner.ts`
   - Engine failure catch path now marks project `running` unconditionally, so terminal round failures can become invisible.
   - Fix: distinguish retryable/non-terminal failure from terminal failure and surface terminal failure as `failed` or `needs_attention`.

## P1 Important Fixes

1. `src/lib/platform-credits.ts`
   - Unsigned mock webhook bypass is controlled only by env and has no production guard.
   - Fix: allow bypass only outside production-like deployment and only for mock provider.

2. `src/novel_drama_engine/drama_quality.py`
   - Advisory text is injected into `rewrite_instruction`, which can pollute downstream repair targeting and prompts.
   - Fix: move advisory text to a dedicated advisory field/artifact and keep `rewrite_instruction` empty for usable reports.

3. `src/lib/engine-runner.ts`
   - Run-all still schedules the next round when current quality status is `needs_rewrite` or `needs_human_review`.
   - Fix: pause run-all and write a visible reason when current round quality is not usable.

4. `src/lib/jobs.ts`
   - Stale round-generation jobs fail the round while leaving the project running with no active job.
   - Fix: auto-requeue if attempts remain; otherwise mark project visible attention/failed.

5. `src/lib/jobs.ts`
   - Unique constraint error classification is too broad and can mask unrelated unique failures.
   - Fix: match only `jobs_active_round_generation_unique`.

6. `package.json` / `tests/p0_platform.test.ts`
   - TS tests run through `tsx` without typecheck; tests write `maxAttempts`, which is not in the schema.
   - Fix: add `tsc --noEmit` and either add a real `max_attempts` column or remove fake test fields.

## P2 Followups

1. `src/novel_drama_engine/source_evidence.py`
   - Evidence span status is `matched` when script line exists even if source line is missing.
   - Fix: require both source and script span for strict matched, or introduce `script_only`.

2. `src/novel_drama_engine/source_evidence.py` and `src/novel_drama_engine/adaptation_quality.py`
   - Token matching assumes the first four Chinese characters are a name-like prefix.
   - Fix: use known character names from Story Bible or source analysis instead of fixed slicing.

3. `src/lib/jobs.ts`
   - Retry state restoration clears `rounds.summaryJson`, losing diagnostic context.
   - Fix: preserve old summary in job history/result or only clear error-specific fields.

4. `package.json`
   - `test:ts` depends on shell glob behavior.
   - Fix: use a more stable test target and declare the required Node version.

5. `src/app/api/health/route.ts`
   - Health route imports `engine-runner`, which can drag heavy dependencies into health checks.
   - Fix: move engine mode resolution to a lightweight module shared by health and runner.

## Quality Chain Risk

Fable 5 judged the chain direction correct but not yet a proof that pipeline output beats direct LLM rewrite. Missing pieces:

- Direct baseline artifacts and their quality/source evidence reports should be persisted in experiment mode.
- The removed LLM QA line-level rules need a coverage matrix mapping each rule to deterministic gate code and tests.
- `SourceEvidenceReport.coverage_score` and missing spans are not yet consumed by a hard quality gate or run-all decision.

## Minimal Next Plan

1. Fix manifest semantic compatibility and add old-manifest reuse test.
2. Make migration 0008 clean duplicate active jobs before adding the unique index.
3. Fix terminal failure/project visibility and stale job handling.
4. Pause run-all when current round quality is not usable.
5. Remove advisory pollution from `rewrite_instruction` and lock webhook mock bypass behind non-production.
6. Add TS typecheck and resolve fake `maxAttempts`.
7. Add baseline artifacts plus quality/source-evidence comparison in experiment mode.
8. Re-run `python3 -m pytest -q && npm run typecheck && npm run test:ts && npm run build && git diff --check`.
