from novel_drama_engine.demo import demo_localization_output
from novel_drama_engine.renderer import (
    render_episode,
    render_localization_result,
    render_round_summary,
)


def test_render_episode_outputs_short_drama_format(happy_round_outputs):
    script_batch = happy_round_outputs[3]

    text = render_episode(script_batch.episodes[0])

    assert "第1集 被赶出生日宴" in text
    assert "1-1 夜-内-林家宴会厅" in text
    assert "人物：林晚、林雪、顾承" in text
    assert "顾承（冷）：滚出去。" in text


def test_render_round_summary_includes_quality_status(happy_round_outputs):
    quality = happy_round_outputs[4]
    script_batch = happy_round_outputs[3]

    text = render_round_summary(script_batch, quality)

    assert "质量结论：usable" in text
    assert "Hook: 9" in text


def test_render_localization_result_includes_notes_and_script():
    localized = demo_localization_output(locale="en-US", platform="TikTok")

    text = render_localization_result(localized)

    assert "Locale: en-US" in text
    assert "Adaptation Notes:" in text
    assert "Episode 1: Thrown Out at the Birthday Banquet" in text
    assert "Grant (cold): Get out." in text
