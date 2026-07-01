import json
import zipfile

import pytest

from novel_drama_engine.delivery import (
    DeliveryValidationError,
    build_delivery_preflight_report,
    export_delivery_package,
)
from novel_drama_engine.demo import demo_localization_output
from novel_drama_engine.localization import build_localization_package
from novel_drama_engine.models import (
    LocalizationProfile,
    QualityStatus,
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


def test_export_delivery_package_includes_round_artifacts(tmp_path, happy_round_outputs):
    store = ProjectStore(tmp_path)
    result = build_round_result(1, happy_round_outputs)
    store.write_round_result(result)
    store.write_text_artifact(1, "rendered_scripts.md", "script text")
    store.write_text_artifact(1, "video_brief.md", "video brief")

    zip_path = export_delivery_package(store)

    assert zip_path == tmp_path / "round_001" / "delivery_round_001.zip"
    with zipfile.ZipFile(zip_path) as archive:
        names = set(archive.namelist())
        manifest = json.loads(archive.read("delivery_manifest.json"))

    assert "round_001/round_result.json" in names
    assert "round_001/rendered_scripts.md" in names
    assert "round_001/video_brief.md" in names
    assert "round_001/delivery_round_001.zip" not in names
    assert manifest["project_id"] == "demo"
    assert manifest["round_number"] == 1
    assert manifest["quality_status"] == "usable"
    assert manifest["warnings"] == []
    assert any(item["path"] == "round_001/video_brief.md" for item in manifest["included_files"])


def test_export_delivery_package_accepts_custom_output(tmp_path, happy_round_outputs):
    store = ProjectStore(tmp_path / "project")
    store.write_round_result(build_round_result(2, happy_round_outputs))
    store.write_text_artifact(2, "rendered_scripts.md", "script text")
    output_path = tmp_path / "exports" / "demo.zip"

    zip_path = export_delivery_package(store, round_number=2, output_path=output_path)

    assert zip_path == output_path
    assert zip_path.exists()


def test_export_delivery_package_blocks_non_usable_quality(tmp_path, happy_round_outputs):
    store = ProjectStore(tmp_path)
    result = build_round_result(1, happy_round_outputs)
    result = result.model_copy(
        update={
            "quality_report": result.quality_report.model_copy(
                update={"status": QualityStatus.NEEDS_HUMAN_REVIEW}
            )
        }
    )
    store.write_round_result(result)
    store.write_text_artifact(1, "rendered_scripts.md", "script text")

    with pytest.raises(DeliveryValidationError) as exc_info:
        export_delivery_package(store)

    assert "quality status is needs_human_review" in str(exc_info.value)


def test_export_delivery_package_allows_warnings_when_requested(tmp_path, happy_round_outputs):
    store = ProjectStore(tmp_path)
    result = build_round_result(1, happy_round_outputs)
    profile = LocalizationProfile(
        profile_id="us_tiktok",
        locale="en-US",
        platform="TikTok",
        target_language="en",
        forbidden_terms=["林晚"],
    )
    package = build_localization_package(result, profile)
    store.write_round_result(result)
    store.write_text_artifact(1, "rendered_scripts.md", "script text")
    store.write_round_artifact(1, "localization_us_tiktok", package)

    zip_path = export_delivery_package(store, allow_issues=True)

    with zipfile.ZipFile(zip_path) as archive:
        manifest = json.loads(archive.read("delivery_manifest.json"))

    assert "localization_us_tiktok.json has 2 localization review issue(s)" in manifest["warnings"]


def test_build_delivery_preflight_report_ready(tmp_path, happy_round_outputs):
    store = ProjectStore(tmp_path)
    store.write_round_result(build_round_result(1, happy_round_outputs))
    store.write_text_artifact(1, "rendered_scripts.md", "script text")

    report = build_delivery_preflight_report(store)

    assert report.ready is True
    assert report.warnings == []
    assert report.quality_status == "usable"
    assert any(file.path == "round_001/rendered_scripts.md" for file in report.files)


def test_build_delivery_preflight_report_warns_on_missing_artifacts(
    tmp_path,
    happy_round_outputs,
):
    store = ProjectStore(tmp_path)
    store.write_round_result(build_round_result(1, happy_round_outputs))

    report = build_delivery_preflight_report(store)

    assert report.ready is False
    assert "missing required artifact: rendered_scripts.md" in report.warnings


def test_build_delivery_preflight_report_warns_on_legacy_localization_json(
    tmp_path,
    happy_round_outputs,
):
    store = ProjectStore(tmp_path)
    store.write_round_result(build_round_result(1, happy_round_outputs))
    store.write_text_artifact(1, "rendered_scripts.md", "script text")
    store.write_round_artifact(
        1,
        "localization_en-US_TikTok",
        demo_localization_output(locale="en-US", platform="TikTok"),
    )

    report = build_delivery_preflight_report(store)

    assert report.ready is False
    assert (
        "localization_en-US_TikTok.json is not a delivery localization package"
        in report.warnings
    )
