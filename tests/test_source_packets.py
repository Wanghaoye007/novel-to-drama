from novel_drama_engine.models import (
    EpisodeContext,
    EpisodePlan,
    EpisodeSourcePacket,
    EpisodeSourcePackets,
    GenerationVariant,
    StoryBible,
    StoryStage,
)
from novel_drama_engine.source_packets import (
    build_episode_source_packets,
    normalize_story_bible_against_source_packets,
    sanitize_episode_plan_against_source_packets,
    story_bible_source_packet_conflicts,
)


def test_story_bible_forbidden_changes_do_not_override_source_packet_required_assets():
    bible = StoryBible(
        genre="豪门",
        mainline="林晚在公开羞辱中反击。",
        characters=["林晚"],
        relationships=[],
        speech_styles={},
        immutable_facts=[],
        forbidden_changes=["不得新增亲哥哥救场", "不得提前公开亲子鉴定"],
    )
    packets = EpisodeSourcePackets(
        packets=[
            EpisodeSourcePacket(
                episode=1,
                source_anchor="亲哥哥救场",
                source_excerpt="林晚被赶出时，亲哥哥突然救场。",
                c1_must_keep_assets=["亲哥哥救场"],
            )
        ]
    )

    conflicts = story_bible_source_packet_conflicts(bible, packets)
    normalized = normalize_story_bible_against_source_packets(bible, packets)

    assert conflicts == ["不得新增亲哥哥救场"]
    assert normalized.forbidden_changes == ["不得提前公开亲子鉴定"]


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


def test_episode_source_packets_keep_plan_assets_out_of_source_evidence():
    source_text = """
# 第 1 集
婚礼夜冷暴力。林婉晴被规矩纸压到餐桌前。

# 第 2 集
林婉晴把外卖袋放上餐桌，反问傅家会不会饿死。

# 第 3 集
傅盈盈伸手推人，林婉晴反手别住她的手腕。
"""
    context = EpisodeContext(
        target_episode_range="EP01-EP01",
        story_stage=StoryStage.OPENING_PRESSURE,
        source_to_episode_mapping=[
            {
                "source": "婚礼夜冷暴力与规矩纸",
                "target_episode": "EP01",
                "retained_assets": ["婚礼夜冷暴力", "规矩纸"],
                "information_increment": "傅家规矩压迫新婚妻子。",
                "adaptation_action": "保留餐桌规矩纸压迫。",
            },
        ],
        must_carry_context=[],
        forbidden_reveals=[],
        adaptation_actions=[],
        confidence=0.9,
    )
    plan = EpisodePlan(
        variant=GenerationVariant.DRAMA_ENGINE_FIRST,
        target_episode_range="EP01-EP01",
        adaptation_strategy="测试计划污染",
        episodes=[
            {
                "episode": 1,
                "title": "错位计划",
                "drama_engine": "压迫反击",
                "protagonist_misbelief": "忍一忍",
                "truth_gap": "傅家规矩只是控制工具",
                "physical_action_chain": [
                    "林婉晴把外卖袋放上餐桌。",
                    "傅盈盈伸手推人，林婉晴反手别住她的手腕。",
                    "林婉晴把规矩纸折进兜里。",
                ],
                "scene_dynamics": [
                    "餐桌规矩纸压迫。",
                    "厨房外卖袋成为反击道具。",
                ],
                "emotional_turns": ["压迫", "克制"],
                "audience_information_gap": "傅家不知道她不是软柿子。",
                "three_pull_beats": ["婆婆压迫", "小姑挑衅", "女主接下规矩"],
                "false_payoff": "傅家以为规矩能压住她。",
                "planted_key": "规矩纸",
                "strongest_line": "这规矩，我记住了。",
                "cliffhanger_design": "她折起规矩纸。",
                "source_assets_to_keep": ["婚礼夜冷暴力", "外卖袋", "反手别腕"],
                "forbidden_shortcuts": ["不得提前写外卖打脸"],
            }
        ],
    )

    packets = build_episode_source_packets(
        source_text=source_text,
        episode_context=context,
        episode_plan=plan,
        target_episode_count=3,
    )
    packet = packets.packets[0]

    assert packet.c1_must_keep_assets == ["婚礼夜冷暴力", "规矩纸"]
    assert packet.c2_visual_assets == ["保留餐桌规矩纸压迫。"]
    assert "外卖袋" not in " ".join(packet.c1_must_keep_assets + packet.c2_visual_assets)
    assert "反手别住" not in " ".join(packet.c1_must_keep_assets + packet.c2_visual_assets)


def test_light_edit_plan_sanitizer_drops_assets_not_in_current_source_packet():
    source_text = """
# 第 1 集
婚礼夜冷暴力。林婉晴被规矩纸压到餐桌前。

# 第 2 集
林婉晴把外卖袋放上餐桌，反问傅家会不会饿死。
"""
    context = EpisodeContext(
        target_episode_range="EP01-EP01",
        story_stage=StoryStage.OPENING_PRESSURE,
        source_to_episode_mapping=[
            {
                "source": "婚礼夜冷暴力与规矩纸",
                "target_episode": "EP01",
                "retained_assets": ["婚礼夜冷暴力", "规矩纸"],
                "information_increment": "傅家规矩压迫新婚妻子。",
                "adaptation_action": "保留餐桌规矩纸压迫。",
            },
        ],
        must_carry_context=[],
        forbidden_reveals=[],
        adaptation_actions=[],
        confidence=0.9,
    )
    plan = EpisodePlan(
        variant=GenerationVariant.DRAMA_ENGINE_FIRST,
        target_episode_range="EP01-EP01",
        adaptation_strategy="轻改计划",
        episodes=[
            {
                "episode": 1,
                "title": "轻改",
                "drama_engine": "压迫反击",
                "protagonist_misbelief": "忍一忍",
                "truth_gap": "傅家规矩只是控制工具",
                "physical_action_chain": [
                    "林婉晴把规矩纸折进兜里。",
                    "林婉晴把外卖袋放上餐桌。",
                    "傅盈盈被反手别腕。",
                ],
                "scene_dynamics": [
                    "餐桌规矩纸压迫。",
                    "厨房外卖袋成为反击道具。",
                ],
                "emotional_turns": ["压迫", "克制"],
                "audience_information_gap": "傅家不知道她不是软柿子。",
                "three_pull_beats": ["婆婆压迫", "小姑挑衅", "女主接下规矩"],
                "false_payoff": "傅家以为规矩能压住她。",
                "planted_key": "规矩纸",
                "strongest_line": "这规矩，我记住了。",
                "cliffhanger_design": "她折起规矩纸。",
                "source_assets_to_keep": ["婚礼夜冷暴力", "规矩纸", "外卖袋"],
                "forbidden_shortcuts": ["不得提前写外卖打脸"],
            }
        ],
    )
    packets = build_episode_source_packets(
        source_text=source_text,
        episode_context=context,
        target_episode_count=2,
    )

    sanitized = sanitize_episode_plan_against_source_packets(plan, packets)
    episode = sanitized.episodes[0]

    assert episode.source_assets_to_keep == ["婚礼夜冷暴力", "规矩纸"]
    assert "林婉晴把规矩纸折进兜里。" in episode.physical_action_chain
    assert "餐桌规矩纸压迫。" in episode.scene_dynamics
    assert len(episode.physical_action_chain) >= 3
    assert len(episode.scene_dynamics) >= 2
    assert "外卖袋" not in " ".join(
        episode.source_assets_to_keep
        + episode.physical_action_chain
        + episode.scene_dynamics
    )
    assert "反手别腕" not in " ".join(episode.physical_action_chain)
    EpisodePlan.model_validate(sanitized.model_dump())
    assert "外卖袋" not in episode.cliffhanger_design
