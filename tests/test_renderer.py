from novel_drama_engine.renderer import render_episode, render_round_summary


def test_render_episode_outputs_short_drama_format(happy_round_outputs):
    script_batch = happy_round_outputs[3]

    text = render_episode(script_batch.episodes[0])

    assert "第1集 被赶出生日宴" in text
    assert "1-1 夜-内-林家宴会厅" in text
    assert "人物：林晚、林雪、顾承" in text
    assert "顾承（冷）：滚出去。" in text
    assert "3秒 Hook" not in text
    assert "主情绪" not in text
    assert "消费理由" not in text
    assert "结尾钩子" not in text


def test_render_round_summary_includes_quality_status(happy_round_outputs):
    quality = happy_round_outputs[4]
    script_batch = happy_round_outputs[3]

    text = render_round_summary(script_batch, quality)

    assert "质量结论：usable" in text
    assert "Hook: 9" in text
