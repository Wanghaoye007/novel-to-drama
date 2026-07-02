from novel_drama_engine.models import EpisodeContext, StoryStage
from novel_drama_engine.source_packets import build_episode_source_packets


def test_episode_source_packets_extract_heading_sections_without_cross_episode_bleed():
    source_text = """
# 第 1 集
一号名场面。林晚在宴会厅被逼到墙角。

# 第 2 集
二号秘密。助理拿出私人飞机钥匙。
"""
    context = EpisodeContext(
        target_episode_range="EP01-EP02",
        story_stage=StoryStage.OPENING_PRESSURE,
        source_to_episode_mapping=[
            {
                "source": "第 1 集宴会厅羞辱",
                "target_episode": "EP01",
                "retained_assets": ["一号名场面"],
                "information_increment": "女主被公开压迫。",
                "adaptation_action": "保留宴会厅压迫。",
            },
            {
                "source": "第 2 集助理身份反差",
                "target_episode": "EP02",
                "retained_assets": ["二号秘密"],
                "information_increment": "助理身份抬升。",
                "adaptation_action": "保留私人飞机钥匙。",
            },
        ],
        must_carry_context=[],
        forbidden_reveals=["不能提前暴露霍家全貌"],
        adaptation_actions=[],
        confidence=0.9,
    )

    packets = build_episode_source_packets(
        source_text=source_text,
        episode_context=context,
        target_episode_count=2,
    )

    first, second = packets.packets
    assert first.episode == 1
    assert "一号名场面" in first.source_excerpt
    assert "二号秘密" not in first.source_excerpt
    assert "一号名场面" in first.c1_must_keep_assets
    assert second.episode == 2
    assert "二号秘密" in second.source_excerpt
