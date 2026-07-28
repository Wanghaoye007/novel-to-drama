import json
import time
from typing import Any

import pytest
from pydantic import BaseModel

from novel_drama_engine.demo import demo_haomen_source, demo_round_outputs
from novel_drama_engine.llm import StaticJsonLLM
from novel_drama_engine.models import (
    AdaptationIntensity,
    EpisodeContext,
    EpisodeSourceMapping,
    EpisodeSourcePacket,
    EpisodeSourcePackets,
    EpisodeScript,
    GenerationVariant,
    NextRoundContext,
    QualityReport,
    QualityIssue,
    QualityScores,
    QualityStatus,
    RoundResult,
    RepairPatchBatch,
    Scene,
    SceneLine,
    ScriptBatch,
    SourceAnalysis,
    SourceDialogueCue,
    SourceFact,
    SourceFactLedger,
    SourceSpan,
    SourceStrengthLevel,
    SourceStrengthProfile,
    StoryBible,
)
from novel_drama_engine.pipeline import (
    EmptySourceError,
    InstrumentedJsonLLM,
    RepairBudget,
    RoundPipeline,
    build_run_manifest,
    normalize_repair_budget,
    prompt_trace_enabled,
    quality_instruction_for_episode,
    strong_source_light_adaptation,
    use_episode_first_script_generation,
)
from novel_drama_engine.rounds import (
    ContinuityBoomChecker,
    EpisodeBeatPlanner,
    EpisodeContextResolver,
    InternalBibleBuilder,
    ScriptBatchGenerator,
    SourceParser,
    StateWriter,
)
from novel_drama_engine.source_packets import SourcePacketConfidenceError
from novel_drama_engine.script_quality import build_current_episode_repair_packet
from novel_drama_engine.storage import ProjectStore


HAPPY_SOURCE_TEXT = demo_haomen_source()


def _patch_batch_for_issue(
    episode: EpisodeScript,
    issue: QualityIssue,
    replacement: str,
) -> RepairPatchBatch:
    allowed_patch = build_current_episode_repair_packet(
        episode,
        issue.message,
        quality_issue=issue,
    ).repair_patches[0]
    return RepairPatchBatch(
        episode=episode.episode,
        patches=[allowed_patch.model_copy(update={"replacement": replacement})],
    )


class RecordingLLM:
    def __init__(self, outputs: list[BaseModel | dict[str, Any] | Exception]) -> None:
        self._outputs = list(outputs)
        self.calls: list[dict[str, Any]] = []

    def complete(self, *, system: str, user: str, response_model: type[BaseModel]) -> BaseModel:
        self.calls.append(
            {
                "system": system,
                "user": user,
                "response_model": response_model,
            }
        )
        if not self._outputs:
            raise AssertionError("No static LLM output remains")
        raw = self._outputs.pop(0)
        if isinstance(raw, Exception):
            raise raw
        if isinstance(raw, response_model):
            return raw
        return response_model.model_validate(raw)


class ModelQueuedLLM:
    def __init__(self, outputs_by_model: dict[type[BaseModel], list[BaseModel]]) -> None:
        self._outputs = {
            model.__name__: list(outputs) for model, outputs in outputs_by_model.items()
        }
        self.calls: list[dict[str, Any]] = []

    def complete(self, *, system: str, user: str, response_model: type[BaseModel]) -> BaseModel:
        self.calls.append(
            {
                "system": system,
                "user": user,
                "response_model": response_model,
            }
        )
        outputs = self._outputs.get(response_model.__name__, [])
        if not outputs:
            raise AssertionError(f"No static LLM output remains for {response_model.__name__}")
        return outputs.pop(0)


def test_strong_source_light_protection_applies_to_drama_engine_first():
    profile = SourceStrengthProfile(
        conflict_strength=9,
        hook_strength=9,
        character_tag_strength=8,
        emotion_asset_strength=9,
        signature_scene_strength=9,
        visualization_readiness=8,
        overall_level=SourceStrengthLevel.STRONG,
        recommended_intensity=AdaptationIntensity.LIGHT,
        reasons=["原文已有强冲突，不应重构因果。"],
    )

    assert strong_source_light_adaptation(
        profile,
        GenerationVariant.DRAMA_ENGINE_FIRST,
    )


def test_episode_first_generation_defaults_by_model_when_env_is_unset(monkeypatch):
    monkeypatch.delenv("NOVEL_DRAMA_SCRIPT_EPISODE_FIRST", raising=False)

    assert use_episode_first_script_generation(
        "bytedance-seed/seed-2.0-mini"
    )
    assert not use_episode_first_script_generation("google/gemini-3.5-flash")

def test_prompt_trace_is_enabled_by_default_and_can_be_disabled(monkeypatch):
    monkeypatch.delenv("NOVEL_DRAMA_TRACE_PROMPTS", raising=False)

    assert prompt_trace_enabled()

    monkeypatch.setenv("NOVEL_DRAMA_TRACE_PROMPTS", "0")

    assert not prompt_trace_enabled()


def test_instrumented_llm_writes_running_heartbeat_for_slow_calls():
    class TinyModel(BaseModel):
        value: str

    class SlowLLM:
        def complete(
            self,
            *,
            system: str,
            user: str,
            response_model: type[BaseModel],
        ) -> BaseModel:
            time.sleep(0.22)
            return response_model.model_validate({"value": "ok"})

    updates: list[list[dict[str, Any]]] = []

    def on_update() -> None:
        updates.append([call.model_dump() for call in tracked_llm.snapshot_calls()])

    tracked_llm = InstrumentedJsonLLM(
        SlowLLM(),
        on_update=on_update,
        heartbeat_seconds=0.05,
    )
    tracked_llm.current_stage = "script_batch"

    result = tracked_llm.complete(system="system", user="user", response_model=TinyModel)

    assert result.value == "ok"
    assert len(tracked_llm.calls) == 1
    assert tracked_llm.calls[0].status == "succeeded"
    assert tracked_llm.calls[0].stage == "script_batch"
    assert any(
        update
        and update[0]["status"] == "running"
        and update[0]["response_model"] == "TinyModel"
        for update in updates
    )


def test_instrumented_llm_reports_prompt_trace():
    class TinyModel(BaseModel):
        value: str

    traces: list[dict[str, object]] = []
    tracked_llm = InstrumentedJsonLLM(
        StaticJsonLLM([{"value": "ok"}]),
        on_prompt=traces.append,
    )
    tracked_llm.current_stage = "source_analysis"

    result = tracked_llm.complete(
        system="system prompt",
        user="user prompt",
        response_model=TinyModel,
    )

    assert result.value == "ok"
    assert traces[0]["call_index"] == 0
    assert traces[0]["stage"] == "source_analysis"
    assert traces[0]["response_model"] == "TinyModel"
    assert traces[0]["system_prompt"] == "system prompt"
    assert traces[0]["user_prompt"] == "user prompt"
    assert traces[0]["system_prompt_chars"] == len("system prompt")
    assert traces[0]["user_prompt_chars"] == len("user prompt")
    assert isinstance(traces[0]["system_prompt_sha256"], str)
    assert isinstance(traces[0]["user_prompt_sha256"], str)


def test_round_services_consume_llm_outputs_in_order(happy_round_outputs):
    llm = StaticJsonLLM(happy_round_outputs)
    source = SourceParser(llm).run(HAPPY_SOURCE_TEXT)
    context = EpisodeContextResolver(llm).run(HAPPY_SOURCE_TEXT, None, source)
    bible = InternalBibleBuilder(llm).run(HAPPY_SOURCE_TEXT, source, context)
    scripts = ScriptBatchGenerator(llm).run(
        HAPPY_SOURCE_TEXT,
        source,
        context,
        bible,
        None,
        "",
    )
    quality = ContinuityBoomChecker(llm).run(source, context, bible, scripts, None)
    next_context = StateWriter(llm).run(source, context, bible, scripts, quality, None)

    assert source.candidate_hooks == ["把她拖出去！"]
    assert context.target_episode_range == "EP01-EP05"
    assert scripts.episodes[0].hook_3s == "把她拖出去！"
    assert quality.status == "usable"
    assert next_context.current_episode == 5


def test_script_batch_generator_fills_missing_target_episodes(happy_round_outputs):
    outputs = demo_round_outputs(include_episode_plan=True)
    source, context, bible, episode_plan, full_batch = outputs[:5]
    partial_batch = ScriptBatch(episodes=[full_batch.episodes[0]])
    llm = RecordingLLM([partial_batch, *full_batch.episodes[1:]])

    result = ScriptBatchGenerator(llm).run(
        HAPPY_SOURCE_TEXT,
        source,
        context,
        bible,
        None,
        "",
        episode_plan=episode_plan,
    )

    assert [episode.episode for episode in result.episodes] == [1, 2, 3, 4, 5]
    assert [
        call["response_model"].__name__
        for call in llm.calls
    ] == ["ScriptBatch", "EpisodeScript", "EpisodeScript", "EpisodeScript", "EpisodeScript"]


def test_script_batch_generator_can_generate_episode_first(happy_round_outputs):
    outputs = demo_round_outputs(include_episode_plan=True)
    source, context, bible, episode_plan, full_batch = outputs[:5]
    llm = RecordingLLM(full_batch.episodes)
    packets = EpisodeSourcePackets(
        packets=[
            EpisodeSourcePacket(
                episode=1,
                source_anchor="EP01",
                source_excerpt="EP01_ONLY_SOURCE",
            ),
            EpisodeSourcePacket(
                episode=2,
                source_anchor="EP02",
                source_excerpt="EP02_ONLY_SECRET",
            ),
            EpisodeSourcePacket(
                episode=3,
                source_anchor="EP03",
                source_excerpt="EP03_ONLY_SOURCE",
            ),
            EpisodeSourcePacket(
                episode=4,
                source_anchor="EP04",
                source_excerpt="EP04_ONLY_SOURCE",
            ),
            EpisodeSourcePacket(
                episode=5,
                source_anchor="EP05",
                source_excerpt="EP05_ONLY_SOURCE",
            ),
        ],
    )

    result = ScriptBatchGenerator(llm).run_episode_batch(
        "FULL_SOURCE_SHOULD_NOT_APPEAR EP02_ONLY_SECRET",
        source,
        context,
        bible,
        None,
        "",
        episode_plan=episode_plan,
        episode_source_packets=packets,
    )

    assert [episode.episode for episode in result.episodes] == [1, 2, 3, 4, 5]
    assert [
        call["response_model"].__name__
        for call in llm.calls
    ] == ["EpisodeScript", "EpisodeScript", "EpisodeScript", "EpisodeScript", "EpisodeScript"]
    assert "逐集优先生成模式" in llm.calls[0]["user"]
    assert "本集原文包" in llm.calls[0]["user"]
    assert "EP01_ONLY_SOURCE" in llm.calls[0]["user"]
    assert "FULL_SOURCE_SHOULD_NOT_APPEAR" not in llm.calls[0]["user"]
    assert "EP02_ONLY_SECRET" not in llm.calls[0]["user"]
    assert full_batch.episodes[0].cliffhanger in llm.calls[1]["user"]


def test_episode_first_resume_generates_only_missing_episodes(happy_round_outputs):
    outputs = demo_round_outputs(include_episode_plan=True)
    source, context, bible, episode_plan, full_batch = outputs[:5]
    persisted = full_batch.episodes[:4]
    llm = RecordingLLM([full_batch.episodes[4]])

    result = ScriptBatchGenerator(llm).run_episode_batch(
        HAPPY_SOURCE_TEXT,
        source,
        context,
        bible,
        None,
        "",
        episode_plan=episode_plan,
        existing_episodes=persisted,
    )

    assert [episode.episode for episode in result.episodes] == [1, 2, 3, 4, 5]
    assert [call["response_model"].__name__ for call in llm.calls] == [
        "EpisodeScript"
    ]
    assert full_batch.episodes[3].cliffhanger in llm.calls[0]["user"]


def test_episode_first_resume_discards_non_contiguous_tail_after_a_gap(
    happy_round_outputs,
):
    outputs = demo_round_outputs(include_episode_plan=True)
    source, context, bible, episode_plan, full_batch = outputs[:5]
    persisted = [full_batch.episodes[0], full_batch.episodes[2]]
    regenerated_two = full_batch.episodes[1]
    regenerated_three = full_batch.episodes[2].model_copy(
        update={"title": "EP03 regenerated after gap"}
    )
    llm = RecordingLLM(
        [regenerated_two, regenerated_three, full_batch.episodes[3], full_batch.episodes[4]]
    )

    result = ScriptBatchGenerator(llm).run_episode_batch(
        HAPPY_SOURCE_TEXT,
        source,
        context,
        bible,
        None,
        "",
        episode_plan=episode_plan,
        existing_episodes=persisted,
    )

    assert len(llm.calls) == 4
    assert result.episodes[2].title == "EP03 regenerated after gap"
    assert regenerated_two.cliffhanger in llm.calls[1]["user"]


def test_episode_first_generation_receives_only_current_source_facts(
    happy_round_outputs,
):
    outputs = demo_round_outputs(include_episode_plan=True)
    source, context, bible, episode_plan, full_batch = outputs[:5]
    llm = RecordingLLM(full_batch.episodes)
    packets = EpisodeSourcePackets(
        packets=[
            EpisodeSourcePacket(
                episode=episode_number,
                source_anchor=f"EP{episode_number:02d}",
                source_excerpt=f"EP{episode_number:02d}_SOURCE",
            )
            for episode_number in range(1, 6)
        ],
    )
    fact_ledger = SourceFactLedger(
        source_hash="test-source",
        spans=[
            SourceSpan(
                span_id=f"S-EP{episode_number:02d}",
                episode=episode_number,
                start=episode_number,
                end=episode_number + 1,
                text=f"EP{episode_number:02d}_SOURCE",
            )
            for episode_number in range(1, 6)
        ],
        facts=[
            SourceFact(
                fact_id=f"F-EP{episode_number:02d}-C0-01",
                episode=episode_number,
                content=f"EP{episode_number:02d} only source fact",
                source_span_ids=[f"S-EP{episode_number:02d}"],
                fact_type="event",
                confidence=1.0,
                status="source_confirmed",
            )
            for episode_number in range(1, 6)
        ],
    )

    ScriptBatchGenerator(llm).run_episode_batch(
        "FULL_SOURCE_SHOULD_NOT_APPEAR",
        source,
        context,
        bible,
        None,
        "",
        episode_plan=episode_plan,
        episode_source_packets=packets,
        source_fact_ledger=fact_ledger,
    )

    first_prompt = llm.calls[0]["user"]
    assert "F-EP01-C0-01" in first_prompt
    assert "EP01 only source fact" in first_prompt
    assert "F-EP02-C0-01" not in first_prompt
    assert "EP02 only source fact" not in first_prompt
    assert "不得新增无 source_span_ids 的核心事实" in first_prompt


def test_script_batch_generator_emits_each_episode_when_generated():
    outputs = demo_round_outputs(include_episode_plan=True)
    source, context, bible, episode_plan, full_batch = outputs[:5]
    llm = RecordingLLM(full_batch.episodes)
    emitted: list[EpisodeScript] = []

    result = ScriptBatchGenerator(llm, episode_writer=emitted.append).run_episode_batch(
        HAPPY_SOURCE_TEXT,
        source,
        context,
        bible,
        None,
        "",
        episode_plan=episode_plan,
    )

    assert [episode.episode for episode in result.episodes] == [1, 2, 3, 4, 5]
    assert [episode.episode for episode in emitted] == [1, 2, 3, 4, 5]


def test_episode_writer_receives_source_reconciled_speaker_before_incremental_emit(
    happy_round_outputs,
):
    source, context, bible = happy_round_outputs[:3]
    wrong_episode = EpisodeScript(
        episode=2,
        title="说话人串位",
        hook_3s="张雅冷笑",
        main_emotion="压迫",
        watch_reason="看张雅反击",
        scenes=[
            Scene(
                scene_id="EP02-S01",
                heading="2-1 夜-内-张雅出租屋",
                characters=["张雅", "江毅"],
                lines=[
                    SceneLine(
                        line_id="EP02-S01-L01",
                        kind="dialogue",
                        speaker="江毅",
                        text="你都知道她是个母亲",
                    )
                ],
            )
        ],
        cliffhanger="你都知道她是个母亲",
        state_update={},
    )
    packet = EpisodeSourcePacket(
        episode=2,
        source_anchor="EP02",
        source_excerpt="闻言我冷笑。‘你都知道她是个母亲。’",
        dialogue_cues=[
            SourceDialogueCue(
                cue_id="D-EP02-source",
                speaker="张雅",
                text="你都知道她是个母亲",
                source_span_ids=["S-EP02"],
                attribution="first_person_narrator",
                confidence="high",
            )
        ],
    )
    emitted: list[EpisodeScript] = []

    result = ScriptBatchGenerator(
        RecordingLLM([wrong_episode]),
        episode_writer=emitted.append,
    ).run_episode(
        HAPPY_SOURCE_TEXT,
        source,
        context,
        bible,
        None,
        None,
        2,
        "",
        episode_source_packet=packet,
    )

    assert result.scenes[0].lines[0].speaker == "张雅"
    assert emitted[0].scenes[0].lines[0].speaker == "张雅"


def test_episode_beat_planner_consumes_llm_output(happy_round_outputs):
    outputs = demo_round_outputs(include_episode_plan=True)
    source, context, bible, episode_plan = outputs[:4]
    llm = StaticJsonLLM([episode_plan])

    plan = EpisodeBeatPlanner(llm).run(HAPPY_SOURCE_TEXT, source, context, bible, None)

    assert plan.variant == GenerationVariant.DRAMA_ENGINE_FIRST
    assert plan.target_episode_range == "EP01-EP05"
    assert plan.episodes[0].physical_action_chain
    assert "信息差" in plan.adaptation_strategy


def test_pipeline_rejects_empty_source_before_llm_call(tmp_path):
    llm = RecordingLLM([])
    pipeline = RoundPipeline(llm=llm, store=ProjectStore(tmp_path))

    with pytest.raises(EmptySourceError):
        pipeline.run(project_id="demo", round_number=1, source_text="   ")

    assert llm.calls == []
    assert not (tmp_path / "round_001").exists()


def test_pipeline_persists_artifacts(tmp_path, happy_round_outputs):
    pipeline = RoundPipeline(llm=StaticJsonLLM(happy_round_outputs), store=ProjectStore(tmp_path))

    result = pipeline.run(
        project_id="demo",
        round_number=1,
        source_text=HAPPY_SOURCE_TEXT,
        generation_variant=GenerationVariant.CURRENT_DENSITY,
    )

    assert result.script_batch.episodes[0].title == "被赶出生日宴"
    for artifact_name in [
        "source_analysis",
        "source_strength_profile",
        "episode_context",
        "story_bible",
        "episode_source_packets",
        "source_spans",
        "source_fact_ledger",
        "source_fact_candidates",
        "script_batch",
        "runtime_report",
        "run_manifest",
        "quality_report",
        "adaptation_quality_report",
        "methodology_quality_report",
        "drama_quality_report",
        "script_novelty_report",
        "source_evidence_report",
        "dialogue_attribution_report",
        "story_state_ledger",
        "prompt_trace_analysis",
        "round_result",
        "next_round_context",
    ]:
        assert (tmp_path / "round_001" / f"{artifact_name}.json").exists()
    assert (tmp_path / "round_001" / "creative_script.md").exists()
    assert (tmp_path / "round_001" / "shooting_script.md").exists()
    assert (tmp_path / "round_001" / "rendered_scripts.md").exists()
    assert (tmp_path / "round_001" / "script_novelty_report.md").exists()
    assert (tmp_path / "round_001" / "source_evidence_report.md").exists()
    assert (tmp_path / "round_001" / "prompt_trace_analysis.md").exists()
    assert (tmp_path / "round_001" / "raw_llm_output.jsonl").exists()
    source_packets = json.loads(
        (tmp_path / "round_001" / "episode_source_packets.json").read_text(
            encoding="utf-8"
        )
    )
    assert all(packet["source_span_ids"] for packet in source_packets["packets"])
    assert all("dialogue_cues" in packet for packet in source_packets["packets"])
    source_facts = json.loads(
        (tmp_path / "round_001" / "source_fact_ledger.json").read_text(
            encoding="utf-8"
        )
    )
    assert {fact["origin"] for fact in source_facts["facts"]} == {
        "direct_extraction"
    }
    assert result.adaptation_quality_report is not None
    assert result.methodology_quality_report is not None
    assert result.drama_quality_report is not None
    assert result.drama_quality_report.overall_score >= 7
    assert result.script_novelty_report is not None
    assert result.script_novelty_report.overall_score >= 7
    assert result.source_evidence_report is not None
    assert result.source_evidence_report.coverage_score >= 0
    assert any(item.evidence_spans for item in result.source_evidence_report.items)
    assert result.source_strength_profile is not None
    assert result.story_state_ledger is not None
    assert result.runtime_report is not None
    assert result.runtime_report.total_llm_calls == 6


def test_pipeline_default_generation_variant_is_drama_engine_first(tmp_path):
    outputs = demo_round_outputs(include_episode_plan=True)
    pipeline = RoundPipeline(llm=StaticJsonLLM(outputs), store=ProjectStore(tmp_path))

    result = pipeline.run(project_id="demo", round_number=1, source_text=HAPPY_SOURCE_TEXT)

    assert result.episode_plan is not None
    assert result.episode_plan.variant == GenerationVariant.DRAMA_ENGINE_FIRST
    assert result.episode_plan.episodes[0].beats
    assert (tmp_path / "round_001" / "episode_plan.json").exists()
    assert (tmp_path / "round_001" / "episode_plan_fact_bound.json").exists()


def test_pipeline_source_evidence_missing_assets_downgrades_final_quality(
    tmp_path,
    happy_round_outputs,
):
    source, context, bible, scripts, quality, next_context = happy_round_outputs
    context = context.model_copy(
        update={
            "target_episode_range": "EP01-EP01",
            "source_to_episode_mapping": [
                EpisodeSourceMapping(
                    source="原文里亲哥哥突然救场。",
                    target_episode="EP01",
                    retained_assets=["林晚被赶出时，亲哥哥突然出现"],
                    adaptation_reason="必须保留原文亲哥哥救场资产。",
                )
            ]
        },
        deep=True,
    )
    pipeline = RoundPipeline(
        llm=StaticJsonLLM([source, context, bible, scripts, quality, next_context]),
        store=ProjectStore(tmp_path),
    )

    result = pipeline.run(
        project_id="demo",
        round_number=1,
        source_text="林晚被赶出时，亲哥哥突然出现。" * 20,
        target_episode_count=1,
        episodes_per_round=1,
        repair_budget="none",
        generation_variant=GenerationVariant.CURRENT_DENSITY,
    )

    assert result.source_evidence_report is not None
    assert result.source_evidence_report.missing_items == [
        "EP01 缺少原文资产：林晚被赶出时，亲哥哥突然出现"
    ]
    assert "亲哥哥救场" not in result.source_evidence_report.missing_items[0]
    assert result.quality_report.status == QualityStatus.NEEDS_HUMAN_REVIEW
    assert any(
        issue.code == "MISSING_REQUIRED_FACT"
        and issue.episode == 1
        and issue.scene_id is None
        for issue in result.quality_report.issues
    )
    context_path = tmp_path / "round_001" / "next_round_context.json"
    assert context_path.exists()
    assert ProjectStore(tmp_path).read_next_round_context(context_path).current_episode == 1


def test_pipeline_blocks_low_confidence_source_packets_before_script_generation(
    tmp_path,
    happy_round_outputs,
):
    source, context, bible, *_ = happy_round_outputs
    context = context.model_copy(
        update={
            "target_episode_range": "EP02-EP02",
            "source_to_episode_mapping": [
                EpisodeSourceMapping(
                    source="不存在的第二集锚点",
                    target_episode="EP02",
                    retained_assets=["不存在的雪地烟火激吻"],
                    adaptation_reason="测试弱映射不能继续写。",
                )
            ],
        },
        deep=True,
    )
    llm = RecordingLLM([source, context, bible])
    pipeline = RoundPipeline(llm=llm, store=ProjectStore(tmp_path))
    source_text = "\n".join(
        [
            f"第{i}段，林挽清在颁奖礼后台承受羞辱，路淮北把她藏在镜头之外。"
            for i in range(900)
        ]
    )

    with pytest.raises(SourcePacketConfidenceError):
        pipeline.run(
            project_id="demo",
            round_number=1,
            source_text=source_text,
            target_episode_count=5,
        )

    response_models = [call["response_model"].__name__ for call in llm.calls]
    assert "ScriptBatch" not in response_models
    assert (
        tmp_path / "round_001" / "source_packet_confidence_report.md"
    ).exists()


def test_pipeline_source_evidence_gap_without_node_scope_stops_for_human_review(
    tmp_path,
    happy_round_outputs,
):
    source, context, bible, scripts, quality, next_context = happy_round_outputs
    context = context.model_copy(
        update={
            "target_episode_range": "EP01-EP01",
            "source_to_episode_mapping": [
                EpisodeSourceMapping(
                    source="原文里亲哥哥突然救场。",
                    target_episode="EP01",
                    retained_assets=["亲哥哥救场"],
                    adaptation_reason="必须保留原文亲哥哥救场资产。",
                )
            ],
        },
        deep=True,
    )
    llm = ModelQueuedLLM(
        {
            SourceAnalysis: [source],
            EpisodeContext: [context],
            StoryBible: [bible],
            ScriptBatch: [scripts],
            QualityReport: [quality],
            NextRoundContext: [next_context],
        }
    )
    pipeline = RoundPipeline(llm=llm, store=ProjectStore(tmp_path))

    result = pipeline.run(
        project_id="demo",
        round_number=1,
        source_text="原文里亲哥哥救场。\n" + HAPPY_SOURCE_TEXT,
        generation_variant=GenerationVariant.CURRENT_DENSITY,
    )

    patch_calls = [
        call
        for call in llm.calls
        if call["response_model"].__name__ == "RepairPatchBatch"
    ]
    assert patch_calls == []
    assert result.quality_report.status == QualityStatus.NEEDS_HUMAN_REVIEW
    assert result.source_evidence_report is not None
    assert result.source_evidence_report.missing_items == ["EP01 缺少原文资产：亲哥哥救场"]
    decision = json.loads(
        (tmp_path / "round_001" / "pre_repair_quality_decision.json").read_text(
            encoding="utf-8"
        )
    )
    assert decision["repair_targets"] == []
    assert decision["unscoped_hard_dispositions"][0]["disposition"] == "missing_scope_metadata"


def test_pipeline_drama_quality_warning_does_not_create_an_unscoped_patch(
    tmp_path,
    happy_round_outputs,
):
    source, context, bible, scripts, quality, next_context = happy_round_outputs
    context = context.model_copy(update={"target_episode_range": "EP01-EP01"}, deep=True)
    bad_episode = scripts.episodes[0].model_copy(deep=True)
    bad_episode.scenes[0].characters.extend(["周扬", "沈曼", "赵凯", "韩峥"])
    bad_episode.scenes[0].lines.extend(
        [
            SceneLine(kind="dialogue", speaker="周扬", text="我来解释。"),
            SceneLine(kind="dialogue", speaker="沈曼", text="流程都办好了。"),
            SceneLine(kind="dialogue", speaker="赵凯", text="证据在这里。"),
            SceneLine(kind="dialogue", speaker="韩峥", text="结果马上出。"),
        ]
    )
    bad_scripts = ScriptBatch(episodes=[bad_episode])
    llm = ModelQueuedLLM(
        {
            SourceAnalysis: [source],
            EpisodeContext: [context],
            StoryBible: [bible],
            ScriptBatch: [bad_scripts],
            QualityReport: [quality],
            NextRoundContext: [next_context],
        }
    )
    pipeline = RoundPipeline(llm=llm, store=ProjectStore(tmp_path))

    result = pipeline.run(
        project_id="demo",
        round_number=1,
        source_text=HAPPY_SOURCE_TEXT,
        target_episode_count=1,
        episodes_per_round=1,
        generation_variant=GenerationVariant.CURRENT_DENSITY,
    )

    patch_calls = [
        call
        for call in llm.calls
        if call["response_model"].__name__ == "RepairPatchBatch"
    ]
    assert patch_calls == []
    assert (tmp_path / "round_001" / "pre_repair_drama_quality_report.json").exists()
    assert result.quality_report.status == QualityStatus.NEEDS_HUMAN_REVIEW


def test_pipeline_writes_prompt_trace_when_enabled(
    tmp_path,
    happy_round_outputs,
    monkeypatch,
):
    monkeypatch.setenv("NOVEL_DRAMA_TRACE_PROMPTS", "1")
    monkeypatch.delenv("NOVEL_DRAMA_SCRIPT_EPISODE_FIRST", raising=False)
    pipeline = RoundPipeline(llm=StaticJsonLLM(happy_round_outputs), store=ProjectStore(tmp_path))

    pipeline.run(
        project_id="demo",
        round_number=1,
        source_text=HAPPY_SOURCE_TEXT,
        generation_variant=GenerationVariant.CURRENT_DENSITY,
    )

    trace_path = tmp_path / "round_001" / "prompt_trace.json"
    assert trace_path.exists()
    traces = json.loads(trace_path.read_text(encoding="utf-8"))
    assert traces[0]["stage"] == "source_analysis"
    assert traces[0]["response_model"] == "SourceAnalysis"
    assert "林家生日宴" in traces[0]["user_prompt"]
    assert any(trace["stage"] == "script_batch" for trace in traces)
    assert all("system_prompt_sha256" in trace for trace in traces)
    analysis = json.loads(
        (tmp_path / "round_001" / "prompt_trace_analysis.json").read_text(
            encoding="utf-8"
        )
    )
    assert analysis["artifacts_present"]["prompt_trace.json"] is True
    assert analysis["total_llm_calls"] == len(traces)


def test_pipeline_persists_source_strength_profile(tmp_path, happy_round_outputs):
    pipeline = RoundPipeline(llm=StaticJsonLLM(happy_round_outputs), store=ProjectStore(tmp_path))

    result = pipeline.run(
        project_id="demo",
        round_number=1,
        source_text=HAPPY_SOURCE_TEXT,
        generation_variant=GenerationVariant.CURRENT_DENSITY,
    )

    assert result.source_strength_profile is not None
    assert result.source_strength_profile.recommended_intensity in {"light", "medium", "heavy"}
    assert (tmp_path / "round_001" / "source_strength_profile.json").exists()


def test_pipeline_records_methodology_but_scripts_from_lean_source_contract(
    tmp_path,
    happy_round_outputs,
):
    llm = RecordingLLM(happy_round_outputs)
    pipeline = RoundPipeline(llm=llm, store=ProjectStore(tmp_path))

    result = pipeline.run(
        project_id="demo",
        round_number=1,
        source_text=HAPPY_SOURCE_TEXT,
        generation_variant=GenerationVariant.CURRENT_DENSITY,
    )

    script_call = next(
        call for call in llm.calls if call["response_model"].__name__ == "ScriptBatch"
    )
    assert result.methodology_context is not None
    card_names = [card.name for card in result.methodology_context.cards]
    assert "强原文轻改规则" in card_names
    assert "动作行三层结构与微型叙事弧" in card_names
    assert "【P0 轻链路主输入】" in script_call["user"]
    assert "source_annotation 是首稿最高优先级基准" in script_call["user"]
    assert "episode_cut_table 决定本轮分集边界" in script_call["user"]
    assert "强原文轻改规则" not in script_call["user"]
    assert "动作行三层结构与微型叙事弧" not in script_call["user"]
    assert result.production_spec is not None
    assert result.source_annotation is not None
    assert result.episode_cut_table is not None
    assert result.runtime_report is not None
    assert "强原文轻改规则" in result.runtime_report.methodology_cards
    assert "动作行三层结构与微型叙事弧" in result.runtime_report.methodology_cards
    assert (tmp_path / "round_001" / "methodology_context.json").exists()


def test_pipeline_resumes_from_cached_round_artifacts(tmp_path, happy_round_outputs):
    source, context, bible, scripts, quality, next_context = happy_round_outputs
    store = ProjectStore(tmp_path)
    store.write_round_artifact(1, "source_analysis", source)
    store.write_round_artifact(1, "episode_context", context)
    store.write_round_artifact(1, "story_bible", bible)
    store.write_round_artifact(1, "script_batch", scripts)
    llm = RecordingLLM([quality, next_context])
    pipeline = RoundPipeline(llm=llm, store=store)
    manifest = build_run_manifest(
        project_id="demo",
        round_number=1,
        source_text=HAPPY_SOURCE_TEXT,
        target_episode_count=None,
        episodes_per_round=5,
        generation_variant=GenerationVariant.CURRENT_DENSITY,
        repair_budget=RepairBudget.EPISODE,
        llm=llm,
        methodology_cards_path=None,
    )
    store.write_text_artifact(
        1,
        "run_manifest.json",
        json.dumps(manifest, ensure_ascii=False, indent=2),
    )

    result = pipeline.run(
        project_id="demo",
        round_number=1,
        source_text=HAPPY_SOURCE_TEXT,
        generation_variant=GenerationVariant.CURRENT_DENSITY,
    )

    assert [call["response_model"].__name__ for call in llm.calls] == [
        "QualityReport",
        "NextRoundContext",
    ]
    assert result.runtime_report is not None
    assert result.runtime_report.total_llm_calls == 2
    assert any(
        stage.name == "script_batch" and stage.status == "cached"
        for stage in result.runtime_report.stages
    )


def test_pipeline_resume_reuses_four_episode_files_and_only_generates_the_fifth(
    tmp_path,
):
    outputs = demo_round_outputs(include_episode_plan=True)
    source, context, bible, episode_plan, scripts, quality, next_context = outputs
    llm = RecordingLLM([scripts.episodes[4], quality, next_context])
    store = ProjectStore(tmp_path)
    store.write_round_artifact(1, "source_analysis", source)
    store.write_round_artifact(1, "episode_context", context)
    store.write_round_artifact(1, "story_bible", bible)
    store.write_round_artifact(1, "episode_plan", episode_plan)
    for episode in scripts.episodes[:4]:
        store.write_round_artifact(1, f"episode_{episode.episode:03d}", episode)
    manifest = build_run_manifest(
        project_id="demo",
        round_number=1,
        source_text=HAPPY_SOURCE_TEXT,
        target_episode_count=5,
        episodes_per_round=5,
        generation_variant=GenerationVariant.CURRENT_DENSITY,
        repair_budget=RepairBudget.NONE,
        llm=llm,
        methodology_cards_path=None,
    )
    store.write_text_artifact(
        1,
        "run_manifest.json",
        json.dumps(manifest, ensure_ascii=False, indent=2),
    )

    result = RoundPipeline(llm=llm, store=store).run(
        project_id="demo",
        round_number=1,
        source_text=HAPPY_SOURCE_TEXT,
        target_episode_count=5,
        episodes_per_round=5,
        repair_budget="none",
        generation_variant=GenerationVariant.CURRENT_DENSITY,
    )

    assert [episode.episode for episode in result.script_batch.episodes] == [1, 2, 3, 4, 5]
    assert [call["response_model"].__name__ for call in llm.calls].count(
        "EpisodeScript"
    ) == 1


def test_run_manifest_tracks_quality_policy_code_fingerprint():
    llm = StaticJsonLLM([])

    manifest = build_run_manifest(
        project_id="demo",
        round_number=1,
        source_text=HAPPY_SOURCE_TEXT,
        target_episode_count=None,
        episodes_per_round=5,
        generation_variant=GenerationVariant.CURRENT_DENSITY,
        repair_budget=RepairBudget.EPISODE,
        llm=llm,
        methodology_cards_path=None,
    )

    assert "quality_policy.py" in manifest["code"]


def test_run_manifest_ignores_deprecated_script_prompt_mode_env(monkeypatch):
    monkeypatch.setenv("NOVEL_DRAMA_SCRIPT_PROMPT_MODE", "legacy")
    llm = StaticJsonLLM([])

    manifest = build_run_manifest(
        project_id="demo",
        round_number=1,
        source_text=HAPPY_SOURCE_TEXT,
        target_episode_count=None,
        episodes_per_round=5,
        generation_variant=GenerationVariant.DRAMA_ENGINE_FIRST,
        repair_budget=RepairBudget.EPISODE,
        llm=llm,
        methodology_cards_path=None,
    )

    assert "NOVEL_DRAMA_SCRIPT_PROMPT_MODE" not in manifest["env"]


def test_pipeline_ignores_cached_round_without_matching_manifest(tmp_path, happy_round_outputs):
    source, context, bible, scripts, stale_quality, stale_next_context = happy_round_outputs
    fresh_outputs = demo_round_outputs()
    store = ProjectStore(tmp_path)
    store.write_round_artifact(1, "source_analysis", source)
    store.write_round_artifact(1, "episode_context", context)
    store.write_round_artifact(1, "story_bible", bible)
    store.write_round_artifact(1, "script_batch", scripts)
    store.write_round_artifact(
        1,
        "round_result",
        RoundResult(
            project_id="demo",
            round_number=1,
            source_analysis=source,
            episode_context=context,
            story_bible=bible,
            script_batch=scripts,
            quality_report=stale_quality,
            next_round_context=stale_next_context,
        ),
    )
    llm = RecordingLLM(fresh_outputs)
    pipeline = RoundPipeline(llm=llm, store=store)

    result = pipeline.run(
        project_id="demo",
        round_number=1,
        source_text=HAPPY_SOURCE_TEXT,
        generation_variant=GenerationVariant.CURRENT_DENSITY,
    )

    assert result.runtime_report is not None
    assert result.runtime_report.total_llm_calls > 0
    assert llm.calls
    manifest = json.loads((tmp_path / "round_001" / "run_manifest.json").read_text())
    assert manifest["cache_status"] == "completed"


def test_pipeline_reuses_prior_round_story_bible(tmp_path, happy_round_outputs):
    _, _, prior_bible, _, _, previous_context = happy_round_outputs
    round_two_outputs = demo_round_outputs(
        round_number=2,
        previous_context=previous_context,
        include_story_bible=False,
    )
    store = ProjectStore(tmp_path)
    store.write_round_artifact(1, "story_bible", prior_bible)
    llm = RecordingLLM(round_two_outputs)
    prior_manifest = build_run_manifest(
        project_id="demo",
        round_number=1,
        source_text=HAPPY_SOURCE_TEXT,
        target_episode_count=None,
        episodes_per_round=5,
        generation_variant=GenerationVariant.CURRENT_DENSITY,
        repair_budget=RepairBudget.EPISODE,
        llm=llm,
        methodology_cards_path=None,
    )
    store.write_text_artifact(
        1,
        "run_manifest.json",
        json.dumps(prior_manifest, ensure_ascii=False, indent=2),
    )
    pipeline = RoundPipeline(llm=llm, store=store)

    result = pipeline.run(
        project_id="demo",
        round_number=2,
        source_text=HAPPY_SOURCE_TEXT,
        previous_context=previous_context,
        generation_variant=GenerationVariant.CURRENT_DENSITY,
    )

    assert result.story_bible == prior_bible
    assert "StoryBible" not in [
        call["response_model"].__name__ for call in llm.calls
    ]
    assert (tmp_path / "round_002" / "story_bible.json").exists()
    assert any(
        stage.name == "story_bible" and stage.status == "cached"
        for stage in result.runtime_report.stages
    )


def test_pipeline_reuses_prior_story_bible_when_same_round_resume_is_disabled(
    tmp_path,
    happy_round_outputs,
    monkeypatch,
):
    monkeypatch.setenv("NOVEL_DRAMA_RESUME_ARTIFACTS", "0")
    _, _, prior_bible, _, _, previous_context = happy_round_outputs
    round_two_outputs = demo_round_outputs(
        round_number=2,
        previous_context=previous_context,
        include_story_bible=False,
    )
    store = ProjectStore(tmp_path)
    store.write_round_artifact(1, "story_bible", prior_bible)
    llm = RecordingLLM(round_two_outputs)
    prior_manifest = build_run_manifest(
        project_id="demo",
        round_number=1,
        source_text=HAPPY_SOURCE_TEXT,
        target_episode_count=None,
        episodes_per_round=5,
        generation_variant=GenerationVariant.CURRENT_DENSITY,
        repair_budget=RepairBudget.EPISODE,
        llm=llm,
        methodology_cards_path=None,
    )
    store.write_text_artifact(
        1,
        "run_manifest.json",
        json.dumps(prior_manifest, ensure_ascii=False, indent=2),
    )

    result = RoundPipeline(llm=llm, store=store).run(
        project_id="demo",
        round_number=2,
        source_text=HAPPY_SOURCE_TEXT,
        previous_context=previous_context,
        generation_variant=GenerationVariant.CURRENT_DENSITY,
    )

    assert result.story_bible == prior_bible
    assert "StoryBible" not in [
        call["response_model"].__name__ for call in llm.calls
    ]


def test_pipeline_reuses_prior_story_bible_when_legacy_manifest_has_stale_code_or_env(
    tmp_path,
    happy_round_outputs,
):
    _, _, prior_bible, _, _, previous_context = happy_round_outputs
    round_two_outputs = demo_round_outputs(
        round_number=2,
        previous_context=previous_context,
        include_story_bible=False,
    )
    store = ProjectStore(tmp_path)
    store.write_round_artifact(1, "story_bible", prior_bible)
    llm = RecordingLLM(round_two_outputs)
    legacy_manifest = build_run_manifest(
        project_id="demo",
        round_number=1,
        source_text=HAPPY_SOURCE_TEXT,
        target_episode_count=None,
        episodes_per_round=5,
        generation_variant=GenerationVariant.CURRENT_DENSITY,
        repair_budget=RepairBudget.EPISODE,
        llm=llm,
        methodology_cards_path=None,
    )
    legacy_manifest["code"] = {"prompts.py": "legacy-code-fingerprint"}
    legacy_manifest["env"] = {}
    store.write_text_artifact(
        1,
        "run_manifest.json",
        json.dumps(legacy_manifest, ensure_ascii=False, indent=2),
    )
    pipeline = RoundPipeline(llm=llm, store=store)

    result = pipeline.run(
        project_id="demo",
        round_number=2,
        source_text=HAPPY_SOURCE_TEXT,
        previous_context=previous_context,
        generation_variant=GenerationVariant.CURRENT_DENSITY,
    )

    assert result.story_bible == prior_bible
    assert "StoryBible" not in [
        call["response_model"].__name__ for call in llm.calls
    ]
    assert any(
        stage.name == "story_bible" and stage.status == "cached"
        for stage in result.runtime_report.stages
    )


def test_pipeline_skips_prior_round_story_bible_without_compatible_manifest(
    tmp_path,
    happy_round_outputs,
):
    _, _, prior_bible, _, _, previous_context = happy_round_outputs
    stale_bible = prior_bible.model_copy(update={"mainline": "STALE OLD BIBLE"})
    round_two_outputs = demo_round_outputs(
        round_number=2,
        previous_context=previous_context,
    )
    store = ProjectStore(tmp_path)
    store.write_round_artifact(1, "story_bible", stale_bible)
    llm = RecordingLLM(round_two_outputs)
    pipeline = RoundPipeline(llm=llm, store=store)

    result = pipeline.run(
        project_id="demo",
        round_number=2,
        source_text=HAPPY_SOURCE_TEXT,
        previous_context=previous_context,
        generation_variant=GenerationVariant.CURRENT_DENSITY,
    )

    assert result.story_bible.mainline != "STALE OLD BIBLE"
    assert "StoryBible" in [
        call["response_model"].__name__ for call in llm.calls
    ]
    assert any(
        stage.name == "story_bible" and stage.status == "succeeded"
        for stage in result.runtime_report.stages
    )


def test_pipeline_drama_engine_variant_persists_episode_plan(tmp_path):
    outputs = demo_round_outputs(include_episode_plan=True)
    pipeline = RoundPipeline(llm=StaticJsonLLM(outputs), store=ProjectStore(tmp_path))

    result = pipeline.run(
        project_id="demo",
        round_number=1,
        source_text=HAPPY_SOURCE_TEXT,
        generation_variant=GenerationVariant.DRAMA_ENGINE_FIRST,
    )

    assert result.episode_plan is not None
    assert result.episode_plan.variant == GenerationVariant.DRAMA_ENGINE_FIRST
    assert result.episode_plan.episodes[0].three_pull_beats
    assert (tmp_path / "round_001" / "episode_plan.json").exists()


def test_pipeline_sanitizes_episode_plan_against_source_packets_by_default(
    tmp_path,
    monkeypatch,
):
    monkeypatch.setenv("NOVEL_DRAMA_SOURCE_STRENGTH_COST_CONTROL", "0")
    outputs = demo_round_outputs(include_episode_plan=True)
    source, context, bible, plan, script_batch, quality, next_context = outputs
    plan = plan.model_copy(deep=True)
    script_batch = script_batch.model_copy(deep=True)
    script_batch.episodes[0].scenes[0].lines.insert(
        0,
        SceneLine(
            kind="action",
            text="△特写宴会公开羞辱中，林晚被保安推到门口。",
        ),
    )
    script_batch.episodes[1].scenes[0].lines.insert(
        0,
        SceneLine(
            kind="action",
            text="△特写林婉晴把外卖袋放上餐桌。",
        ),
    )
    first_episode = plan.episodes[0].model_copy(
        update={
            "source_assets_to_keep": [
                "宴会公开羞辱",
                "外卖袋未来资产",
            ],
            "physical_action_chain": [
                "宴会公开羞辱中林晚被推到门口。",
                "林婉晴把外卖袋放上餐桌。",
                "傅盈盈被反手别腕。",
            ],
            "scene_dynamics": [
                "宴会公开羞辱形成压迫。",
                "厨房外卖袋成为反击道具。",
            ],
        },
        deep=True,
    )
    plan = plan.model_copy(update={"episodes": [first_episode, *plan.episodes[1:]]})
    llm = RecordingLLM([source, context, bible, plan, script_batch, quality, next_context])
    pipeline = RoundPipeline(llm=llm, store=ProjectStore(tmp_path))

    grounded_source = "\n\n".join(
        [
            "# 第 1 集\n" + "宴会公开羞辱。林晚被保安推到门口。" * 12,
            "# 第 2 集\n" + "林婉晴把外卖袋放上餐桌。" * 12,
            "# 第 3 集\n" + "林晚回到宴会侧厅核对邀请函碎片。" * 12,
            "# 第 4 集\n" + "顾承在走廊追问老管家旧木盒的来历。" * 12,
            "# 第 5 集\n" + "林雪试图藏起旧照片，林晚当场拦住她。" * 12,
        ]
    )
    result = pipeline.run(
        project_id="demo",
        round_number=1,
        source_text=grounded_source,
        generation_variant=GenerationVariant.DRAMA_ENGINE_FIRST,
        repair_budget="none",
    )

    sanitized_text = (
        tmp_path / "round_001" / "episode_plan_sanitized.json"
    ).read_text(encoding="utf-8")
    assert result.episode_plan is not None
    assert "外卖袋未来资产" not in sanitized_text
    first_episode_text = json.dumps(
        result.episode_plan.episodes[0].model_dump(),
        ensure_ascii=False,
    )
    assert "外卖袋放上餐桌" not in first_episode_text
    assert "反手别腕" not in first_episode_text
    assert "宴会公开羞辱" in sanitized_text


def test_pipeline_sop_full_stack_persists_upstream_plans(tmp_path):
    outputs = demo_round_outputs(include_sop_stack=True, target_episode_count=30)
    pipeline = RoundPipeline(llm=StaticJsonLLM(outputs), store=ProjectStore(tmp_path))

    result = pipeline.run(
        project_id="demo",
        round_number=1,
        source_text=HAPPY_SOURCE_TEXT,
        target_episode_count=30,
        generation_variant=GenerationVariant.SOP_FULL_STACK,
    )

    assert result.viral_asset_report is not None
    assert result.viral_asset_report.signature_scenes
    assert result.series_structure_plan is not None
    assert result.series_structure_plan.target_episode_count == 30
    assert result.series_structure_plan.episode_outlines[0].information_increment
    assert result.episode_plan is not None
    assert result.episode_plan.variant == GenerationVariant.SOP_FULL_STACK
    assert (tmp_path / "round_001" / "viral_asset_report.json").exists()
    assert (tmp_path / "round_001" / "series_structure_plan.json").exists()
    assert (tmp_path / "round_001" / "episode_plan.json").exists()


def test_pipeline_respects_configured_episodes_per_round(tmp_path):
    outputs = demo_round_outputs(
        include_sop_stack=True,
        include_episode_plan=True,
        target_episode_count=30,
        episodes_per_round=2,
    )
    llm = RecordingLLM(outputs)
    pipeline = RoundPipeline(llm=llm, store=ProjectStore(tmp_path))

    result = pipeline.run(
        project_id="demo",
        round_number=1,
        source_text=HAPPY_SOURCE_TEXT,
        target_episode_count=30,
        episodes_per_round=2,
        generation_variant=GenerationVariant.SOP_FULL_STACK,
    )

    episode_context_call = next(
        call for call in llm.calls if call["response_model"].__name__ == "EpisodeContext"
    )
    assert "本轮目标集数：最多 2 集" in episode_context_call["user"]
    assert result.episode_context.target_episode_range == "EP01-EP02"
    assert [episode.episode for episode in result.script_batch.episodes] == [1, 2]
    assert result.next_round_context.current_episode == 2


def test_pipeline_normalizes_malformed_episode_context_range(tmp_path, happy_round_outputs):
    outputs = list(happy_round_outputs)
    outputs[1] = outputs[1].model_copy(
        update={
            "target_episode_range": "1-5",
            "adaptation_actions": ["先写前五集"],
        }
    )
    llm = RecordingLLM(outputs)
    pipeline = RoundPipeline(llm=llm, store=ProjectStore(tmp_path))

    result = pipeline.run(
        project_id="demo",
        round_number=1,
        source_text=HAPPY_SOURCE_TEXT,
        target_episode_count=30,
        generation_variant=GenerationVariant.CURRENT_DENSITY,
    )

    script_call = next(
        call for call in llm.calls if call["response_model"].__name__ == "ScriptBatch"
    )
    artifact_text = (tmp_path / "round_001" / "episode_context.json").read_text(
        encoding="utf-8"
    )
    assert result.episode_context.target_episode_range == "EP01-EP05"
    assert any(
        action.startswith("系统已将本轮集数范围规范为 EP01-EP05")
        for action in result.episode_context.adaptation_actions
    )
    assert '"target_episode_range": "EP01-EP05"' in artifact_text
    assert '"target_episode_range": "EP01-EP05"' in script_call["user"]


def test_quality_checker_keeps_underfilled_script_as_advisory(happy_round_outputs):
    source, context, bible = happy_round_outputs[:3]
    context = context.model_copy(update={"target_episode_range": "EP01-EP01"})
    weak_script = ScriptBatch(
        episodes=[
            EpisodeScript(
                episode=1,
                title="过短脚本",
                hook_3s="她来了。",
                main_emotion="平",
                watch_reason="信息不足。",
                scenes=[
                Scene(
                    heading="1-1 日-内-屋内",
                    characters=["甲", "乙"],
                    lines=[
                        SceneLine(kind="action", text="△甲站着。"),
                        SceneLine(kind="dialogue", speaker="甲", emotion="平", text="你好。"),
                        SceneLine(kind="dialogue", speaker="乙", emotion="平", text="嗯。"),
                        SceneLine(kind="action", text="△乙把门推开一条缝。"),
                    ],
                ),
                Scene(
                    heading="1-2 日-内-屋内门口",
                    characters=["甲", "乙"],
                    lines=[
                        SceneLine(kind="action", text="△甲盯着门缝。"),
                        SceneLine(kind="dialogue", speaker="甲", emotion="疑", text="谁在外面？"),
                        SceneLine(kind="dialogue", speaker="乙", emotion="慌", text="别出声。"),
                        SceneLine(kind="action", text="△门外传来脚步声。"),
                    ],
                )
                ],
                cliffhanger="她来了。",
                state_update={},
            )
        ]
    )
    self_reported_usable = QualityReport(
        status=QualityStatus.USABLE,
        scores=QualityScores(
            hook=9,
            conflict=9,
            cliffhanger=9,
            continuity=9,
            video_feasibility=9,
        ),
        blocking_issues=[],
        rewrite_instruction="",
    )

    report = ContinuityBoomChecker(StaticJsonLLM([self_reported_usable])).run(
        source,
        context,
        bible,
        weak_script,
        None,
    )

    assert report.status == QualityStatus.USABLE
    assert report.blocking_issues == []
    assert any("too short" in issue for issue in report.advisory_warnings)
    assert report.rewrite_instruction == ""


def test_pipeline_default_repair_targets_episode_without_batch_rewrite(
    tmp_path,
    happy_round_outputs,
):
    outputs = list(happy_round_outputs)
    first_script = outputs[3]
    target_line = first_script.episodes[0].scenes[0].lines[0]
    repair_issue = QualityIssue(
        code="STRUCTURE_INVALID",
        severity="hard",
        episode=1,
        scene_id=first_script.episodes[0].scenes[0].scene_id,
        target_ids=[target_line.line_id],
        evidence=[target_line.text],
        message="EP01 contains an exposed analysis line.",
    )
    failed_quality = QualityReport(
        status=QualityStatus.NEEDS_REWRITE,
        scores=QualityScores(
            hook=4,
            conflict=6,
            cliffhanger=5,
            continuity=9,
            video_feasibility=8,
        ),
        blocking_issues=[],
        rewrite_instruction="EP01 只修被点名的可见分析行。",
        issues=[repair_issue],
    )
    allowed_patch = build_current_episode_repair_packet(
        first_script.episodes[0],
        failed_quality.rewrite_instruction,
        quality_issue=repair_issue,
    ).repair_patches[0]
    repair_patch_batch = RepairPatchBatch(
        episode=1,
        patches=[
            allowed_patch.model_copy(
                update={"replacement": "△近景推近林晚攥紧邀请函，指节泛白。"}
            )
        ],
    )
    final_quality = QualityReport(
        status=QualityStatus.USABLE,
        scores=QualityScores(
            hook=9,
            conflict=9,
            cliffhanger=8,
            continuity=10,
            video_feasibility=8,
        ),
        blocking_issues=[],
        rewrite_instruction="",
    )
    outputs = outputs[:4] + [failed_quality, repair_patch_batch, final_quality, outputs[5]]
    llm = RecordingLLM(outputs)
    pipeline = RoundPipeline(llm=llm, store=ProjectStore(tmp_path))

    result = pipeline.run(
        project_id="demo",
        round_number=1,
        source_text=HAPPY_SOURCE_TEXT,
        generation_variant=GenerationVariant.CURRENT_DENSITY,
    )

    script_calls = [
        call
        for call in llm.calls
        if call["response_model"].__name__ == "ScriptBatch"
    ]
    patch_calls = [
        call
        for call in llm.calls
        if call["response_model"].__name__ == "RepairPatchBatch"
    ]
    assert result.script_batch.episodes[0].scenes[0].lines[0].text == "△近景推近林晚攥紧邀请函，指节泛白。"
    assert result.script_batch.episodes[1] == first_script.episodes[1]
    assert result.quality_report.status == QualityStatus.USABLE
    assert len(script_calls) == 1
    assert len(patch_calls) == 1
    assert failed_quality.rewrite_instruction not in script_calls[0]["user"]
    assert repair_issue.message in patch_calls[0]["user"]
    assert "current_episode_repair_packet" in patch_calls[0]["user"]
    assert "当前集旧稿是文本基线" in patch_calls[0]["user"]
    assert "baseline_episode_text" in patch_calls[0]["user"]
    assert "不得输出 EpisodeScript" in patch_calls[0]["user"]
    assert (tmp_path / "round_001" / "quality_report_before_rewrite.json").exists()
    assert (tmp_path / "round_001" / "script_batch_episode_repair.json").exists()
    quality_decision = json.loads(
        (tmp_path / "round_001" / "pre_repair_quality_decision.json").read_text(
            encoding="utf-8"
        )
    )
    repair_patches = json.loads(
        (tmp_path / "round_001" / "repair_patches.json").read_text(
            encoding="utf-8"
        )
    )
    assert quality_decision["repair_targets"] == [1]
    assert repair_patches[0]["episode"] == 1
    repair_packets = json.loads(
        (tmp_path / "round_001" / "current_episode_repair_packets.json").read_text(
            encoding="utf-8"
        )
    )
    assert repair_packets[0]["episode"] == 1
    assert repair_packets[0]["quality_issue"]["scene_id"] == first_script.episodes[0].scenes[0].scene_id
    assert "当前集旧稿是文本基线" in repair_packets[0]["baseline_policy"]
    assert "baseline_episode_text" in repair_packets[0]
    assert not (tmp_path / "round_001" / "script_batch_rewrite.json").exists()


def test_pipeline_limits_each_episode_to_one_patch_batch_when_multiple_hard_issues(
    tmp_path,
    happy_round_outputs,
):
    outputs = list(happy_round_outputs)
    episode = outputs[3].episodes[0]
    first_line = episode.scenes[0].lines[0]
    second_line = episode.scenes[0].lines[1]
    first_issue = QualityIssue(
        code="STRUCTURE_INVALID",
        severity="hard",
        episode=1,
        scene_id=episode.scenes[0].scene_id,
        target_ids=[first_line.line_id],
        evidence=[first_line.text],
        message="EP01 exposes a user-visible analysis line.",
    )
    second_issue = QualityIssue(
        code="CAUSALITY_CONFLICT",
        severity="hard",
        episode=1,
        scene_id=episode.scenes[0].scene_id,
        target_ids=[second_line.line_id],
        evidence=[second_line.text],
        message="EP01 reverses a source-grounded causal action.",
    )
    first_quality = QualityReport(
        status=QualityStatus.NEEDS_REWRITE,
        scores=QualityScores(hook=4, conflict=5, cliffhanger=6, continuity=8, video_feasibility=8),
        blocking_issues=[],
        rewrite_instruction="",
        issues=[first_issue, second_issue],
    )
    patch_batch = _patch_batch_for_issue(
        episode,
        first_issue,
        "△近景推近林晚指节压住邀请函，纸边被攥出褶皱。",
    )
    final_quality = QualityReport(
        status=QualityStatus.USABLE,
        scores=QualityScores(hook=9, conflict=9, cliffhanger=9, continuity=9, video_feasibility=9),
        blocking_issues=[],
        rewrite_instruction="",
    )
    llm = RecordingLLM(outputs[:4] + [first_quality, patch_batch, final_quality, outputs[5]])

    result = RoundPipeline(llm=llm, store=ProjectStore(tmp_path)).run(
        project_id="demo",
        round_number=1,
        source_text=HAPPY_SOURCE_TEXT,
        generation_variant=GenerationVariant.CURRENT_DENSITY,
    )

    assert [
        call["response_model"].__name__ for call in llm.calls
    ].count("RepairPatchBatch") == 1
    assert result.quality_report.status == QualityStatus.NEEDS_HUMAN_REVIEW
    audit = json.loads(
        (tmp_path / "round_001" / "repair_patch_application.json").read_text(
            encoding="utf-8"
        )
    )
    assert audit[0]["accepted"] is True
    assert any("additional structured hard issue" in warning for warning in result.quality_report.advisory_warnings)


def test_pipeline_does_not_cascade_a_patch_into_the_next_episode(
    tmp_path,
    happy_round_outputs,
):
    outputs = list(happy_round_outputs)
    first_episode = outputs[3].episodes[0]
    target_line = first_episode.scenes[-1].lines[-1]
    issue = QualityIssue(
        code="STRUCTURE_INVALID",
        severity="hard",
        episode=1,
        scene_id=first_episode.scenes[-1].scene_id,
        target_ids=[target_line.line_id],
        evidence=[target_line.text],
        message="EP01 final action exposes production metadata.",
    )
    first_quality = QualityReport(
        status=QualityStatus.NEEDS_REWRITE,
        scores=QualityScores(hook=4, conflict=6, cliffhanger=5, continuity=8, video_feasibility=8),
        blocking_issues=[],
        rewrite_instruction="",
        issues=[issue],
    )
    patch_batch = _patch_batch_for_issue(
        first_episode,
        issue,
        "△特写门把手缓缓转动，门外的人停在阴影里。",
    )
    final_quality = QualityReport(
        status=QualityStatus.USABLE,
        scores=QualityScores(hook=9, conflict=9, cliffhanger=9, continuity=9, video_feasibility=9),
        blocking_issues=[],
        rewrite_instruction="",
    )
    llm = RecordingLLM(outputs[:4] + [first_quality, patch_batch, final_quality, outputs[5]])

    RoundPipeline(llm=llm, store=ProjectStore(tmp_path)).run(
        project_id="demo",
        round_number=1,
        source_text=HAPPY_SOURCE_TEXT,
        generation_variant=GenerationVariant.CURRENT_DENSITY,
    )

    assert [
        call["response_model"].__name__ for call in llm.calls
    ].count("RepairPatchBatch") == 1
    packets = json.loads(
        (tmp_path / "round_001" / "current_episode_repair_packets.json").read_text(
            encoding="utf-8"
        )
    )
    assert [packet["episode"] for packet in packets] == [1]


def test_pipeline_rejected_patch_keeps_baseline_and_writes_audit(
    tmp_path,
    happy_round_outputs,
):
    outputs = list(happy_round_outputs)
    episode = outputs[3].episodes[0]
    target_line = episode.scenes[0].lines[0]
    issue = QualityIssue(
        code="STRUCTURE_INVALID",
        severity="hard",
        episode=1,
        scene_id=episode.scenes[0].scene_id,
        target_ids=[target_line.line_id],
        evidence=[target_line.text],
        message="EP01 contains a malformed visible action line.",
    )
    first_quality = QualityReport(
        status=QualityStatus.NEEDS_REWRITE,
        scores=QualityScores(hook=4, conflict=6, cliffhanger=5, continuity=8, video_feasibility=8),
        blocking_issues=[],
        rewrite_instruction="",
        issues=[issue],
    )
    final_quality = QualityReport(
        status=QualityStatus.USABLE,
        scores=QualityScores(hook=9, conflict=9, cliffhanger=9, continuity=9, video_feasibility=9),
        blocking_issues=[],
        rewrite_instruction="",
    )
    llm = RecordingLLM(
        outputs[:4]
        + [first_quality, RepairPatchBatch(episode=1, patches=[]), final_quality, outputs[5]]
    )

    result = RoundPipeline(llm=llm, store=ProjectStore(tmp_path)).run(
        project_id="demo",
        round_number=1,
        source_text=HAPPY_SOURCE_TEXT,
        generation_variant=GenerationVariant.CURRENT_DENSITY,
    )

    assert result.script_batch.episodes[0] == episode
    assert result.quality_report.status == QualityStatus.NEEDS_HUMAN_REVIEW
    audit = json.loads(
        (tmp_path / "round_001" / "repair_patch_application.json").read_text(
            encoding="utf-8"
        )
    )
    assert audit[0]["accepted"] is False
    assert audit[0]["rejections"] == ["repair model returned no patches"]


@pytest.mark.skip(reason="Superseded by node-scoped RepairPatch protocol; free-text intent drift cannot trigger an EpisodeScript rewrite.")
def test_pipeline_pre_adaptation_gate_rewrites_source_intent_drift(
    tmp_path,
    happy_round_outputs,
):
    outputs = list(happy_round_outputs)
    source_analysis = outputs[0].model_copy(
        update={"candidate_hooks": [], "visual_moments": []}
    )
    episode_context = outputs[1].model_copy(
        update={
            "target_episode_range": "EP01-EP01",
            "source_to_episode_mapping": [],
            "forbidden_reveals": [],
        }
    )
    story_bible = outputs[2].model_copy(
        update={"immutable_facts": [], "forbidden_changes": []}
    )
    drift_episode = outputs[3].episodes[0].model_copy(deep=True)
    repaired_episode = outputs[3].episodes[0].model_copy(deep=True)
    drift_episode.scenes[0].lines[1].text = "你答应过我的影后呢？"
    repaired_episode.scenes[0].lines[1].text = "你给我的惊喜，是她？"
    first_script = ScriptBatch(episodes=[drift_episode])
    self_reported_usable = QualityReport(
        status=QualityStatus.USABLE,
        scores=QualityScores(
            hook=9,
            conflict=9,
            cliffhanger=9,
            continuity=9,
            video_feasibility=9,
        ),
        blocking_issues=[],
        rewrite_instruction="",
    )
    final_quality = QualityReport(
        status=QualityStatus.USABLE,
        scores=QualityScores(
            hook=9,
            conflict=9,
            cliffhanger=9,
            continuity=9,
            video_feasibility=9,
        ),
        blocking_issues=[],
        rewrite_instruction="",
    )
    next_context = outputs[5].model_copy(update={"current_episode": 1})
    llm = RecordingLLM(
        [
            source_analysis,
            episode_context,
            story_bible,
            first_script,
            self_reported_usable,
            repaired_episode,
            final_quality,
            next_context,
        ]
    )
    pipeline = RoundPipeline(llm=llm, store=ProjectStore(tmp_path))

    result = pipeline.run(
        project_id="demo",
        round_number=1,
        source_text=(
            "颁奖礼暗处，路淮北低声说：给你准备了惊喜。林挽清只是僵住，没有追问。\n"
            + HAPPY_SOURCE_TEXT
        ),
        target_episode_count=1,
        generation_variant=GenerationVariant.CURRENT_DENSITY,
    )

    script_calls = [
        call
        for call in llm.calls
        if call["response_model"].__name__ == "ScriptBatch"
    ]
    episode_calls = [
        call
        for call in llm.calls
        if call["response_model"].__name__ == "EpisodeScript"
    ]
    assert len(script_calls) == 1
    assert len(episode_calls) == 1
    assert result.script_batch.episodes[0].scenes[0].lines[1].text == "你给我的惊喜，是她？"
    assert "主动索取" in episode_calls[0]["user"]
    assert "改编一致性阻断" in episode_calls[0]["user"]
    assert (tmp_path / "round_001" / "pre_repair_adaptation_quality.json").exists()
    assert (tmp_path / "round_001" / "quality_report_before_rewrite.json").exists()


@pytest.mark.skip(reason="Superseded by node-scoped RepairPatch protocol; free-text batch findings cannot trigger EpisodeScript rewrites.")
def test_pipeline_episode_first_skips_batch_rewrite_and_repairs_by_episode(
    tmp_path,
    happy_round_outputs,
    monkeypatch,
):
    monkeypatch.setenv("NOVEL_DRAMA_SCRIPT_EPISODE_FIRST", "1")
    outputs = list(happy_round_outputs)
    source, context, bible, first_script, _, next_context = outputs[:6]
    first_quality = QualityReport(
        status=QualityStatus.NEEDS_REWRITE,
        scores=QualityScores(
            hook=4,
            conflict=6,
            cliffhanger=5,
            continuity=9,
            video_feasibility=8,
        ),
        blocking_issues=["EP01-EP05 原文事实偏离：关键事件顺序错误"],
        rewrite_instruction="按逐集模式恢复 EP01-EP05 的原文事件顺序。",
    )
    final_quality = QualityReport(
        status=QualityStatus.USABLE,
        scores=QualityScores(
            hook=9,
            conflict=9,
            cliffhanger=9,
            continuity=9,
            video_feasibility=9,
        ),
        blocking_issues=[],
        rewrite_instruction="",
    )
    llm = RecordingLLM(
        [source, context, bible]
        + first_script.episodes
        + [first_quality]
        + first_script.episodes
        + [final_quality, next_context]
    )
    pipeline = RoundPipeline(llm=llm, store=ProjectStore(tmp_path))

    result = pipeline.run(
        project_id="demo",
        round_number=1,
        source_text=HAPPY_SOURCE_TEXT,
        generation_variant=GenerationVariant.CURRENT_DENSITY,
    )

    script_calls = [
        call
        for call in llm.calls
        if call["response_model"].__name__ == "ScriptBatch"
    ]
    episode_calls = [
        call
        for call in llm.calls
        if call["response_model"].__name__ == "EpisodeScript"
    ]
    assert result.quality_report.status == QualityStatus.USABLE
    assert script_calls == []
    assert len(episode_calls) == 10
    assert (tmp_path / "round_001" / "quality_report_before_rewrite.json").exists()
    assert (tmp_path / "round_001" / "quality_report_before_episode_repair.json").exists()
    assert (tmp_path / "round_001" / "script_batch_episode_repair.json").exists()
    assert not (tmp_path / "round_001" / "script_batch_rewrite.json").exists()


def test_pipeline_strong_source_cost_control_blocks_fallback_repair(tmp_path):
    outputs = demo_round_outputs(include_sop_stack=True)
    source = outputs[0]
    viral_asset_report = outputs[1]
    context = outputs[2]
    bible = outputs[3]
    series_structure_plan = outputs[4]
    episode_plan = outputs[5]
    first_script = outputs[6]
    next_context = outputs[8]
    first_quality = QualityReport(
        status=QualityStatus.NEEDS_REWRITE,
        scores=QualityScores(
            hook=6,
            conflict=8,
            cliffhanger=8,
            continuity=9,
            video_feasibility=8,
        ),
        blocking_issues=["整体仍可加强，但没有明确失败集。"],
        rewrite_instruction="增强镜头和情绪，不要改变原文核心因果。",
    )
    llm = RecordingLLM(
        [
            source,
            viral_asset_report,
            context,
            bible,
            series_structure_plan,
            episode_plan,
            first_script,
            first_quality,
            next_context,
        ]
    )
    pipeline = RoundPipeline(llm=llm, store=ProjectStore(tmp_path))

    result = pipeline.run(
        project_id="demo",
        round_number=1,
        source_text=(
            "林晚在颁奖礼被公开羞辱，早已准备好解约协议。\n"
            + HAPPY_SOURCE_TEXT
        ),
        generation_variant=GenerationVariant.SOP_FULL_STACK,
        repair_budget="rewrite",
    )

    script_calls = [
        call
        for call in llm.calls
        if call["response_model"].__name__ == "ScriptBatch"
    ]
    episode_calls = [
        call
        for call in llm.calls
        if call["response_model"].__name__ == "EpisodeScript"
    ]
    decision = (tmp_path / "round_001" / "cost_control_decision.json").read_text(
        encoding="utf-8"
    )
    assert result.quality_report.status == QualityStatus.USABLE
    assert result.runtime_report.repair_budget == RepairBudget.EPISODE
    assert len(script_calls) == 1
    assert episode_calls == []
    assert "strong_source_light_adaptation" in decision
    assert "script_batch_rewrite" not in {
        stage.name for stage in result.runtime_report.stages
    }
    assert not (tmp_path / "round_001" / "episode_repair_targets.md").exists()
    assert not (tmp_path / "round_001" / "script_batch_rewrite.json").exists()
    assert not (tmp_path / "round_001" / "script_batch_episode_repair.json").exists()


@pytest.mark.skip(reason="Replaced by structured unscoped QualityIssue coverage.")
def test_pipeline_marks_unscoped_hard_issue_for_human_review_without_repair(
    tmp_path,
    happy_round_outputs,
):
    outputs = list(happy_round_outputs)
    unscoped_hard_issue = QualityReport(
        status=QualityStatus.NEEDS_REWRITE,
        scores=QualityScores(
            hook=6,
            conflict=8,
            cliffhanger=8,
            continuity=8,
            video_feasibility=8,
        ),
        blocking_issues=["source_evidence: 原文关键资产未落到正片，但未定位具体集数"],
        rewrite_instruction="先由人工定位受影响集数，禁止猜测性重写。",
    )
    llm = RecordingLLM(outputs[:4] + [unscoped_hard_issue])
    pipeline = RoundPipeline(llm=llm, store=ProjectStore(tmp_path))

    result = pipeline.run(
        project_id="demo",
        round_number=1,
        source_text=HAPPY_SOURCE_TEXT,
        repair_budget="episode",
        generation_variant=GenerationVariant.CURRENT_DENSITY,
    )

    episode_repair_calls = [
        call
        for call in llm.calls
        if call["response_model"].__name__ == "EpisodeScript"
    ]
    assert result.quality_report.status == QualityStatus.NEEDS_HUMAN_REVIEW
    assert episode_repair_calls == []
    assert (tmp_path / "round_001" / "episode_repair_targets.md").read_text(
        encoding="utf-8"
    ).startswith("none")
    assert not (tmp_path / "round_001" / "script_batch_episode_repair.json").exists()


@pytest.mark.skip(reason="Superseded by typed QualityIssue scope tests; a named string is not an authorized Patch scope.")
def test_pipeline_strong_source_cost_control_repairs_named_episode_only(tmp_path):
    outputs = demo_round_outputs(include_sop_stack=True)
    source = outputs[0]
    viral_asset_report = outputs[1]
    context = outputs[2]
    bible = outputs[3]
    series_structure_plan = outputs[4]
    episode_plan = outputs[5]
    first_script = outputs[6]
    repaired_episode = first_script.episodes[0].model_copy(
        deep=True,
        update={"title": "被赶出生日宴，只修第一集"},
    )
    final_quality = QualityReport(
        status=QualityStatus.USABLE,
        scores=QualityScores(
            hook=9,
            conflict=9,
            cliffhanger=9,
            continuity=9,
            video_feasibility=8,
        ),
        blocking_issues=[],
        rewrite_instruction="",
    )
    next_context = outputs[8]
    first_quality = QualityReport(
        status=QualityStatus.NEEDS_REWRITE,
        scores=QualityScores(
            hook=6,
            conflict=8,
            cliffhanger=8,
            continuity=9,
            video_feasibility=8,
        ),
        blocking_issues=["EP01 原文事实偏离：主角提前知道秘密。"],
        rewrite_instruction="只修 EP01 的人物知识状态，其余集保持原文因果。",
    )
    llm = RecordingLLM(
        [
            source,
            viral_asset_report,
            context,
            bible,
            series_structure_plan,
            episode_plan,
            first_script,
            first_quality,
            repaired_episode,
            final_quality,
            next_context,
        ]
    )
    pipeline = RoundPipeline(llm=llm, store=ProjectStore(tmp_path))

    result = pipeline.run(
        project_id="demo",
        round_number=1,
        source_text=(
            "林晚在颁奖礼被公开羞辱，早已准备好解约协议。\n"
            + HAPPY_SOURCE_TEXT
        ),
        generation_variant=GenerationVariant.SOP_FULL_STACK,
        repair_budget="episode",
    )

    episode_calls = [
        call
        for call in llm.calls
        if call["response_model"].__name__ == "EpisodeScript"
    ]
    target_text = (tmp_path / "round_001" / "episode_repair_targets.md").read_text(
        encoding="utf-8"
    )

    assert result.quality_report.status == QualityStatus.USABLE
    assert len(episode_calls) == 1
    assert "只修第一集" in result.script_batch.episodes[0].title
    assert result.script_batch.episodes[1] == first_script.episodes[1]
    assert target_text == "EP01"
    assert not (tmp_path / "round_001" / "script_batch_rewrite.json").exists()


@pytest.mark.skip(reason="Superseded by one PatchBatch-per-episode coverage.")
def test_pipeline_escalates_second_rewrite_to_human_review(
    tmp_path,
    happy_round_outputs,
):
    outputs = list(happy_round_outputs)
    first_script = outputs[3]
    repaired_episode = first_script.episodes[0].model_copy(deep=True)
    first_quality = QualityReport(
        status=QualityStatus.NEEDS_REWRITE,
        scores=QualityScores(
            hook=3,
            conflict=5,
            cliffhanger=4,
            continuity=9,
            video_feasibility=8,
        ),
        blocking_issues=["EP01 原文事实偏离：主动方被改错。"],
        rewrite_instruction="只修 EP01 的主动方和人物知识状态。",
    )
    second_quality = QualityReport(
        status=QualityStatus.NEEDS_REWRITE,
        scores=QualityScores(
            hook=5,
            conflict=6,
            cliffhanger=5,
            continuity=9,
            video_feasibility=8,
        ),
        blocking_issues=["EP01 原文事实偏离仍未修复。"],
        rewrite_instruction="需要人工重构。",
    )
    llm = RecordingLLM(
        outputs[:4] + [first_quality, repaired_episode, second_quality, outputs[5]]
    )
    pipeline = RoundPipeline(llm=llm, store=ProjectStore(tmp_path))

    result = pipeline.run(
        project_id="demo",
        round_number=1,
        source_text=HAPPY_SOURCE_TEXT,
        target_episode_count=1,
        episodes_per_round=1,
        repair_budget="episode",
        generation_variant=GenerationVariant.CURRENT_DENSITY,
    )

    script_calls = [
        call
        for call in llm.calls
        if call["response_model"].__name__ == "ScriptBatch"
    ]
    episode_repair_calls = [
        call
        for call in llm.calls
        if call["response_model"].__name__ == "EpisodeScript"
    ]
    quality_path = tmp_path / "round_001" / "quality_report.json"
    assert result.quality_report.status == QualityStatus.NEEDS_HUMAN_REVIEW
    assert len(script_calls) == 1
    assert len(episode_repair_calls) == 1
    assert "needs_human_review" in quality_path.read_text(encoding="utf-8")
    assert (tmp_path / "round_001" / "round_result.json").exists()
    assert not (tmp_path / "round_001" / "next_round_context.json").exists()
    assert "NextRoundContext" not in [
        call["response_model"].__name__ for call in llm.calls
    ]
    assert (tmp_path / "round_001" / "quality_report_before_episode_repair.json").exists()
    assert (tmp_path / "round_001" / "script_batch_episode_repair.json").exists()


@pytest.mark.skip(reason="Superseded by structured QualityIssue target coverage.")
def test_pipeline_episode_repair_targets_reported_episode_only(
    tmp_path,
    happy_round_outputs,
):
    outputs = list(happy_round_outputs)
    first_script = outputs[3]
    repaired_episode = first_script.episodes[0].model_copy(
        deep=True,
        update={"title": "定向修复第一集"},
    )
    first_quality = QualityReport(
        status=QualityStatus.NEEDS_REWRITE,
        scores=QualityScores(
            hook=3,
            conflict=5,
            cliffhanger=4,
            continuity=9,
            video_feasibility=8,
        ),
        blocking_issues=["EP01 原文事实偏离：主动方被改错"],
        rewrite_instruction="只修 EP01 的主动方，其他集保持边界不变。",
    )
    final_quality = QualityReport(
        status=QualityStatus.USABLE,
        scores=QualityScores(
            hook=9,
            conflict=9,
            cliffhanger=9,
            continuity=9,
            video_feasibility=8,
        ),
        blocking_issues=[],
        rewrite_instruction="",
    )
    llm = RecordingLLM(outputs[:4] + [first_quality, repaired_episode, final_quality, outputs[5]])
    pipeline = RoundPipeline(llm=llm, store=ProjectStore(tmp_path))

    result = pipeline.run(
        project_id="demo",
        round_number=1,
        source_text=HAPPY_SOURCE_TEXT,
        repair_budget="episode",
        generation_variant=GenerationVariant.CURRENT_DENSITY,
    )

    episode_repair_calls = [
        call
        for call in llm.calls
        if call["response_model"].__name__ == "EpisodeScript"
    ]
    target_text = (tmp_path / "round_001" / "episode_repair_targets.md").read_text(
        encoding="utf-8"
    )
    assert len(episode_repair_calls) == 1
    assert result.script_batch.episodes[0].title == "定向修复第一集"
    assert result.script_batch.episodes[1] == first_script.episodes[1]
    assert target_text == "EP01"


@pytest.mark.skip(reason="Phase 2 owns cross-episode cascade repair; Phase 1 intentionally does not auto-patch the next episode.")
def test_pipeline_repairs_only_next_opening_when_prior_handoff_changes(
    tmp_path,
    happy_round_outputs,
):
    outputs = list(happy_round_outputs)
    first_script = outputs[3]
    repaired_first_episode = first_script.episodes[0].model_copy(
        deep=True,
        update={"cliffhanger": "△门外的人抬手敲响。"},
    )
    repaired_first_episode.scenes[-1].lines[-1].text = "△门外的人抬手敲响。"
    first_quality = QualityReport(
        status=QualityStatus.NEEDS_REWRITE,
        scores=QualityScores(
            hook=5,
            conflict=7,
            cliffhanger=7,
            continuity=9,
            video_feasibility=8,
        ),
        blocking_issues=["EP01 原文事实偏离：主动方被改错。"],
        rewrite_instruction="只修 EP01 的主动方，不得改动其他集。",
    )
    final_quality = QualityReport(
        status=QualityStatus.USABLE,
        scores=QualityScores(
            hook=9,
            conflict=9,
            cliffhanger=9,
            continuity=9,
            video_feasibility=9,
        ),
        blocking_issues=[],
        rewrite_instruction="",
    )
    llm = RecordingLLM(
        outputs[:4]
        + [
            first_quality,
            repaired_first_episode,
            first_script.episodes[1],
            final_quality,
            outputs[5],
        ]
    )
    pipeline = RoundPipeline(llm=llm, store=ProjectStore(tmp_path))

    result = pipeline.run(
        project_id="demo",
        round_number=1,
        source_text=HAPPY_SOURCE_TEXT,
        repair_budget="episode",
        generation_variant=GenerationVariant.CURRENT_DENSITY,
    )

    episode_calls = [
        call
        for call in llm.calls
        if call["response_model"].__name__ == "EpisodeScript"
    ]
    packets = json.loads(
        (tmp_path / "round_001" / "current_episode_repair_packets.json").read_text(
            encoding="utf-8"
        )
    )
    assert result.quality_report.status == QualityStatus.USABLE
    assert len(episode_calls) == 2
    assert "修复级别：跨集承接开场局部修复" in episode_calls[1]["user"]
    assert packets[1]["episode"] == 2
    assert packets[1]["repair_mode"] == "handoff_patch"
    assert "第一场前 8-12 行" in packets[1]["allowed_change_scope"]


@pytest.mark.skip(reason="Superseded by Patch application rejection coverage; repair no longer accepts an episode candidate.")
def test_pipeline_rejects_catastrophically_short_episode_repair_candidate(
    tmp_path,
    happy_round_outputs,
):
    outputs = list(happy_round_outputs)
    first_script = outputs[3]
    collapsed_episode = first_script.episodes[0].model_copy(
        deep=True,
        update={
            "scenes": [
                Scene(
                    heading="1-1 夜-内-温家走廊",
                    characters=["林晚", "温舟"],
                    lines=[
                        SceneLine(kind="action", text="△中景推近林晚。"),
                        SceneLine(kind="dialogue", speaker="林晚", text="让开。"),
                        SceneLine(kind="dialogue", speaker="温舟", text="不行。"),
                    ],
                )
            ],
            "cliffhanger": "让开。",
        },
    )
    first_quality = QualityReport(
        status=QualityStatus.NEEDS_REWRITE,
        scores=QualityScores(
            hook=4,
            conflict=5,
            cliffhanger=4,
            continuity=8,
            video_feasibility=8,
        ),
        blocking_issues=["EP01 原文事实偏离：主角提前知道秘密"],
        rewrite_instruction="只修 EP01 的人物知识状态。",
    )
    final_quality = QualityReport(
        status=QualityStatus.USABLE,
        scores=QualityScores(
            hook=9,
            conflict=9,
            cliffhanger=9,
            continuity=9,
            video_feasibility=9,
        ),
        blocking_issues=[],
        rewrite_instruction="",
    )
    llm = RecordingLLM(
        outputs[:4] + [first_quality, collapsed_episode, final_quality, outputs[5]]
    )
    pipeline = RoundPipeline(llm=llm, store=ProjectStore(tmp_path))

    result = pipeline.run(
        project_id="demo",
        round_number=1,
        source_text=HAPPY_SOURCE_TEXT,
        repair_budget="episode",
        generation_variant=GenerationVariant.CURRENT_DENSITY,
    )

    assert result.script_batch.episodes[0] == first_script.episodes[0]
    assert (tmp_path / "round_001" / "episode_revision_rejections.md").exists()
    repair_diffs = json.loads(
        (tmp_path / "round_001" / "repair_diff.json").read_text(encoding="utf-8")
    )
    assert repair_diffs[0]["accepted"] is False


def test_pipeline_retry_keeps_persisted_episode_when_new_first_draft_collapses(
    tmp_path,
    happy_round_outputs,
    monkeypatch,
):
    monkeypatch.setenv("NOVEL_DRAMA_RESUME_ARTIFACTS", "0")
    source, context, bible, scripts, quality, next_context = happy_round_outputs
    context = context.model_copy(
        deep=True,
        update={"target_episode_range": "EP01-EP01"},
    )
    persisted_episode = scripts.episodes[0]
    collapsed_episode = persisted_episode.model_copy(
        deep=True,
        update={
            "scenes": [
                Scene(
                    heading="1-1 夜-内-温家走廊",
                    characters=["林晚", "温舟"],
                    lines=[
                        SceneLine(kind="action", text="△中景推近林晚。"),
                        SceneLine(kind="dialogue", speaker="林晚", text="让开。"),
                        SceneLine(kind="dialogue", speaker="温舟", text="不行。"),
                    ],
                )
            ],
        },
    )
    collapsed_batch = ScriptBatch(episodes=[collapsed_episode])
    llm = RecordingLLM(
        [source, context, bible, collapsed_batch, quality, next_context]
    )
    store = ProjectStore(tmp_path)
    manifest = build_run_manifest(
        project_id="demo",
        round_number=1,
        source_text=HAPPY_SOURCE_TEXT,
        target_episode_count=1,
        episodes_per_round=1,
        generation_variant=GenerationVariant.CURRENT_DENSITY,
        repair_budget=RepairBudget.NONE,
        llm=llm,
        methodology_cards_path=None,
    )
    store.write_text_artifact(
        1,
        "run_manifest.json",
        json.dumps(manifest, ensure_ascii=False, indent=2),
    )
    store.write_round_artifact(1, "episode_001", persisted_episode)
    pipeline = RoundPipeline(llm=llm, store=store)

    result = pipeline.run(
        project_id="demo",
        round_number=1,
        source_text=HAPPY_SOURCE_TEXT,
        target_episode_count=1,
        episodes_per_round=1,
        repair_budget="none",
        generation_variant=GenerationVariant.CURRENT_DENSITY,
    )

    assert result.script_batch.episodes[0] == persisted_episode
    assert (
        tmp_path / "round_001" / "script_batch_generation_rejections.md"
    ).exists()


def test_quality_instruction_for_episode_excludes_other_episode_and_unscoped_failures():
    quality_report = QualityReport(
        status=QualityStatus.NEEDS_REWRITE,
        scores=QualityScores(
            hook=4,
            conflict=5,
            cliffhanger=4,
            continuity=8,
            video_feasibility=8,
        ),
        blocking_issues=[
            "EP01 too short: 664 chars, expected >= 800",
            "EP02 has non-shooting scene headings: 2-1 白-内-林挽清公寓",
            "source_evidence: EP05 缺少原文资产：雪地烟火激吻",
            "source_asset_preservation：恢复原文强冲突、关键情绪和不可改事实。",
        ],
        rewrite_instruction=(
            "方法论阻断：本素材被判定为强原文，只允许轻改；"
            "EP01 has 8 action lines, expected >= 10；"
            "EP02 too short: 660 chars, expected >= 800；"
            "The provided scripts accurately map to the source. No blocking issues detected."
        ),
    )

    scoped = quality_instruction_for_episode(quality_report, 1)

    assert "方法论阻断" not in scoped
    assert "source_asset_preservation" not in scoped
    assert "EP01 too short" in scoped
    assert "EP01 has 8 action lines" in scoped
    assert "EP02" not in scoped
    assert "EP05" not in scoped
    assert "雪地烟火激吻" not in scoped
    assert "No blocking issues detected" not in scoped


@pytest.mark.skip(reason="Superseded by one PatchBatch-per-episode coverage.")
def test_pipeline_runs_at_most_one_repair_pass(
    tmp_path,
    happy_round_outputs,
):
    outputs = list(happy_round_outputs)
    first_script = outputs[3]
    bad_episode = first_script.episodes[0].model_copy(deep=True)
    bad_episode.cliffhanger = "明天再说。"
    bad_episode.scenes[-1].lines[-2:] = [
        SceneLine(kind="dialogue", speaker="林晚", text="明天再说。"),
        SceneLine(kind="action", text="△中景林晚转身离开。"),
    ]
    first_quality = QualityReport(
        status=QualityStatus.NEEDS_REWRITE,
        scores=QualityScores(
            hook=3,
            conflict=5,
            cliffhanger=4,
            continuity=9,
            video_feasibility=8,
        ),
        blocking_issues=["EP01 原文事实偏离：主动方被改错。"],
        rewrite_instruction="只修 EP01 的主动方和人物知识状态。",
    )
    final_quality = QualityReport(
        status=QualityStatus.USABLE,
        scores=QualityScores(
            hook=9,
            conflict=9,
            cliffhanger=9,
            continuity=9,
            video_feasibility=8,
        ),
        blocking_issues=[],
        rewrite_instruction="",
    )
    llm = RecordingLLM(
        outputs[:4] + [first_quality, bad_episode, final_quality, outputs[5]]
    )
    pipeline = RoundPipeline(llm=llm, store=ProjectStore(tmp_path))

    result = pipeline.run(
        project_id="demo",
        round_number=1,
        source_text=HAPPY_SOURCE_TEXT,
        target_episode_count=1,
        episodes_per_round=1,
        repair_budget="episode",
        generation_variant=GenerationVariant.CURRENT_DENSITY,
    )

    episode_repair_calls = [
        call
        for call in llm.calls
        if call["response_model"].__name__ == "EpisodeScript"
    ]
    assert result.quality_report.status in {
        QualityStatus.USABLE,
        QualityStatus.NEEDS_HUMAN_REVIEW,
    }
    assert len(episode_repair_calls) == 1
    assert not (tmp_path / "round_001" / "script_batch_episode_polish.json").exists()
    assert not (tmp_path / "round_001" / "episode_polish_instructions.md").exists()


@pytest.mark.skip(reason="Superseded by one PatchBatch-per-episode coverage.")
def test_pipeline_does_not_run_a_second_automatic_repair_pass(
    tmp_path,
    happy_round_outputs,
):
    outputs = list(happy_round_outputs)
    first_script = outputs[3]
    bad_episode = first_script.episodes[0].model_copy(deep=True)
    bad_episode.cliffhanger = "明天再说。"
    bad_episode.scenes[-1].lines[-2:] = [
        SceneLine(kind="dialogue", speaker="林晚", text="明天再说。"),
        SceneLine(kind="action", text="△中景林晚转身离开。"),
    ]
    first_quality = QualityReport(
        status=QualityStatus.NEEDS_REWRITE,
        scores=QualityScores(
            hook=3,
            conflict=5,
            cliffhanger=4,
            continuity=9,
            video_feasibility=8,
        ),
        blocking_issues=["EP01 原文事实偏离：主动方被改错。"],
        rewrite_instruction="只修 EP01 的主动方和人物知识状态。",
    )
    final_quality = QualityReport(
        status=QualityStatus.USABLE,
        scores=QualityScores(
            hook=9,
            conflict=9,
            cliffhanger=9,
            continuity=9,
            video_feasibility=8,
        ),
        blocking_issues=[],
        rewrite_instruction="",
    )
    llm = RecordingLLM(outputs[:4] + [first_quality, bad_episode, final_quality, outputs[5]])
    pipeline = RoundPipeline(llm=llm, store=ProjectStore(tmp_path))

    result = pipeline.run(
        project_id="demo",
        round_number=1,
        source_text=HAPPY_SOURCE_TEXT,
        target_episode_count=1,
        episodes_per_round=1,
        repair_budget="episode",
        generation_variant=GenerationVariant.CURRENT_DENSITY,
    )

    episode_repair_calls = [
        call
        for call in llm.calls
        if call["response_model"].__name__ == "EpisodeScript"
    ]
    assert len(episode_repair_calls) == 1
    assert "episode_quality_polish" not in {
        stage.name for stage in result.runtime_report.stages
    }
    assert not (tmp_path / "round_001" / "episode_polish_instructions.md").exists()
    assert not (tmp_path / "round_001" / "script_batch_episode_polish.json").exists()


@pytest.mark.skip(reason="Superseded by constrained Patch application coverage.")
def test_pipeline_keeps_the_single_repair_result_without_extra_compilation(
    tmp_path,
    happy_round_outputs,
):
    outputs = list(happy_round_outputs)
    first_script = outputs[3]
    bad_episode = first_script.episodes[0].model_copy(deep=True)
    bad_episode.cliffhanger = "明天再说。"
    bad_episode.scenes[-1].lines[-2:] = [
        SceneLine(kind="dialogue", speaker="林晚", text="明天再说。"),
        SceneLine(kind="action", text="△中景林晚转身离开。"),
    ]
    first_quality = QualityReport(
        status=QualityStatus.NEEDS_REWRITE,
        scores=QualityScores(
            hook=3,
            conflict=5,
            cliffhanger=4,
            continuity=9,
            video_feasibility=8,
        ),
        blocking_issues=["EP01 原文事实偏离：主动方被改错。"],
        rewrite_instruction="只修 EP01 的主动方和人物知识状态。",
    )
    final_quality = QualityReport(
        status=QualityStatus.USABLE,
        scores=QualityScores(
            hook=9,
            conflict=9,
            cliffhanger=9,
            continuity=9,
            video_feasibility=8,
        ),
        blocking_issues=[],
        rewrite_instruction="",
    )
    llm = RecordingLLM(
        outputs[:4] + [first_quality, bad_episode, final_quality, outputs[5]]
    )
    pipeline = RoundPipeline(llm=llm, store=ProjectStore(tmp_path))

    result = pipeline.run(
        project_id="demo",
        round_number=1,
        source_text=HAPPY_SOURCE_TEXT,
        target_episode_count=1,
        episodes_per_round=1,
        repair_budget="episode",
        generation_variant=GenerationVariant.CURRENT_DENSITY,
    )

    assert result.quality_report.status in {
        QualityStatus.USABLE,
        QualityStatus.NEEDS_HUMAN_REVIEW,
    }
    assert result.script_batch.episodes[0] == bad_episode
    assert not (tmp_path / "round_001" / "script_batch_episode_polish.json").exists()
    assert not (tmp_path / "round_001" / "script_batch_hook_dialogue_polish.json").exists()


@pytest.mark.skip(reason="Superseded by constrained Patch application coverage.")
def test_pipeline_does_not_automatically_recompile_hook_or_dialogue_after_repair(
    tmp_path,
    happy_round_outputs,
):
    outputs = list(happy_round_outputs)
    first_script = outputs[3]
    soft_tail_episode = first_script.episodes[0].model_copy(deep=True)
    soft_tail_episode.cliffhanger = "明天再说。"
    soft_tail_episode.scenes[-1].lines[-2:] = [
        SceneLine(kind="dialogue", speaker="林晚", text="明天再说。"),
        SceneLine(kind="action", text="△中景林晚转身离开。"),
    ]
    first_quality = QualityReport(
        status=QualityStatus.NEEDS_REWRITE,
        scores=QualityScores(
            hook=3,
            conflict=5,
            cliffhanger=4,
            continuity=9,
            video_feasibility=8,
        ),
        blocking_issues=["EP01 原文事实偏离：主动方被改错。"],
        rewrite_instruction="只修 EP01 的主动方和人物知识状态。",
    )
    final_quality = QualityReport(
        status=QualityStatus.USABLE,
        scores=QualityScores(
            hook=9,
            conflict=9,
            cliffhanger=9,
            continuity=9,
            video_feasibility=8,
        ),
        blocking_issues=[],
        rewrite_instruction="",
    )
    llm = RecordingLLM(
        outputs[:4] + [first_quality, soft_tail_episode, final_quality, outputs[5]]
    )
    pipeline = RoundPipeline(llm=llm, store=ProjectStore(tmp_path))

    result = pipeline.run(
        project_id="demo",
        round_number=1,
        source_text=HAPPY_SOURCE_TEXT,
        target_episode_count=1,
        episodes_per_round=1,
        repair_budget="episode",
        generation_variant=GenerationVariant.CURRENT_DENSITY,
    )

    episode_calls = [
        call
        for call in llm.calls
        if call["response_model"].__name__ == "EpisodeScript"
    ]
    assert result.quality_report.status in {
        QualityStatus.USABLE,
        QualityStatus.NEEDS_HUMAN_REVIEW,
    }
    assert len(episode_calls) == 1
    assert not (tmp_path / "round_001" / "hook_dialogue_polish_instructions.md").exists()
    assert not (tmp_path / "round_001" / "script_batch_hook_dialogue_polish.json").exists()


@pytest.mark.skip(reason="Superseded by constrained Patch application coverage.")
def test_pipeline_keeps_single_repair_result_without_hook_polish(
    tmp_path,
    happy_round_outputs,
):
    outputs = list(happy_round_outputs)
    first_script = outputs[3]
    soft_tail_episode = first_script.episodes[0].model_copy(deep=True)
    soft_tail_episode.cliffhanger = "明天再说。"
    soft_tail_episode.scenes[-1].lines[-2:] = [
        SceneLine(kind="dialogue", speaker="林晚", text="明天再说。"),
        SceneLine(kind="action", text="△中景林晚转身离开。"),
    ]
    first_quality = QualityReport(
        status=QualityStatus.NEEDS_REWRITE,
        scores=QualityScores(
            hook=3,
            conflict=5,
            cliffhanger=4,
            continuity=9,
            video_feasibility=8,
        ),
        blocking_issues=["EP01 原文事实偏离：主动方被改错。"],
        rewrite_instruction="只修 EP01 的主动方和人物知识状态。",
    )
    final_quality = QualityReport(
        status=QualityStatus.USABLE,
        scores=QualityScores(
            hook=9,
            conflict=9,
            cliffhanger=9,
            continuity=9,
            video_feasibility=8,
        ),
        blocking_issues=[],
        rewrite_instruction="",
    )
    llm = RecordingLLM(
        outputs[:4] + [first_quality, soft_tail_episode, final_quality, outputs[5]]
    )
    pipeline = RoundPipeline(llm=llm, store=ProjectStore(tmp_path))

    result = pipeline.run(
        project_id="demo",
        round_number=1,
        source_text=HAPPY_SOURCE_TEXT,
        target_episode_count=1,
        episodes_per_round=1,
        repair_budget="episode",
        generation_variant=GenerationVariant.CURRENT_DENSITY,
    )

    assert result.quality_report.status in {
        QualityStatus.USABLE,
        QualityStatus.NEEDS_HUMAN_REVIEW,
    }
    assert result.script_batch.episodes[0] == soft_tail_episode
    assert not (tmp_path / "round_001" / "script_batch_hook_dialogue_polish.json").exists()


def test_pipeline_default_repair_budget_is_episode():
    assert normalize_repair_budget(None) == RepairBudget.EPISODE


def test_quality_instruction_for_episode_does_not_leak_other_episode_or_global_advice():
    report = QualityReport(
        status=QualityStatus.NEEDS_REWRITE,
        scores=QualityScores(hook=6, conflict=8, cliffhanger=8, continuity=8, video_feasibility=8),
        blocking_issues=[
            "source_evidence: EP01 缺少原文资产：生日宴羞辱",
            "EP02 character knowledge conflict: 提前知道秘密",
        ],
        rewrite_instruction=(
            "全局说明：不要为了镜头密度自由加戏；"
            "EP01 只恢复生日宴羞辱；EP02 只修人物知识状态。"
        ),
    )

    instruction = quality_instruction_for_episode(report, 2)

    assert "EP02" in instruction
    assert "EP01" not in instruction
    assert "不要为了镜头密度自由加戏" not in instruction


@pytest.mark.skip(reason="Superseded by one PatchBatch-per-episode coverage.")
def test_pipeline_rewrite_budget_is_constrained_to_single_episode_repair(
    tmp_path,
    happy_round_outputs,
):
    outputs = list(happy_round_outputs)
    first_script = outputs[3]
    repaired_episode = first_script.episodes[0].model_copy(deep=True)
    first_quality = QualityReport(
        status=QualityStatus.NEEDS_REWRITE,
        scores=QualityScores(
            hook=3,
            conflict=5,
            cliffhanger=4,
            continuity=9,
            video_feasibility=8,
        ),
        blocking_issues=["EP01 原文事实错误：主角提前知道秘密"],
        rewrite_instruction="EP01 修复人物知识状态，不能提前揭露秘密。",
    )
    final_quality = QualityReport(
        status=QualityStatus.USABLE,
        scores=QualityScores(
            hook=9,
            conflict=9,
            cliffhanger=9,
            continuity=9,
            video_feasibility=8,
        ),
        blocking_issues=[],
        rewrite_instruction="",
    )
    llm = RecordingLLM(
        outputs[:4] + [first_quality, repaired_episode, final_quality, outputs[5]]
    )
    pipeline = RoundPipeline(llm=llm, store=ProjectStore(tmp_path))

    result = pipeline.run(
        project_id="demo",
        round_number=1,
        source_text=HAPPY_SOURCE_TEXT,
        repair_budget="rewrite",
        generation_variant=GenerationVariant.CURRENT_DENSITY,
    )

    episode_repair_calls = [
        call
        for call in llm.calls
        if call["response_model"].__name__ == "EpisodeScript"
    ]
    script_batch_calls = [
        call
        for call in llm.calls
        if call["response_model"].__name__ == "ScriptBatch"
    ]
    assert result.quality_report.status in {
        QualityStatus.USABLE,
        QualityStatus.NEEDS_HUMAN_REVIEW,
    }
    assert len(script_batch_calls) == 1
    assert len(episode_repair_calls) == 1
    assert (tmp_path / "round_001" / "quality_report_before_rewrite.json").exists()
    assert (tmp_path / "round_001" / "script_batch_episode_repair.json").exists()
    assert not (tmp_path / "round_001" / "script_batch_rewrite.json").exists()
    assert not (tmp_path / "round_001" / "script_batch_episode_polish.json").exists()
    assert not (tmp_path / "round_001" / "script_batch_hook_dialogue_polish.json").exists()
    assert result.runtime_report is not None
    assert result.runtime_report.repair_budget == "episode"
