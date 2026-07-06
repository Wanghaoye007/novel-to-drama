from novel_drama_engine.adaptation_quality import (
    build_adaptation_quality_report,
    build_story_state_ledger,
    build_methodology_quality_report,
    merge_methodology_quality_into_report,
)
from novel_drama_engine.models import (
    AdaptationIntensity,
    EpisodeContext,
    EpisodeScript,
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
