import json

from typer.testing import CliRunner

import novel_drama_engine.cli as cli
from novel_drama_engine.demo import demo_localization_output, demo_marketing_assets
from novel_drama_engine.llm import StaticJsonLLM
from novel_drama_engine.models import (
    LocalizationRewrite,
    LocalizedEpisodePackage,
    LocalizedScene,
    RoundResult,
)
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


def test_cli_serve_forwards_server_options(monkeypatch):
    captured = {}

    def fake_run_api_server(host, port, reload):
        captured["host"] = host
        captured["port"] = port
        captured["reload"] = reload

    monkeypatch.setattr(cli, "run_api_server", fake_run_api_server)

    result = CliRunner().invoke(
        cli.app,
        ["serve", "--host", "0.0.0.0", "--port", "9000", "--reload"],
    )

    assert result.exit_code == 0
    assert captured == {"host": "0.0.0.0", "port": 9000, "reload": True}


def test_cli_batch_runs_matching_sources(tmp_path):
    input_dir = tmp_path / "sources"
    input_dir.mkdir()
    (input_dir / "haomen.txt").write_text("林晚被赶出生日宴。", encoding="utf-8")
    (input_dir / "xianxia.txt").write_text("师姐当众退婚。", encoding="utf-8")
    (input_dir / "notes.md").write_text("ignore me", encoding="utf-8")
    project_root = tmp_path / "projects"

    result = CliRunner().invoke(
        cli.app,
        [
            "batch",
            "--mock",
            "--input-dir",
            str(input_dir),
            "--project-root",
            str(project_root),
        ],
    )

    assert result.exit_code == 0
    assert "Batch sources: 2" in result.stdout
    assert "Batch complete: 2 succeeded, 0 failed" in result.stdout
    assert (project_root / "haomen" / "round_001" / "round_result.json").exists()
    assert (project_root / "xianxia" / "round_001" / "rendered_scripts.md").exists()
    assert not (project_root / "notes").exists()


def test_cli_batch_preserves_nested_relative_paths_with_globstar(tmp_path):
    input_dir = tmp_path / "sources"
    nested_dir = input_dir / "genre" / "haomen"
    nested_dir.mkdir(parents=True)
    (nested_dir / "book.txt").write_text("林晚被赶出生日宴。", encoding="utf-8")
    project_root = tmp_path / "projects"

    result = CliRunner().invoke(
        cli.app,
        [
            "batch",
            "--mock",
            "--input-dir",
            str(input_dir),
            "--project-root",
            str(project_root),
            "--pattern",
            "**/*.txt",
        ],
    )

    assert result.exit_code == 0
    assert (project_root / "genre" / "haomen" / "book" / "round_001").exists()


def test_cli_batch_runs_manifest_jobs(tmp_path):
    manifest_dir = tmp_path / "manifest_dir"
    manifest_dir.mkdir()
    (manifest_dir / "source.txt").write_text("林晚被赶出生日宴。", encoding="utf-8")
    manifest_path = manifest_dir / "batch.json"
    manifest_path.write_text(
        json.dumps(
            {
                "jobs": [
                    {
                        "source": "source.txt",
                        "project_id": "manifest-haomen",
                        "project_dir": "custom/haomen",
                        "round_number": 3,
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    project_root = tmp_path / "projects"

    result = CliRunner().invoke(
        cli.app,
        [
            "batch",
            "--mock",
            "--manifest",
            str(manifest_path),
            "--project-root",
            str(project_root),
        ],
    )

    round_result_path = project_root / "custom" / "haomen" / "round_003" / "round_result.json"
    round_result = json.loads(round_result_path.read_text(encoding="utf-8"))
    assert result.exit_code == 0
    assert "Batch sources: 1" in result.stdout
    assert round_result["project_id"] == "manifest-haomen"
    assert round_result["round_number"] == 3


def test_cli_batch_manifest_generates_requested_deliverables(tmp_path):
    manifest_dir = tmp_path / "manifest_dir"
    manifest_dir.mkdir()
    (manifest_dir / "source.txt").write_text("林晚被赶出生日宴。", encoding="utf-8")
    manifest_path = manifest_dir / "batch.json"
    manifest_path.write_text(
        json.dumps(
            {
                "jobs": [
                    {
                        "source": "source.txt",
                        "project_id": "haomen-us",
                        "locale": "en-US",
                        "platform": "TikTok/Reels",
                        "deliverables": ["localization", "ad_assets"],
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    project_root = tmp_path / "projects"

    result = CliRunner().invoke(
        cli.app,
        [
            "batch",
            "--mock",
            "--manifest",
            str(manifest_path),
            "--project-root",
            str(project_root),
        ],
    )

    project_dir = project_root / "haomen-us"
    assert result.exit_code == 0
    assert "deliverables=localization,ad_assets" in result.stdout
    assert (project_dir / "round_001" / "round_result.json").exists()
    assert (project_dir / "round_001" / "localization_en-US_TikTok-Reels.json").exists()
    assert (project_dir / "round_001" / "marketing_assets_en-US_TikTok-Reels.md").exists()

    status = CliRunner().invoke(
        cli.app,
        ["status", "--project-dir", str(project_dir)],
    )
    assert "Localizations: en-US_TikTok-Reels" in status.stdout
    assert "Marketing assets: en-US_TikTok-Reels" in status.stdout


def test_cli_batch_reports_no_matching_sources(tmp_path):
    input_dir = tmp_path / "sources"
    input_dir.mkdir()
    (input_dir / "notes.md").write_text("ignore me", encoding="utf-8")

    result = CliRunner().invoke(
        cli.app,
        ["batch", "--mock", "--input-dir", str(input_dir)],
    )

    assert result.exit_code == 1
    assert "No source files matched" in result.output


def test_cli_batch_requires_exactly_one_source_mode(tmp_path):
    result = CliRunner().invoke(cli.app, ["batch", "--mock"])

    assert result.exit_code == 1
    assert "Pass exactly one of --input-dir or --manifest" in result.output


def test_cli_batch_reports_invalid_manifest_json(tmp_path):
    manifest_path = tmp_path / "batch.json"
    manifest_path.write_text("{not json", encoding="utf-8")

    result = CliRunner().invoke(
        cli.app,
        ["batch", "--mock", "--manifest", str(manifest_path)],
    )

    assert result.exit_code == 1
    assert "Manifest is not valid JSON" in result.output


def test_cli_batch_continues_after_source_failure(tmp_path):
    input_dir = tmp_path / "sources"
    input_dir.mkdir()
    (input_dir / "blank.txt").write_text("   ", encoding="utf-8")
    (input_dir / "valid.txt").write_text("林晚被赶出生日宴。", encoding="utf-8")
    project_root = tmp_path / "projects"

    result = CliRunner().invoke(
        cli.app,
        [
            "batch",
            "--mock",
            "--input-dir",
            str(input_dir),
            "--project-root",
            str(project_root),
        ],
    )

    assert result.exit_code == 1
    assert "[failed]" in result.stdout
    assert "source_text is empty" in result.stdout
    assert "Batch completed with 1 failure(s), 1 succeeded" in result.output
    assert not (project_root / "blank" / "round_001").exists()
    assert (project_root / "valid" / "round_001" / "round_result.json").exists()


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


def test_cli_localize_mock_writes_outputs(tmp_path, happy_round_outputs):
    project_dir = tmp_path / "project"
    store = ProjectStore(project_dir)
    store.write_round_result(build_round_result(1, happy_round_outputs))

    result = CliRunner().invoke(
        cli.app,
        [
            "localize",
            "--mock",
            "--project-dir",
            str(project_dir),
            "--round-number",
            "1",
            "--locale",
            "en-US",
            "--platform",
            "TikTok/Reels",
        ],
    )

    json_path = project_dir / "round_001" / "localization_en-US_TikTok-Reels.json"
    markdown_path = project_dir / "round_001" / "localized_scripts_en-US_TikTok-Reels.md"
    localized = json.loads(json_path.read_text(encoding="utf-8"))
    assert result.exit_code == 0
    assert "Localized round: 1" in result.stdout
    assert localized["locale"] == "en-US"
    assert localized["platform"] == "TikTok/Reels"
    assert "Thrown Out at the Birthday Banquet" in markdown_path.read_text(encoding="utf-8")


def test_cli_localize_defaults_to_latest_round(tmp_path, happy_round_outputs):
    project_dir = tmp_path / "project"
    store = ProjectStore(project_dir)
    store.write_round_result(build_round_result(1, happy_round_outputs))
    store.write_round_result(build_round_result(2, happy_round_outputs))

    result = CliRunner().invoke(
        cli.app,
        ["localize", "--mock", "--project-dir", str(project_dir)],
    )

    assert result.exit_code == 0
    assert "Localized round: 2" in result.stdout
    assert (project_dir / "round_002" / "localized_scripts_en-US_TikTok.md").exists()


def test_cli_localize_reports_empty_project(tmp_path):
    project_dir = tmp_path / "project"

    result = CliRunner().invoke(
        cli.app,
        ["localize", "--mock", "--project-dir", str(project_dir)],
    )

    assert result.exit_code == 1
    assert "No completed rounds found" in result.output


def test_cli_ad_assets_mock_writes_outputs(tmp_path, happy_round_outputs):
    project_dir = tmp_path / "project"
    store = ProjectStore(project_dir)
    store.write_round_result(build_round_result(1, happy_round_outputs))
    store.write_round_artifact(
        1,
        "localization_en-US_TikTok",
        demo_localization_output(locale="en-US", platform="TikTok"),
    )

    result = CliRunner().invoke(
        cli.app,
        [
            "ad-assets",
            "--mock",
            "--project-dir",
            str(project_dir),
            "--locale",
            "en-US",
            "--platform",
            "TikTok",
        ],
    )

    json_path = project_dir / "round_001" / "marketing_assets_en-US_TikTok.json"
    markdown_path = project_dir / "round_001" / "marketing_assets_en-US_TikTok.md"
    assets = json.loads(json_path.read_text(encoding="utf-8"))
    assert result.exit_code == 0
    assert "Ad assets round: 1" in result.stdout
    assert assets["campaign_angle"] == "Public humiliation turns into an identity mystery."
    assert "They Threw Her Out" in markdown_path.read_text(encoding="utf-8")


def test_cli_ad_assets_reports_empty_project(tmp_path):
    project_dir = tmp_path / "project"

    result = CliRunner().invoke(
        cli.app,
        ["ad-assets", "--mock", "--project-dir", str(project_dir)],
    )

    assert result.exit_code == 1
    assert "No completed rounds found" in result.output


def test_cli_export_video_brief_writes_outputs(tmp_path, happy_round_outputs):
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
            "60",
        ],
    )
    payload = json.loads(
        (project_dir / "round_001" / "video_brief.json").read_text(encoding="utf-8")
    )

    assert result.exit_code == 0
    assert "Video brief round: 1" in result.stdout
    assert payload["episodes"][0]["target_duration_seconds"] == 60
    assert (project_dir / "round_001" / "video_brief.md").exists()


def test_cli_export_video_brief_reports_empty_project(tmp_path):
    project_dir = tmp_path / "project"

    result = CliRunner().invoke(
        cli.app,
        ["export-video-brief", "--project-dir", str(project_dir)],
    )

    assert result.exit_code == 1
    assert "No completed rounds found" in result.output


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


def test_cli_status_lists_localization_and_marketing_artifacts(
    tmp_path,
    happy_round_outputs,
):
    project_dir = tmp_path / "project"
    store = ProjectStore(project_dir)
    store.write_round_result(build_round_result(1, happy_round_outputs))
    store.write_round_artifact(
        1,
        "localization_en-US_TikTok",
        demo_localization_output(locale="en-US", platform="TikTok"),
    )
    store.write_round_artifact(
        1,
        "marketing_assets_en-US_TikTok",
        demo_marketing_assets(locale="en-US", platform="TikTok"),
    )

    result = CliRunner().invoke(
        cli.app,
        ["status", "--project-dir", str(project_dir)],
    )

    assert result.exit_code == 0
    assert "Localizations: en-US_TikTok" in result.stdout
    assert "Marketing assets: en-US_TikTok" in result.stdout


def test_cli_status_json_output_includes_round_deliverables(
    tmp_path,
    happy_round_outputs,
):
    project_dir = tmp_path / "project"
    store = ProjectStore(project_dir)
    store.write_round_result(build_round_result(1, happy_round_outputs))
    store.write_next_round_context(build_round_result(1, happy_round_outputs))
    store.write_round_artifact(
        1,
        "localization_en-US_TikTok",
        demo_localization_output(locale="en-US", platform="TikTok"),
    )
    store.write_round_artifact(
        1,
        "marketing_assets_en-US_TikTok",
        demo_marketing_assets(locale="en-US", platform="TikTok"),
    )

    result = CliRunner().invoke(
        cli.app,
        ["status", "--project-dir", str(project_dir), "--json-output"],
    )
    payload = json.loads(result.stdout)

    assert result.exit_code == 0
    assert payload["round_count"] == 1
    assert payload["current_episode"] == 1
    assert payload["rounds"][0]["quality_status"] == "usable"
    assert payload["rounds"][0]["localizations"] == ["en-US_TikTok"]
    assert payload["rounds"][0]["marketing_assets"] == ["en-US_TikTok"]
    assert payload["latest_context"].endswith("next_round_context.json")


def test_cli_status_json_output_handles_empty_project(tmp_path):
    project_dir = tmp_path / "project"

    result = CliRunner().invoke(
        cli.app,
        ["status", "--project-dir", str(project_dir), "--json-output"],
    )
    payload = json.loads(result.stdout)

    assert result.exit_code == 0
    assert payload["round_count"] == 0
    assert payload["rounds"] == []
    assert payload["latest_context"] is None


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


def test_cli_export_delivery_writes_zip(tmp_path, happy_round_outputs):
    project_dir = tmp_path / "project"
    store = ProjectStore(project_dir)
    store.write_round_result(build_round_result(1, happy_round_outputs))
    store.write_text_artifact(1, "rendered_scripts.md", "script text")

    result = CliRunner().invoke(
        cli.app,
        [
            "export-delivery",
            "--project-dir",
            str(project_dir),
        ],
    )

    zip_path = project_dir / "round_001" / "delivery_round_001.zip"
    assert result.exit_code == 0
    assert "Delivery package exported:" in result.stdout
    assert zip_path.exists()


def test_cli_export_delivery_blocks_review_issues(tmp_path, happy_round_outputs):
    project_dir = tmp_path / "project"
    store = ProjectStore(project_dir)
    result = build_round_result(1, happy_round_outputs)
    store.write_round_result(result)
    store.write_text_artifact(1, "rendered_scripts.md", "script text")
    profile_path = tmp_path / "profile.json"
    profile_path.write_text(
        json.dumps(
            {
                "profile_id": "us_tiktok",
                "locale": "en-US",
                "platform": "TikTok",
                "target_language": "en",
                "forbidden_terms": ["林晚"],
            }
        ),
        encoding="utf-8",
    )
    CliRunner().invoke(
        cli.app,
        [
            "export-localization",
            "--project-dir",
            str(project_dir),
            "--profile",
            str(profile_path),
        ],
    )

    result = CliRunner().invoke(
        cli.app,
        ["export-delivery", "--project-dir", str(project_dir)],
    )

    assert result.exit_code == 1
    assert "Delivery package blocked" in result.output
    assert "review issue" in result.output


def test_cli_export_delivery_allows_review_issues(tmp_path, happy_round_outputs):
    project_dir = tmp_path / "project"
    store = ProjectStore(project_dir)
    result = build_round_result(1, happy_round_outputs)
    store.write_round_result(result)
    store.write_text_artifact(1, "rendered_scripts.md", "script text")
    profile_path = tmp_path / "profile.json"
    profile_path.write_text(
        json.dumps(
            {
                "profile_id": "us_tiktok",
                "locale": "en-US",
                "platform": "TikTok",
                "target_language": "en",
                "forbidden_terms": ["林晚"],
            }
        ),
        encoding="utf-8",
    )
    CliRunner().invoke(
        cli.app,
        [
            "export-localization",
            "--project-dir",
            str(project_dir),
            "--profile",
            str(profile_path),
        ],
    )

    result = CliRunner().invoke(
        cli.app,
        ["export-delivery", "--allow-issues", "--project-dir", str(project_dir)],
    )

    assert result.exit_code == 0
    assert (project_dir / "round_001" / "delivery_round_001.zip").exists()


def test_cli_check_delivery_reports_ready(tmp_path, happy_round_outputs):
    project_dir = tmp_path / "project"
    store = ProjectStore(project_dir)
    store.write_round_result(build_round_result(1, happy_round_outputs))
    store.write_text_artifact(1, "rendered_scripts.md", "script text")

    result = CliRunner().invoke(
        cli.app,
        ["check-delivery", "--project-dir", str(project_dir)],
    )

    assert result.exit_code == 0
    assert "Delivery ready: yes" in result.stdout
    assert "Quality: usable" in result.stdout
    assert "Files: 2" in result.stdout


def test_cli_check_delivery_strict_fails_on_warnings(tmp_path, happy_round_outputs):
    project_dir = tmp_path / "project"
    store = ProjectStore(project_dir)
    store.write_round_result(build_round_result(1, happy_round_outputs))

    result = CliRunner().invoke(
        cli.app,
        ["check-delivery", "--strict", "--project-dir", str(project_dir)],
    )

    assert result.exit_code == 1
    assert "Delivery ready: no" in result.stdout
    assert "missing required artifact: rendered_scripts.md" in result.stdout
    assert "Delivery preflight failed" in result.output


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


def test_cli_export_localization_can_rewrite_with_llm(
    tmp_path,
    happy_round_outputs,
    monkeypatch,
):
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
                "forbidden_terms": ["heiress"],
            }
        ),
        encoding="utf-8",
    )
    rewrite = LocalizationRewrite(
        episodes=[
            LocalizedEpisodePackage(
                episode=1,
                title="Kicked Out of the Gala",
                hook_3s="Throw her out!",
                main_emotion="public humiliation",
                watch_reason="Viewers want the comeback.",
                cliffhanger="The butler calls her the heiress.",
                scenes=[
                    LocalizedScene(
                        heading="1-1 Night / Interior / Gala",
                        characters=["Lena", "Selena", "Grant"],
                        adapted_lines=["Grant: Get out."],
                    )
                ],
            )
        ]
    )
    monkeypatch.setattr(cli, "build_llm", lambda model=None: StaticJsonLLM([rewrite]))

    result = CliRunner().invoke(
        cli.app,
        [
            "export-localization",
            "--rewrite-with-llm",
            "--project-dir",
            str(project_dir),
            "--profile",
            str(profile_path),
            "--model",
            "gpt-test",
        ],
    )

    json_path = project_dir / "round_001" / "localization_us_tiktok_llm.json"
    assert result.exit_code == 0
    assert "Rewrite: llm" in result.stdout
    assert "Review issues: 1" in result.stdout
    assert json_path.exists()
    assert "Kicked Out of the Gala" in json_path.read_text(encoding="utf-8")


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
