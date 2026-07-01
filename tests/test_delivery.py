import json
import zipfile

from novel_drama_engine.delivery import export_delivery_package
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
    assert any(item["path"] == "round_001/video_brief.md" for item in manifest["included_files"])


def test_export_delivery_package_accepts_custom_output(tmp_path, happy_round_outputs):
    store = ProjectStore(tmp_path / "project")
    store.write_round_result(build_round_result(2, happy_round_outputs))
    output_path = tmp_path / "exports" / "demo.zip"

    zip_path = export_delivery_package(store, round_number=2, output_path=output_path)

    assert zip_path == output_path
    assert zip_path.exists()
