# Source-Grounded Core Phase 1 Audit Example

## Purpose

This is a compact example of the artifacts an operator or reviewer reads after one round. It documents the Phase 1 evidence and repair boundary; it is not a claim that cross-episode state recomputation exists.

## Reproducible Mock Run

```bash
PYTHONPATH=src python3 -m novel_drama_engine.cli run \
  --input examples/haomen_source.txt \
  --project-dir /tmp/novel-drama-phase1-audit \
  --project-id phase1-audit \
  --round-number 1 \
  --target-episode-count 1 \
  --episodes-per-round 1 \
  --mock
```

The run writes a normal, no-repair audit bundle under `round_001/`:

```text
source_spans.json
source_fact_ledger.json
source_fact_candidates.json
episode_source_packets.json
quality_decision.json
prompt_trace.json
```

Example canonical source span:

```json
{
  "span_id": "S-00000026-00000056-c5968004",
  "start": 26,
  "end": 56,
  "text": "林雪挽着顾承的手，温柔地说：“姐姐，你怎么穿成这样就来了？”"
}
```

The span includes the trailing quote. Its ID changes only when the full-source offset or exact source text changes, not when an episode packet is repartitioned.

For the same mock source, `source_fact_candidates.json` contains origin-labelled candidates from `source_packet`, `story_bible`, and `episode_plan`. Every candidate has:

```json
{
  "status": "inferred",
  "verification_status": "unverified"
}
```

The accompanying `quality_decision.json` for a clean run has no repair target:

```json
{
  "issues": [],
  "repair_targets": [],
  "unscoped_hard_dispositions": []
}
```

The deterministic quality-sample smoke run passed five sample inputs with its direct-baseline comparator. This verifies the pipeline and audit wiring, not real-provider writing quality; provider A/B evidence remains a separate production-quality exercise.

## Accepted Patch Example

When a structured hard issue identifies `EP01-S01-L01`, the system writes these repair artifacts:

```text
current_episode_repair_packets.json
repair_patches.json
repair_patch_application.json
repair_diff.json
```

`repair_patches.json` records the system-generated allow-list before the LLM call:

```json
{
  "patch_id": "P-EP01-01",
  "episode": 1,
  "scene_id": "EP01-S01",
  "target_type": "action",
  "target_ids": ["EP01-S01-L01"],
  "operation": "replace",
  "expected_before_hash": "<baseline line hash>",
  "issue_code": "STRUCTURE_INVALID"
}
```

The model may only supply `replacement`. A stale hash, unknown patch ID, changed target, protected Beat removal, or an extra Patch rejects the entire batch. `repair_patch_application.json` then records `accepted: false` and the persisted episode remains the baseline.

## Test Evidence

| Contract | Regression coverage |
| --- | --- |
| Actor, negation, and timing reversals stay inferred | `tests/test_source_facts.py` |
| Full-source Span IDs survive packet repartition | `tests/test_source_facts.py` |
| Bible/Plan claims never become source-confirmed | `tests/test_source_facts.py` |
| Stable system node IDs | `tests/test_repair_patches.py` |
| Stale hash, extra patch, and protected Beat rejection | `tests/test_repair_patches.py` |
| Soft findings do not block or rewrite | `tests/test_quality_policy.py` |
| Unscoped hard finding routes to human review | `tests/test_quality_policy.py` |
| One PatchBatch per episode and no automatic cascade | `tests/test_pipeline.py` |

## Phase 2 Boundary

An accepted Patch does not automatically recalculate character knowledge, re-audit dependent later episodes, or regenerate later content. The audit records the patch so Phase 2 can use it as a precise invalidation input rather than guessing from a rewritten whole episode.
