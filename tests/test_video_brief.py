import json

from novel_drama_engine.models import RoundResult
from novel_drama_engine.storage import ProjectStore
from novel_drama_engine.video_brief import build_video_brief, export_project_video_brief


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


def test_build_video_brief_from_round_result(happy_round_outputs):
    round_result = build_round_result(1, happy_round_outputs)

    brief = build_video_brief(round_result, duration_seconds=60, aspect_ratio="9:16")

    assert brief.project_id == "demo"
    assert brief.target_episode_range == "EP01-EP01"
    assert brief.episodes[0].target_duration_seconds == 60
    assert brief.episodes[0].aspect_ratio == "9:16"
    assert brief.episodes[0].shots[0].visual_prompt
    assert brief.episodes[0].shots[0].dialogue_beats


def test_export_project_video_brief_writes_json_and_markdown(tmp_path, happy_round_outputs):
    store = ProjectStore(tmp_path)
    store.write_round_result(build_round_result(1, happy_round_outputs))

    brief, json_path, markdown_path = export_project_video_brief(
        store=store,
        round_number=1,
        duration_seconds=60,
        aspect_ratio="9:16",
    )
    payload = json.loads(json_path.read_text(encoding="utf-8"))
    markdown = markdown_path.read_text(encoding="utf-8")

    assert brief.episodes[0].target_duration_seconds == 60
    assert payload["episodes"][0]["shots"][0]["source_scene"]
    assert "# Video Production Brief" in markdown
    assert "Aspect Ratio: 9:16" in markdown
