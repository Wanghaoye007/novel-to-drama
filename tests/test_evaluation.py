import json

import pytest
from typer.testing import CliRunner

import novel_drama_engine.cli as cli
from novel_drama_engine.demo import demo_round_outputs
from novel_drama_engine.evaluation import (
    QualitySampleEvaluator,
    read_quality_sample_manifest,
)
from novel_drama_engine.llm import LLMProviderLimitError, StaticJsonLLM
from novel_drama_engine.models import GenerationVariant


def write_sample_manifest(path):
    path.write_text(
        json.dumps(
            {
                "samples": [
                    {
                        "sample_id": "haomen",
                        "label": "豪门羞辱",
                        "source_text": "林晚在生日宴上被当众羞辱。",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )


class FailingLLM:
    def __init__(self, exc):
        self.exc = exc

    def complete(self, *, system, user, response_model):
        raise self.exc


def test_quality_sample_evaluator_runs_multiple_rounds(
    tmp_path,
    happy_round_outputs,
):
    manifest = tmp_path / "samples.json"
    write_sample_manifest(manifest)
    second_round_outputs = demo_round_outputs(
        round_number=2,
        previous_context=happy_round_outputs[-1],
        include_story_bible=False,
    )
    output_sets = iter([happy_round_outputs, second_round_outputs])

    report = QualitySampleEvaluator(
        projects_dir=tmp_path / "eval",
        llm_factory=lambda round_number, previous_context, sample: StaticJsonLLM(
            next(output_sets)
        ),
        rounds_per_sample=2,
    ).run(manifest)

    assert report.passed_count == 1
    assert report.failed_count == 0
    assert len(report.samples[0].rounds) == 2
    assert (tmp_path / "eval" / "quality_sample_report.json").exists()
    assert (
        tmp_path
        / "eval"
        / "haomen"
        / "round_002"
        / "rendered_scripts.md"
    ).exists()


def test_quality_sample_evaluator_fails_fast_on_provider_limit(tmp_path):
    manifest = tmp_path / "samples.json"
    manifest.write_text(
        json.dumps(
            {
                "samples": [
                    {
                        "sample_id": "quota_case",
                        "label": "额度失败样本",
                        "source_text": "林晚在生日宴上被当众羞辱。",
                    },
                    {
                        "sample_id": "should_not_run",
                        "label": "不应继续执行",
                        "source_text": "顾承发现鉴定报告被调包。",
                    },
                ]
            }
        ),
        encoding="utf-8",
    )
    projects_dir = tmp_path / "eval"

    with pytest.raises(LLMProviderLimitError):
        QualitySampleEvaluator(
            projects_dir=projects_dir,
            llm_factory=lambda round_number, previous_context, sample, variant: FailingLLM(
                LLMProviderLimitError(
                    "LLM_PROVIDER_LIMIT: provider quota or key daily limit exceeded"
                )
            ),
            rounds_per_sample=2,
            generation_variants=[
                GenerationVariant.SOP_FULL_STACK,
                GenerationVariant.DRAMA_ENGINE_FIRST,
            ],
        ).run(manifest)

    report = json.loads(
        (projects_dir / "quality_sample_report.json").read_text(encoding="utf-8")
    )
    assert [sample["sample_id"] for sample in report["samples"]] == ["quota_case"]
    assert report["samples"][0]["rounds"][0]["round_number"] == 1
    assert "LLM_PROVIDER_LIMIT" in report["samples"][0]["rounds"][0]["warnings"][0]


def test_read_quality_sample_manifest_validates_samples(tmp_path):
    manifest = tmp_path / "samples.json"
    write_sample_manifest(manifest)

    parsed = read_quality_sample_manifest(manifest)

    assert parsed.samples[0].sample_id == "haomen"


def test_cli_evaluate_samples_writes_report(tmp_path):
    manifest = tmp_path / "samples.json"
    write_sample_manifest(manifest)
    projects_dir = tmp_path / "eval"

    result = CliRunner().invoke(
        cli.app,
        [
            "evaluate-samples",
            "--mock",
            "--samples",
            str(manifest),
            "--projects-dir",
            str(projects_dir),
            "--rounds",
            "2",
        ],
    )

    assert result.exit_code == 0
    assert "Quality samples: 1 passed, 0 failed" in result.stdout
    assert (projects_dir / "quality_sample_report.json").exists()


def test_quality_sample_evaluator_runs_multiple_variants(tmp_path):
    manifest = tmp_path / "samples.json"
    write_sample_manifest(manifest)
    output_sets = iter(
        [
            demo_round_outputs(include_sop_stack=True, include_episode_plan=True),
            demo_round_outputs(include_episode_plan=True),
        ]
    )

    report = QualitySampleEvaluator(
        projects_dir=tmp_path / "eval",
        llm_factory=lambda round_number, previous_context, sample, variant: StaticJsonLLM(
            next(output_sets)
        ),
        rounds_per_sample=1,
        generation_variants=[
            GenerationVariant.SOP_FULL_STACK,
            GenerationVariant.DRAMA_ENGINE_FIRST,
        ],
    ).run(manifest)

    assert report.variants == [
        GenerationVariant.SOP_FULL_STACK,
        GenerationVariant.DRAMA_ENGINE_FIRST,
    ]
    assert [sample.variant for sample in report.samples] == [
        GenerationVariant.SOP_FULL_STACK,
        GenerationVariant.DRAMA_ENGINE_FIRST,
    ]
    assert (
        tmp_path
        / "eval"
        / "haomen"
        / "sop_full_stack"
        / "round_001"
        / "rendered_scripts.md"
    ).exists()
