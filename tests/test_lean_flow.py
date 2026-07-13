from novel_drama_engine import prompts
from novel_drama_engine.lean_flow import (
    build_episode_cut_table,
    build_production_spec,
    build_source_annotation,
)
from novel_drama_engine.models import (
    EpisodeContext,
    EpisodeSourceMapping,
    EpisodeSourcePacket,
    EpisodeSourcePackets,
    SourceAnalysis,
    StoryBible,
    StoryStage,
)


def make_context() -> EpisodeContext:
    return EpisodeContext(
        target_episode_range="EP01-EP02",
        story_stage=StoryStage.OPENING_PRESSURE,
        source_to_episode_mapping=[
            EpisodeSourceMapping(
                source="颁奖礼暗处羞辱 -> EP01",
                target_episode=1,
                retained_assets=["暗处羞辱", "提前准备的解约协议"],
                information_increment="女主已经决定离开",
            ),
            EpisodeSourceMapping(
                source="VIP通道对峙 -> EP02",
                target_episode=2,
                retained_assets=["VIP通道黄色灯光", "许念念撞开女主"],
                information_increment="解约进入公开对抗",
            ),
        ],
        must_carry_context=["EP01 结尾停在聚光灯打向女主"],
        forbidden_reveals=["不得提前公开幕后证据"],
        adaptation_actions=["只做视听化补强，不改变主动方"],
        confidence=0.9,
    )


def make_source_analysis() -> SourceAnalysis:
    return SourceAnalysis(
        characters=["林挽清", "路淮北", "许念念"],
        events=["林挽清在颁奖礼被羞辱", "解约协议早已准备好"],
        conflicts=["公开羞辱与主动离开"],
        visual_moments=["红裙与白裙对比", "VIP通道黄色灯光"],
        low_value_passages=["重复回忆十年资源变化"],
        candidate_hooks=["聚光灯打在她的红裙上"],
    )


def make_bible() -> StoryBible:
    return StoryBible(
        genre="现言娱乐圈复仇",
        mainline="林挽清在公开羞辱后主动离开并事业自救。",
        characters=["林挽清：克制清醒", "路淮北：傲慢控制", "许念念：主动布局"],
        relationships=["路淮北压迫林挽清", "许念念抢夺资源"],
        speech_styles={"林挽清": "克制、冷、短句"},
        immutable_facts=["解约协议早已准备好"],
        forbidden_changes=["不得把预谋解约改成临场赌气"],
    )


def make_packets() -> EpisodeSourcePackets:
    return EpisodeSourcePackets(
        packets=[
            EpisodeSourcePacket(
                episode=1,
                source_anchor="颁奖礼暗处羞辱",
                source_excerpt="她僵在暗处，聚光灯突然打过来。解约协议早已放在办公室。",
                c0_facts=["解约协议早已准备好"],
                c1_must_keep_assets=["暗处羞辱", "红裙与白裙对比"],
                c2_visual_assets=["聚光灯", "红裙"],
                c3_compress_assets=["十年资源变化回忆"],
                c4_forbidden_additions=["不得把女主写成功利索要影后"],
                golden_lines=["合作到此为止。"],
                active_party="路淮北主动羞辱，林挽清主动离开",
                key_decision_timing="开场前已决定解约",
            ),
            EpisodeSourcePacket(
                episode=2,
                source_anchor="VIP通道对峙",
                source_excerpt="VIP通道灯光发黄，许念念撞开她。她把解约协议拍到桌上。",
                c0_facts=["林挽清主动解约"],
                c1_must_keep_assets=["VIP通道黄色灯光", "许念念撞开女主"],
                c2_visual_assets=["黄色灯光", "带血指甲"],
                c4_forbidden_additions=["不得让支持角色替她解约"],
            ),
        ]
    )


def test_lean_artifacts_preserve_source_as_script_baseline():
    spec = build_production_spec()
    annotation = build_source_annotation(
        source_text="颁奖礼暗处羞辱。VIP通道对峙。",
        source_analysis=make_source_analysis(),
        episode_context=make_context(),
        story_bible=make_bible(),
        episode_source_packets=make_packets(),
    )
    cut_table = build_episode_cut_table(
        episode_context=make_context(),
        episode_source_packets=make_packets(),
    )

    assert spec.primary_output == "creative_script"
    assert "创作稿先成立" in "；".join(spec.script_priorities)
    assert annotation.north_star == "原文标注稿是首稿最高优先级基准"
    assert annotation.global_must_keep == ["解约协议早已准备好"]
    assert annotation.episodes[0].must_keep_assets == ["暗处羞辱", "红裙与白裙对比"]
    assert annotation.episodes[1].must_keep_events == ["林挽清主动解约", "VIP通道对峙"]
    assert annotation.episodes[1].visual_assets == ["黄色灯光", "带血指甲"]
    assert "解约进入公开对抗" not in annotation.episodes[1].must_keep_events
    assert "红裙与白裙对比" not in annotation.episodes[1].visual_assets
    assert "聚光灯打在她的红裙上" not in annotation.global_must_keep
    assert "公开羞辱与主动离开" not in annotation.global_must_keep
    assert "不得让支持角色替她解约" in annotation.episodes[1].forbidden_changes
    assert "不得把预谋解约改成临场赌气" in annotation.episodes[1].forbidden_changes
    assert cut_table.cuts[0].core_conflict == "颁奖礼暗处羞辱"
    assert cut_table.cuts[1].source_anchor == "VIP通道对峙"


def test_script_prompt_makes_lean_flow_inputs_authoritative():
    spec = build_production_spec()
    annotation = build_source_annotation(
        source_text="颁奖礼暗处羞辱。VIP通道对峙。",
        source_analysis=make_source_analysis(),
        episode_context=make_context(),
        story_bible=make_bible(),
        episode_source_packets=make_packets(),
    )
    cut_table = build_episode_cut_table(
        episode_context=make_context(),
        episode_source_packets=make_packets(),
    )

    user_prompt = prompts.script_user(
        "颁奖礼暗处羞辱。VIP通道对峙。",
        make_source_analysis(),
        make_context(),
        make_bible(),
        None,
        "",
        round_number=1,
        target_episode_count=25,
        episode_source_packets=make_packets(),
        production_spec=spec,
        source_annotation=annotation,
        episode_cut_table=cut_table,
    )

    assert "【P0 轻链路主输入】" in user_prompt
    assert "source_annotation 是首稿最高优先级基准" in user_prompt
    assert "episode_cut_table 决定本轮分集边界" in user_prompt
    assert "本集计划、全剧结构参考和方法论参考只作辅助" in user_prompt
    assert user_prompt.index("source_annotation") < user_prompt.index("episode_plan")
