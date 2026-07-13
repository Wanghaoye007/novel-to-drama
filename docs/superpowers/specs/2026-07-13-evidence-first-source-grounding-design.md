# Evidence-First Source Grounding Design

## Status

Approved implementation scope for the source-grounded core PR. This document supersedes the evidence and repair portions of `2026-07-13-source-grounded-core-design.md`.

## Goal

Make every automatic script repair traceable to immutable source evidence and an executable, bounded patch. A model summary, a Story Bible item, or an episode-plan statement must never become a `source_confirmed` fact merely because its words overlap the novel.

## Scope

This phase delivers:

1. Stable, fine-grained `SourceSpan` values generated from the full source text.
2. Direct source evidence separate from upstream `SourceFactCandidate` inference.
3. Stable scene and line identifiers in an `EpisodeScript`.
4. A system-applied `RepairPatch` protocol with baseline-hash and immutable-node validation.
5. Structured `QualityIssue` values that alone drive automated repair.
6. Audit artifacts and regressions for the failure modes in the PR review.

This phase does not deliver cross-episode knowledge-state reduction, cascading invalidation, or downstream episode regeneration. Those remain Phase 2.

## Source Evidence Model

### Stable spans

The full source is segmented before any episode packet is interpreted. A span is a source paragraph or sentence-window with immutable source offsets:

```text
span_id = S-{start:08d}-{end:08d}-{sha256(text)[:8]}
```

`EpisodeSourcePacket` stores `source_span_ids`; its legacy excerpt and offset fields stay readable for older artifacts but are not canonical evidence identifiers. Re-splitting the same source into different episode packets must not change the span IDs.

### Facts and candidates

`SourceFact` is an evidence-backed, direct extraction from one or more canonical spans. Its content is verbatim source evidence or a deterministic projection of that evidence, and it is the only type that may be marked `source_confirmed`.

`SourceFactCandidate` records a claim from a packet, Bible, or plan with its origin and verification status. Candidates are `inferred` by default. They can inform planning, but cannot satisfy a required fact, cause a source-fidelity pass, or enter a hard repair constraint unless a separate source extractor creates an evidence-backed `SourceFact`.

The implementation deliberately avoids pretending that n-gram overlap is semantic verification. A candidate such as "林晚主动签署合同" remains inferred even if the source contains "林晚拒绝签署合同".

## Script Node and Patch Model

Every accepted `EpisodeScript` is canonicalized with deterministic IDs:

- `scene_id`: `EP{episode:02d}-S{scene_index:02d}`
- `line_id`: `{scene_id}-L{line_index:02d}`

The repair model receives the current script plus a finite list of patches. It returns patch operations only, not a replacement `EpisodeScript`. Each patch declares its target IDs, expected pre-image hash, operation, replacement, required fact IDs, protected beat IDs, and required post-state. The system then:

1. Resolves target IDs against the current baseline.
2. Requires the pre-image hash to match.
3. Applies the operation deterministically.
4. Rejects a patch that changes any non-target node, changes a protected beat, or violates required source facts.
5. Emits accepted and rejected patch audit records.

One episode receives at most one repair attempt. A rejected patch leaves the original episode untouched and becomes a human-review condition.

## Quality Contract

New producers emit `QualityIssue` directly:

```python
QualityIssue(
    code="MISSING_REQUIRED_FACT",
    severity="hard",
    episode=3,
    scene_id="EP03-S02",
    evidence=["F-...", "S-..."],
    message="...",
)
```

Only an issue with `severity="hard"` and usable scope may generate an automatic patch. Free-text legacy findings remain visible as compatibility/advisory output and cannot trigger repair. An unscoped hard issue is recorded with an explicit reason (`global_structure_failure`, `producer_contract_failure`, or `missing_scope_metadata`) and requires human review.

## Artifacts

New or updated rounds persist:

- `source_spans.json`
- `source_fact_ledger.json`
- `source_fact_candidates.json`
- `episode_source_packets.json` with `source_span_ids`
- `quality_decision.json` with structured issues and disposition
- `repair_patches.json`
- `repair_diff.json`
- `repair_patch_application.json`

## Verification

The test suite must prove:

- Opposite action, reversed actor, removed negation, and reversed timing candidates never become confirmed source facts.
- Span IDs are invariant when packet boundaries change.
- A patch cannot modify another scene or line, change a protected beat, or apply against stale text.
- A soft issue mentioning `C1` or "人物动机" remains advisory.
- An unscoped hard issue has an explicit non-repair disposition.
- A second automatic repair for one episode is refused.

