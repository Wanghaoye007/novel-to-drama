# Source-Grounded Core Phase 1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (\`- [ ]\`) syntax for tracking.

**Goal:** Replace the current multi-rewrite engine path with source-evidenced facts, fact-bound episode beats, and one constrained patch repair per episode.

**Architecture:** A deterministic \`SourceFactLedger\` is derived from existing source packets so Phase 1 adds no model call. The planner binds each episode to source-supported beats; the generator sees only those beats and matching facts. Quality classifies findings as hard or advisory, and only hard findings can create a validated patch.

**Tech Stack:** Python 3.11, Pydantic v2, pytest, existing OpenAI-compatible \`TrackedLLM\`, existing JSON artifact store.

## Global Constraints

- Existing project artifacts remain readable; only new rounds emit the new fact/beat/patch artifacts.
- \`source_confirmed\` facts must include one or more \`source_span_ids\`.
- A default run performs no batch rewrite, no optional quality polish, and no hook/dialogue polish.
- An episode may have one initial generation plus one patch repair at most.
- Hook, dialogue density, novelty, emotional intensity, and shooting density are advisory and cannot trigger repair.
- Source facts, character knowledge, event causality, continuity/state conflicts, required beats, and malformed structure are hard checks.
- New code retains \`QualityReport\`, \`StoryBible\`, \`EpisodeSourcePackets\`, and \`RoundResult\` compatibility fields.

---

### Task 1: Add deterministic source facts and repair-patch schemas

**Files:**
- Create: \`src/novel_drama_engine/source_facts.py\`
- Modify: \`src/novel_drama_engine/models.py\`
- Create: \`tests/test_source_facts.py\`

**Interfaces:**
- Consumes: \`source_text: str\`, \`EpisodeSourcePackets\`
- Produces: \`build_source_fact_ledger(source_text, packets) -> SourceFactLedger\`
- Produces: \`facts_for_episode(ledger, episode) -> list[SourceFact]\`
- Produces: \`build_repair_patches(issue_text, episode) -> list[RepairPatch]\`

- [ ] **Step 1: Write the failing tests**

~~~python
def test_source_confirmed_fact_has_stable_span_evidence():
    packets = EpisodeSourcePackets(packets=[
        EpisodeSourcePacket(
            episode=1,
            source_anchor="家宴",
            source_excerpt="父亲当众宣布与沈川断绝关系。沈川毫不知情。",
            source_start=10,
            source_end=34,
            c0_facts=["父亲主动宣布断绝关系", "沈川此前不知情"],
        )
    ])

    ledger = build_source_fact_ledger(
        "前言。父亲当众宣布与沈川断绝关系。沈川毫不知情。", packets
    )

    assert all(fact.source_span_ids for fact in ledger.facts)
    assert {fact.status for fact in ledger.facts} == {"source_confirmed"}
    assert ledger.facts[0].fact_id == "F-EP01-C0-01"


def test_repair_patch_never_targets_unrelated_scene():
    patch = RepairPatch(
        target="scene_2.line_3",
        issue="角色提前知道秘密",
        operation="replace",
        constraint="不能改变本场事件结果",
    )

    assert patch.target == "scene_2.line_3"
~~~

- [ ] **Step 2: Verify RED**

Run: \`python3 -m pytest tests/test_source_facts.py -q\`

Expected: import failure for \`SourceFactLedger\` and \`build_source_fact_ledger\`.

- [ ] **Step 3: Write the minimal implementation**

~~~python
class SourceSpan(BaseModel):
    span_id: str
    start: int = Field(ge=0)
    end: int = Field(ge=0)
    text: str


class SourceFact(BaseModel):
    fact_id: str
    content: str
    source_span_ids: list[str] = Field(min_length=1)
    fact_type: Literal[
        "character", "relationship", "event", "timeline",
        "location", "item", "knowledge", "secret",
    ]
    confidence: float = Field(ge=0.0, le=1.0)
    status: Literal["source_confirmed", "inferred", "adapted"]
    adaptation_reason: str | None = None


class SourceFactLedger(BaseModel):
    source_hash: str
    spans: list[SourceSpan] = Field(default_factory=list)
    facts: list[SourceFact] = Field(default_factory=list)


class RepairPatch(BaseModel):
    target: str
    issue: str
    operation: Literal["replace", "insert_after", "delete"]
    constraint: str
~~~

\`source_facts.py\` derives spans from \`EpisodeSourcePacket.source_start/source_end\`. It derives facts from C0, C1, active-party, and decision-timing inputs only when the text is present in the packet excerpt. It must never derive source-confirmed facts from a bible or planner summary.

- [ ] **Step 4: Verify GREEN**

Run: \`python3 -m pytest tests/test_source_facts.py -q\`

Expected: all source-fact tests pass.

- [ ] **Step 5: Commit**

~~~bash
git add src/novel_drama_engine/models.py src/novel_drama_engine/source_facts.py tests/test_source_facts.py
git commit -m "feat: add source fact ledger contracts"
~~~

### Task 2: Bind every episode plan to source-supported beats

**Files:**
- Modify: \`src/novel_drama_engine/models.py\`
- Modify: \`src/novel_drama_engine/source_packets.py\`
- Modify: \`src/novel_drama_engine/pipeline.py\`
- Modify: \`tests/test_source_packets.py\`
- Modify: \`tests/test_pipeline.py\`

**Interfaces:**
- Consumes: \`EpisodePlan\`, \`EpisodeSourcePackets\`, \`SourceFactLedger\`
- Produces: \`bind_episode_plan_to_facts(plan, packets, ledger) -> EpisodePlan\`
- Produces: \`EpisodeDramaPlan.beats: list[EpisodeBeat]\`

- [ ] **Step 1: Write the failing tests**

~~~python
def test_plan_beat_uses_only_facts_in_its_episode_packet():
    bound = bind_episode_plan_to_facts(plan, packets, ledger)
    beat = bound.episodes[0].beats[0]

    assert beat.source_span_ids == ["S-EP01"]
    assert beat.required_fact_ids == ["F-EP01-C0-01"]
    assert "不能改成男主主动离家" in beat.forbidden_changes


def test_unsupported_provider_beat_is_replaced_by_source_fact_beat():
    plan.episodes[0].beats = [
        EpisodeBeat(
            beat_id="EP01-B01",
            event="母亲死亡",
            source_span_ids=["S-UNKNOWN"],
            required_fact_ids=["F-UNKNOWN"],
        )
    ]

    bound = bind_episode_plan_to_facts(plan, packets, ledger)

    assert all(beat.source_span_ids for beat in bound.episodes[0].beats)
    assert "母亲死亡" not in "\n".join(beat.event for beat in bound.episodes[0].beats)
~~~

- [ ] **Step 2: Verify RED**

Run: \`python3 -m pytest tests/test_source_packets.py -q -k "beat"\`

Expected: missing \`EpisodeBeat\` or \`bind_episode_plan_to_facts\`.

- [ ] **Step 3: Write the minimal implementation**

~~~python
class EpisodeBeat(BaseModel):
    beat_id: str
    event: str
    source_span_ids: list[str] = Field(min_length=1)
    required_fact_ids: list[str] = Field(min_length=1)
    forbidden_changes: list[str] = Field(default_factory=list)
    allowed_adaptation: str = "允许压缩旁白，改成可拍动作与短对白。"
    state_before: list[str] = Field(default_factory=list)
    state_after: list[str] = Field(default_factory=list)
~~~

\`bind_episode_plan_to_facts\` retains provider beats only when every referenced span and fact belongs to the current episode. Otherwise it creates one to three deterministic beats from C0 facts and C1 assets, including C4 rules as \`forbidden_changes\`.

- [ ] **Step 4: Persist canonical planning artifacts**

In \`Pipeline.run\`, immediately after episode source packets are built:

~~~python
source_fact_ledger = build_source_fact_ledger(source_text, episode_source_packets)
self.store.write_round_artifact(round_number, "source_fact_ledger", source_fact_ledger)

episode_plan = bind_episode_plan_to_facts(
    episode_plan, episode_source_packets, source_fact_ledger
)
self.store.write_round_artifact(round_number, "episode_plan_fact_bound", episode_plan)
~~~

- [ ] **Step 5: Verify GREEN and commit**

Run: \`python3 -m pytest tests/test_source_packets.py tests/test_pipeline.py -q\`

~~~bash
git add src/novel_drama_engine/models.py src/novel_drama_engine/source_packets.py src/novel_drama_engine/pipeline.py tests/test_source_packets.py tests/test_pipeline.py
git commit -m "feat: bind episode beats to source facts"
~~~

### Task 3: Make source facts and beats the script-generator contract

**Files:**
- Modify: \`src/novel_drama_engine/rounds.py\`
- Modify: \`src/novel_drama_engine/prompts.py\`
- Modify: \`src/novel_drama_engine/pipeline.py\`
- Modify: \`tests/test_pipeline.py\`

**Interfaces:**
- Consumes: \`source_fact_ledger: SourceFactLedger | None\`
- Consumes: fact-bound \`EpisodePlan\`
- Produces: generator requests that contain only current-episode facts and beats as hard constraints.

- [ ] **Step 1: Write a failing prompt-contract test**

~~~python
def test_script_generation_receives_current_episode_facts_and_never_future_facts(tmp_path):
    result = run_pipeline_with_static_llm(tmp_path)
    episode_call = first_call_for("EpisodeScript")

    assert '"F-EP01-C0-01"' in episode_call["user"]
    assert '"F-EP02-C0-01"' not in episode_call["user"]
    assert "不得新增无 source_span_ids 的核心事实" in episode_call["user"]
~~~

- [ ] **Step 2: Verify RED**

Run: \`python3 -m pytest tests/test_pipeline.py -q -k "current_episode_facts"\`

Expected: the prompt has no fact-ledger contract.

- [ ] **Step 3: Thread the contract through the generator**

Add optional \`source_fact_ledger\` to \`ScriptBatchGenerator.run\`, \`run_episode\`, and prompt builders. Resolve facts with \`facts_for_episode(ledger, episode_number)\` and include this contract in the user payload:

~~~text
当前集只能把 required_fact_ids 和 source_span_ids 对应的事实写成剧情结果。
没有 source_span_ids 的信息不得作为核心事件、人物动机、关系变化或秘密揭露写入。
禁止提前使用下一集或后续 arc 的事实；不确定时保留悬念，不得补编解释。
~~~

- [ ] **Step 4: Verify GREEN and commit**

Run: \`python3 -m pytest tests/test_pipeline.py -q -k "current_episode_facts or source_packet"\`

~~~bash
git add src/novel_drama_engine/rounds.py src/novel_drama_engine/prompts.py src/novel_drama_engine/pipeline.py tests/test_pipeline.py
git commit -m "feat: ground script prompts in source facts"
~~~

### Task 4: Replace free-form rewrite chains with one constrained patch repair

**Files:**
- Modify: \`src/novel_drama_engine/models.py\`
- Modify: \`src/novel_drama_engine/script_quality.py\`
- Modify: \`src/novel_drama_engine/rounds.py\`
- Modify: \`src/novel_drama_engine/pipeline.py\`
- Modify: \`tests/test_script_quality.py\`
- Modify: \`tests/test_pipeline.py\`

**Interfaces:**
- Consumes: \`EpisodeScript\`, hard quality findings, \`CurrentEpisodeRepairPacket\`
- Produces: \`EpisodeRepairPatch\` and \`apply_episode_repair_patch(episode, patch) -> EpisodeScript\`
- Produces: no more than one repair attempt per episode.

- [ ] **Step 1: Write failing tests for hard-vs-advisory classification and patch limits**

~~~python
def test_hook_density_warning_is_advisory_and_does_not_select_repair_target():
    assert not quality_issue_requires_patch("EP01 cliffhanger is too soft")


def test_source_fact_conflict_selects_one_patch_target():
    assert quality_issue_requires_patch("EP01 source fact missing: F-EP01-C0-01")
    packet = build_current_episode_repair_packet(
        episode, "source fact missing: F-EP01-C0-01"
    )
    assert packet.repair_mode == "creative_episode_repair"
    assert packet.editable_targets


def test_default_pipeline_never_writes_batch_or_optional_polish_artifacts(tmp_path):
    run_pipeline_with_hard_repair(tmp_path)

    assert not (tmp_path / "round_001" / "script_batch_rewrite.json").exists()
    assert not (tmp_path / "round_001" / "script_batch_episode_polish.json").exists()
    assert not (tmp_path / "round_001" / "script_batch_hook_dialogue_polish.json").exists()
~~~

- [ ] **Step 2: Verify RED**

Run: \`python3 -m pytest tests/test_script_quality.py tests/test_pipeline.py -q -k "patch or optional_polish"\`

Expected: advisory warnings still choose repair targets or legacy artifacts are written.

- [ ] **Step 3: Implement constrained patch behavior**

1. Add \`EpisodeRepairPatch\` with \`episode\`, \`patches\`, and \`preserved_beat_ids\`.
2. Make the repair generator request \`EpisodeRepairPatch\`, not a fresh \`EpisodeScript\`.
3. \`apply_episode_repair_patch\` may change only \`scene_N.line_N\` targets declared in \`CurrentEpisodeRepairPacket\`; reject a patch that deletes a scene, changes an undeclared target, or removes a required beat fact anchor.
4. Derive repair targets only from source evidence/fact, knowledge, causality, continuity/state, or structure. Treat all style/Hook/dialogue/novelty findings as advisory.
5. Remove \`script_batch_rewrite\`, \`episode_quality_polish\`, and \`hook_dialogue_polish\` execution branches from the default pipeline. Retain legacy readers only for historical artifacts.

- [ ] **Step 4: Verify GREEN and commit**

Run: \`python3 -m pytest tests/test_script_quality.py tests/test_pipeline.py -q\`

~~~bash
git add src/novel_drama_engine/models.py src/novel_drama_engine/script_quality.py src/novel_drama_engine/rounds.py src/novel_drama_engine/pipeline.py tests/test_script_quality.py tests/test_pipeline.py
git commit -m "fix: restrict generation to one source-safe repair"
~~~

### Task 5: Make final quality one hard/advisory result and verify regression coverage

**Files:**
- Create: \`src/novel_drama_engine/quality_policy.py\`
- Modify: \`src/novel_drama_engine/pipeline.py\`
- Modify: \`src/novel_drama_engine/models.py\`
- Create: \`tests/test_quality_policy.py\`
- Modify: \`tests/test_pipeline.py\`

**Interfaces:**
- Consumes: existing quality reports plus source-fact and state results
- Produces: \`QualityDecision(hard_issues, advisory_issues, repair_targets)\`

- [ ] **Step 1: Write failing quality-policy tests**

~~~python
def test_quality_policy_blocks_source_fact_and_knowledge_conflicts():
    decision = decide_quality([
        "source fact missing: F-EP01-C0-01",
        "角色提前知道秘密",
    ])

    assert decision.hard_issues
    assert decision.repair_targets == {1}


def test_quality_policy_keeps_hook_and_novelty_advisory():
    decision = decide_quality([
        "EP01 cliffhanger is too soft",
        "EP02 novelty low",
    ])

    assert not decision.hard_issues
    assert decision.advisory_issues
~~~

- [ ] **Step 2: Verify RED**

Run: \`python3 -m pytest tests/test_quality_policy.py -q\`

Expected: missing \`decide_quality\`.

- [ ] **Step 3: Integrate a single decision point**

\`Pipeline.run\` constructs \`QualityDecision\` after deterministic reports are merged. Only \`decision.hard_issues\` may call patch repair. Persist \`quality_decision.json\`, \`repair_patches.json\`, and \`repair_diff.json\`; keep \`quality_report.json\` as a compatibility summary with advisory text separated from blocking text.

- [ ] **Step 4: Run full verification and commit**

Run:

~~~bash
python3 -m pytest -q
npm run test:ts
npm run typecheck
npm run build
~~~

Expected: all suites pass and no default run writes legacy multi-rewrite artifacts.

~~~bash
git add src/novel_drama_engine/quality_policy.py src/novel_drama_engine/models.py src/novel_drama_engine/pipeline.py tests/test_quality_policy.py tests/test_pipeline.py
git commit -m "feat: unify hard and advisory quality decisions"
~~~

## Verification Matrix

| Behavior | Test |
| --- | --- |
| Source fact has stable source evidence | \`tests/test_source_facts.py\` |
| Provider plan cannot inject unsupported beat | \`tests/test_source_packets.py\` |
| Prompt receives only current-episode facts | \`tests/test_pipeline.py\` |
| Hook/dialogue warning does not rewrite content | \`tests/test_script_quality.py\` |
| Source/state conflict uses one target patch | \`tests/test_pipeline.py\` |
| No default batch/polish/hook rewrite artifacts | \`tests/test_pipeline.py\` |
| Existing Web contracts keep passing | \`npm run test:ts\` and \`npm run typecheck\` |

