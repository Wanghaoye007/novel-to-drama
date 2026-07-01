import json

from typer.testing import CliRunner

import novel_drama_engine.cli as cli
from novel_drama_engine.demo import demo_round_outputs
from novel_drama_engine.evaluation import (
    QualitySampleEvaluator,
    read_quality_sample_manifest,
)
from novel_drama_engine.llm import StaticJsonLLM


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


def test_quality_sample_evaluator_runs_multiple_rounds(
    tmp_path,
    happy_round_outputs,
):
    manifest = tmp_path / "samples.json"
    write_sample_manifest(manifest)
    second_round_outputs = demo_round_outputs(
        round_number=2,
        previous_context=happy_round_outputs[-1],
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
