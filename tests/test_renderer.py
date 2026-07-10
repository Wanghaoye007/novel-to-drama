from novel_drama_engine.renderer import (
    render_creative_episode,
    render_episode,
    render_round_summary,
    render_shooting_episode,
)
from novel_drama_engine.models import EpisodeScript, Scene, SceneLine


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


def test_render_creative_episode_removes_shooting_prefix(happy_round_outputs):
    script_batch = happy_round_outputs[3]

    text = render_creative_episode(script_batch.episodes[0])

    assert "# EPISODE 1" in text
    assert "▲ 过生日宴长桌" in text
    assert "△中近景推近" not in text
    assert "顾承（冷）：滚出去。" in text


def test_shooting_renderer_adds_camera_fallback_without_mutating_creative_script():
    episode = EpisodeScript(
        episode=1,
        title="门口对峙",
        hook_3s="别碰她。",
        main_emotion="压迫",
        watch_reason="内部字段",
        scenes=[
            Scene(
                heading="1-1 夜-内-宴会厅门口",
                characters=["林晚"],
                lines=[
                    SceneLine(kind="action", text="林晚攥紧被撕碎的邀请函。"),
                    SceneLine(kind="dialogue", speaker="林晚", text="我自己走。"),
                ],
            )
        ],
        cliffhanger="门外有人喊住她。",
        state_update={},
    )

    creative = render_creative_episode(episode)
    shooting = render_shooting_episode(episode)

    assert "▲ 林晚攥紧被撕碎的邀请函。" in creative
    assert "中近景推近" not in creative
    assert "△中近景推近，林晚攥紧被撕碎的邀请函。" in shooting
    assert episode.scenes[0].lines[0].text == "林晚攥紧被撕碎的邀请函。"
