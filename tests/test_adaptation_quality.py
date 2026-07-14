from novel_drama_engine.adaptation_quality import (
    build_adaptation_quality_report,
    build_story_state_ledger,
    build_methodology_quality_report,
    merge_methodology_quality_into_report,
    _hook_acknowledged,
    _forbidden_rule_leaked,
    _story_event_markers,
)
from novel_drama_engine.models import (
    AdaptationIntensity,
    EpisodeContext,
    EpisodeScript,
    EpisodeSourcePacket,
    EpisodeSourcePackets,
    MethodologyCard,
    MethodologyContext,
    MethodologyStage,
    MethodologyStatus,
    NextRoundContext,
    QualityReport,
    QualityScores,
    QualityStatus,
    Scene,
    SceneLine,
    ScriptBatch,
    SourceAnalysis,
    SourceStrengthLevel,
    SourceStrengthProfile,
    StoryBible,
    StoryStage,
)


def make_episode(
    episode: int = 1,
    *,
    title: str = "宴会反击",
    hook: str = "谁敢碰她一下！",
    final: str = "你到底是谁？",
    state_update=None,
) -> EpisodeScript:
    return EpisodeScript(
        episode=episode,
        title=title,
        hook_3s=hook,
        main_emotion="羞辱",
        watch_reason="系统内部看点",
        scenes=[
            Scene(
                heading=f"{episode}-1 夜-内-林家宴会厅",
                characters=["林晚", "林雪"],
                lines=[
                    SceneLine(
                        kind="action",
                        text="△中景推近林晚被推到宴会中央，宾客手机在前景抬起。",
                    ),
                    SceneLine(
                        kind="dialogue",
                        speaker="林晚",
                        emotion="冷",
                        text=hook,
                    ),
                    SceneLine(
                        kind="action",
                        text="△特写推近旧木盒打开，半枚玉佩压在邀请函上。",
                    ),
                    SceneLine(
                        kind="dialogue",
                        speaker="林雪",
                        emotion="慌",
                        text=final,
                    ),
                ],
            )
        ],
        cliffhanger=final,
        state_update=state_update or {"open_hook": final, "prop": "旧木盒已公开"},
    )


def make_plain_episode(
    episode: int,
    *,
    hook: str,
    final: str,
    title: str = "关键节点",
) -> EpisodeScript:
    return EpisodeScript(
        episode=episode,
        title=title,
        hook_3s=hook,
        main_emotion="紧张",
        watch_reason="系统内部看点",
        scenes=[
            Scene(
                heading=f"{episode}-1 夜-内-主场景",
                characters=["甲", "乙"],
                lines=[
                    SceneLine(
                        kind="action",
                        text="△中景推近甲站到灯下，乙在画面边缘抬头。",
                    ),
                    SceneLine(
                        kind="dialogue",
                        speaker="甲",
                        emotion="冷",
                        text=hook,
                    ),
                    SceneLine(
                        kind="dialogue",
                        speaker="乙",
                        emotion="震惊",
                        text=final,
                    ),
                ],
            )
        ],
        cliffhanger=final,
        state_update={"open_hook": final},
    )


def make_context() -> EpisodeContext:
    return EpisodeContext(
        target_episode_range="EP01-EP01",
        story_stage=StoryStage.OPENING_PRESSURE,
        source_to_episode_mapping=["林晚生日宴被羞辱，旧木盒出现 -> EP01"],
        must_carry_context=[],
        forbidden_reveals=["不得提前一次性公开亲子鉴定"],
        adaptation_actions=["保留公开羞辱开场"],
        confidence=0.9,
    )


def make_source_analysis(hook: str = "谁敢碰她一下！") -> SourceAnalysis:
    return SourceAnalysis(
        characters=["林晚", "林雪"],
        events=["林晚生日宴被羞辱，旧木盒出现"],
        conflicts=["真假千金身份冲突"],
        visual_moments=["旧木盒打开"],
        low_value_passages=[],
        candidate_hooks=[hook],
    )


def make_bible() -> StoryBible:
    return StoryBible(
        genre="豪门真假千金",
        mainline="林晚在公开羞辱中逐集反击。",
        characters=["林晚", "林雪"],
        relationships=["林雪压迫林晚"],
        speech_styles={"林晚": "克制短句", "林雪": "温柔带刺"},
        immutable_facts=["林晚被公开羞辱"],
        forbidden_changes=["不得新增亲哥哥救场"],
    )


def make_next_context() -> NextRoundContext:
    return NextRoundContext(
        summary="EP01 停在林雪追问身份。",
        current_episode=1,
        open_hooks=["你到底是谁？"],
        forbidden_reveals=["亲子鉴定完整结果"],
        character_knowledge={"林晚": ["知道旧木盒能推进身份线"]},
        relationship_changes=["林晚与林雪公开对立"],
        prop_states=["旧木盒已公开"],
        foreshadowing_ledger=["玉佩将在 EP02 继续推进"],
    )


def make_strong_profile() -> SourceStrengthProfile:
    return SourceStrengthProfile(
        conflict_strength=9,
        hook_strength=9,
        character_tag_strength=8,
        emotion_asset_strength=9,
        signature_scene_strength=10,
        visualization_readiness=8,
        overall_level=SourceStrengthLevel.STRONG,
        recommended_intensity=AdaptationIntensity.LIGHT,
        reasons=["原文已有强钩子和名场面。"],
    )


def make_methodology_context() -> MethodologyContext:
    return MethodologyContext(
        source_strength_level=SourceStrengthLevel.STRONG,
        adaptation_intensity=AdaptationIntensity.LIGHT,
        cards=[
            MethodologyCard(
                id="method_card_strong_source_light_v1",
                source_id="method_source_strong_source_light_v1",
                name="强原文轻改规则",
                category="source_fidelity",
                applies_to_channel=["female"],
                applies_to_genre=["identity"],
                applies_to_stage=[MethodologyStage.QUALITY_GATE],
                trigger="原文已具备强冲突、强钩子、强反差或高情绪名场面",
                generation_rule="只做视听化、压缩和镜头补强，不改变主动方和因果顺序。",
                quality_rule="删除 C1 名场面必须 needs_rewrite。",
                negative_examples=["把原文预谋解约改成现场赌气解约"],
                status=MethodologyStatus.ACTIVE,
            )
        ],
    )


def test_adaptation_quality_blocks_dropped_original_hook():
    report = build_adaptation_quality_report(
        source_text="生日宴上，林晚被逼到角落。林雪低声说：谁敢碰她一下！",
        source_analysis=make_source_analysis("谁敢碰她一下！"),
        episode_context=make_context(),
        story_bible=make_bible(),
        script_batch=ScriptBatch(
            episodes=[
                make_episode(
                    hook="欢迎回来。",
                    final="旧木盒怎么会在这里？",
                )
            ]
        ),
        next_round_context=make_next_context(),
        previous_context=None,
    )

    assert report.source_fidelity.preserved_original_hook is False
    assert any("original strong hook" in item for item in report.blocking_warnings)
    assert report.source_fidelity.score < 100


def test_hook_acknowledgement_requires_specific_event_overlap_not_only_shared_name():
    assert not _hook_acknowledged(
        "许念念举起提前准备好的解约协议",
        "许念念低头喝水，镜头扫过桌面。",
    )
    assert _hook_acknowledged(
        "许念念举起提前准备好的解约协议",
        "许念念从包里抽出解约协议，举到镜头前。",
    )


def test_forbidden_reveal_allows_investigation_before_identity_result():
    report = build_adaptation_quality_report(
        source_text="林晚生日宴被羞辱，旧木盒出现。",
        source_analysis=make_source_analysis("谁敢碰她一下！"),
        episode_context=make_context(),
        story_bible=make_bible(),
        script_batch=ScriptBatch(
            episodes=[
                make_episode(
                    hook="谁敢碰她一下！",
                    final="鉴定结果出来前，她不会停手。",
                )
            ]
        ),
        next_round_context=make_next_context(),
        previous_context=None,
    )

    assert not any(
        "forbidden addition/reveal may have leaked" in item
        for item in report.blocking_warnings
    )


def test_forbidden_reveal_blocks_public_identity_result():
    report = build_adaptation_quality_report(
        source_text="林晚生日宴被羞辱，旧木盒出现。",
        source_analysis=make_source_analysis("谁敢碰她一下！"),
        episode_context=make_context(),
        story_bible=make_bible(),
        script_batch=ScriptBatch(
            episodes=[
                make_episode(
                    hook="谁敢碰她一下！",
                    final="亲子鉴定结果公开，林晚才是真千金。",
                )
            ]
        ),
        next_round_context=make_next_context(),
        previous_context=None,
    )

    assert any(
        "forbidden addition/reveal may have leaked" in item
        for item in report.blocking_warnings
    )


def test_forbidden_rule_does_not_block_normal_source_faithful_terms():
    bible = make_bible().model_copy(
        update={
            "forbidden_changes": [
                "严禁改变林晚解约的主动性。解约在开场就是谋划好的既定行动，决非临时赌气。",
                "严禁林晚性格软弱。面对电话纠缠时，她必须克制、冷静、坚定。",
            ]
        }
    )
    report = build_adaptation_quality_report(
        source_text="林晚早就把解约协议放在桌上。电话响起时，她克制冷静地说：合作到此为止。",
        source_analysis=make_source_analysis("合作到此为止"),
        episode_context=make_context(),
        story_bible=bible,
        script_batch=ScriptBatch(
            episodes=[
                make_episode(
                    hook="林晚早就决定解约。",
                    final="合作到此为止。",
                )
            ]
        ),
        next_round_context=make_next_context(),
        previous_context=None,
    )

    assert not any(
        "forbidden addition/reveal may have leaked" in item
        for item in report.blocking_warnings
    )


def test_generic_unseen_reveal_placeholder_does_not_block_normal_identity_language():
    assert not _forbidden_rule_leaked(
        "林晚的身份被当众质疑，但亲子鉴定尚未公开。",
        "原文未出现的身份、证据或结果",
    )


def test_forbidden_reveal_allows_explicit_pending_result_without_leaking_identity():
    context = make_context().model_copy(
        update={"forbidden_reveals": ["暂不公开亲子鉴定结果"]}
    )
    report = build_adaptation_quality_report(
        source_text="亲子鉴定被人调包，报告还没出结果。",
        source_analysis=make_source_analysis("报告被谁换了？"),
        episode_context=context,
        story_bible=make_bible(),
        script_batch=ScriptBatch(
            episodes=[
                make_episode(
                    hook="报告被谁换了？",
                    final="亲子鉴定还没出结果，谁换了样本？",
                )
            ]
        ),
        next_round_context=make_next_context(),
        previous_context=None,
    )

    assert not any(
        "forbidden addition/reveal may have leaked" in item
        for item in report.blocking_warnings
    )


def test_plain_future_fact_requires_performed_relation_not_scattered_keywords():
    script_text = (
        "霍庭琛把蛋糕放在桌上。\n"
        "林挽清想起十年前收到的第一份粉丝礼物。\n"
        "她没有认出送礼的人。"
    )
    rule = "霍庭琛是十年前给林挽清送蛋糕的粉丝"

    assert not _forbidden_rule_leaked(script_text, rule)
    assert _forbidden_rule_leaked(
        "林挽清终于确认：十年前送蛋糕的粉丝就是霍庭琛。",
        rule,
    )


def test_plain_future_outcome_does_not_match_character_names_alone():
    assert not _forbidden_rule_leaked(
        "路淮北在电话里威胁林挽清，霍庭琛站在一旁。",
        "路淮北狱中惨死的结局",
    )
    assert _forbidden_rule_leaked(
        "三年后，路淮北最终惨死狱中。",
        "路淮北狱中惨死的结局",
    )


def test_source_fidelity_scores_required_assets_without_treating_actions_as_source():
    context = EpisodeContext(
        target_episode_range="EP01-EP01",
        story_stage=StoryStage.OPENING_PRESSURE,
        source_to_episode_mapping=[
            {
                "source": "颁奖礼后台羞辱",
                "target_episode": "EP01",
                "retained_assets": "西装手部压迫、包臀裙羞辱、手机短信嘲讽",
                "information_increment": "女主身份、隐藏恋情与背叛危机",
                "adaptation_action": "将内心OS转为紧迫呼吸和局部特写",
            }
        ],
        must_carry_context=[],
        forbidden_reveals=[],
        adaptation_actions=[],
        confidence=0.9,
    )
    script = EpisodeScript(
        episode=1,
        title="颁奖台下",
        hook_3s="别出声。",
        main_emotion="羞辱",
        watch_reason="系统内部看点",
        scenes=[
            Scene(
                heading="1-1 夜-内-颁奖礼后台",
                characters=["林挽清", "路淮北"],
                lines=[
                    SceneLine(
                        kind="action",
                        text="△特写推近路淮北西装手部压迫林挽清，包臀裙羞辱被聚光灯扫到。",
                    ),
                    SceneLine(kind="dialogue", speaker="路淮北", emotion="低声", text="别出声。"),
                ],
            )
        ],
        cliffhanger="手机在她掌心震动。",
        state_update={},
    )

    report = build_adaptation_quality_report(
        source_text="颁奖礼后台，路淮北用西装手臂压住她，包臀裙被迫皱起，手机后来震动。",
        source_analysis=make_source_analysis("手机后来震动").model_copy(
            update={"visual_moments": ["包臀裙被迫皱起"]}
        ),
        episode_context=context,
        story_bible=make_bible().model_copy(
            update={"immutable_facts": ["包臀裙被迫皱起"]}
        ),
        script_batch=ScriptBatch(episodes=[script]),
        next_round_context=make_next_context(),
        previous_context=None,
    )

    assert report.source_fidelity.score == 67
    assert any(check.category == "source_mapping_required" for check in report.source_fidelity.checks)
    assert any(check.category == "source_mapping_context" for check in report.source_fidelity.checks)
    assert not any("将内心OS转为" in item for item in report.blocking_warnings)


def test_source_fidelity_blocks_upstream_assets_that_cannot_be_traced_to_source_packets():
    source_text = "林晚被赶出生日宴，门口管家喊住了她。"
    source_analysis = make_source_analysis("把她拖出去！").model_copy(
        update={"visual_moments": ["旧木盒打开"]}
    )
    story_bible = make_bible().model_copy(
        update={"immutable_facts": ["林晚是真千金"]}
    )
    packets = EpisodeSourcePackets(
        packets=[
            EpisodeSourcePacket(
                episode=1,
                source_anchor="生日宴驱逐",
                source_excerpt=source_text,
                source_evidence_assets=["林晚被赶出生日宴"],
            )
        ]
    )

    report = build_adaptation_quality_report(
        source_text=source_text,
        source_analysis=source_analysis,
        episode_context=make_context(),
        story_bible=story_bible,
        script_batch=ScriptBatch(episodes=[make_episode(hook="把她拖出去！")]),
        next_round_context=make_next_context(),
        previous_context=None,
        episode_source_packets=packets,
    )

    assert any(
        "unsupported upstream source asset leaked into script" in warning
        for warning in report.source_fidelity.blocking_warnings
    )
    assert report.source_fidelity.score < 50


def test_source_fidelity_does_not_punish_unused_untraceable_upstream_asset():
    source_text = "林晚被赶出生日宴，有人喊把她拖出去，门口管家喊住了她。"
    source_analysis = make_source_analysis("把她拖出去！").model_copy(
        update={
            "visual_moments": [
                f"Fireworks kiss under the snow {index}" for index in range(10)
            ]
        }
    )
    packets = EpisodeSourcePackets(
        packets=[
            EpisodeSourcePacket(
                episode=1,
                source_anchor="生日宴驱逐",
                source_excerpt=source_text,
                source_evidence_assets=["林晚被赶出生日宴"],
            )
        ]
    )

    report = build_adaptation_quality_report(
        source_text=source_text,
        source_analysis=source_analysis,
        episode_context=make_context(),
        story_bible=make_bible(),
        script_batch=ScriptBatch(episodes=[make_episode(hook="把她拖出去！")]),
        next_round_context=make_next_context(),
        previous_context=None,
        episode_source_packets=packets,
    )

    assert not any(
        "Fireworks kiss under the snow" in warning
        for warning in report.source_fidelity.blocking_warnings
    )
    assert any(
        "Fireworks kiss under the snow" in warning
        for warning in report.source_fidelity.advisory_warnings
    )
    assert report.source_fidelity.score >= 80


def test_source_fidelity_does_not_block_current_round_on_future_episode_assets():
    context = EpisodeContext(
        target_episode_range="EP01-EP02",
        story_stage=StoryStage.OPENING_PRESSURE,
        source_to_episode_mapping=[
            {
                "source": "颁奖礼后台羞辱",
                "target_episode": "EP01",
                "retained_assets": "路淮北手部压迫、许念念台上领奖",
                "information_increment": "隐藏恋情与背叛危机",
                "adaptation_action": "保留开场压迫",
            },
            {
                "source": "雪地烟火激吻，照片随后被公开",
                "target_episode": "EP08",
                "retained_assets": "雪地烟火激吻、照片被公开",
                "information_increment": "后续公开关系危机",
                "adaptation_action": "未来轮次承接",
            },
        ],
        must_carry_context=[],
        forbidden_reveals=[],
        adaptation_actions=[],
        confidence=0.9,
    )
    script = EpisodeScript(
        episode=1,
        title="颁奖台下",
        hook_3s="别出声。",
        main_emotion="羞辱",
        watch_reason="系统内部看点",
        scenes=[
            Scene(
                heading="1-1 夜-内-颁奖礼后台",
                characters=["林挽清", "路淮北", "许念念"],
                lines=[
                    SceneLine(
                        kind="action",
                        text="△特写推近路淮北手部压迫林挽清，门缝外许念念台上领奖。",
                    ),
                    SceneLine(kind="dialogue", speaker="路淮北", emotion="低声", text="别出声。"),
                ],
            )
        ],
        cliffhanger="主持人的声音压过门缝。",
        state_update={},
    )

    report = build_adaptation_quality_report(
        source_text="颁奖礼后台，路淮北压住她。很久之后，雪地烟火下两人接吻，照片被公开。",
        source_analysis=make_source_analysis("别出声。"),
        episode_context=context,
        story_bible=make_bible(),
        script_batch=ScriptBatch(episodes=[script]),
        next_round_context=make_next_context(),
        previous_context=None,
    )

    warning_text = "\n".join(report.blocking_warnings)
    assert "雪地烟火激吻" not in warning_text
    assert "照片被公开" not in warning_text


def test_source_fidelity_uses_source_packet_boundary_when_context_mapping_drifts():
    context = EpisodeContext(
        target_episode_range="EP02-EP02",
        story_stage=StoryStage.OPENING_PRESSURE,
        source_to_episode_mapping=[
            {
                "source": "经纪人团队失联，小助理出现，前往瑞士避世",
                "target_episode": "EP02",
                "retained_assets": ["被公司扣押团队", "小助理的陪伴", "订购前往瑞士的机票"],
                "information_increment": "确认离开巨星后的孤立无援与环境转换",
                "adaptation_action": "压缩经纪人与日常抱怨",
            },
        ],
        must_carry_context=[],
        forbidden_reveals=[],
        adaptation_actions=[],
        confidence=0.9,
    )
    packet = EpisodeSourcePacket(
        episode=2,
        source_anchor="EP02 当前集原文",
        source_excerpt="小助理红着眼陪她看评论。林挽清躺在沙发上订了去瑞士的机票。",
        c1_must_keep_assets=["小助理的陪伴", "订购前往瑞士的机票"],
        source_evidence_assets=["小助理的陪伴", "订购前往瑞士的机票"],
    )
    script = EpisodeScript(
        episode=2,
        title="瑞士机票",
        hook_3s="别回头。",
        main_emotion="孤立",
        watch_reason="系统内部看点",
        scenes=[
            Scene(
                heading="2-1 夜-内-公寓客厅",
                characters=["林挽清", "小助理"],
                lines=[
                    SceneLine(
                        kind="action",
                        text="△中景推近小助理红着眼坐到沙发边，陪伴她看完手机评论区。",
                    ),
                    SceneLine(
                        kind="dialogue",
                        speaker="小助理",
                        emotion="气",
                        text="我陪你走。",
                    ),
                    SceneLine(
                        kind="action",
                        text="△特写推近林挽清点下瑞士机票，屏幕冷光切到她疲惫的眼。",
                    ),
                ],
            )
        ],
        cliffhanger="机票订单确认。",
        state_update={},
    )

    report = build_adaptation_quality_report(
        source_text="小助理红着眼陪她看评论。林挽清躺在沙发上订了去瑞士的机票。",
        source_analysis=make_source_analysis("瑞士机票").model_copy(
            update={"visual_moments": ["小助理红着眼陪她看评论"]}
        ),
        episode_context=context,
        story_bible=make_bible().model_copy(
            update={"immutable_facts": ["林挽清订了去瑞士的机票"]}
        ),
        script_batch=ScriptBatch(episodes=[script]),
        next_round_context=make_next_context(),
        previous_context=None,
        episode_source_packets=EpisodeSourcePackets(packets=[packet]),
    )

    warning_text = "\n".join(report.blocking_warnings)
    assert "被公司扣押团队" not in warning_text
    assert "小助理的陪伴" not in warning_text
    assert "订购前往瑞士的机票" not in warning_text
    assert any("source packet" in item for item in report.advisory_warnings)
    assert report.source_fidelity.score >= 90


def test_source_fidelity_rejects_weak_overlap_with_wrong_episode_packet():
    context = EpisodeContext(
        target_episode_range="EP02-EP02",
        story_stage=StoryStage.OPENING_PRESSURE,
        source_to_episode_mapping=[
            {
                "source": "通道对峙并提出解约",
                "target_episode": "EP02",
                "retained_assets": ["初见时的青涩笑容对峙", "拿出解约协议的决绝"],
                "information_increment": "完成分手决裂",
                "adaptation_action": "用解约协议做断点",
            },
        ],
        must_carry_context=[],
        forbidden_reveals=[],
        adaptation_actions=[],
        confidence=0.9,
    )
    packet = EpisodeSourcePacket(
        episode=2,
        source_anchor="林挽清在沙发上订去瑞士的机票。",
        source_excerpt="小助理红着眼陪她看评论。林挽清想起烟火晚会，然后订了去瑞士的机票。",
        c1_must_keep_assets=["小助理的陪伴", "瑞士机票"],
    )
    script = EpisodeScript(
        episode=2,
        title="瑞士机票",
        hook_3s="别回头。",
        main_emotion="孤立",
        watch_reason="系统内部看点",
        scenes=[
            Scene(
                heading="2-1 夜-内-公寓客厅",
                characters=["林挽清", "小助理"],
                lines=[
                    SceneLine(
                        kind="action",
                        text="△中景推近小助理红着眼坐在沙发边，陪林挽清翻看评论区。",
                    ),
                    SceneLine(kind="dialogue", speaker="小助理", text="我陪你走。"),
                    SceneLine(
                        kind="action",
                        text="△特写推近瑞士机票订单确认，屏幕冷光切到林挽清疲惫的眼。",
                    ),
                ],
            )
        ],
        cliffhanger="机票订单确认。",
        state_update={},
    )

    report = build_adaptation_quality_report(
        source_text=packet.source_excerpt,
        source_analysis=make_source_analysis("别回头。"),
        episode_context=context,
        story_bible=make_bible(),
        script_batch=ScriptBatch(episodes=[script]),
        next_round_context=make_next_context(),
        previous_context=None,
        episode_source_packets=EpisodeSourcePackets(packets=[packet]),
    )

    warning_text = "\n".join(report.blocking_warnings)
    assert "初见时的青涩笑容对峙" not in warning_text
    assert "拿出解约协议的决绝" not in warning_text
    assert any("初见时的青涩笑容对峙" in item for item in report.advisory_warnings)
    assert any("拿出解约协议的决绝" in item for item in report.advisory_warnings)


def test_forbidden_change_detection_does_not_flag_broad_character_name_overlap():
    bible = make_bible()
    bible.forbidden_changes = [
        "禁止在林挽清对路淮北死心前增加暧昧戏份。",
        "严禁将路淮北写出任何洗白情节或苦衷背景。",
    ]

    report = build_adaptation_quality_report(
        source_text="林挽清被路淮北公开羞辱后冷静离开。",
        source_analysis=SourceAnalysis(
            characters=["林挽清", "路淮北"],
            events=["公开羞辱"],
            conflicts=["背叛"],
            visual_moments=[],
            low_value_passages=[],
            candidate_hooks=[],
        ),
        episode_context=EpisodeContext(
            target_episode_range="EP01-EP01",
            story_stage=StoryStage.OPENING_PRESSURE,
            source_to_episode_mapping=[],
            must_carry_context=[],
            forbidden_reveals=[],
            adaptation_actions=[],
            confidence=0.9,
        ),
        story_bible=bible,
        script_batch=ScriptBatch(
            episodes=[
                EpisodeScript(
                    episode=1,
                    title="冷静离开",
                    hook_3s="别碰我。",
                    main_emotion="羞辱",
                    watch_reason="系统内部看点",
                    scenes=[
                        Scene(
                            heading="1-1 夜-内-走廊",
                            characters=["林挽清", "路淮北"],
                            lines=[
                                SceneLine(
                                    kind="action",
                                    text="△中景推近林挽清绕开路淮北，指尖攥紧解约协议。",
                                ),
                                SceneLine(kind="dialogue", speaker="林挽清", emotion="冷", text="让开。"),
                            ],
                        )
                    ],
                    cliffhanger="协议被她按在桌上。",
                    state_update={},
                )
            ]
        ),
        next_round_context=make_next_context(),
        previous_context=None,
    )

    assert report.source_fidelity.score >= 90
    assert not any(
        "forbidden addition/reveal may have leaked" in item
        for item in report.blocking_warnings
    )


def test_pending_forbidden_reveal_requires_concrete_topic_leak():
    report = build_adaptation_quality_report(
        source_text="林挽清在瑞士接起路淮北电话。",
        source_analysis=make_source_analysis("你到底是谁？"),
        episode_context=EpisodeContext(
            target_episode_range="EP05-EP05",
            story_stage=StoryStage.MIDPOINT_REVERSAL,
            source_to_episode_mapping=[],
            must_carry_context=[],
            forbidden_reveals=[
                "暂不揭示林挽清在环宇娱乐的具体持股意图",
                "暂不揭示路淮北公司账目违规的具体细节，留待后集法务介入",
            ],
            adaptation_actions=[],
            confidence=0.9,
        ),
        story_bible=make_bible(),
        script_batch=ScriptBatch(
            episodes=[
                make_plain_episode(
                    5,
                    hook="林挽清接起电话。",
                    final="路总，解约协议签完。",
                )
            ]
        ),
        next_round_context=make_next_context(),
        previous_context=None,
    )

    assert not any(
        "forbidden addition/reveal may have leaked" in item
        for item in report.blocking_warnings
    )


def test_forbidden_rule_still_blocks_concrete_added_asset():
    report = build_adaptation_quality_report(
        source_text="林晚在生日宴被羞辱，只能靠自己拿出旧木盒反击。",
        source_analysis=make_source_analysis("谁敢碰她一下！"),
        episode_context=make_context(),
        story_bible=make_bible(),
        script_batch=ScriptBatch(
            episodes=[
                make_episode(
                    hook="谁敢碰她一下！",
                    final="她亲哥哥冲进来，替她救场。",
                )
            ]
        ),
        next_round_context=make_next_context(),
        previous_context=None,
    )

    assert any(
        "forbidden addition/reveal may have leaked" in item
        for item in report.blocking_warnings
    )

def test_agency_ramp_allows_source_with_hidden_power_setup():
    report = build_adaptation_quality_report(
        source_text="赘婿叶辰被岳父一家羞辱，下一秒黑卡被银行经理亲自送到门口。",
        source_analysis=make_source_analysis("所有证据都在我手里。"),
        episode_context=make_context(),
        story_bible=make_bible(),
        script_batch=ScriptBatch(
            episodes=[
                make_episode(
                    hook="所有证据都在我手里。",
                    final="谁还敢说他没资格？",
                )
            ]
        ),
        next_round_context=make_next_context(),
        previous_context=None,
    )

    assert not any("主角情绪/主动权递进漂移" in item for item in report.blocking_warnings)


def test_agency_ramp_ignores_other_character_question_about_prior_knowledge():
    report = build_adaptation_quality_report(
        source_text="林晚在生日宴上被当众羞辱，老管家拿着旧木盒冲进来。",
        source_analysis=make_source_analysis("谁敢碰她一下！"),
        episode_context=make_context(),
        story_bible=make_bible(),
        script_batch=ScriptBatch(
            episodes=[
                make_episode(
                    hook="谁敢碰她一下！",
                    final="录像？你们早就知道？",
                )
            ]
        ),
        next_round_context=make_next_context(),
        previous_context=None,
    )

    assert not any("主角情绪/主动权递进漂移" in item for item in report.blocking_warnings)


def test_methodology_quality_blocks_strong_source_dropped_hook():
    methodology_report = build_methodology_quality_report(
        source_analysis=make_source_analysis("谁敢碰她一下！"),
        script_batch=ScriptBatch(
            episodes=[
                make_episode(
                    hook="欢迎回来。",
                    final="旧木盒怎么会在这里？",
                )
            ]
        ),
        source_strength_profile=make_strong_profile(),
        methodology_context=make_methodology_context(),
    )

    assert methodology_report.issues
    assert methodology_report.issues[0].severity == "blocking"
    assert "原文开场钩子未被保留" in methodology_report.issues[0].message


def test_methodology_negative_example_requires_high_confidence_match():
    script = EpisodeScript(
        episode=1,
        title="决裂",
        hook_3s="签了它。",
        main_emotion="决裂",
        watch_reason="系统内部看点",
        scenes=[
            Scene(
                heading="1-1 夜-内-VIP通道",
                characters=["林挽清", "路淮北"],
                lines=[
                    SceneLine(
                        kind="action",
                        text="△中近景推近林挽清从口袋抽出解约协议，重重拍在路淮北西装上。",
                    ),
                    SceneLine(kind="dialogue", speaker="林挽清", text="签了它。"),
                ],
            )
        ],
        cliffhanger="签了它。",
        state_update={},
    )

    methodology_report = build_methodology_quality_report(
        source_analysis=make_source_analysis("签了它。"),
        script_batch=ScriptBatch(episodes=[script]),
        source_strength_profile=make_strong_profile(),
        methodology_context=make_methodology_context(),
    )

    assert not any("现场赌气解约" in issue.message for issue in methodology_report.issues)


def test_methodology_quality_does_not_force_opening_scene_after_first_round():
    methodology_report = build_methodology_quality_report(
        source_analysis=make_source_analysis("谁敢碰她一下！"),
        script_batch=ScriptBatch(
            episodes=[
                make_episode(
                    episode=3,
                    title="第三集新推进",
                    hook="档案编号被换过！",
                    final="这份记录，为什么有顾家的章？",
                )
            ]
        ),
        source_strength_profile=make_strong_profile(),
        methodology_context=make_methodology_context(),
    )

    assert methodology_report.issues == []


def test_methodology_quality_merge_marks_needs_rewrite():
    base_report = QualityReport(
        status=QualityStatus.USABLE,
        scores=QualityScores(hook=8, conflict=8, cliffhanger=8, continuity=8, video_feasibility=8),
        blocking_issues=[],
        rewrite_instruction="",
    )
    methodology_report = build_methodology_quality_report(
        source_analysis=make_source_analysis("谁敢碰她一下！"),
        script_batch=ScriptBatch(
            episodes=[
                make_episode(
                    hook="欢迎回来。",
                    final="旧木盒怎么会在这里？",
                )
            ]
        ),
        source_strength_profile=make_strong_profile(),
        methodology_context=make_methodology_context(),
    )

    merged = merge_methodology_quality_into_report(base_report, methodology_report)

    assert merged.status == QualityStatus.NEEDS_REWRITE
    assert merged.blocking_issues
    assert "方法论阻断" in merged.rewrite_instruction


def test_story_state_ledger_collects_episode_and_next_context_state():
    episode = make_episode()
    report = build_adaptation_quality_report(
        source_text="林晚生日宴被羞辱，旧木盒出现。",
        source_analysis=make_source_analysis(),
        episode_context=make_context(),
        story_bible=make_bible(),
        script_batch=ScriptBatch(episodes=[episode]),
        next_round_context=make_next_context(),
        previous_context=None,
    )

    ledger = report.story_state_ledger
    assert ledger.current_episode == 1
    assert any(entry.kind == "episode_state" for entry in ledger.entries)
    assert "旧木盒已公开" in ledger.prop_states


def test_story_state_ledger_closes_previous_context_hook_when_opening_acknowledges_it():
    previous_context = make_next_context()
    previous_context.open_hooks = ["你到底是谁？"]
    episode = make_episode(hook="你到底是谁？", final="新的证据在哪？")

    ledger = build_story_state_ledger(
        script_batch=ScriptBatch(episodes=[episode]),
        next_round_context=make_next_context(),
        previous_context=previous_context,
    )

    previous_entries = [
        entry
        for entry in ledger.entries
        if entry.kind == "open_hook" and entry.source == "previous_context"
    ]
    assert previous_entries[0].status == "closed"


def test_story_state_ledger_closes_episode_hook_when_next_opening_acknowledges_it():
    first = make_episode(episode=1, final="门外的人是谁？")
    second = make_episode(
        episode=2,
        hook="门外的人是谁？",
        final="盒子里还有什么？",
    )

    ledger = build_story_state_ledger(
        script_batch=ScriptBatch(episodes=[first, second]),
        next_round_context=make_next_context(),
        previous_context=None,
    )

    first_hook = next(
        entry
        for entry in ledger.entries
        if entry.kind == "open_hook"
        and entry.source == "episode.cliffhanger"
        and entry.episode == 1
    )
    assert first_hook.status == "closed"
    assert "next_round_context open_hooks does not carry the final episode cliffhanger" in ledger.warnings


def test_story_state_ledger_allows_exit_decision_consequence_without_duplicate_block():
    first = make_plain_episode(
        episode=1,
        hook="协议在桌上。",
        final="合作到此为止。",
        title="解约决定",
    )
    first.scenes[0].lines = [
        SceneLine(
            kind="action",
            text="△中景推近林挽清把早就准备好的解约协议放在办公桌上。",
        ),
        SceneLine(kind="dialogue", speaker="林挽清", text="合作到此为止。"),
    ]
    second = make_plain_episode(
        episode=5,
        hook="电话又响。",
        final="别再找我。",
        title="电话余波",
    )
    second.scenes[0].lines = [
        SceneLine(
            kind="action",
            text="△特写推近手机来电，路淮北的名字在屏幕上震动。",
        ),
        SceneLine(kind="dialogue", speaker="林挽清", text="解约协议签完，别再找我。"),
    ]

    ledger = build_story_state_ledger(
        script_batch=ScriptBatch(episodes=[first, second]),
        next_round_context=make_next_context(),
        previous_context=None,
    )

    assert not any("不可逆关系/合同决定" in item for item in ledger.blocking_warnings)


def test_continuity_blocks_forbidden_previous_reveal_leak():
    previous_context = make_next_context()
    previous_context.forbidden_reveals = ["亲子鉴定完整结果"]
    report = build_adaptation_quality_report(
        source_text="林晚生日宴被羞辱，旧木盒出现。",
        source_analysis=make_source_analysis(),
        episode_context=make_context(),
        story_bible=make_bible(),
        script_batch=ScriptBatch(
            episodes=[
                make_episode(
                    hook="亲子鉴定完整结果出来了。",
                    final="你到底是谁？",
                )
            ]
        ),
        next_round_context=make_next_context(),
        previous_context=previous_context,
    )

    assert any("forbidden reveal leaked" in item for item in report.blocking_warnings)


def test_continuity_allows_partial_identity_clue_without_full_reveal():
    previous_context = make_next_context()
    previous_context.forbidden_reveals = ["林晚是真千金"]
    report = build_adaptation_quality_report(
        source_text="林晚生日宴被羞辱，旧木盒出现。",
        source_analysis=make_source_analysis("谁敢碰她一下！"),
        episode_context=make_context(),
        story_bible=make_bible(),
        script_batch=ScriptBatch(
            episodes=[
                make_episode(
                    hook="这块玉佩，只有真千金才有。",
                    final="她到底是不是林家人？",
                )
            ]
        ),
        next_round_context=make_next_context(),
        previous_context=previous_context,
    )

    assert not any("forbidden reveal leaked" in item for item in report.blocking_warnings)


def test_source_fidelity_blocks_passive_promise_rewritten_as_protagonist_demand():
    report = build_adaptation_quality_report(
        source_text="颁奖礼暗处，对手低声说：给你准备了惊喜。主角只是僵住，没有追问。",
        source_analysis=make_source_analysis("给你准备了惊喜"),
        episode_context=make_context(),
        story_bible=make_bible(),
        script_batch=ScriptBatch(
            episodes=[
                make_episode(
                    hook="你答应过我的影后呢？",
                    final="你到底骗了我多久？",
                )
            ]
        ),
        next_round_context=make_next_context(),
        previous_context=None,
    )

    assert any("主动索取" in item for item in report.blocking_warnings)


def test_source_fidelity_blocks_preplanned_decision_rewritten_as_impulse():
    report = build_adaptation_quality_report(
        source_text="她早就把解约协议放在办公室抽屉里，这是她深思熟虑后的离开。",
        source_analysis=make_source_analysis("她早就把解约协议放在办公室抽屉里"),
        episode_context=make_context(),
        story_bible=make_bible(),
        script_batch=ScriptBatch(
            episodes=[
                make_episode(
                    hook="我现在就解约。",
                    final="这字，我当场签。",
                )
            ]
        ),
        next_round_context=make_next_context(),
        previous_context=None,
    )

    assert any("现场冲动决定" in item for item in report.blocking_warnings)


def test_source_fidelity_blocks_removed_high_tension_opening():
    report = build_adaptation_quality_report(
        source_text=(
            "开场，她被抱坐在路淮北腿上，男人的手擦过衣服边缘。"
            "她僵住，害怕被颁奖礼镜头拍到。"
        ),
        source_analysis=make_source_analysis("害怕被颁奖礼镜头拍到"),
        episode_context=make_context(),
        story_bible=make_bible(),
        script_batch=ScriptBatch(
            episodes=[
                make_episode(
                    hook="颁奖礼开始了。",
                    final="名单公布了。",
                )
            ]
        ),
        next_round_context=make_next_context(),
        previous_context=None,
    )

    assert any("opening tension asset" in item for item in report.blocking_warnings)


def empty_source_analysis() -> SourceAnalysis:
    return SourceAnalysis(
        characters=["甲", "乙", "丙"],
        events=[],
        conflicts=[],
        visual_moments=[],
        low_value_passages=[],
        candidate_hooks=[],
    )


def test_story_event_ledger_blocks_repeated_high_impact_intimacy_exposure():
    report = build_adaptation_quality_report(
        source_text="公开亲密曝光是单次高价值名场面，后续只能承接后果。",
        source_analysis=empty_source_analysis(),
        episode_context=EpisodeContext(
            target_episode_range="EP05-EP09",
            story_stage=StoryStage.MISUNDERSTANDING_ESCALATION,
            source_to_episode_mapping=[],
            must_carry_context=[],
            forbidden_reveals=[],
            adaptation_actions=[],
            confidence=0.9,
        ),
        story_bible=make_bible(),
        script_batch=ScriptBatch(
            episodes=[
                make_episode(
                    5,
                    hook="订婚宴舞台上，他低头吻住她，直播镜头亮起。",
                    final="照片已经上热搜。",
                ),
                make_episode(
                    9,
                    hook="庆典镜头前，他再次吻住她，偷拍视频曝光。",
                    final="全网又炸了。",
                ),
            ]
        ),
        next_round_context=NextRoundContext(
            summary="EP09 停在二次曝光。",
            current_episode=9,
            open_hooks=["全网又炸了。"],
            forbidden_reveals=[],
            character_knowledge={},
            relationship_changes=[],
            prop_states=[],
            foreshadowing_ledger=[],
        ),
        previous_context=None,
    )

    assert any("仪式化/高场面亲密节点" in item for item in report.blocking_warnings)
    assert any("亲密关系公开/曝光节点" in item for item in report.blocking_warnings)
    assert any(
        entry.kind == "story_event" and entry.key == "public_intimacy_exposure"
        for entry in report.story_state_ledger.entries
    )


def test_story_event_markers_ignore_exit_recap_as_a_second_decision():
    assert "irreversible_exit_decision" not in {
        key for key, _ in _story_event_markers("我已经提交了解约协议。")
    }


def test_story_event_markers_do_not_join_unrelated_lines_into_reckoning():
    text = (
        "十年时间，感谢您和公司的栽培，但一切到此为止。\n"
        "你敢签这份协议，就别怪我封杀你。\n"
        "只要你道歉，我可以给你。\n"
        "巨星有很多优秀伙伴，他们更需要公司的培养。"
    )

    assert "institutional_reckoning" not in {
        key for key, _ in _story_event_markers(text)
    }


def test_story_event_ledger_blocks_institutional_reckoning_without_evidence_chain():
    report = build_adaptation_quality_report(
        source_text="机构清算线需要证据、验证、公开、后果顺序。",
        source_analysis=empty_source_analysis(),
        episode_context=EpisodeContext(
            target_episode_range="EP10-EP10",
            story_stage=StoryStage.PUBLIC_REVEAL,
            source_to_episode_mapping=[],
            must_carry_context=[],
            forbidden_reveals=[],
            adaptation_actions=[],
            confidence=0.9,
        ),
        story_bible=make_bible(),
        script_batch=ScriptBatch(
            episodes=[
                make_plain_episode(
                    10,
                    hook="公司官方发布会开启。",
                    final="全网反转，公司倒台。",
                )
            ]
        ),
        next_round_context=NextRoundContext(
            summary="EP10 机构清算。",
            current_episode=10,
            open_hooks=["全网反转，公司倒台。"],
            forbidden_reveals=[],
            character_knowledge={},
            relationship_changes=[],
            prop_states=[],
            foreshadowing_ledger=[],
        ),
        previous_context=None,
    )

    assert any("证据链" in item for item in report.story_state_ledger.blocking_warnings)
    assert any("证据链" in item for item in report.blocking_warnings)


def test_story_event_ledger_allows_institutional_reckoning_after_visible_evidence_chain():
    report = build_adaptation_quality_report(
        source_text="证据先出现，再进入机构清算和舆论反转。",
        source_analysis=empty_source_analysis(),
        episode_context=EpisodeContext(
            target_episode_range="EP08-EP09",
            story_stage=StoryStage.PUBLIC_REVEAL,
            source_to_episode_mapping=[],
            must_carry_context=[],
            forbidden_reveals=[],
            adaptation_actions=[],
            confidence=0.9,
        ),
        story_bible=make_bible(),
        script_batch=ScriptBatch(
            episodes=[
                make_plain_episode(
                    8,
                    hook="录音原件和合同已经公证。",
                    final="律师函递出。",
                ),
                make_plain_episode(
                    9,
                    hook="公司官方发布会开启。",
                    final="全网反转，公司倒台。",
                ),
            ]
        ),
        next_round_context=NextRoundContext(
            summary="EP09 机构清算。",
            current_episode=9,
            open_hooks=["全网反转，公司倒台。"],
            forbidden_reveals=[],
            character_knowledge={},
            relationship_changes=[],
            prop_states=[],
            foreshadowing_ledger=[],
        ),
        previous_context=None,
    )

    assert not any("证据链" in item for item in report.blocking_warnings)


def test_story_event_ledger_blocks_identity_reveal_without_evidence_chain():
    report = build_adaptation_quality_report(
        source_text="身份结论公开需要可见证据链。",
        source_analysis=empty_source_analysis(),
        episode_context=EpisodeContext(
            target_episode_range="EP06-EP06",
            story_stage=StoryStage.PUBLIC_REVEAL,
            source_to_episode_mapping=[],
            must_carry_context=[],
            forbidden_reveals=[],
            adaptation_actions=[],
            confidence=0.9,
        ),
        story_bible=make_bible(),
        script_batch=ScriptBatch(
            episodes=[
                make_plain_episode(
                    6,
                    hook="全场公开他的真实身份。",
                    final="少主身份终于坐实。",
                )
            ]
        ),
        next_round_context=NextRoundContext(
            summary="EP06 身份公开。",
            current_episode=6,
            open_hooks=["少主身份终于坐实。"],
            forbidden_reveals=[],
            character_knowledge={},
            relationship_changes=[],
            prop_states=[],
            foreshadowing_ledger=[],
        ),
        previous_context=None,
    )

    assert any("身份/真相结论公开" in item for item in report.blocking_warnings)
    assert any("证据链" in item for item in report.blocking_warnings)


def test_story_event_ledger_allows_identity_reveal_after_visible_evidence_chain():
    report = build_adaptation_quality_report(
        source_text="身份结论由令牌和鉴定书支撑。",
        source_analysis=empty_source_analysis(),
        episode_context=EpisodeContext(
            target_episode_range="EP05-EP06",
            story_stage=StoryStage.PUBLIC_REVEAL,
            source_to_episode_mapping=[],
            must_carry_context=[],
            forbidden_reveals=[],
            adaptation_actions=[],
            confidence=0.9,
        ),
        story_bible=make_bible(),
        script_batch=ScriptBatch(
            episodes=[
                make_plain_episode(
                    5,
                    hook="祖传令牌和鉴定书同时亮出。",
                    final="长老要求当众验证。",
                ),
                make_plain_episode(
                    6,
                    hook="全场公开他的真实身份。",
                    final="少主身份终于坐实。",
                ),
            ]
        ),
        next_round_context=NextRoundContext(
            summary="EP06 身份公开。",
            current_episode=6,
            open_hooks=["少主身份终于坐实。"],
            forbidden_reveals=[],
            character_knowledge={},
            relationship_changes=[],
            prop_states=["祖传令牌和鉴定书已公开"],
            foreshadowing_ledger=[],
        ),
        previous_context=None,
    )

    assert not any("身份/真相结论公开" in item for item in report.blocking_warnings)


def character_agency_source_analysis() -> SourceAnalysis:
    return SourceAnalysis(
        characters=["主角", "对手", "支持者"],
        events=["主角在公开压迫中僵住，随后逐步清醒"],
        conflicts=["主角被对手持续压迫"],
        visual_moments=[],
        low_value_passages=[],
        candidate_hooks=[],
    )


def character_agency_bible() -> StoryBible:
    return StoryBible(
        genre="通用强冲突短剧",
        mainline="主角在压迫中逐步清醒并反击。",
        characters=["主角", "对手", "支持者"],
        relationships=["对手持续压迫主角", "支持者给主角后盾"],
        speech_styles={"主角": "克制短句", "对手": "直白施压", "支持者": "短句给后盾"},
        immutable_facts=["主角经历公开压迫"],
        forbidden_changes=["不得让支持者替主角完成核心决定"],
    )


def test_source_fidelity_blocks_early_omniscient_counterattack_when_source_is_vulnerable():
    report = build_adaptation_quality_report(
        source_text="开场主角被公开羞辱，僵住，手指发抖。她没有立刻反击，只是在心碎后逐步清醒。",
        source_analysis=character_agency_source_analysis(),
        episode_context=make_context(),
        story_bible=character_agency_bible(),
        script_batch=ScriptBatch(
            episodes=[
                make_plain_episode(
                    1,
                    hook="我早就知道你们完了。",
                    final="所有证据都在我手里。",
                )
            ]
        ),
        next_round_context=make_next_context(),
        previous_context=None,
    )

    assert any("全知全能式开杀" in item for item in report.blocking_warnings)
    assert any(check.category == "agency_ramp" for check in report.source_fidelity.checks)


def test_source_fidelity_allows_omniscient_counterattack_when_source_has_preexisting_power():
    report = build_adaptation_quality_report(
        source_text="主角重生归来，早就知道对手设局，也提前布好证据。她曾被羞辱，这一次要主动破局。",
        source_analysis=character_agency_source_analysis(),
        episode_context=make_context(),
        story_bible=character_agency_bible(),
        script_batch=ScriptBatch(
            episodes=[
                make_plain_episode(
                    1,
                    hook="我早就知道你们完了。",
                    final="所有证据都在我手里。",
                )
            ]
        ),
        next_round_context=make_next_context(),
        previous_context=None,
    )

    assert not any("全知全能式开杀" in item for item in report.blocking_warnings)


def test_source_fidelity_blocks_support_role_taking_over_protagonist_choice():
    report = build_adaptation_quality_report(
        source_text="主角必须自己做离开决定，支持者只能递证据和兜底。",
        source_analysis=character_agency_source_analysis(),
        episode_context=make_context(),
        story_bible=character_agency_bible(),
        script_batch=ScriptBatch(
            episodes=[
                make_plain_episode(
                    1,
                    hook="你不用出面，剩下交给我。",
                    final="我已经替你签了。",
                )
            ]
        ),
        next_round_context=make_next_context(),
        previous_context=None,
    )

    assert any("支持型角色主动权越界" in item for item in report.blocking_warnings)
    assert any(check.category == "support_role_boundary" for check in report.source_fidelity.checks)


def test_source_fidelity_allows_support_role_giving_choice_and_backing():
    report = build_adaptation_quality_report(
        source_text="主角必须自己做离开决定，支持者只能递证据和兜底。",
        source_analysis=character_agency_source_analysis(),
        episode_context=make_context(),
        story_bible=character_agency_bible(),
        script_batch=ScriptBatch(
            episodes=[
                make_plain_episode(
                    1,
                    hook="证据给你，你自己决定。",
                    final="我给你撑腰。",
                )
            ]
        ),
        next_round_context=make_next_context(),
        previous_context=None,
    )

    assert not any("支持型角色主动权越界" in item for item in report.blocking_warnings)


def test_source_fidelity_blocks_passive_opponent_without_countermove():
    report = build_adaptation_quality_report(
        source_text="对手一直主动压迫主角，后续必须有反制。",
        source_analysis=character_agency_source_analysis(),
        episode_context=make_context(),
        story_bible=character_agency_bible(),
        script_batch=ScriptBatch(
            episodes=[
                make_plain_episode(
                    1,
                    hook="反派脸色发白，躲在角落发抖。",
                    final="反派不敢说话。",
                )
            ]
        ),
        next_round_context=make_next_context(),
        previous_context=None,
    )

    assert any("对手行动线空心" in item for item in report.blocking_warnings)
    assert any(check.category == "opponent_agency" for check in report.source_fidelity.checks)


def test_source_fidelity_allows_opponent_with_active_countermove():
    report = build_adaptation_quality_report(
        source_text="对手一直主动压迫主角，后续必须有反制。",
        source_analysis=character_agency_source_analysis(),
        episode_context=make_context(),
        story_bible=character_agency_bible(),
        script_batch=ScriptBatch(
            episodes=[
                make_plain_episode(
                    1,
                    hook="反派买通媒体，删掉监控。",
                    final="他威胁证人改口。",
                )
            ]
        ),
        next_round_context=make_next_context(),
        previous_context=None,
    )

    assert not any("对手行动线空心" in item for item in report.blocking_warnings)
