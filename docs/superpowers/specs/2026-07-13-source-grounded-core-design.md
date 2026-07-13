# Source-Grounded Core Design

**Status:** approved for implementation on 2026-07-13

## Goal

Make the adaptation engine reliably preserve source facts and episode continuity by reducing the generation path to one source-grounded draft and, at most, one constrained repair. The Web product, exports, historical artifacts, and peripheral workers remain compatible.

## Problem

The existing engine has useful source packets, evidence reports, and a story-state ledger, but they are not a single upstream contract. A batch can be generated, rewritten, repaired, polished, and hook/dialogue-polished. Those independent transformations can preserve local formatting while changing motives, event order, or revealed knowledge.

## Chosen Architecture

New rounds use the following canonical path:

```
source text
  -> stable source spans
  -> source fact ledger
  -> arc-aware episode plan with evidence-backed beats
  -> source-grounded script batch
  -> deterministic hard validation
  -> one constrained patch repair per affected episode
  -> output + audit artifacts
```

`StoryBible`, `EpisodeSourcePackets`, and the existing `StoryStateLedger` remain compatibility views. They may summarize the ledger, but cannot introduce a source-confirmed fact that has no span evidence.

## Core Contracts

### Source spans and facts

- Every source text is deterministically split into `SourceSpan` records with a stable `span_id`, offsets, and text.
- `SourceFact` carries `fact_id`, content, fact type, confidence, source span ids, and provenance status.
- Only `source_confirmed` facts with one or more source spans are hard generation constraints.
- `inferred` facts are contextual hints only. `adapted` facts require an explicit adaptation reason and cannot replace a source-confirmed event, motive, knowledge state, or timeline fact.

### Episode beats

- Each `EpisodeDramaPlan` receives a list of `EpisodeBeat` records.
- A beat declares its event, required fact ids, source spans, forbidden changes, allowed adaptation, and before/after state requirements.
- Script generation receives only the current episode's source packet plus its fact-backed beats, the active arc summary, preceding handoff, and state constraints.
- A plan item without evidence is downgraded to advisory and cannot require a script event.

### State and continuity

- `StoryStateLedger` is reduced deterministically from the episode plan and accepted script result, not from an unconstrained model prose summary.
- State tracks character knowledge, relationship changes, locations, item ownership, completed events, and open hooks.
- Before generating an episode, the engine validates the required state. After generation, it validates the declared state delta.

### Quality and repair

- Hard checks: unsupported source facts, missing required facts, timeline/knowledge/state conflicts, causality failures, and malformed script structure.
- Advisory checks: hook strength, dialogue density, novelty, emotional intensity, and optional shooting detail.
- Advisory checks are recorded but never trigger a rewrite.
- A failed hard check produces a `RepairPatch` scoped to an episode and one or more lines/scenes. The repair prompt treats the current episode as immutable baseline outside those targets and may not alter beat outcomes or state transitions.
- Each episode has a maximum of one generation and one patch repair in a round. The engine never invokes batch rewrite, optional quality polish, or hook/dialogue polish by default.

## Compatibility and Migration

- Existing project artifacts remain read-only and are not reinterpreted or migrated.
- New rounds and explicit retries emit the new ledger and plan artifacts alongside existing names so the Web application and exports continue to work.
- Legacy `quality_report` remains the public compatibility summary. It is populated from the new hard/advisory outcome, rather than driving additional free-form rewrites.
- A new run manifest records the source-fact, plan, script, and quality-policy version fingerprints so cache reuse is explainable.

## Delivery Phases

### Phase 1: Stop source drift

1. Add source spans/facts, evidence-backed beat schema, and a source-fact artifact.
2. Build deterministic fact extraction from source packets and source evidence anchors.
3. Feed the fact/beat contract into script prompts and sanitize plans that lack evidence.
4. Remove default batch rewrite, quality polish, and hook/dialogue polish paths.
5. Keep one target-only repair pass for hard issues and persist patch/audit artifacts.

### Phase 2: Enforce continuity

1. Expand the state ledger with character knowledge and explicit before/after requirements.
2. Validate state before and after each episode.
3. Invalidate downstream episode artifacts when a repair changes knowledge, relationship, or core event state.
4. Separate story arcs from execution batches while retaining a maximum batch size of five.

### Phase 3: Operational correctness

1. Version layered caches by source, facts, plan, script, and quality policy.
2. Persist stage checkpoints for resume at the last completed artifact.
3. Standardize worker leases, heartbeats, idempotency, and job stage status.

### Phase 4: Evaluation

1. Add five human-annotated golden source sets.
2. Measure event recall/order, unsupported additions, knowledge conflicts, state conflicts, and unresolved hooks.
3. Use model-scored drama metrics only as advisory comparisons.

## Non-Goals for Phase 1

- No migration or alteration of historical project artifacts.
- No Web information architecture rewrite.
- No changes to video brief, localization, billing, or payment flows.
- No attempt to make every source fact a hard requirement; only episode-selected facts constrain the current episode.

## Acceptance Criteria

- A generated episode cannot rely on a source-confirmed fact without source span evidence.
- Every required episode beat has source evidence and is visible to the script generator.
- No default run invokes more than one script-generation attempt plus one patch repair per episode.
- Hook, dialogue, novelty, and visual-density findings never cause free-form rewrites.
- A hard repair preserves the old episode outside target locations and preserves the declared beat outcomes.
- Existing engine and Web test suites remain green.
