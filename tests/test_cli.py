import json

from typer.testing import CliRunner

import novel_drama_engine.cli as cli
from novel_drama_engine.llm import StaticJsonLLM
from novel_drama_engine.models import RoundResult
from novel_drama_engine.storage import ProjectStore


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


def write_manifest(path, projects):
    path.write_text(json.dumps({"projects": projects}), encoding="utf-8")


def test_cli_run_writes_outputs(tmp_path, happy_round_outputs, monkeypatch):
    source = tmp_path / "source.txt"
    source.write_text("林晚被赶出生日宴。", encoding="utf-8")
    project_dir = tmp_path / "project"

    monkeypatch.setattr(cli, "build_llm", lambda model=None: StaticJsonLLM(happy_round_outputs))

    result = CliRunner().invoke(
        cli.app,
        ["run", "--input", str(source), "--project-dir", str(project_dir), "--project-id", "demo"],
    )

    assert result.exit_code == 0
    assert "EP01-EP01" in result.stdout
    assert "第1集 被赶出生日宴" in result.stdout
    assert (project_dir / "round_001" / "rendered_scripts.md").exists()


def test_cli_run_forwards_model_option(tmp_path, happy_round_outputs, monkeypatch):
    source = tmp_path / "source.txt"
    source.write_text("林晚被赶出生日宴。", encoding="utf-8")
    project_dir = tmp_path / "project"
    captured = {}

    def fake_build_llm(model=None):
        captured["model"] = model
        return StaticJsonLLM(happy_round_outputs)

    monkeypatch.setattr(cli, "build_llm", fake_build_llm)

    result = CliRunner().invoke(
        cli.app,
        [
            "run",
            "--input",
            str(source),
            "--project-dir",
            str(project_dir),
            "--project-id",
            "demo",
            "--model",
            "gpt-test",
        ],
    )

    assert result.exit_code == 0
    assert captured["model"] == "gpt-test"


def test_cli_mock_run_writes_outputs_without_openai_key(tmp_path, monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    source = tmp_path / "source.txt"
    source.write_text("林晚被赶出生日宴。", encoding="utf-8")
    project_dir = tmp_path / "mock_project"

    result = CliRunner().invoke(
        cli.app,
        [
            "run",
            "--mock",
            "--input",
            str(source),
            "--project-dir",
            str(project_dir),
            "--project-id",
            "demo",
        ],
    )

    assert result.exit_code == 0
    assert "Episode range: EP01-EP01" in result.stdout
    assert "质量结论：usable" in result.stdout
    assert (project_dir / "round_001" / "round_result.json").exists()


def test_cli_run_auto_continues_from_latest_project_context(
    tmp_path,
    happy_round_outputs,
    monkeypatch,
):
    source = tmp_path / "source.txt"
    source.write_text("管家认出林晚后，林雪开始慌了。", encoding="utf-8")
    project_dir = tmp_path / "project"
    ProjectStore(project_dir).write_round_artifact(
        1,
        "next_round_context",
        happy_round_outputs[-1],
    )

    monkeypatch.setattr(cli, "build_llm", lambda model=None: StaticJsonLLM(happy_round_outputs))

    result = CliRunner().invoke(
        cli.app,
        [
            "run",
            "--input",
            str(source),
            "--project-dir",
            str(project_dir),
            "--project-id",
            "demo",
        ],
    )

    assert result.exit_code == 0
    assert "Round: 2" in result.stdout
    assert "Loaded context:" in result.stdout
    assert (project_dir / "round_002" / "round_result.json").exists()
    assert (project_dir / "round_002" / "rendered_scripts.md").exists()


def test_cli_real_run_reports_missing_api_key(tmp_path, monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    source = tmp_path / "source.txt"
    source.write_text("林晚被赶出生日宴。", encoding="utf-8")

    result = CliRunner().invoke(
        cli.app,
        ["run", "--input", str(source), "--project-dir", str(tmp_path / "project")],
    )

    assert result.exit_code == 1
    assert "OPENAI_API_KEY is not set" in result.output
    assert "Use --mock" in result.output


def test_cli_status_lists_completed_rounds(tmp_path, happy_round_outputs):
    project_dir = tmp_path / "project"
    store = ProjectStore(project_dir)
    store.write_round_result(build_round_result(1, happy_round_outputs))
    store.write_next_round_context(build_round_result(1, happy_round_outputs))

    result = CliRunner().invoke(
        cli.app,
        ["status", "--project-dir", str(project_dir)],
    )

    assert result.exit_code == 0
    assert f"Project: {project_dir}" in result.stdout
    assert "Rounds: 1" in result.stdout
    assert "Current episode: 1" in result.stdout
    assert "Round 1 | EP01-EP01 | usable" in result.stdout
    assert "EP01 被赶出生日宴" in result.stdout
    assert "Open hooks: 管家为什么叫林晚大小姐" in result.stdout
    assert "Latest context:" in result.stdout


def test_cli_status_handles_empty_project(tmp_path):
    project_dir = tmp_path / "project"

    result = CliRunner().invoke(
        cli.app,
        ["status", "--project-dir", str(project_dir)],
    )

    assert result.exit_code == 0
    assert f"No completed rounds found in: {project_dir}" in result.stdout


def test_cli_export_video_brief_writes_latest_round_outputs(tmp_path, happy_round_outputs):
    project_dir = tmp_path / "project"
    store = ProjectStore(project_dir)
    store.write_round_result(build_round_result(1, happy_round_outputs))

    result = CliRunner().invoke(
        cli.app,
        [
            "export-video-brief",
            "--project-dir",
            str(project_dir),
            "--duration-seconds",
            "75",
        ],
    )

    json_path = project_dir / "round_001" / "video_brief.json"
    markdown_path = project_dir / "round_001" / "video_brief.md"
    assert result.exit_code == 0
    assert "Video brief exported for round 1" in result.stdout
    assert json_path.exists()
    assert markdown_path.exists()
    assert '"target_duration_seconds":75' in json_path.read_text(encoding="utf-8").replace(" ", "")
    assert "EP01-S01" in markdown_path.read_text(encoding="utf-8")


def test_cli_export_video_brief_requires_completed_round(tmp_path):
    project_dir = tmp_path / "project"

    result = CliRunner().invoke(
        cli.app,
        ["export-video-brief", "--project-dir", str(project_dir)],
    )

    assert result.exit_code == 1
    assert "No completed rounds found" in result.output


def test_cli_export_localization_writes_profile_outputs(tmp_path, happy_round_outputs):
    project_dir = tmp_path / "project"
    store = ProjectStore(project_dir)
    store.write_round_result(build_round_result(1, happy_round_outputs))
    profile_path = tmp_path / "profile.json"
    profile_path.write_text(
        json.dumps(
            {
                "profile_id": "us_tiktok",
                "locale": "en-US",
                "platform": "TikTok",
                "target_language": "en",
                "replacements": {"林晚": "Lena Lin", "顾承": "Grant Gu"},
                "forbidden_terms": ["Lena Lin"],
            }
        ),
        encoding="utf-8",
    )

    result = CliRunner().invoke(
        cli.app,
        [
            "export-localization",
            "--project-dir",
            str(project_dir),
            "--profile",
            str(profile_path),
        ],
    )

    json_path = project_dir / "round_001" / "localization_us_tiktok.json"
    markdown_path = project_dir / "round_001" / "localization_us_tiktok.md"
    assert result.exit_code == 0
    assert "Localization package exported for round 1" in result.stdout
    assert "Review issues: 2" in result.stdout
    assert json_path.exists()
    assert markdown_path.exists()
    assert "Lena Lin" in json_path.read_text(encoding="utf-8")
    assert "Review Issues" in markdown_path.read_text(encoding="utf-8")


def test_cli_batch_run_writes_project_reports(tmp_path):
    source = tmp_path / "source.txt"
    source.write_text("林晚被赶出生日宴。", encoding="utf-8")
    manifest = tmp_path / "manifest.json"
    write_manifest(
        manifest,
        [
            {"project_id": "alpha", "input": "source.txt"},
            {"project_id": "beta", "input": "source.txt"},
        ],
    )
    projects_dir = tmp_path / "projects"

    result = CliRunner().invoke(
        cli.app,
        [
            "batch-run",
            "--mock",
            "--manifest",
            str(manifest),
            "--projects-dir",
            str(projects_dir),
        ],
    )

    assert result.exit_code == 0
    assert "completed: alpha" in result.stdout
    assert "completed: beta" in result.stdout
    assert "Batch summary: 2 completed, 0 failed" in result.stdout
    assert (projects_dir / "alpha" / "round_001" / "round_result.json").exists()
    assert (projects_dir / "beta" / "round_001" / "rendered_scripts.md").exists()
    assert (projects_dir / "batch_report.json").exists()


def test_cli_batch_run_returns_failure_when_any_item_fails(tmp_path):
    source = tmp_path / "source.txt"
    source.write_text("林晚被赶出生日宴。", encoding="utf-8")
    manifest = tmp_path / "manifest.json"
    write_manifest(
        manifest,
        [
            {"project_id": "missing", "input": "missing.txt"},
            {"project_id": "ok", "input": "source.txt"},
        ],
    )
    projects_dir = tmp_path / "projects"

    result = CliRunner().invoke(
        cli.app,
        [
            "batch-run",
            "--mock",
            "--manifest",
            str(manifest),
            "--projects-dir",
            str(projects_dir),
        ],
    )

    assert result.exit_code == 1
    assert "failed: missing" in result.stdout
    assert "completed: ok" in result.stdout
    assert "Batch summary: 1 completed, 1 failed" in result.stdout
    assert "Batch completed with 1 failed item" in result.output
    assert (projects_dir / "batch_report.json").exists()
