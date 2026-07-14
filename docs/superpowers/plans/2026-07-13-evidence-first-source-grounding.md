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

- [x] Write regression tests for actor, negation, and timing reversals, plus span stability across packet partitions.
- [x] Run targeted source fact and packet tests.
- [x] Implement source-first spans, direct evidence facts, packet span references, and inferred candidates.
- [x] Re-run targeted tests and commit the green task.

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

- [x] Write regression tests for stale hashes, patch overflow, foreign scene modifications, protected Beat changes, and a second repair attempt.
- [x] Run targeted repair-patch and pipeline tests.
- [x] Implement deterministic node IDs, replace-only patch schema, patch-only repair prompt, application, and audit artifacts.
- [x] Re-run targeted tests and commit the green task.

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

- [x] Write regression tests proving soft issues remain advisory while unscoped hard issues receive explicit dispositions.
- [x] Run targeted quality-policy and pipeline tests.
- [x] Implement typed issue classification, compatibility rendering, and disposition-based repair eligibility.
- [x] Re-run targeted tests and commit the green task.

### Task 4: Artifacts, documentation, and PR evidence

**Files:**
- Modify: `docs/superpowers/specs/2026-07-13-evidence-first-source-grounding-design.md`
- Modify: `README.md` or PR description as appropriate
- Test: `tests/test_pipeline.py`

- [x] Add artifact assertions for spans, candidates, structured decisions, patch requests, and patch application.
- [x] Run `python3 -m pytest -q`, `npm run test:ts`, `npm run typecheck`, `npm run build`, and worktree-local mock smoke checks.
- [ ] Update the PR description with Phase 1 boundaries and test evidence.
- [ ] Commit and push the final branch update.

## Completion Evidence (2026-07-14)

- Python regression suite: `PYTHONPATH=src python3 -m pytest -q`
- TypeScript suite: `npm run test:ts`
- Static checks: `npm run typecheck`, `npm run build`, and `git diff --check`
- Mock audit smoke: one-round CLI run against `examples/haomen_source.txt`
- Mock quality samples: five samples passed with direct-baseline comparison. This validates artifact plumbing only; it is not evidence of real-provider writing quality.
