from novel_drama_engine.models import (
    EpisodeBeat,
    EpisodeContext,
    EpisodePlan,
    EpisodeSourcePacket,
    EpisodeSourcePackets,
    GenerationVariant,
    StoryBible,
    StoryStage,
)
from novel_drama_engine.source_packets import (
    bind_episode_plan_to_facts,
    build_episode_source_packets,
    build_source_packet_confidence_report,
    normalize_story_bible_against_source_packets,
    render_source_packet_confidence_report,
    sanitize_episode_plan_against_source_packets,
    story_bible_source_packet_conflicts,
)
from novel_drama_engine.source_facts import build_source_fact_ledger, facts_for_episode


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


def test_episode_source_packets_group_shooting_scene_headings_by_episode():
    source_text = """
1-1 夜-外-博物馆门口
林修签下夜班合同，苏秘书烧毁合同。

1-2 夜-内-博物馆大厅
规则书渗出血字。

2-1 夜-内-青铜展厅
林修开始修复八臂修罗。

3-1 日-外-城市废墟
白捷捻起金色粉末，追查昨夜出手的大能。

3-2 日-内-博物馆办公室
胖子发来现场视频，林修认出八臂修罗。

4-1 夜-内-博物馆展厅
苏秘书宣布修复奖金翻十倍。
"""
    context = EpisodeContext(
        target_episode_range="EP01-EP04",
        story_stage=StoryStage.OPENING_PRESSURE,
        source_to_episode_mapping=[
            {
                "source": "3-1至3-2段落（白捷调查，林修看到视频）",
                "target_episode": "EP03",
                "retained_assets": ["白捷捻起金色粉末", "胖子发来现场视频"],
                "information_increment": "镇灵司开始追查神秘大能。",
                "adaptation_action": "保留林修与外界的信息差。",
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
        target_episode_count=4,
    )
    third = packets.packets[2]
    report = build_source_packet_confidence_report(
        packets,
        source_text=source_text,
        target_episode_count=4,
    )

    assert third.source_selection_method == "heading"
    assert third.source_anchor == "3-1 日-外-城市废墟"
    assert "白捷捻起金色粉末" in third.source_excerpt
    assert "胖子发来现场视频" in third.source_excerpt
    assert "林修开始修复八臂修罗" not in third.source_excerpt
    assert "苏秘书宣布修复奖金翻十倍" not in third.source_excerpt
    assert report.items[2].status != "blocking"


def test_episode_source_packets_do_not_promote_partial_keyword_overlap_to_source_evidence():
    source_text = """
2-1 夜-内-博物馆走廊
林修穿过走廊，看见破碎的八臂修罗。

2-2 夜-内-修复台
林修拿出金缮工具，开始拼接碎片。
"""
    inferred_asset = "守则第5、6条：不能修八臂修罗与注意其他文物反应"
    context = EpisodeContext(
        target_episode_range="EP02-EP02",
        story_stage=StoryStage.OPENING_PRESSURE,
        source_to_episode_mapping=[
            {
                "source": "第2集八臂修罗",
                "target_episode": "EP02",
                "retained_assets": [inferred_asset],
                "information_increment": "林修发现八臂修罗。",
                "adaptation_action": "保留走廊探索。",
            }
        ],
        must_carry_context=[],
        forbidden_reveals=[],
        adaptation_actions=[],
        confidence=0.9,
    )

    packet = build_episode_source_packets(
        source_text=source_text,
        episode_context=context,
        target_episode_count=2,
    ).packets[0]

    assert packet.source_selection_method == "heading"
    assert packet.source_evidence_assets == []
    assert inferred_asset not in packet.c1_must_keep_assets


def test_novel_chapters_are_partitioned_across_target_episodes_instead_of_treated_as_episode_numbers():
    source_text = """
第1章 初见
第一章事件。女主在雨夜捡到戒指。

第2章 误会
第二章事件。男主误认戒指主人。

第3章 对峙
第三章事件。两人在公司正面对峙。

第4章 反转
第四章事件。监控证明戒指来源。
"""
    context = EpisodeContext(
        target_episode_range="EP01-EP02",
        story_stage=StoryStage.OPENING_PRESSURE,
        source_to_episode_mapping=[],
        must_carry_context=[],
        forbidden_reveals=[],
        adaptation_actions=[],
        confidence=0.8,
    )

    packets = build_episode_source_packets(
        source_text=source_text,
        episode_context=context,
        target_episode_count=2,
    )

    first, second = packets.packets
    assert first.source_selection_method == "chapter_partition"
    assert "第一章事件" in first.source_excerpt
    assert "第二章事件" in first.source_excerpt
    assert "第三章事件" not in first.source_excerpt
    assert "第三章事件" in second.source_excerpt
    assert "第四章事件" in second.source_excerpt
    assert first.source_start == source_text.index("第1章")
    assert first.source_end <= second.source_start
    assert first.source_hash
    assert all(not asset.startswith("第1章") for asset in first.c1_must_keep_assets)


def test_bare_numbered_chapters_follow_episode_context_chapter_ranges():
    source_text = "\n\n".join(
        f"\u3000\u3000{number}.\n第{number}章独立事件。线索{number}只在这里出现。"
        + (f"第{number}章补充原文内容。" * 90)
        for number in range(1, 10)
    )
    context = EpisodeContext(
        target_episode_range="EP01-EP05",
        story_stage=StoryStage.OPENING_PRESSURE,
        source_to_episode_mapping=[
            {
                "source": "原文第1-2章：开场行动",
                "target_episode": "EP01",
                "retained_assets": ["开场人物主动设局的强冲突"],
            },
            {
                "source": "原文第3-4章：取得证据",
                "target_episode": "EP02",
                "retained_assets": ["关键物证的近景特写"],
            },
            {
                "source": "原文第5-6章：主动布局",
                "target_episode": "EP03",
                "retained_assets": ["主角扩大舆论压力"],
            },
            {
                "source": "原文第7章：窃听真相",
                "target_episode": "EP04",
                "retained_assets": ["暗室窃听的紧张场景"],
            },
            {
                "source": "原文第8-9章：公开反击",
                "target_episode": "EP05",
                "retained_assets": ["宴会现场的群体冲突"],
            },
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

    assert [packet.source_selection_method for packet in packets.packets] == [
        "chapter_partition"
    ] * 5
    assert "第1章独立事件" in packets.packets[0].source_excerpt
    assert "第2章独立事件" in packets.packets[0].source_excerpt
    assert "第3章独立事件" not in packets.packets[0].source_excerpt
    assert "第3章独立事件" in packets.packets[1].source_excerpt
    assert "第7章独立事件" in packets.packets[3].source_excerpt
    assert "第8章独立事件" in packets.packets[4].source_excerpt
    assert "第9章独立事件" in packets.packets[4].source_excerpt
    assert len({packet.source_hash for packet in packets.packets}) == 5
    assert report.status != "blocking"


def test_overbroad_or_missing_chapter_ranges_fall_back_to_target_episode_budget():
    source_text = "\n\n".join(
        f"{number}.\n第{number}段原文。" + (f"只属于章节{number}的连续剧情。" * 70)
        for number in [*range(1, 11), 12, 13]
    )
    context = EpisodeContext(
        target_episode_range="EP01-EP05",
        story_stage=StoryStage.OPENING_PRESSURE,
        source_to_episode_mapping=[
            {"source": "原文第1-3章开头", "target_episode": "EP01"},
            {"source": "原文第3章后半-6章", "target_episode": "EP02"},
            {"source": "原文第7-8章", "target_episode": "EP03"},
            {"source": "原文第9-10章", "target_episode": "EP04"},
            {"source": "原文第11章", "target_episode": "EP05"},
        ],
        must_carry_context=[],
        forbidden_reveals=[],
        adaptation_actions=[],
        confidence=0.9,
    )

    packets = build_episode_source_packets(
        source_text=source_text,
        episode_context=context,
        target_episode_count=40,
    )

    assert [packet.source_selection_method for packet in packets.packets] == [
        "target_budget_partition"
    ] * 5
    assert [packet.source_start for packet in packets.packets] == sorted(
        packet.source_start for packet in packets.packets
    )
    assert all(
        current.source_end <= following.source_start
        for current, following in zip(packets.packets, packets.packets[1:])
    )
    assert packets.packets[-1].source_end <= len(source_text) * 5 // 40 + 1
    assert all(
        any("目标集数预算" in warning for warning in packet.source_confidence_warnings)
        for packet in packets.packets
    )


def test_chapter_count_is_used_as_episode_budget_when_target_count_is_omitted():
    source_text = "\n".join(
        f"第{number}章 节点{number}\n第{number}章独立事件。"
        for number in range(1, 5)
    )
    context = EpisodeContext(
        target_episode_range="EP01-EP02",
        story_stage=StoryStage.OPENING_PRESSURE,
        source_to_episode_mapping=[],
        must_carry_context=[],
        forbidden_reveals=[],
        adaptation_actions=[],
        confidence=0.8,
    )

    first, second = build_episode_source_packets(
        source_text=source_text,
        episode_context=context,
    ).packets

    assert "第1章独立事件" in first.source_excerpt
    assert "第2章独立事件" not in first.source_excerpt
    assert "第2章独立事件" in second.source_excerpt
    assert "第3章独立事件" not in second.source_excerpt


def test_asset_window_provenance_covers_all_matched_assets_when_excerpt_is_compacted(
    monkeypatch,
):
    monkeypatch.setenv("NOVEL_DRAMA_SOURCE_PACKET_CHARS", "2000")
    source_text = "开场钩子" + ("甲" * 4500) + "结尾证据"
    context = EpisodeContext(
        target_episode_range="EP01",
        story_stage=StoryStage.OPENING_PRESSURE,
        source_to_episode_mapping=[
            {
                "source": "开场钩子",
                "target_episode": "EP01",
                "retained_assets": ["开场钩子", "结尾证据"],
            }
        ],
        must_carry_context=[],
        forbidden_reveals=[],
        adaptation_actions=[],
        confidence=0.9,
    )

    packet = build_episode_source_packets(
        source_text=source_text,
        episode_context=context,
        target_episode_count=1,
    ).packets[0]

    assert packet.source_start == 0
    assert packet.source_end == len(source_text)
    assert "开场钩子" in packet.source_excerpt
    assert "结尾证据" in packet.source_excerpt


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


def test_episode_plan_beats_are_bound_to_current_source_facts():
    source_text = "父亲当众宣布与沈川断绝关系。沈川毫不知情。"
    packets = EpisodeSourcePackets(
        packets=[
            EpisodeSourcePacket(
                episode=1,
                source_anchor="断绝关系",
                source_excerpt=source_text,
                source_start=0,
                source_end=len(source_text),
                c0_facts=["父亲当众宣布断绝关系", "沈川毫不知情"],
                c4_forbidden_additions=["不能改成沈川主动离家"],
            )
        ]
    )
    plan = EpisodePlan(
        variant=GenerationVariant.DRAMA_ENGINE_FIRST,
        target_episode_range="EP01-EP01",
        adaptation_strategy="测试",
        episodes=[
            {
                "episode": 1,
                "title": "断绝关系",
                "drama_engine": "公开断绝关系",
                "protagonist_misbelief": "父亲会保护自己",
                "truth_gap": "父亲已经决定切割",
                "physical_action_chain": ["父亲宣布", "沈川僵住", "沈川沉默"],
                "scene_dynamics": ["客厅对峙", "众人围观"],
                "emotional_turns": ["震惊", "心冷"],
                "audience_information_gap": "父亲的决定无法撤回",
                "three_pull_beats": ["宣布", "僵住", "沉默"],
                "false_payoff": "沈川以为父亲会解释",
                "planted_key": "断绝关系",
                "strongest_line": "我不知情。",
                "cliffhanger_design": "父亲转身离开。",
                "source_assets_to_keep": ["父亲当众宣布断绝关系"],
                "forbidden_shortcuts": [],
            }
        ],
    )
    ledger = build_source_fact_ledger(source_text, packets)

    bound = bind_episode_plan_to_facts(plan, packets, ledger)
    beat = bound.episodes[0].beats[0]

    episode_facts = facts_for_episode(ledger, 1)
    assert beat.source_span_ids == episode_facts[0].source_span_ids
    assert beat.required_fact_ids == [episode_facts[0].fact_id]
    assert "不能改成沈川主动离家" in beat.forbidden_changes


def test_unsupported_provider_beat_is_replaced_by_source_fact_beat():
    source_text = "父亲当众宣布与沈川断绝关系。"
    packets = EpisodeSourcePackets(
        packets=[
            EpisodeSourcePacket(
                episode=1,
                source_anchor="断绝关系",
                source_excerpt=source_text,
                source_start=0,
                source_end=len(source_text),
                c0_facts=["父亲当众宣布断绝关系"],
            )
        ]
    )
    plan = EpisodePlan(
        variant=GenerationVariant.DRAMA_ENGINE_FIRST,
        target_episode_range="EP01-EP01",
        adaptation_strategy="测试",
        episodes=[
            {
                "episode": 1,
                "title": "断绝关系",
                "drama_engine": "公开断绝关系",
                "protagonist_misbelief": "父亲会保护自己",
                "truth_gap": "父亲已经决定切割",
                "physical_action_chain": ["父亲宣布", "沈川僵住", "沈川沉默"],
                "scene_dynamics": ["客厅对峙", "众人围观"],
                "emotional_turns": ["震惊", "心冷"],
                "audience_information_gap": "父亲的决定无法撤回",
                "three_pull_beats": ["宣布", "僵住", "沉默"],
                "false_payoff": "沈川以为父亲会解释",
                "planted_key": "断绝关系",
                "strongest_line": "我不知情。",
                "cliffhanger_design": "父亲转身离开。",
                "source_assets_to_keep": ["父亲当众宣布断绝关系"],
                "forbidden_shortcuts": [],
                "beats": [
                    EpisodeBeat(
                        beat_id="EP01-B01",
                        event="母亲死亡",
                        source_span_ids=["S-UNKNOWN"],
                        required_fact_ids=["F-UNKNOWN"],
                    ).model_dump()
                ],
            }
        ],
    )

    bound = bind_episode_plan_to_facts(
        plan,
        packets,
        build_source_fact_ledger(source_text, packets),
    )

    assert all(beat.source_span_ids for beat in bound.episodes[0].beats)
    assert "母亲死亡" not in "\n".join(
        beat.event for beat in bound.episodes[0].beats
    )


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
            sanitized.adaptation_strategy,
            episode.title,
            episode.drama_engine,
            episode.false_payoff,
            episode.planted_key,
            episode.strongest_line,
            episode.cliffhanger_design,
            *episode.emotional_turns,
            *episode.physical_action_chain,
            *episode.scene_dynamics,
            *episode.source_assets_to_keep,
            *episode.forbidden_shortcuts,
        ]
    )

    assert "雪夜" not in sanitized_text
    assert "亲吻" not in sanitized_text
    assert "追踪手机" not in sanitized_text
    assert "舆论战" not in sanitized_text
    assert "霍雅偷拍照片" in sanitized_text
    assert "逐集以当前 source packet" in sanitized.adaptation_strategy


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


def test_source_packet_confidence_blocks_when_target_episode_count_exceeds_source_budget():
    source_text = "林晚被赶出生日宴，管家在门口认出她。" * 20
    context = EpisodeContext(
        target_episode_range="EP01-EP05",
        story_stage=StoryStage.OPENING_PRESSURE,
        source_to_episode_mapping=[],
        must_carry_context=[],
        forbidden_reveals=[],
        adaptation_actions=[],
        confidence=0.7,
    )
    packets = build_episode_source_packets(
        source_text=source_text,
        episode_context=context,
        target_episode_count=25,
    )

    report = build_source_packet_confidence_report(
        packets,
        source_text=source_text,
        target_episode_count=25,
    )

    assert report.status == "blocking"
    assert any("原文信息预算不足" in warning for warning in report.blocking_warnings)


def test_source_packet_confidence_infers_budget_from_requested_episode_range():
    source_text = "林晚被赶出生日宴，管家在门口认出她。" * 5
    context = EpisodeContext(
        target_episode_range="EP01-EP05",
        story_stage=StoryStage.OPENING_PRESSURE,
        source_to_episode_mapping=[],
        must_carry_context=[],
        forbidden_reveals=[],
        adaptation_actions=[],
        confidence=0.7,
    )
    packets = build_episode_source_packets(
        source_text=source_text,
        episode_context=context,
    )

    report = build_source_packet_confidence_report(
        packets,
        source_text=source_text,
    )

    assert report.status == "blocking"
    assert any("目标 5 集" in warning for warning in report.blocking_warnings)
