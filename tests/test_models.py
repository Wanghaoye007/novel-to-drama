import pytest
from pydantic import ValidationError

from novel_drama_engine.models import (
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
    SourceAnalysis,
    StoryBible,
    StoryStage,
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
    assert data["script_batch"]["episodes"][0]["hook_3s"] == "把她拖出去！"
