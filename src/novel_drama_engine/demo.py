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
    ("被赶出生日宴", "把她拖出去！", "羞辱", "老管家突然跪下：大小姐，您受苦了！"),
    ("管家跪叫大小姐", "谁敢碰她一下！", "身份悬念", "林雪攥着旧玉佩发抖：这东西怎么会在她手里？"),
    ("旧玉佩反咬假千金", "这块玉佩，只有真千金才有。", "反击", "顾承盯住档案编号：林雪，你到底换了什么？"),
    ("顾承第一次动摇", "你到底是谁？", "误会松动", "林雪把鉴定样本扔进火里：她今晚必须死！"),
    ("林雪设局换样本", "鉴定结果出来前，她必须消失。", "阴谋升级", "仓库门被锁死，林晚听见汽油泼在门外！"),
    ("仓库直播反杀", "镜头开着，你们继续说。", "反杀", "直播间刷爆：林雪刚才亲口承认了！"),
    ("顾承公开护错人", "我只信林雪。", "错爱压迫", "林晚亮出备份：顾承，这次跪下的人该是你！"),
    ("第二份鉴定曝光", "这一次，谁也换不了。", "身份逼近", "林父看到护士签名，当场摔了杯子：把她带来！"),
    ("林父深夜查旧案", "二十年前抱错的人，不止一个。", "旧案", "顾家名字出现在名单上，顾承脸色彻底变了！"),
    ("顾家秘密浮出", "顾承，你母亲也在名单上。", "家族反转", "林雪拨通神秘电话：她查到你了！"),
    ("神秘女人归来", "当年，是我亲手换的孩子。", "真相逼近", "神秘女人指向林晚：她根本不该活到今天！"),
    ("林晚拿回继承权", "林家的门，我自己走回来。", "夺回", "林雪被赶出主宅，却掏出最后一份遗嘱！"),
    ("林雪最后一搏", "没有我，你们谁也别想好过。", "疯批反扑", "林母被推上天台，林雪吼：选她还是选我？"),
    ("天台救母", "妈，别再为假女儿求情。", "亲情撕裂", "林母第一次叫她女儿，顾承却跪在门外！"),
    ("公开认亲宴", "今天，我只认一个女儿。", "公开爽点", "顾承跪下道歉，林晚只问：你配吗？"),
]

SONG_EPISODE_BEATS = [
    ("醒来就喝毒药", "大郎，起来喝药了。", "穿越惊险", "武植攥紧剪刀：想让我死？那就一起死！"),
    ("金莲夜送炊饼", "守宫砂还在？", "误会反转", "武植愣住：剧本不对，潘金莲怎么这么良善？"),
    ("葱油饼开张", "炊饼？狗都不吃！", "降维碾压", "白胜掀摊：三寸丁，给老子滚出来！"),
    ("白胜抢摊被反杀", "你再动她一下试试！", "护妻打脸", "罗真人盯住武植：此人命数，不在此世！"),
    ("罗真人试探武植", "你到底从何处来？", "身份悬念", "武植OS：这老道不会看出我是穿来的吧？"),
    ("西门庆递拜帖", "清河县的女人，还没人敢拒绝我。", "强敌登场", "金莲看见拜帖落款，脸色瞬间白了！"),
    ("武植反摆鸿门宴", "要吃饼可以，先跪下排队。", "装逼反击", "西门庆笑了：今晚，我要他铺子消失！"),
    ("夜砸饼铺", "给我砸！砸到他跪！", "极限压迫", "武植点燃灶火：谁敢进门，我让他横着出去！"),
    ("县衙当众验饼", "这饼，能卖进东京。", "中立裁决", "县令拍桌：武植，你可愿入官坊？"),
    ("金莲被逼赴宴", "她是我娘子，不是你们的酒菜。", "关系绑定", "西门庆举杯：那我偏要尝尝！"),
    ("醉仙楼护妻", "把手拿开。", "男主护场", "武植一脚踹翻桌子：今天谁也别想站着出去！"),
    ("东京商队押注", "三日内，做不出千张饼，你就滚出清河。", "商战卡点", "武植看向空粮仓：有人断了我的面粉！"),
    ("断粮危机", "没有面，我照样开张。", "绝境反击", "第一锅新饼出炉，香味把整条街都逼疯了！"),
    ("西门庆买通衙役", "武大郎，你这铺子封定了。", "权力压迫", "公文落下，武植却笑了：你们封错人了！"),
    ("官坊身份反转", "从今天起，这铺子归官府护着。", "身份升级", "西门庆终于变脸：他背后到底是谁？"),
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


def _story_profile(source_text: str) -> str:
    if any(
        keyword in source_text
        for keyword in ["武植", "武大郎", "金莲", "潘金莲", "西门庆", "大宋", "清河"]
    ):
        return "song"
    return "haomen"


def _source_hint(source_text: str) -> str:
    compact = " ".join(source_text.split())
    if not compact:
        return "豪门生日宴羞辱"
    return compact[:48]


def _beat(episode: int, profile: str = "haomen") -> tuple[str, str, str, str]:
    beats = SONG_EPISODE_BEATS if profile == "song" else EPISODE_BEATS
    return beats[(episode - 1) % len(beats)]


def _haomen_scene_lines(
    episode: int,
    title: str,
    hook: str,
    cliffhanger: str,
) -> list[Scene]:
    ep = f"EP{episode:02d}"
    return [
        Scene(
            heading=f"{episode}-1 夜-内-林家宴会厅",
            characters=["林晚", "林雪", "顾承"],
            lines=[
                SceneLine(kind="action", text=f"△{ep} 开场，林晚被推到宴会厅中央，所有镜头和宾客目光同时压过来。"),
                SceneLine(kind="dialogue", speaker="林雪", emotion="温柔带刺", text="姐姐，你再闹下去，今天所有人都会记住你的难堪。"),
                SceneLine(kind="dialogue", speaker="林晚", emotion="克制", text="我不怕被记住，我怕你们不敢把真相听完。"),
                SceneLine(kind="os", speaker="林晚", text="他们以为我今晚只会哭。可直播还开着，证据也在路上。"),
                SceneLine(kind="action", text="△林晚垂眼，拇指在手机侧键上连按两下，屏幕亮起直播中的红点。"),
                SceneLine(kind="action", text="△顾承抬手拦住她，保安的脚步声逼近，手机直播弹幕开始暴涨。"),
                SceneLine(kind="dialogue", speaker="顾承", emotion="冷", text="滚出去。"),
                SceneLine(kind="dialogue", speaker="顾承", emotion="压怒", text=hook),
                SceneLine(kind="dialogue", speaker="林雪", emotion="压低威胁", text="姐姐，你再多说一个字，我让你连跪着求饶的机会都没有。"),
                SceneLine(kind="dialogue", speaker="林晚", emotion="冷笑", text="你现在护着她，等会儿别求我回头看你。"),
                SceneLine(kind="action", text="△特写林雪的手，她把半截鉴定编号攥进掌心，指甲几乎掐出血。"),
            ],
        ),
        Scene(
            heading=f"{episode}-2 夜-内-宴会厅侧门",
            characters=["林晚", "老管家", "林雪", "顾承"],
            lines=[
                SceneLine(kind="action", text="△侧门忽然打开，老管家握着一只旧木盒冲进来，盒角还沾着雨水。"),
                SceneLine(kind="dialogue", speaker="老管家", emotion="颤抖", text="大小姐，这东西我替您守了二十年。"),
                SceneLine(kind="dialogue", speaker="林雪", emotion="慌", text="一个下人说的话，也配当证据？"),
                SceneLine(kind="dialogue", speaker="顾承", emotion="讥冷", text="林晚，找个老头演戏，你就以为能翻身？"),
                SceneLine(kind="dialogue", speaker="林晚", emotion="逼近", text="那就让你亲手打开，看清楚里面写的是谁的名字。"),
                SceneLine(kind="os", speaker="林晚", text="她越怕这个盒子，我越要让所有人看见。"),
                SceneLine(kind="action", text="△林晚没有伸手抢，反而后退半步，把木盒推到主桌灯光最亮的位置。"),
                SceneLine(kind="action", text="△木盒打开，旧照片、出生牌、半枚玉佩同时露出，宾客席一片死寂。"),
                SceneLine(kind="dialogue", speaker="顾承", emotion="动摇", text="林雪，你刚才说你从没见过这只盒子。"),
                SceneLine(kind="dialogue", speaker="林雪", emotion="强笑", text="我没见过。可谁知道她是不是提前伪造的？"),
                SceneLine(kind="action", text="△镜头扫过宾客手机，直播间弹幕从嘲笑变成一排排问号。"),
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
                SceneLine(kind="dialogue", speaker="林晚", emotion="压住怒意", text="我给过你三次机会。你每一次，都选了把我往死里踩。"),
                SceneLine(kind="action", text="△主屏突然跳出一段未公开录音，林雪的声音先响起来。"),
                SceneLine(kind="dialogue", speaker="录音里的林雪", emotion="阴冷", text=cliffhanger),
                SceneLine(kind="action", text="△全场灯光骤暗，只剩主屏白光打在林雪脸上，她第一次笑不出来。"),
            ],
        ),
    ]


def _song_scene_lines(
    episode: int,
    title: str,
    hook: str,
    cliffhanger: str,
) -> list[Scene]:
    return [
        Scene(
            heading=f"{episode}-1 夜-内-武家卧室",
            characters=["武植", "金莲"],
            lines=[
                SceneLine(kind="vo", speaker="黑幕", text=hook),
                SceneLine(kind="action", text="△黑屏中先听见药碗轻碰瓷勺，镜头慢慢亮起，只给金莲端碗的手。"),
                SceneLine(kind="action", text="△武植猛地睁眼，视线从烛火虚焦到金莲的脸，额头冷汗滚下来。"),
                SceneLine(kind="dialogue", speaker="金莲", emotion="温柔", text="大郎，趁热喝了，喝了身子就好了。"),
                SceneLine(kind="os", speaker="武植", text="不是吧？我刚还在交易所敲钟，睁眼就成武大郎？"),
                SceneLine(kind="action", text="△武植下意识张嘴，药勺已经递到唇边，黑色药汁晃出一圈冷光。"),
                SceneLine(kind="dialogue", speaker="武植", emotion="惊醒", text="等等！你刚才叫我什么？"),
                SceneLine(kind="dialogue", speaker="金莲", emotion="疑惑", text="大郎，你不认得奴家了？奴家是金莲啊。"),
                SceneLine(kind="os", speaker="武植", text="潘金莲！那这碗不就是送命汤？"),
                SceneLine(kind="action", text="△武植一巴掌打飞药碗，药汁泼在地上冒着热气，瓷片炸开。"),
                SceneLine(kind="dialogue", speaker="武植", emotion="炸毛", text="拿走！我不喝！你想毒死我啊！"),
            ],
        ),
        Scene(
            heading=f"{episode}-2 夜-内-武家楼梯口",
            characters=["武植", "金莲", "张嫂"],
            lines=[
                SceneLine(kind="action", text="△武植贴着门缝偷看，镜头只给他攥紧剪刀的手，指节发白。"),
                SceneLine(kind="vo", speaker="张嫂", text="小娘子，东西我可备齐了，你这边如何？"),
                SceneLine(kind="dialogue", speaker="金莲", emotion="压低", text="嫂嫂放心，约莫四更天便能妥当。"),
                SceneLine(kind="os", speaker="武植", text="四更天？好啊，这是连夜送我上路！"),
                SceneLine(kind="action", text="△武植往前一步踩空，整个人差点滚下楼梯，又硬生生捂住嘴。"),
                SceneLine(kind="dialogue", speaker="张嫂", emotion="催促", text="大官人那边可等不及了，你别误了时辰。"),
                SceneLine(kind="dialogue", speaker="武植", emotion="咬牙低声", text="西门庆是吧？行，老子先送你上路。"),
                SceneLine(kind="action", text="△金莲忽然抬头看向楼梯，镜头定格在武植瞪大的眼睛。"),
            ],
        ),
        Scene(
            heading=f"{episode}-3 日-外-武家门口摊子",
            characters=["武植", "金莲", "白胜", "围观百姓"],
            lines=[
                SceneLine(kind="action", text=f"△快剪：和面、摔打、抹油、下锅，{title} 的香气顺着街口炸开。"),
                SceneLine(kind="dialogue", speaker="武植", emotion="吆喝", text="武大郎葱油饼！不好吃不要钱，好吃别插队！"),
                SceneLine(kind="dialogue", speaker="白胜", emotion="嚣张", text="三寸丁，谁准你在这条街摆摊？"),
                SceneLine(kind="dialogue", speaker="武植", emotion="笑", text="我摆摊还得问狗？你会说人话吗？"),
                SceneLine(kind="action", text="△围观人群轰地笑开，白胜脸色一沉，抬脚踹向油锅。"),
                SceneLine(kind="dialogue", speaker="金莲", emotion="惊呼", text="大郎，小心！"),
                SceneLine(kind="action", text="△武植一把拽过锅柄，热油擦着白胜鞋面溅过去，白胜惨叫跳脚。"),
                SceneLine(kind="dialogue", speaker="武植", emotion="压低", text="想砸我的摊？先问问你这双腿够不够硬。"),
                SceneLine(kind="dialogue", speaker="白胜", emotion="暴怒", text=cliffhanger),
                SceneLine(kind="action", text="△镜头切到街角，一辆华贵马车停下，帘子后有人正盯着武植。"),
            ],
        ),
    ]


def _episode_script(episode: int, profile: str = "haomen") -> EpisodeScript:
    title, hook, emotion, cliffhanger = _beat(episode, profile)
    scenes = (
        _song_scene_lines(episode, title, hook, cliffhanger)
        if profile == "song"
        else _haomen_scene_lines(episode, title, hook, cliffhanger)
    )
    watch_reason = (
        "观众要看现代认知如何碾压宋代小混混，并看武植和金莲的误会如何反转成护妻爽点。"
        if profile == "song"
        else "观众要看女主在公开压迫下连续反击，并确认真假千金身份线如何推进。"
    )
    return EpisodeScript(
        episode=episode,
        title=title,
        hook_3s=hook,
        main_emotion=emotion,
        watch_reason=watch_reason,
        scenes=scenes,
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
    profile = _story_profile(source_text)
    start, end = episode_window(
        round_number=round_number,
        previous_context=previous_context,
        target_episode_count=target_episode_count,
        episodes_per_round=episodes_per_round,
    )
    episodes = [_episode_script(episode, profile) for episode in range(start, end + 1)]
    target_range = f"EP{start:02d}-EP{end:02d}"
    source_hint = _source_hint(source_text)
    stage = STORY_STAGES[min(round_number - 1, len(STORY_STAGES) - 1)]
    last_episode = episodes[-1]

    if profile == "song":
        return [
            SourceAnalysis(
                characters=["武植", "金莲", "张嫂", "白胜", "西门庆", "罗真人"],
                events=[source_hint, f"{target_range} 围绕穿越认知差、误会反转、护妻打脸推进"],
                conflicts=["现代认知对古代身份压迫", "武植误会金莲", "西门庆/地痞压迫", "小人物逆袭打脸"],
                visual_moments=["药碗被打飞", "剪刀攥紧", "守宫砂反转", "葱油饼开张", "白胜掀摊"],
                low_value_passages=["长篇背景设定", "重复心理独白"],
                candidate_hooks=[episodes[0].hook_3s],
            ),
            EpisodeContext(
                target_episode_range=target_range,
                story_stage=stage,
                source_to_episode_mapping=[
                    f"{source_hint} -> {target_range}",
                    f"上一轮承接 -> 从 EP{start:02d} 继续清河压迫线"
                    if previous_context
                    else "穿越醒来喝药 -> EP01 起势",
                ],
                must_carry_context=(previous_context.open_hooks if previous_context else []),
                forbidden_reveals=["不得过早让西门庆彻底退场", "不得把金莲写成主动害夫的单薄恶人"],
                adaptation_actions=[
                    "每集前 3 秒直接给危机或强台词",
                    "保留武植 OS 的现代认知吐槽，但 OS 后必须马上落到动作",
                    "用可拍摄动作替代长篇说明，结尾留强威胁或反转",
                ],
                confidence=0.93,
            ),
            StoryBible(
                genre="男频穿越轻喜打脸",
                mainline="现代人穿成武植后，误以为自己必死于金莲和西门庆之手，靠现代认知做饼经商、护妻破局，在清河县一路打脸升级。",
                characters=["武植", "金莲", "张嫂", "白胜", "西门庆", "罗真人"],
                relationships=["武植先误会金莲，后逐步转向护妻", "西门庆觊觎金莲并压迫武家", "白胜代表街面地痞压力"],
                speech_styles={
                    "武植": "现代吐槽 OS 加短促反击，嘴硬、行动快",
                    "金莲": "温软克制，委屈中有韧性",
                    "西门庆": "轻佻威胁，权势压人",
                    "白胜": "街头粗横，几句就动手",
                },
                immutable_facts=["武植是穿越视角", "金莲不应被写成无动机恶毒工具人", "清河县压迫线逐轮升级"],
                forbidden_changes=["不得套用真假千金模板", "不得用长篇旁白替代动作戏", "不得让现代能力无代价解决全部问题"],
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
                open_hooks=[last_episode.cliffhanger, "西门庆与清河县权力线仍在加压"],
                forbidden_reveals=["罗真人真实目的", "西门庆背后完整势力"],
                character_knowledge={
                    "武植": [f"已推进到 EP{end:02d}", "知道清河压迫不是一两场冲突能结束"],
                    "金莲": ["开始看见武植反常但可靠的一面", "仍未完全理解武植的现代思维"],
                    "西门庆": ["察觉武植难缠", "准备从街面压迫转为权势压迫"],
                },
                relationship_changes=[f"武植与金莲在 {target_range} 从误会走向共同对外"],
                prop_states=["药碗已打翻", "剪刀暴露武植的求生本能", "饼摊成为后续商战与打脸主战场"],
                foreshadowing_ledger=[f"下一轮从 EP{end + 1:02d} 承接西门庆/罗真人双线施压"],
            ),
        ]

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
