# Evidence-First Source Grounding Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace packet-certified facts and full-episode repair candidates with canonical source evidence, structured issues, and system-applied bounded patches.

**Architecture:** First create immutable source spans and direct evidence facts from the source text, then map packets and beats to those IDs. Canonicalize scripts with stable scene/line IDs. Quality producers return typed, scoped issues; the repair model produces only patch operations, which the system applies and validates against the current script baseline.

**Tech Stack:** Python 3.11, Pydantic v2, pytest, existing OpenAI-compatible `TrackedLLM`, existing JSON artifact store.

## Global Constraints

- This is Phase 1 only; do not add cross-episode state reduction or cascade regeneration.
- Existing stored artifacts remain readable through compatibility defaults.
- Packet/Bible/Plan claims cannot become `source_confirmed` facts.
- One episode receives one automatic patch attempt at most.
- Only structured, scoped hard issues may trigger a patch.

---

### Task 1: Canonical source spans and direct facts

**Files:**
- Modify: `src/novel_drama_engine/models.py`
- Modify: `src/novel_drama_engine/source_facts.py`
- Modify: `src/novel_drama_engine/source_packets.py`
- Test: `tests/test_source_facts.py`
- Test: `tests/test_source_packets.py`

**Interfaces:**
- Produces: `build_source_spans(source_text) -> list[SourceSpan]`
- Produces: `build_source_fact_ledger(source_text, packets) -> SourceFactLedger`
- Produces: `SourceFactCandidate` records for Packet/Bible/Plan claims.

- [ ] Write failing tests for actor, negation, and timing reversals, plus span stability across packet partitions.
- [ ] Run `python3 -m pytest tests/test_source_facts.py tests/test_source_packets.py -q` and confirm failures are behavior failures.
- [ ] Implement source-first spans, direct evidence facts, packet span references, and inferred candidates.
- [ ] Re-run targeted tests and commit the green task.

### Task 2: Stable script node identifiers and patch application

**Files:**
- Modify: `src/novel_drama_engine/models.py`
- Create: `src/novel_drama_engine/repair_patches.py`
- Modify: `src/novel_drama_engine/rounds.py`
- Modify: `src/novel_drama_engine/prompts.py`
- Modify: `src/novel_drama_engine/pipeline.py`
- Modify: `src/novel_drama_engine/script_quality.py`
- Test: `tests/test_repair_patches.py`
- Test: `tests/test_pipeline.py`

**Interfaces:**
- Produces: `canonicalize_episode_nodes(episode) -> EpisodeScript`
- Produces: `apply_repair_patches(baseline, patches, facts, beats) -> PatchApplicationResult`
- Consumes: a constrained `RepairPatchBatch` from the repair model.

- [ ] Write failing tests for stale hashes, foreign scene modifications, protected Beat changes, and a second repair attempt.
- [ ] Run `python3 -m pytest tests/test_repair_patches.py tests/test_pipeline.py -q` and confirm failures.
- [ ] Implement deterministic node IDs, executable patch schema, patch-only repair prompt, application, and audit artifacts.
- [ ] Re-run targeted tests and commit the green task.

### Task 3: Structured quality issues and repair decisions

**Files:**
- Modify: `src/novel_drama_engine/models.py`
- Modify: `src/novel_drama_engine/quality_policy.py`
- Modify: `src/novel_drama_engine/pipeline.py`
- Modify: quality-report producer modules that emit repair-driving issues
- Test: `tests/test_quality_policy.py`
- Test: `tests/test_pipeline.py`

**Interfaces:**
- Produces: `QualityIssue` and `QualityDecision` with a disposition per hard issue.
- Consumes: structured issues to derive scoped repair targets.

- [ ] Write failing tests proving `C1` and "人物动机表达不够强" remain advisory, while unscoped hard issues receive explicit dispositions.
- [ ] Run `python3 -m pytest tests/test_quality_policy.py tests/test_pipeline.py -q` and confirm failures.
- [ ] Implement typed issue classification, compatibility rendering, and disposition-based repair eligibility.
- [ ] Re-run targeted tests and commit the green task.

### Task 4: Artifacts, documentation, and PR evidence

**Files:**
- Modify: `docs/superpowers/specs/2026-07-13-evidence-first-source-grounding-design.md`
- Modify: `README.md` or PR description as appropriate
- Test: `tests/test_pipeline.py`

- [ ] Add artifact assertions for spans, candidates, structured decisions, patch requests, and patch application.
- [ ] Run `python3 -m pytest -q`, `npm run test:ts`, `npm run typecheck`, `npm run build`, and a worktree-local mock smoke run.
- [ ] Update the PR description with Phase 1 boundaries and test evidence.
- [ ] Commit and push the final branch update.

