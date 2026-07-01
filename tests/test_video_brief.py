import json

from novel_drama_engine.models import RoundResult
from novel_drama_engine.storage import ProjectStore
from novel_drama_engine.video_brief import (
    build_video_brief,
    export_project_video_brief,
    render_video_brief_markdown,
)


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
    result = build_round_result(1, happy_round_outputs)

    brief = build_video_brief(result, duration_seconds=60, aspect_ratio="9:16")

    assert brief.project_id == "demo"
    assert brief.target_episode_range == "EP01-EP01"
    assert brief.profile == "vertical_short_drama"
    assert brief.episodes[0].aspect_ratio == "9:16"
    assert brief.episodes[0].target_duration_seconds == 60
    assert brief.episodes[0].shots[0].shot_id == "EP01-S01"
    assert "前3秒必须打出钩子：把她拖出去！" in brief.episodes[0].shots[0].visual_prompt
    assert "结尾停在钩子：门口老管家一震：大小姐？" in brief.episodes[0].shots[0].visual_prompt
    assert "顾承（冷）：滚出去。" in brief.episodes[0].shots[0].dialogue_beats
    assert "道具状态：邀请函被撕碎" in brief.episodes[0].shots[0].asset_requirements


def test_render_video_brief_markdown(happy_round_outputs):
    result = build_round_result(1, happy_round_outputs)
    brief = build_video_brief(result)

    text = render_video_brief_markdown(brief)

    assert "# Video Brief Round 1" in text
    assert "## EP01 被赶出生日宴" in text
    assert "### EP01-S01 1-1 夜-内-林家宴会厅" in text
    assert "Visual prompt:" in text
    assert "- 顾承（冷）：滚出去。" in text


def test_export_project_video_brief_writes_json_and_markdown(
    tmp_path,
    happy_round_outputs,
):
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
    assert payload["episodes"][0]["shots"][0]["shot_id"] == "EP01-S01"
    assert "# Video Brief Round 1" in markdown
    assert "Aspect ratio: 9:16" in markdown
