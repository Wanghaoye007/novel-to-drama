import pytest
from pydantic import ValidationError

from novel_drama_engine.models import (
    EpisodeDramaPlan,
    EpisodePlan,
    EpisodeContext,
    EpisodeScript,
    NextRoundContext,
    QualityReport,
    QualityScores,
    QualityStatus,
    RoundResult,
    Scene,
    SceneLine,
    ScriptBatch,
    CharacterProfile,
    ConflictStack,
    SeriesEpisodeOutline,
    SeriesStructurePlan,
    SourceAnalysis,
    StoryBible,
    StoryStage,
    ViralAssetReport,
    GenerationVariant,
)


def test_story_stage_rejects_unknown_value():
    with pytest.raises(ValidationError):
        EpisodeContext(
            target_episode_range="EP01-EP03",
            story_stage="slow_setup",
            source_to_episode_mapping=[],
            must_carry_context=[],
            forbidden_reveals=[],
            adaptation_actions=[],
            confidence=0.8,
        )


def test_round_result_serializes_nested_models():
    script = EpisodeScript(
        episode=1,
        title="宴会羞辱",
        hook_3s="把她拖出去！",
        main_emotion="羞辱",
        watch_reason="观众想看女主如何反击。",
        scenes=[
            Scene(
                heading="1-1 夜-内-林家宴会厅",
                characters=["林晚", "林雪"],
                lines=[
                    SceneLine(kind="action", text="△林晚站在宴会厅中央，邀请函被撕成两半。"),
                    SceneLine(kind="dialogue", speaker="林雪", emotion="温柔带刺", text="姐姐，你是不是走错地方了？"),
                ],
            )
        ],
        cliffhanger="管家推门而入：大小姐，我们终于找到您了。",
        state_update={"new_fact": "管家认出林晚"},
    )
    result = RoundResult(
        project_id="demo",
        round_number=1,
        source_analysis=SourceAnalysis(
            characters=["林晚", "林雪"],
            events=["生日宴羞辱"],
            conflicts=["真假千金身份冲突"],
            visual_moments=["邀请函被撕碎"],
            low_value_passages=[],
            candidate_hooks=["把她拖出去！"],
        ),
        episode_context=EpisodeContext(
            target_episode_range="EP01-EP01",
            story_stage=StoryStage.OPENING_PRESSURE,
            source_to_episode_mapping=["生日宴羞辱 -> EP01"],
            must_carry_context=[],
            forbidden_reveals=["林晚是真千金"],
            adaptation_actions=["压缩铺垫，直接从宴会冲突开场"],
            confidence=0.95,
        ),
        story_bible=StoryBible(
            genre="真假千金",
            mainline="林晚被假千金夺走身份后逐步反击。",
            characters=["林晚", "林雪"],
            relationships=["林雪冒充林家千金"],
            speech_styles={"林晚": "克制短句，反击锋利"},
            immutable_facts=["林晚是真千金"],
            forbidden_changes=["不得新增亲哥哥"],
        ),
        script_batch=ScriptBatch(episodes=[script]),
        quality_report=QualityReport(
            status=QualityStatus.USABLE,
            scores=QualityScores(hook=8, conflict=9, cliffhanger=8, continuity=10, video_feasibility=8),
            blocking_issues=[],
            rewrite_instruction="",
        ),
        next_round_context=NextRoundContext(
            summary="EP01 结束于管家认出林晚。",
            current_episode=1,
            open_hooks=["管家为何叫她大小姐"],
            forbidden_reveals=["林晚是真千金"],
            character_knowledge={"林雪": ["林晚身份有问题"]},
            relationship_changes=["林晚与林雪公开对立"],
            prop_states=[],
            foreshadowing_ledger=["管家的称呼将在 EP03 推进"],
        ),
    )

    data = result.model_dump()
    assert data["episode_context"]["story_stage"] == "opening_pressure"
    assert data["episode_context"]["source_to_episode_mapping"][0]["source"] == "生日宴羞辱 -> EP01"
    assert data["script_batch"]["episodes"][0]["hook_3s"] == "把她拖出去！"


def test_episode_context_accepts_structured_source_mapping_from_kimi():
    context = EpisodeContext.model_validate(
        {
            "target_episode_range": "EP01-EP02",
            "story_stage": "opening_pressure",
            "source_to_episode_mapping": [
                {
                    "source": "1-1 夜-内-地府女主住处：女主因冥钞断供欠债。",
                    "target_episode": "EP01",
                    "retained_assets": ["冥钞", "账单", "讨债动机"],
                    "adaptation_reason": "作为前三秒反差设定。",
                    "information_increment": "女主欠下地府巨债。",
                }
            ],
            "must_carry_context": ["女主要找温铮讨债"],
            "forbidden_reveals": ["温铮停烧纸钱的真实原因"],
            "adaptation_actions": ["压缩地府解释，改成账单动作和阎王短台词"],
            "confidence": 0.9,
        }
    )

    mapping = context.source_to_episode_mapping[0]
    assert mapping.source.startswith("1-1 夜-内")
    assert mapping.target_episode == "EP01"
    assert mapping.information_increment == "女主欠下地府巨债。"


def test_scene_line_strips_repeated_speaker_prefix_from_dialogue_text():
    line = SceneLine(
        kind="dialogue",
        speaker="Eleanor",
        emotion="绝望",
        text="Eleanor（电话中）：我只是想让Ellie回家。",
    )

    assert line.text == "我只是想让Ellie回家。"
    assert line.emotion == "绝望"


def test_scene_line_strips_os_marker_from_text():
    line = SceneLine(
        kind="os",
        speaker="Eleanor Park",
        text="（Eleanor OS）我女儿，在他们带走我们两小时后死了。",
    )

    assert line.text == "我女儿，在他们带走我们两小时后死了。"


def test_scene_line_normalizes_action_opening_for_downstream_shots():
    static_line = SceneLine(kind="action", text="△中景，Eleanor转身看向玻璃门。")
    character_line = SceneLine(kind="action", text="△Dom冷笑着走近Eleanor。")

    assert static_line.text.startswith("△中景定镜，")
    assert character_line.text.startswith("△中近景推近，Dom")


def test_series_episode_outline_allows_missing_climax_role_from_kimi():
    outline = SeriesEpisodeOutline.model_validate(
        {
            "episode": 1,
            "core_event": "女主发现温铮订婚。",
            "emotion_node": "震惊转愤怒",
            "information_increment": "温铮停止烧纸钱后即将订婚。",
            "ending_hook_type": "强台词截断",
            "ending_hook": "女主冲进酒店讨债。",
            "source_anchor": "1-4 日-外-五星级酒店门口",
        }
    )

    assert outline.climax_role == "未标注"


def test_episode_plan_requires_physical_action_chain():
    plan = EpisodePlan(
        variant=GenerationVariant.DRAMA_ENGINE_FIRST,
        target_episode_range="EP01-EP01",
        adaptation_strategy="先设计戏剧引擎，再写剧本。",
        episodes=[
            EpisodeDramaPlan(
                episode=1,
                title="宴会羞辱",
                drama_engine="女主用直播证据反压假千金。",
                protagonist_misbelief="反派以为女主孤立无援。",
                truth_gap="女主已经开了直播。",
                physical_action_chain=["开直播", "推开保安", "投屏证据"],
                scene_dynamics=["宴会中心被推搡", "主屏前反压"],
                emotional_turns=["羞辱", "反击"],
                audience_information_gap="观众知道直播已开，反派不知道。",
                three_pull_beats=["保安拖人", "顾承护错人", "证据上屏"],
                false_payoff="老管家出现后反派质疑证据。",
                planted_key="旧木盒",
                strongest_line="你现在护着她，等会儿别求我。",
                cliffhanger_design="主屏弹出录音。",
                source_assets_to_keep=["生日宴", "旧木盒"],
                forbidden_shortcuts=["不得新增亲哥哥"],
            )
        ],
    )

    assert plan.episodes[0].physical_action_chain == ["开直播", "推开保安", "投屏证据"]


def test_sop_full_stack_models_capture_series_contract():
    report = ViralAssetReport(
        channel="女频",
        genre_tags=["豪门", "真假千金"],
        core_setting="真千金被假千金公开压迫。",
        core_dilemma="身份真相不能一次揭完。",
        protagonist_goal="夺回身份。",
        main_conflict="真假千金公开对抗。",
        signature_scenes=["生日宴", "旧木盒", "认亲宴"],
        small_highlights=["邀请函", "玉佩", "录音", "直播", "管家"],
        golden_lines=["谁敢碰她一下！"],
        emotion_curve=["羞辱", "反击", "认亲"],
        adaptation_risks=["过早揭晓"],
        risk_treatments=["分轮兑现证据"],
        low_value_removal_rules=["删除长篇内心"],
    )
    plan = SeriesStructurePlan(
        target_episode_count=30,
        target_episode_range="EP01-EP05",
        structure_rationale="每 3 集小高潮，每 8 集大高潮。",
        opening_contract=["抛设定", "造困境", "主角行动"],
        small_climax_cadence="每 3 集一个小高潮。",
        big_climax_cadence="每 8 集一个大高潮。",
        character_profiles=[
            CharacterProfile(
                name="林晚",
                base_identity="真千金",
                memory_tag="冷脸反击",
                contrast="孤立无援但手握证据",
                core_desire="拿回身份",
                obsession="公开打脸",
                drama_function="打",
                speech_style="短句锋利",
                sample_lines=["你不配。"],
            )
        ],
        conflict_stack=ConflictStack(
            surface_event_conflict="宴会驱逐",
            emotional_conflict="顾承护错人",
            deep_value_conflict="血缘真相和家族利益",
        ),
        global_emotion_curve=["羞辱", "反击", "公开认亲"],
        episode_outlines=[
            SeriesEpisodeOutline(
                episode=1,
                core_event="生日宴驱逐",
                emotion_node="羞辱",
                information_increment="旧玉佩出现",
                ending_hook_type="身份揭晓前",
                ending_hook="管家跪叫大小姐。",
                source_anchor="生日宴段落",
                climax_role="开篇钩子",
            )
        ],
        adaptation_rules=["每集有信息增量"],
        forbidden_slowdowns=["无冲突过渡"],
    )

    assert report.signature_scenes[0] == "生日宴"
    assert plan.episode_outlines[0].information_increment == "旧玉佩出现"
