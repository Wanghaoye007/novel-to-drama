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
    build_source_packet_confidence_report,
    normalize_story_bible_against_source_packets,
    render_source_packet_confidence_report,
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


def test_source_packets_reject_future_episode_assets_even_when_mapping_points_ahead():
    source_text = """
# Episode 5
霍雅偷拍照片，说两个人站在一起太养眼。
林挽清平静地说，对于路淮北，我已经没有期待了。
私人手机响起，路淮北威胁说我现在就去找你。

# Episode 7
雪夜烟花盛开，霍庭琛揉过林挽清冻红的耳朵，两人在烟花下亲吻。
"""
    context = EpisodeContext(
        target_episode_range="EP05-EP05",
        story_stage=StoryStage.MISUNDERSTANDING_ESCALATION,
        source_to_episode_mapping=[
            {
                "source": "Episode 7: 雪夜烟花亲吻",
                "target_episode": "EP05",
                "retained_assets": ["雪夜烟花", "揉耳朵", "亲吻"],
                "information_increment": "两人正式进入亲密关系。",
                "adaptation_action": "把雪夜亲吻提前成宣战。",
            },
        ],
        must_carry_context=[],
        forbidden_reveals=[],
        adaptation_actions=[],
        confidence=0.9,
    )
    plan = EpisodePlan(
        variant=GenerationVariant.DRAMA_ENGINE_FIRST,
        target_episode_range="EP05-EP05",
        adaptation_strategy="错误提前后文",
        episodes=[
            {
                "episode": 5,
                "title": "雪夜吻",
                "drama_engine": "通过雪夜烟花亲吻公开两人关系。",
                "protagonist_misbelief": "她以为自己只是在疗愈。",
                "truth_gap": "路淮北正在追踪手机。",
                "physical_action_chain": [
                    "霍庭琛揉过林挽清冻红的耳朵。",
                    "两人在烟花下亲吻。",
                    "路淮北追踪手机位置。",
                ],
                "scene_dynamics": ["雪夜观景台亲吻。", "手机定位红点闪烁。"],
                "emotional_turns": ["疗愈", "宣战"],
                "audience_information_gap": "路淮北不知道她已经换人保护。",
                "three_pull_beats": ["揉耳朵", "亲吻", "定位威胁"],
                "false_payoff": "观众以为雪夜亲吻会平静，结果路淮北追踪手机。",
                "planted_key": "雪夜烟花照片。",
                "strongest_line": "这不是吻，是宣战。",
                "cliffhanger_design": "雪夜亲吻中弹出路淮北追踪手机的威胁。",
                "source_assets_to_keep": ["雪夜烟花", "揉耳朵", "亲吻"],
                "forbidden_shortcuts": ["不得提前解决舆论战"],
            }
        ],
    )

    packets = build_episode_source_packets(
        source_text=source_text,
        episode_context=context,
        episode_plan=plan,
        target_episode_count=7,
    )
    packet = packets.packets[0]
    packet_text = " ".join(
        [
            packet.source_anchor,
            *packet.c0_facts,
            *packet.c1_must_keep_assets,
            *packet.c2_visual_assets,
            *packet.golden_lines,
        ]
    )

    assert "霍雅偷拍照片" in packet.source_excerpt
    assert "雪夜烟花盛开" not in packet.source_excerpt
    assert "Episode 7" not in packet.source_anchor
    assert "雪夜" not in packet_text
    assert "亲吻" not in packet_text

    sanitized = sanitize_episode_plan_against_source_packets(plan, packets)
    episode = sanitized.episodes[0]
    sanitized_text = " ".join(
        [
            episode.drama_engine,
            episode.false_payoff,
            episode.planted_key,
            episode.strongest_line,
            episode.cliffhanger_design,
            *episode.physical_action_chain,
            *episode.scene_dynamics,
            *episode.source_assets_to_keep,
        ]
    )

    assert "雪夜" not in sanitized_text
    assert "亲吻" not in sanitized_text
    assert "追踪手机" not in sanitized_text
    assert "霍雅偷拍照片" in sanitized_text


def test_source_packet_confidence_blocks_long_proportional_fallback_without_evidence_assets():
    source_text = "\n".join(
        [
            f"第{i}段，林挽清在颁奖礼后台承受羞辱，路淮北把她藏在镜头之外。"
            for i in range(900)
        ]
    )
    context = EpisodeContext(
        target_episode_range="EP02-EP02",
        story_stage=StoryStage.OPENING_PRESSURE,
        source_to_episode_mapping=[
            {
                "source": "不存在的第二集锚点",
                "target_episode": "EP02",
                "retained_assets": ["不存在的雪地烟火激吻"],
                "information_increment": "不存在的信息增量",
                "adaptation_action": "不存在的动作",
            }
        ],
        must_carry_context=[],
        forbidden_reveals=[],
        adaptation_actions=[],
        confidence=0.9,
    )

    packets = build_episode_source_packets(
        source_text=source_text,
        episode_context=context,
        target_episode_count=5,
    )
    report = build_source_packet_confidence_report(
        packets,
        source_text=source_text,
        target_episode_count=5,
    )

    assert report.status == "blocking"
    assert report.items[0].selection_method == "proportional_fallback"
    assert report.items[0].evidence_asset_count == 0
    assert any("EP02" in warning for warning in report.blocking_warnings)
    assert "proportional_fallback" in render_source_packet_confidence_report(report)
