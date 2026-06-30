from __future__ import annotations

from pydantic import BaseModel

from novel_drama_engine.models import (
    EpisodeContext,
    EpisodeScript,
    LocalizedScriptBatch,
    MarketingAssets,
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


def demo_round_outputs() -> list[BaseModel]:
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


def demo_localization_output(
    locale: str = "en-US",
    platform: str = "TikTok",
) -> LocalizedScriptBatch:
    return LocalizedScriptBatch(
        locale=locale,
        platform=platform,
        title_strategy="Keep the public humiliation hook, but make dialogue sharper and more direct for vertical short drama.",
        episodes=[
            EpisodeScript(
                episode=1,
                title="Thrown Out at the Birthday Banquet",
                hook_3s="Throw her out!",
                main_emotion="public humiliation",
                watch_reason="Viewers want to see how Lina turns a public insult into a comeback.",
                scenes=[
                    Scene(
                        heading="1-1 NIGHT - INT. LIN FAMILY BANQUET HALL",
                        characters=["Lina", "Celia", "Grant"],
                        lines=[
                            SceneLine(
                                kind="action",
                                text="Lina stands frozen in the middle of the banquet hall as Grant rips her invitation in half.",
                            ),
                            SceneLine(
                                kind="dialogue",
                                speaker="Grant",
                                emotion="cold",
                                text="Get out.",
                            ),
                            SceneLine(
                                kind="dialogue",
                                speaker="Celia",
                                emotion="sweet but cruel",
                                text="Lina, don't make this harder than it has to be.",
                            ),
                        ],
                    )
                ],
                cliffhanger='The old butler stops at the door and whispers, "Miss Lina?"',
                state_update={"open_hook": "The butler recognizes Lina"},
            )
        ],
        adaptation_notes=[
            "Localized character names while preserving the identity-swap premise.",
            "Kept the opening conflict in the first three seconds.",
        ],
        cultural_notes=[
            "Changed formal family-address tension into direct public status humiliation.",
        ],
        compliance_notes=[
            "Avoid showing physical assault; keep the humiliation verbal and visual.",
        ],
        preserved_hooks=[
            "Public expulsion",
            "Butler recognition cliffhanger",
        ],
    )


def demo_marketing_assets(
    locale: str = "en-US",
    platform: str = "TikTok",
) -> MarketingAssets:
    return MarketingAssets(
        locale=locale,
        platform=platform,
        campaign_angle="Public humiliation turns into an identity mystery.",
        titles=[
            "They Threw Her Out. The Butler Knew Her Name.",
            "The Heiress They Humiliated Was Standing Right There",
            "One Torn Invitation Exposed Their Biggest Lie",
        ],
        short_descriptions=[
            "Lina is humiliated in front of everyone, until one whisper changes the room.",
            "A fake heiress smiles as Lina is thrown out. Then the family butler freezes.",
        ],
        opening_hooks=[
            "Throw her out!",
            "She came with an invitation. He tore it in half.",
            "Everyone laughed, until the butler called her Miss Lina.",
        ],
        hashtags=[
            "#ShortDrama",
            "#RevengeDrama",
            "#HiddenHeiress",
            "#VerticalDrama",
        ],
        primary_cta="Watch Episode 1 to see why the butler recognized her.",
        audience_notes=[
            "Targets viewers who respond to identity reveals and public humiliation reversals.",
        ],
        compliance_notes=[
            "Keep ad copy focused on humiliation and mystery; avoid threats of physical harm.",
        ],
    )
