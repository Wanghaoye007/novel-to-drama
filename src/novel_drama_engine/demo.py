from __future__ import annotations

from pydantic import BaseModel

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

EPISODES_PER_ROUND = 5

STORY_STAGES = [
    StoryStage.OPENING_PRESSURE,
    StoryStage.IDENTITY_HOOK,
    StoryStage.FIRST_COUNTERATTACK,
    StoryStage.MISUNDERSTANDING_ESCALATION,
    StoryStage.MIDPOINT_REVERSAL,
    StoryStage.TRUTH_NEAR_REVEAL,
    StoryStage.PUBLIC_REVEAL,
    StoryStage.FINAL_RECKONING,
]

EPISODE_BEATS = [
    ("被赶出生日宴", "把她拖出去！", "羞辱", "管家认出林晚"),
    ("管家跪叫大小姐", "谁敢碰她一下！", "身份悬念", "林雪发现管家带来旧玉佩"),
    ("旧玉佩反咬假千金", "这块玉佩，只有真千金才有。", "反击", "顾承看到亲子档案编号"),
    ("顾承第一次动摇", "你到底是谁？", "误会松动", "林雪偷走鉴定样本"),
    ("林雪设局换样本", "鉴定结果出来前，她必须消失。", "阴谋升级", "林晚被关进停电仓库"),
    ("仓库直播反杀", "镜头开着，你们继续说。", "反杀", "全网听见林雪承认换样本"),
    ("顾承公开护错人", "我只信林雪。", "错爱压迫", "林晚拿出第二份备份"),
    ("第二份鉴定曝光", "这一次，谁也换不了。", "身份逼近", "林父看见当年护士签名"),
    ("林父深夜查旧案", "二十年前抱错的人，不止一个。", "旧案", "顾家也卷入抱错真相"),
    ("顾家秘密浮出", "顾承，你母亲也在名单上。", "家族反转", "林雪联系神秘女人"),
    ("神秘女人归来", "当年，是我亲手换的孩子。", "真相逼近", "她点名要见林晚"),
    ("林晚拿回继承权", "林家的门，我自己走回来。", "夺回", "林雪被赶出主宅"),
    ("林雪最后一搏", "没有我，你们谁也别想好过。", "疯批反扑", "林雪绑走林母"),
    ("天台救母", "妈，别再为假女儿求情。", "亲情撕裂", "林母第一次叫林晚女儿"),
    ("公开认亲宴", "今天，我只认一个女儿。", "公开爽点", "顾承跪下道歉"),
]


def episode_window(
    *,
    round_number: int,
    previous_context: NextRoundContext | None,
    target_episode_count: int | None,
    episodes_per_round: int = EPISODES_PER_ROUND,
) -> tuple[int, int]:
    if previous_context:
        start = previous_context.current_episode + 1
    else:
        start = (round_number - 1) * episodes_per_round + 1
    target_end = target_episode_count or (start + episodes_per_round - 1)
    end = min(start + episodes_per_round - 1, target_end)
    if end < start:
        end = start
    return start, end


def _source_hint(source_text: str) -> str:
    compact = " ".join(source_text.split())
    if not compact:
        return "豪门生日宴羞辱"
    return compact[:48]


def _beat(episode: int) -> tuple[str, str, str, str]:
    return EPISODE_BEATS[(episode - 1) % len(EPISODE_BEATS)]


def _scene_lines(episode: int, title: str, hook: str, cliffhanger: str) -> list[Scene]:
    ep = f"EP{episode:02d}"
    return [
        Scene(
            heading=f"{episode}-1 夜-内-林家宴会厅",
            characters=["林晚", "林雪", "顾承"],
            lines=[
                SceneLine(kind="action", text=f"△{ep} 开场，林晚被推到宴会厅中央，所有镜头和宾客目光同时压过来。"),
                SceneLine(kind="dialogue", speaker="林雪", emotion="温柔带刺", text="姐姐，你再闹下去，今天所有人都会记住你的难堪。"),
                SceneLine(kind="dialogue", speaker="林晚", emotion="克制", text="我不怕被记住，我怕你们不敢把真相听完。"),
                SceneLine(kind="action", text="△顾承抬手拦住她，保安的脚步声逼近，手机直播弹幕开始暴涨。"),
                SceneLine(kind="dialogue", speaker="顾承", emotion="冷", text="滚出去。"),
                SceneLine(kind="dialogue", speaker="顾承", emotion="压怒", text=hook),
                SceneLine(kind="dialogue", speaker="林晚", emotion="冷笑", text="你现在护着她，等会儿别求我回头看你。"),
            ],
        ),
        Scene(
            heading=f"{episode}-2 夜-内-宴会厅侧门",
            characters=["林晚", "老管家", "林雪", "顾承"],
            lines=[
                SceneLine(kind="action", text="△侧门忽然打开，老管家握着一只旧木盒冲进来，盒角还沾着雨水。"),
                SceneLine(kind="dialogue", speaker="老管家", emotion="颤抖", text="大小姐，这东西我替您守了二十年。"),
                SceneLine(kind="dialogue", speaker="林雪", emotion="慌", text="一个下人说的话，也配当证据？"),
                SceneLine(kind="dialogue", speaker="林晚", emotion="逼近", text="那就让你亲手打开，看清楚里面写的是谁的名字。"),
                SceneLine(kind="action", text="△木盒打开，旧照片、出生牌、半枚玉佩同时露出，宾客席一片死寂。"),
                SceneLine(kind="dialogue", speaker="顾承", emotion="动摇", text="林雪，你刚才说你从没见过这只盒子。"),
            ],
        ),
        Scene(
            heading=f"{episode}-3 夜-内-宴会厅主屏前",
            characters=["林晚", "林雪", "顾承", "林父"],
            lines=[
                SceneLine(kind="action", text=f"△林晚把证据投到主屏，{title} 的核心冲突被迫摊在所有人面前。"),
                SceneLine(kind="dialogue", speaker="林父", emotion="压低", text="关掉屏幕，今天的事到此为止。"),
                SceneLine(kind="dialogue", speaker="林晚", emotion="锋利", text="二十年都能被你们按下去，今天按不住了。"),
                SceneLine(kind="dialogue", speaker="林雪", emotion="失控", text="她是假的！她就是想毁了林家！"),
                SceneLine(kind="action", text="△主屏突然跳出一段未公开录音，林雪的声音先响起来。"),
                SceneLine(kind="dialogue", speaker="录音里的林雪", emotion="阴冷", text=cliffhanger),
            ],
        ),
    ]


def _episode_script(episode: int) -> EpisodeScript:
    title, hook, emotion, cliffhanger = _beat(episode)
    return EpisodeScript(
        episode=episode,
        title=title,
        hook_3s=hook,
        main_emotion=emotion,
        watch_reason="观众要看女主在公开压迫下连续反击，并确认真假千金身份线如何推进。",
        scenes=_scene_lines(episode, title, hook, cliffhanger),
        cliffhanger=cliffhanger,
        state_update={
            "episode": episode,
            "new_pressure": title,
            "open_hook": cliffhanger,
        },
    )


def demo_round_outputs(
    *,
    source_text: str = "",
    round_number: int = 1,
    previous_context: NextRoundContext | None = None,
    target_episode_count: int | None = None,
    episodes_per_round: int = EPISODES_PER_ROUND,
) -> list[BaseModel]:
    start, end = episode_window(
        round_number=round_number,
        previous_context=previous_context,
        target_episode_count=target_episode_count,
        episodes_per_round=episodes_per_round,
    )
    episodes = [_episode_script(episode) for episode in range(start, end + 1)]
    target_range = f"EP{start:02d}-EP{end:02d}"
    source_hint = _source_hint(source_text)
    stage = STORY_STAGES[min(round_number - 1, len(STORY_STAGES) - 1)]
    last_episode = episodes[-1]

    return [
        SourceAnalysis(
            characters=["林晚", "林雪", "顾承", "老管家", "林父"],
            events=[source_hint, f"{target_range} 围绕真假千金身份线连续升级"],
            conflicts=["真假千金身份冲突", "男主误判女主", "家族压迫与公开反击"],
            visual_moments=["邀请函被撕碎", "旧木盒打开", "主屏投出证据", "直播弹幕爆发"],
            low_value_passages=["长篇心理描写", "重复背景介绍"],
            candidate_hooks=[episodes[0].hook_3s],
        ),
        EpisodeContext(
            target_episode_range=target_range,
            story_stage=stage,
            source_to_episode_mapping=[
                f"{source_hint} -> {target_range}",
                f"上一轮承接 -> 从 EP{start:02d} 开始推进" if previous_context else "开场压迫 -> EP01 起势",
            ],
            must_carry_context=(previous_context.open_hooks if previous_context else []),
            forbidden_reveals=["不得在本轮提前完全公开亲子鉴定", "不得让林雪无代价退场"],
            adaptation_actions=[
                "每集前 3 秒直接进入冲突",
                "每集结尾留下身份或关系钩子",
                "压缩旁白，增加可拍摄动作和短对白",
            ],
            confidence=0.92,
        ),
        StoryBible(
            genre="豪门真假千金",
            mainline="林晚被假千金夺走身份后，在公开羞辱和家族压迫中逐集反击，最终拿回身份与继承权。",
            characters=["林晚", "林雪", "顾承", "老管家", "林父"],
            relationships=["林雪冒充林家千金", "顾承暂时误会林晚", "老管家掌握旧案证据"],
            speech_styles={
                "林晚": "克制短句，反击锋利",
                "林雪": "表面温柔，每句带刺",
                "顾承": "高压命令式，后期逐步动摇",
            },
            immutable_facts=["林晚是真千金", "林雪知道换身份真相"],
            forbidden_changes=["不得新增亲哥哥救场", "不得提前一次性公开全部真相"],
        ),
        ScriptBatch(episodes=episodes),
        QualityReport(
            status=QualityStatus.USABLE,
            scores=QualityScores(
                hook=9,
                conflict=9,
                cliffhanger=9,
                continuity=9,
                video_feasibility=8,
            ),
            blocking_issues=[],
            rewrite_instruction="",
        ),
        NextRoundContext(
            summary=f"{target_range} 已完成，最后停在：{last_episode.cliffhanger}",
            current_episode=end,
            open_hooks=[last_episode.cliffhanger, "林晚身份真相仍未完全公开"],
            forbidden_reveals=["林晚是真千金", "当年换婴完整幕后"],
            character_knowledge={
                "林晚": [f"已推进到 EP{end:02d}", "知道林雪在隐藏关键证据"],
                "林雪": ["身份线持续受威胁", "必须阻止下一份证据公开"],
                "顾承": ["开始怀疑林雪", "仍未完全站到林晚一边"],
            },
            relationship_changes=[f"林晚与林雪在 {target_range} 冲突升级"],
            prop_states=["旧木盒已公开", "玉佩线索仍可继续推进", "录音证据留下二次反转空间"],
            foreshadowing_ledger=[f"下一轮从 EP{end + 1:02d} 承接公开证据后的反扑"],
        ),
    ]
