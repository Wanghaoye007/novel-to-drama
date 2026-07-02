from novel_drama_engine.adaptation_quality import (
    build_adaptation_quality_report,
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
