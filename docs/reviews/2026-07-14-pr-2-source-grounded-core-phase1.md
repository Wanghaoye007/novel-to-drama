## Summary

- derive stable, sentence-granular `SourceSpan` IDs from full-source offsets and text hashes before episode packets are interpreted
- keep direct source facts separate from packet/Bible/Plan `SourceFactCandidate` records; upstream claims are forcibly `inferred/unverified` and cannot be promoted by lexical overlap
- canonicalize every Scene and Line to system-owned IDs and replace full-episode retries with a `RepairPatchBatch` protocol that only permits pre-authorized node replacements
- make structured `QualityIssue` objects the only automatic repair input; legacy quality strings remain operator-facing compatibility output and cannot select a repair target
- persist evidence, quality decisions, patch allow-lists, application outcomes, and actual diffs for every repair attempt

## Phase 1 Boundary

This PR does **not** claim to solve full long-drama continuity. Character knowledge-state reduction, downstream dependency invalidation, and re-generation of later episodes remain Phase 2 work. An accepted Patch changes only its authorized current-episode node; it does not trigger an automatic cascade.

## Audit Artifacts

- `source_spans.json`
- `source_fact_ledger.json`
- `source_fact_candidates.json`
- `quality_decision.json`
- `current_episode_repair_packets.json`
- `repair_patches.json`
- `repair_patch_application.json`
- `repair_diff.json`

See `docs/superpowers/audits/2026-07-14-source-grounded-core-phase1.md` for a reproducible mock run and artifact examples.

## Verification

- `PYTHONPATH=src python3 -m pytest -q`
- `npm run test:ts`
- `npm run typecheck`
- `npm run build`
- `PYTHONPATH=src python3 -m novel_drama_engine.cli run --input examples/haomen_source.txt --project-dir /tmp/novel-drama-phase1-audit --project-id phase1-audit --round-number 1 --target-episode-count 1 --episodes-per-round 1 --mock`
- `PYTHONPATH=src python3 -m novel_drama_engine.cli evaluate-samples --mock --projects-dir /tmp/novel-drama-phase1-samples --rounds 1`

The mock quality samples are deterministic plumbing checks, not proof of real-provider writing quality. Legacy pipeline tests that asserted deprecated full-episode rewrite or automatic cascade behavior are explicitly skipped and replaced by node-scoped Patch regression coverage.
