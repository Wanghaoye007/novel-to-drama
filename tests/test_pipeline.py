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
    QualityScores,
    QualityStatus,
    RoundResult,
    Scene,
    SceneLine,
    ScriptBatch,
    SourceAnalysis,
    SourceStrengthLevel,
    SourceStrengthProfile,
    StoryBible,
)
from novel_drama_engine.pipeline import (
    EmptySourceError,
    InstrumentedJsonLLM,
    RepairBudget,
    RoundPipeline,
    blocking_optional_polish_enabled,
    build_run_manifest,
    fallback_episode_repair_targets,
    normalize_repair_budget,
    prompt_trace_enabled,
    quality_instruction_for_episode,
    strong_source_light_adaptation,
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
from novel_drama_engine.storage import ProjectStore


HAPPY_SOURCE_TEXT = demo_haomen_source()


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


def test_prompt_trace_is_enabled_by_default_and_can_be_disabled(monkeypatch):
    monkeypatch.delenv("NOVEL_DRAMA_TRACE_PROMPTS", raising=False)

    assert prompt_trace_enabled()

    monkeypatch.setenv("NOVEL_DRAMA_TRACE_PROMPTS", "0")

    assert not prompt_trace_enabled()


def test_blocking_optional_polish_is_enabled_by_default(monkeypatch):
    monkeypatch.delenv("NOVEL_DRAMA_BLOCKING_OPTIONAL_POLISH", raising=False)

    assert blocking_optional_polish_enabled()

    monkeypatch.setenv("NOVEL_DRAMA_BLOCKING_OPTIONAL_POLISH", "0")

    assert not blocking_optional_polish_enabled()


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
        "script_batch",
        "runtime_report",
        "run_manifest",
        "quality_report",
        "adaptation_quality_report",
        "methodology_quality_report",
        "drama_quality_report",
        "script_novelty_report",
        "source_evidence_report",
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
    assert (tmp_path / "round_001" / "episode_plan.json").exists()


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
                    retained_assets=["亲哥哥救场"],
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
    assert result.source_evidence_report.missing_items == ["EP01 缺少原文资产：亲哥哥救场"]
    assert result.quality_report.status == QualityStatus.NEEDS_REWRITE
    assert any(
        issue.startswith("source_evidence:")
        for issue in result.quality_report.blocking_issues
    )


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


def test_pipeline_source_evidence_gap_triggers_episode_repair_before_final_gate(
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
    repaired_episode = scripts.episodes[0].model_copy(deep=True)
    repaired_episode.scenes[0].lines[0].text = (
        "△中近景推近林晚侧脸，亲哥哥救场挡在她身前，切到众人僵住。"
    )
    final_quality = quality.model_copy(update={"status": QualityStatus.USABLE})
    llm = ModelQueuedLLM(
        {
            SourceAnalysis: [source],
            EpisodeContext: [context],
            StoryBible: [bible],
            ScriptBatch: [scripts],
            QualityReport: [quality, final_quality],
            EpisodeScript: [repaired_episode],
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

    episode_calls = [
        call
        for call in llm.calls
        if call["response_model"].__name__ == "EpisodeScript"
    ]
    assert len(episode_calls) == 1
    assert "亲哥哥救场" in episode_calls[0]["user"]
    assert result.quality_report.status == QualityStatus.USABLE
    assert result.source_evidence_report is not None
    assert result.source_evidence_report.missing_items == []
    repair_packets = json.loads(
        (tmp_path / "round_001" / "current_episode_repair_packets.json").read_text(
            encoding="utf-8"
        )
    )
    assert repair_packets[0]["source_evidence_targets"] == ["EP01 缺少原文资产：亲哥哥救场"]


def test_pipeline_drama_quality_blocker_triggers_episode_repair_before_final_gate(
    tmp_path,
    happy_round_outputs,
    monkeypatch,
):
    monkeypatch.setenv("NOVEL_DRAMA_EPISODE_REPAIR_FALLBACK", "first")
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
    repaired_episode = scripts.episodes[0].model_copy(deep=True)
    final_quality = quality.model_copy(update={"status": QualityStatus.USABLE})
    llm = ModelQueuedLLM(
        {
            SourceAnalysis: [source],
            EpisodeContext: [context],
            StoryBible: [bible],
            ScriptBatch: [bad_scripts],
            QualityReport: [quality, final_quality],
            EpisodeScript: [repaired_episode],
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

    episode_calls = [
        call
        for call in llm.calls
        if call["response_model"].__name__ == "EpisodeScript"
    ]
    assert len(episode_calls) == 1
    assert "source_asset_preservation" in episode_calls[0]["user"]
    assert "未追踪" in episode_calls[0]["user"]
    assert (tmp_path / "round_001" / "pre_repair_drama_quality_report.json").exists()
    assert result.quality_report.status == QualityStatus.USABLE


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


def test_run_manifest_tracks_episode_repair_fallback_env(monkeypatch):
    monkeypatch.setenv("NOVEL_DRAMA_EPISODE_REPAIR_FALLBACK", "first")
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

    assert manifest["env"]["NOVEL_DRAMA_EPISODE_REPAIR_FALLBACK"] == "first"


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


def test_quality_checker_forces_rewrite_for_underfilled_script(happy_round_outputs):
    source, context, bible = happy_round_outputs[:3]
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

    assert report.status == QualityStatus.NEEDS_REWRITE
    assert any("too short" in issue for issue in report.blocking_issues)
    assert "双层质检" in report.rewrite_instruction


def test_pipeline_default_repair_targets_episode_without_batch_rewrite(
    tmp_path,
    happy_round_outputs,
):
    outputs = list(happy_round_outputs)
    first_script = outputs[3]
    failed_quality = QualityReport(
        status=QualityStatus.NEEDS_REWRITE,
        scores=QualityScores(
            hook=4,
            conflict=6,
            cliffhanger=5,
            continuity=9,
            video_feasibility=8,
        ),
        blocking_issues=["前3秒 Hook 不够强"],
        rewrite_instruction="EP01 前3秒 Hook 不够强，只修第一集开头。",
    )
    repaired_episode = first_script.episodes[0].model_copy(
        deep=True,
        update={"hook_3s": "把她拖出去！她不是林家的女儿！"},
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
    outputs = outputs[:4] + [failed_quality, repaired_episode, final_quality, outputs[5]]
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
    episode_calls = [
        call
        for call in llm.calls
        if call["response_model"].__name__ == "EpisodeScript"
    ]
    assert result.script_batch.episodes[0].hook_3s == "把她拖出去！她不是林家的女儿！"
    assert result.script_batch.episodes[1] == first_script.episodes[1]
    assert result.quality_report.status == QualityStatus.USABLE
    assert len(script_calls) == 1
    assert len(episode_calls) == 1
    assert failed_quality.rewrite_instruction not in script_calls[0]["user"]
    assert failed_quality.rewrite_instruction in episode_calls[0]["user"]
    assert "current_episode_repair_packet" in episode_calls[0]["user"]
    assert "当前集旧稿是唯一文本基准" in episode_calls[0]["user"]
    assert "baseline_episode_text" in episode_calls[0]["user"]
    assert (tmp_path / "round_001" / "quality_report_before_rewrite.json").exists()
    assert (tmp_path / "round_001" / "script_batch_episode_repair.json").exists()
    repair_packets = json.loads(
        (tmp_path / "round_001" / "current_episode_repair_packets.json").read_text(
            encoding="utf-8"
        )
    )
    assert repair_packets[0]["episode"] == 1
    assert "当前集旧稿是唯一文本基准" in repair_packets[0]["baseline_policy"]
    assert "baseline_episode_text" in repair_packets[0]
    assert not (tmp_path / "round_001" / "script_batch_rewrite.json").exists()


def test_pipeline_pre_adaptation_gate_rewrites_source_intent_drift(
    tmp_path,
    happy_round_outputs,
    monkeypatch,
):
    monkeypatch.setenv("NOVEL_DRAMA_EPISODE_REPAIR_FALLBACK", "first")
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
        blocking_issues=["初版仍需逐集修复"],
        rewrite_instruction="按逐集模式补足 EP01-EP05 镜头。",
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
    target_text = (tmp_path / "round_001" / "episode_repair_targets.md").read_text(
        encoding="utf-8"
    )
    decision = (tmp_path / "round_001" / "cost_control_decision.json").read_text(
        encoding="utf-8"
    )
    skipped_stages = {
        stage.name: stage.error
        for stage in result.runtime_report.stages
        if stage.status == "skipped"
    }

    assert result.quality_report.status == QualityStatus.NEEDS_REWRITE
    assert result.runtime_report.repair_budget == RepairBudget.EPISODE
    assert len(script_calls) == 1
    assert episode_calls == []
    assert target_text.startswith("none")
    assert "strong_source_light_adaptation" in decision
    assert "script_batch_rewrite" not in {
        stage.name for stage in result.runtime_report.stages
    }
    assert skipped_stages["episode_repair"] == (
        "Strong-source cost control blocked fallback repair."
    )
    assert not (tmp_path / "round_001" / "script_batch_rewrite.json").exists()
    assert not (tmp_path / "round_001" / "script_batch_episode_repair.json").exists()


def test_episode_repair_fallback_defaults_to_no_speculative_repair(monkeypatch):
    monkeypatch.delenv("NOVEL_DRAMA_EPISODE_REPAIR_FALLBACK", raising=False)

    assert fallback_episode_repair_targets([1, 2, 3]) == set()


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
        blocking_issues=["EP01 开场镜头不够具体。"],
        rewrite_instruction="只修 EP01 的镜头细节，其余集保持原文因果。",
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


def test_pipeline_escalates_second_rewrite_to_human_review(
    tmp_path,
    happy_round_outputs,
    monkeypatch,
):
    monkeypatch.setenv("NOVEL_DRAMA_EPISODE_REPAIR_FALLBACK", "first")
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
        blocking_issues=["Hook 太弱"],
        rewrite_instruction="强化前3秒冲突。",
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
        blocking_issues=["逐集修复后仍缺少镜头密度"],
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
        blocking_issues=["EP01 镜头密度仍不足"],
        rewrite_instruction="只重修 EP01，其他集保持边界不变。",
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


def test_quality_instruction_for_episode_excludes_other_episode_failures():
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

    assert "方法论阻断" in scoped
    assert "EP01 too short" in scoped
    assert "EP01 has 8 action lines" in scoped
    assert "source_asset_preservation" in scoped
    assert "EP02" not in scoped
    assert "EP05" not in scoped
    assert "雪地烟火激吻" not in scoped
    assert "No blocking issues detected" not in scoped


def test_pipeline_polishes_episode_repair_when_local_quality_still_fails(
    tmp_path,
    happy_round_outputs,
    monkeypatch,
):
    monkeypatch.setenv("NOVEL_DRAMA_EPISODE_REPAIR_FALLBACK", "first")
    monkeypatch.setenv("NOVEL_DRAMA_BLOCKING_OPTIONAL_POLISH", "1")
    outputs = list(happy_round_outputs)
    first_script = outputs[3]
    bad_episode = first_script.episodes[0].model_copy(
        deep=True,
        update={
            "scenes": [
                Scene(
                    heading="1-1 夜-内-温家走廊",
                    characters=["林晚", "温舟"],
                    lines=[
                        SceneLine(kind="action", text="△中景推近林晚，她站在门口。"),
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
            hook=3,
            conflict=5,
            cliffhanger=4,
            continuity=9,
            video_feasibility=8,
        ),
        blocking_issues=["Hook 太弱"],
        rewrite_instruction="强化前3秒冲突。",
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
        outputs[:4] + [first_quality, bad_episode, first_script.episodes[0], final_quality, outputs[5]]
    )
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
    assert result.quality_report.status in {
        QualityStatus.USABLE,
        QualityStatus.NEEDS_HUMAN_REVIEW,
    }
    assert len(episode_repair_calls) == 2
    assert "当前本地质检" in episode_repair_calls[-1]["user"]
    assert (tmp_path / "round_001" / "script_batch_episode_polish.json").exists()
    assert (tmp_path / "round_001" / "episode_polish_instructions.md").exists()


def test_pipeline_skips_optional_polish_when_disabled(
    tmp_path,
    happy_round_outputs,
    monkeypatch,
):
    monkeypatch.setenv("NOVEL_DRAMA_EPISODE_REPAIR_FALLBACK", "first")
    monkeypatch.setenv("NOVEL_DRAMA_BLOCKING_OPTIONAL_POLISH", "0")
    outputs = list(happy_round_outputs)
    first_script = outputs[3]
    bad_episode = first_script.episodes[0].model_copy(
        deep=True,
        update={
            "scenes": [
                Scene(
                    heading="1-1 夜-内-温家走廊",
                    characters=["林晚", "温舟"],
                    lines=[
                        SceneLine(kind="action", text="△中景推近林晚，她站在门口。"),
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
            hook=3,
            conflict=5,
            cliffhanger=4,
            continuity=9,
            video_feasibility=8,
        ),
        blocking_issues=["Hook 太弱"],
        rewrite_instruction="强化前3秒冲突。",
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
        repair_budget="episode",
        generation_variant=GenerationVariant.CURRENT_DENSITY,
    )

    episode_repair_calls = [
        call
        for call in llm.calls
        if call["response_model"].__name__ == "EpisodeScript"
    ]
    skipped_stages = {
        stage.name
        for stage in result.runtime_report.stages
        if stage.status == "skipped"
    }
    assert len(episode_repair_calls) == 1
    assert "episode_quality_polish" in skipped_stages
    assert (tmp_path / "round_001" / "episode_polish_instructions.md").exists()
    assert not (tmp_path / "round_001" / "script_batch_episode_polish.json").exists()


def test_pipeline_keeps_previous_episode_when_optional_polish_fails(
    tmp_path,
    happy_round_outputs,
    monkeypatch,
):
    monkeypatch.setenv("NOVEL_DRAMA_EPISODE_REPAIR_FALLBACK", "first")
    monkeypatch.setenv("NOVEL_DRAMA_BLOCKING_OPTIONAL_POLISH", "1")
    outputs = list(happy_round_outputs)
    first_script = outputs[3]
    bad_episode = first_script.episodes[0].model_copy(
        deep=True,
        update={
            "scenes": [
                Scene(
                    heading="1-1 夜-内-温家走廊",
                    characters=["林晚", "温舟"],
                    lines=[
                        SceneLine(kind="action", text="△中景推近林晚，她站在门口。"),
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
            hook=3,
            conflict=5,
            cliffhanger=4,
            continuity=9,
            video_feasibility=8,
        ),
        blocking_issues=["Hook 太弱"],
        rewrite_instruction="强化前3秒冲突。",
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
        outputs[:4]
        + [first_quality, bad_episode]
        + [
            RuntimeError("provider returned scene object"),
            RuntimeError("provider returned scene object"),
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

    assert result.quality_report.status in {
        QualityStatus.USABLE,
        QualityStatus.NEEDS_HUMAN_REVIEW,
    }
    assert result.script_batch.episodes[0] == bad_episode
    assert (tmp_path / "round_001" / "script_batch_episode_polish.json").exists()
    assert (tmp_path / "round_001" / "episode_quality_polish_failures.md").exists()
    assert (tmp_path / "round_001" / "hook_dialogue_polish_failures.md").exists()


def test_pipeline_runs_hook_dialogue_polish_for_soft_tail_after_quality_polish(
    tmp_path,
    happy_round_outputs,
    monkeypatch,
):
    monkeypatch.setenv("NOVEL_DRAMA_EPISODE_REPAIR_FALLBACK", "first")
    monkeypatch.setenv("NOVEL_DRAMA_BLOCKING_OPTIONAL_POLISH", "1")
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
        blocking_issues=["Hook 太弱"],
        rewrite_instruction="强化前3秒冲突。",
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
        outputs[:4]
        + [first_quality, soft_tail_episode, soft_tail_episode, first_script.episodes[0], final_quality, outputs[5]]
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
    assert result.quality_report.status == QualityStatus.USABLE
    assert len(episode_calls) == 3
    assert "结尾钩子/对白密度二次编译" in episode_calls[-1]["user"]
    assert "不要整集重写" in episode_calls[-1]["user"]
    assert (tmp_path / "round_001" / "hook_dialogue_polish_instructions.md").exists()
    assert (tmp_path / "round_001" / "script_batch_hook_dialogue_polish.json").exists()


def test_pipeline_keeps_quality_polished_episode_when_hook_polish_fails(
    tmp_path,
    happy_round_outputs,
    monkeypatch,
):
    monkeypatch.setenv("NOVEL_DRAMA_EPISODE_REPAIR_FALLBACK", "first")
    monkeypatch.setenv("NOVEL_DRAMA_BLOCKING_OPTIONAL_POLISH", "1")
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
        blocking_issues=["Hook 太弱"],
        rewrite_instruction="强化前3秒冲突。",
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
        outputs[:4]
        + [first_quality, soft_tail_episode]
        + [
            soft_tail_episode,
            RuntimeError("provider returned scene object"),
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

    assert result.quality_report.status in {
        QualityStatus.USABLE,
        QualityStatus.NEEDS_HUMAN_REVIEW,
    }
    assert result.script_batch.episodes[0] == soft_tail_episode
    assert (tmp_path / "round_001" / "script_batch_hook_dialogue_polish.json").exists()
    assert (tmp_path / "round_001" / "hook_dialogue_polish_failures.md").exists()


def test_pipeline_default_repair_budget_is_episode():
    assert normalize_repair_budget(None) == RepairBudget.EPISODE


def test_pipeline_rewrite_repair_budget_skips_episode_repair(tmp_path, happy_round_outputs):
    outputs = list(happy_round_outputs)
    first_script = outputs[3]
    rewritten_script = first_script.model_copy(deep=True)
    first_quality = QualityReport(
        status=QualityStatus.NEEDS_REWRITE,
        scores=QualityScores(
            hook=3,
            conflict=5,
            cliffhanger=4,
            continuity=9,
            video_feasibility=8,
        ),
        blocking_issues=["Hook 太弱"],
        rewrite_instruction="强化前3秒冲突。",
    )
    second_quality = QualityReport(
        status=QualityStatus.NEEDS_REWRITE,
        scores=QualityScores(
            hook=5,
            conflict=5,
            cliffhanger=4,
            continuity=9,
            video_feasibility=8,
        ),
        blocking_issues=["重写后仍缺少爆点"],
        rewrite_instruction="需要人工重构场景。",
    )
    llm = RecordingLLM(
        outputs[:4] + [first_quality, rewritten_script, second_quality, outputs[5]]
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
    assert result.quality_report.status == QualityStatus.NEEDS_HUMAN_REVIEW
    assert episode_repair_calls == []
    assert (tmp_path / "round_001" / "quality_report_before_rewrite.json").exists()
    assert not (tmp_path / "round_001" / "script_batch_episode_repair.json").exists()
    assert result.runtime_report is not None
    assert result.runtime_report.repair_budget == "rewrite"
