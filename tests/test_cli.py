from typer.testing import CliRunner

import novel_drama_engine.cli as cli
from novel_drama_engine.llm import StaticJsonLLM
from novel_drama_engine.storage import ProjectStore


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
