from pathlib import Path

from novel_drama_engine.demo import demo_round_outputs
from novel_drama_engine.llm import StaticJsonLLM
from novel_drama_engine.models import QualitySampleManifest, QualitySampleRound
from novel_drama_engine.quality_samples import (
    QUALITY_SAMPLE_REPORT_NAME,
    evaluate_round_result,
    load_quality_sample_manifest,
    run_quality_sample_manifest,
)
from novel_drama_engine.storage import ProjectStore
from novel_drama_engine.models import RoundResult


def build_round_result(round_number, outputs):
    return RoundResult(
        project_id="demo",
        round_number=round_number,
        source_analysis=outputs[0],
        episode_context=outputs[1],
        story_bible=outputs[2],
        script_batch=outputs[3],
        quality_report=outputs[4],
        next_round_context=outputs[5],
    )


def test_quality_sample_manifest_runs_five_genres_for_two_rounds(tmp_path):
    manifest = load_quality_sample_manifest(Path("examples/quality_samples.json"))

    report = run_quality_sample_manifest(
        manifest,
        projects_dir=tmp_path / "quality",
        llm_factory=lambda: StaticJsonLLM(demo_round_outputs()),
    )

    assert report.schema_version == "quality_sample_report.v1"
    assert report.sample_count == 5
    assert report.round_count == 10
    assert report.passed is True
    assert len(report.cases) == 5
    assert all(case.round_count == 2 for case in report.cases)
    assert all(round_result.criteria for case in report.cases for round_result in case.rounds)
    assert (tmp_path / "quality" / QUALITY_SAMPLE_REPORT_NAME).exists()
    assert (tmp_path / "quality" / "haomen_identity_swap" / "round_002" / "round_result.json").exists()


def test_quality_round_evaluation_catches_forbidden_secret_reveal(happy_round_outputs):
    result = build_round_result(1, happy_round_outputs)
    episode = result.script_batch.episodes[0].model_copy(
        update={"cliffhanger": "林晚是真千金，所有人都震惊了。"}
    )
    result = result.model_copy(
        update={
            "script_batch": result.script_batch.model_copy(
                update={"episodes": [episode]}
            )
        }
    )

    report = evaluate_round_result(result)

    secret_check = next(
        criterion for criterion in report.criteria if criterion.name == "secret_reveal_control"
    )
    assert secret_check.passed is False
    assert "premature reveal" in secret_check.detail


def test_quality_sample_manifest_requires_two_rounds():
    payload = {
        "samples": [
            {
                "sample_id": "too_short",
                "genre": "豪门",
                "premise": "只有一轮不够回测。",
                "rounds": [QualitySampleRound(source_text="林晚被赶出宴会。").model_dump()],
            }
        ]
    }

    try:
        QualitySampleManifest.model_validate(payload)
    except Exception as exc:
        assert "at least 2" in str(exc)
    else:
        raise AssertionError("manifest validation should fail")
