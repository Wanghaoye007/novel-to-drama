import pytest

from novel_drama_engine.models import (
    EpisodeContext,
    EpisodeScript,
    NextRoundContext,
    QualityReport,
    QualityScores,
    QualityStatus,
    Scene,
    SceneLine,
    ScriptBatch,
    SourceAnalysis,
    StoryBible,
    StoryStage,
)


@pytest.fixture
def happy_round_outputs():
    return [
        SourceAnalysis(
            characters=["林晚", "林雪", "顾承"],
            events=["林晚在生日宴被赶走"],
            conflicts=["真假千金身份冲突", "男主误判女主"],
            visual_moments=["邀请函被撕碎", "林晚站在宴会中央"],
            low_value_passages=["宴会前长篇心理描写"],
            candidate_hooks=["把她拖出去！"],
        ),
        EpisodeContext(
            target_episode_range="EP01-EP01",
            story_stage=StoryStage.OPENING_PRESSURE,
            source_to_episode_mapping=["生日宴羞辱 -> EP01"],
            must_carry_context=[],
            forbidden_reveals=["林晚是真千金"],
            adaptation_actions=["压缩铺垫，直接从宴会冲突开场"],
            confidence=0.93,
        ),
        StoryBible(
            genre="真假千金",
            mainline="林晚被假千金夺走身份后，在公开羞辱中逐步反击。",
            characters=["林晚", "林雪", "顾承"],
            relationships=["林雪冒充千金", "顾承暂时误会林晚"],
            speech_styles={"林晚": "克制短句，反击锋利", "林雪": "表面温柔，每句带刺"},
            immutable_facts=["林晚是真千金"],
            forbidden_changes=["不得新增亲哥哥", "不得提前公开亲子鉴定"],
        ),
        ScriptBatch(
            episodes=[
                EpisodeScript(
                    episode=1,
                    title="被赶出生日宴",
                    hook_3s="把她拖出去！",
                    main_emotion="羞辱",
                    watch_reason="观众想看林晚如何从公开羞辱里反击。",
                    scenes=[
                        Scene(
                            heading="1-1 夜-内-林家宴会厅",
                            characters=["林晚", "林雪", "顾承"],
                            lines=[
                                SceneLine(
                                    kind="action",
                                    text="△林晚站在宴会厅中央，手里的邀请函被顾承撕成两半。",
                                ),
                                SceneLine(
                                    kind="dialogue",
                                    speaker="顾承",
                                    emotion="冷",
                                    text="滚出去。",
                                ),
                                SceneLine(
                                    kind="dialogue",
                                    speaker="林雪",
                                    emotion="温柔",
                                    text="姐姐，别让大家难堪。",
                                ),
                            ],
                        )
                    ],
                    cliffhanger="门口老管家一震：大小姐？",
                    state_update={"open_hook": "管家认出林晚"},
                )
            ]
        ),
        QualityReport(
            status=QualityStatus.USABLE,
            scores=QualityScores(
                hook=9,
                conflict=9,
                cliffhanger=8,
                continuity=10,
                video_feasibility=8,
            ),
            blocking_issues=[],
            rewrite_instruction="",
        ),
        NextRoundContext(
            summary="EP01 结束于管家认出林晚。",
            current_episode=1,
            open_hooks=["管家为什么叫林晚大小姐"],
            forbidden_reveals=["林晚是真千金"],
            character_knowledge={"林雪": ["林晚身份有问题"], "顾承": ["林晚被赶出宴会"]},
            relationship_changes=["林晚与顾承冲突升级"],
            prop_states=["邀请函被撕碎"],
            foreshadowing_ledger=["管家称呼将在后续推进身份线"],
        ),
    ]
