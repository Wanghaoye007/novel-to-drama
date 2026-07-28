# Novel-to-Drama Code Map

## Runtime Path

- `src/lib/job-worker.ts`: Web job claim and Engine invocation.
- `src/novel_drama_engine/pipeline.py`: round orchestration, artifacts, quality merge and repair.
- `src/novel_drama_engine/rounds.py`: LLM stage adapters and per-episode emission.
- `src/novel_drama_engine/prompts.py`: stage prompt contracts.

## Source Fidelity

- `src/novel_drama_engine/source_packets.py`: episode-to-source mapping and packet confidence.
- `src/novel_drama_engine/source_facts.py`: immutable SourceSpan and source-confirmed facts.
- `src/novel_drama_engine/models.py`: packet, script, quality and patch schemas.
- `src/novel_drama_engine/source_evidence.py`: source asset coverage gate.

## Script Quality

- `src/novel_drama_engine/script_quality.py`: deterministic local script checks.
- `src/novel_drama_engine/quality_policy.py`: hard/advisory disposition.
- `src/novel_drama_engine/repair_patches.py`: node-scoped patch authorization/application.
- `src/novel_drama_engine/dialogue_attribution.py`: source-grounded speaker/addressee cues, reconciliation and attribution audit.
- `src/novel_drama_engine/renderer.py`: user-visible script rendering.

## Platform And Access

- `src/lib/platform-context.ts`: signed session identity, tenant membership and workspace resolution.
- `src/lib/methodology-controls.ts`: internal methodology enable/disable interaction state.
- `src/lib/jobs.ts`: durable jobs, idempotency, stale recovery and retry state.
- `src/lib/deployment-readiness.ts`: online persistence, access, model and backup readiness checks.

## Deployment

- `scripts/start-ops-server.sh`: current macOS web runtime entrypoint.
- `scripts/start-ops-worker.sh`: current macOS worker runtime entrypoint.
- `scripts/backup-ops-data.sh`: consistent SQLite and generated-asset backup.
- `Dockerfile`: combined Node/Python Zeabur image.
- `scripts/start-zeabur.sh`: `/data` mount gate, migrations, readiness, supervised Web/Worker and scheduled backups.
- `src/scripts/migrate-db.ts`: production-only idempotent migration runner without `drizzle-kit`.
- `src/app/api/health/route.ts`: compact Zeabur probe; blocked readiness returns HTTP 503.
- `deploy/zeabur.env.example`: secret-free dashboard variable contract.
- `docs/ZEABUR_DEPLOYMENT.md`: dashboard setup, validation, backup and rollback runbook.
