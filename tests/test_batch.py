import json

from novel_drama_engine.batch import BatchRunner
from novel_drama_engine.demo import (
    demo_haomen_source,
    demo_round_outputs,
    demo_source_grounded_round_outputs,
)
from novel_drama_engine.llm import StaticJsonLLM
from novel_drama_engine.models import BatchItemStatus
from novel_drama_engine.storage import ProjectStore


def write_manifest(path, projects):
    path.write_text(json.dumps({"projects": projects}), encoding="utf-8")


def test_batch_runner_runs_manifest_items_with_relative_inputs(tmp_path):
    source = tmp_path / "source.txt"
    source.write_text(demo_haomen_source(1), encoding="utf-8")
    manifest = tmp_path / "manifest.json"
    write_manifest(
        manifest,
        [
            {
                "project_id": "alpha",
                "input": "source.txt",
                "target_episode_count": 1,
                "episodes_per_round": 1,
            },
            {
                "project_id": "beta",
                "input": "source.txt",
                "target_episode_count": 1,
                "episodes_per_round": 1,
            },
        ],
    )
    projects_dir = tmp_path / "projects"

    report = BatchRunner(
        projects_dir=projects_dir,
        llm_factory=lambda round_number, previous_context, item, source_text, store: StaticJsonLLM(
            demo_source_grounded_round_outputs(source_text=source_text)
        ),
    ).run(manifest)

    assert report.completed_count == 2
    assert report.failed_count == 0
    assert [item.project_id for item in report.items] == ["alpha", "beta"]
    assert (projects_dir / "alpha" / "round_001" / "round_result.json").exists()
    assert (projects_dir / "beta" / "round_001" / "rendered_scripts.md").exists()
    assert (projects_dir / "batch_report.json").exists()


def test_batch_runner_auto_continues_existing_project_round(tmp_path):
    source = tmp_path / "source.txt"
    source.write_text(demo_haomen_source(10), encoding="utf-8")
    manifest = tmp_path / "manifest.json"
    write_manifest(
        manifest,
        [
            {
                "project_id": "alpha",
                "input": "source.txt",
                "target_episode_count": 10,
            }
        ],
    )
    projects_dir = tmp_path / "projects"
    previous_context = demo_round_outputs()[-1]
    ProjectStore(projects_dir / "alpha").write_round_artifact(
        1,
        "next_round_context",
        previous_context,
    )

    report = BatchRunner(
        projects_dir=projects_dir,
        llm_factory=lambda: StaticJsonLLM(
            demo_round_outputs(
                round_number=2,
                previous_context=previous_context,
                include_episode_plan=True,
            )
        ),
    ).run(manifest)

    assert report.items[0].round_number == 2
    assert (projects_dir / "alpha" / "round_002" / "round_result.json").exists()


def test_batch_runner_records_failure_and_continues(tmp_path):
    source = tmp_path / "source.txt"
    source.write_text(demo_haomen_source(10), encoding="utf-8")
    manifest = tmp_path / "manifest.json"
    write_manifest(
        manifest,
        [
            {"project_id": "missing", "input": "missing.txt"},
            {
                "project_id": "ok",
                "input": "source.txt",
                "target_episode_count": 1,
                "episodes_per_round": 1,
            },
        ],
    )
    projects_dir = tmp_path / "projects"

    report = BatchRunner(
        projects_dir=projects_dir,
        llm_factory=lambda round_number, previous_context, item, source_text, store: StaticJsonLLM(
            demo_source_grounded_round_outputs(source_text=source_text)
        ),
    ).run(manifest)

    assert [item.status for item in report.items] == [
        BatchItemStatus.FAILED,
        BatchItemStatus.COMPLETED,
    ]
    assert report.failed_count == 1
    assert report.completed_count == 1
    assert report.items[0].error
    assert (projects_dir / "ok" / "round_001" / "round_result.json").exists()
