from novel_drama_engine.models import RoundResult
from novel_drama_engine.video_brief import build_video_brief, render_video_brief_markdown


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

    brief = build_video_brief(result, target_duration_seconds=75)

    assert brief.project_id == "demo"
    assert brief.target_episode_range == "EP01-EP05"
    assert brief.episodes[0].aspect_ratio == "9:16"
    assert brief.episodes[0].target_duration_seconds == 75
    assert brief.episodes[0].shots[0].shot_id == "EP01-S01"
    assert "开场三秒直接进入可见冲突：把她拖出去！" in brief.episodes[0].shots[0].visual_prompt
    assert "最后一镜停在未完成动作或强反应：" in brief.episodes[0].shots[-1].visual_prompt
    assert "顾承（冷）：滚出去。" in brief.episodes[0].shots[0].dialogue_beats
    assert any(
        item.startswith("道具状态：")
        for item in brief.episodes[0].shots[0].asset_requirements
    )


def test_render_video_brief_markdown(happy_round_outputs):
    result = build_round_result(1, happy_round_outputs)
    brief = build_video_brief(result)

    text = render_video_brief_markdown(brief)

    assert "# Video Brief Round 1" in text
    assert "## EP01 被赶出生日宴" in text
    assert "### EP01-S01 1-1 夜-内-林家宴会厅" in text
    assert "Visual prompt:" in text
    assert "3s hook:" not in text
    assert "Main emotion:" not in text
    assert "- 顾承（冷）：滚出去。" in text
