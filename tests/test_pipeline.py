from typing import Any

import pytest
from pydantic import BaseModel

from novel_drama_engine.llm import StaticJsonLLM
from novel_drama_engine.models import (
    EpisodeScript,
    QualityReport,
    QualityScores,
    QualityStatus,
    Scene,
    SceneLine,
    ScriptBatch,
)
from novel_drama_engine.pipeline import EmptySourceError, RoundPipeline
from novel_drama_engine.rounds import (
    ContinuityBoomChecker,
    EpisodeContextResolver,
    InternalBibleBuilder,
    ScriptBatchGenerator,
    SourceParser,
    StateWriter,
)
from novel_drama_engine.storage import ProjectStore


class RecordingLLM:
    def __init__(self, outputs: list[BaseModel | dict[str, Any]]) -> None:
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
        if isinstance(raw, response_model):
            return raw
        return response_model.model_validate(raw)


def test_round_services_consume_llm_outputs_in_order(happy_round_outputs):
    llm = StaticJsonLLM(happy_round_outputs)
    source = SourceParser(llm).run("林晚被赶出生日宴。")
    context = EpisodeContextResolver(llm).run("林晚被赶出生日宴。", None, source)
    bible = InternalBibleBuilder(llm).run("林晚被赶出生日宴。", source, context)
    scripts = ScriptBatchGenerator(llm).run(
        "林晚被赶出生日宴。",
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


def test_pipeline_rejects_empty_source_before_llm_call(tmp_path):
    llm = RecordingLLM([])
    pipeline = RoundPipeline(llm=llm, store=ProjectStore(tmp_path))

    with pytest.raises(EmptySourceError):
        pipeline.run(project_id="demo", round_number=1, source_text="   ")

    assert llm.calls == []
    assert not (tmp_path / "round_001").exists()


def test_pipeline_persists_artifacts(tmp_path, happy_round_outputs):
    pipeline = RoundPipeline(llm=StaticJsonLLM(happy_round_outputs), store=ProjectStore(tmp_path))

    result = pipeline.run(project_id="demo", round_number=1, source_text="林晚被赶出生日宴。")

    assert result.script_batch.episodes[0].title == "被赶出生日宴"
    for artifact_name in [
        "source_analysis",
        "episode_context",
        "story_bible",
        "script_batch",
        "quality_report",
        "round_result",
        "next_round_context",
    ]:
        assert (tmp_path / "round_001" / f"{artifact_name}.json").exists()


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
    assert "参考短剧密度" in report.rewrite_instruction


def test_pipeline_rewrites_once_when_quality_requires_it(tmp_path, happy_round_outputs):
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
        rewrite_instruction="把开头改成当众驱逐。",
    )
    rewritten_script = first_script.model_copy(deep=True)
    rewritten_script.episodes[0].hook_3s = "把她拖出去！她不是林家的女儿！"
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
    outputs = outputs[:4] + [failed_quality, rewritten_script, final_quality, outputs[5]]
    llm = RecordingLLM(outputs)
    pipeline = RoundPipeline(llm=llm, store=ProjectStore(tmp_path))

    result = pipeline.run(project_id="demo", round_number=1, source_text="林晚被赶出生日宴。")

    script_calls = [
        call
        for call in llm.calls
        if call["response_model"].__name__ == "ScriptBatch"
    ]
    assert result.script_batch.episodes[0].hook_3s == "把她拖出去！她不是林家的女儿！"
    assert result.quality_report.status == QualityStatus.USABLE
    assert len(script_calls) == 2
    assert failed_quality.rewrite_instruction not in script_calls[0]["user"]
    assert failed_quality.rewrite_instruction in script_calls[1]["user"]
    assert (tmp_path / "round_001" / "quality_report_before_rewrite.json").exists()
    assert (tmp_path / "round_001" / "script_batch_rewrite.json").exists()


def test_pipeline_escalates_second_rewrite_to_human_review(tmp_path, happy_round_outputs):
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

    result = pipeline.run(project_id="demo", round_number=1, source_text="林晚被赶出生日宴。")

    script_calls = [
        call
        for call in llm.calls
        if call["response_model"].__name__ == "ScriptBatch"
    ]
    quality_path = tmp_path / "round_001" / "quality_report.json"
    assert result.quality_report.status == QualityStatus.NEEDS_HUMAN_REVIEW
    assert len(script_calls) == 2
    assert "needs_human_review" in quality_path.read_text(encoding="utf-8")
    assert (tmp_path / "round_001" / "round_result.json").exists()
    assert (tmp_path / "round_001" / "next_round_context.json").exists()
