from __future__ import annotations

from pydantic import BaseModel

from novel_drama_engine.models import (
    EpisodeContext,
    EpisodeDramaPlan,
    EpisodePlan,
    EpisodeScript,
    GenerationVariant,
    NextRoundContext,
    QualityReport,
    QualityScores,
    QualityStatus,
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
                SceneLine(kind="action", text=f"△{ep} 全景横移过生日宴长桌，水晶灯冷光压下；镜头跟拍保安把林晚推到画面中央，宾客手机在前景同时抬起。"),
                SceneLine(kind="dialogue", speaker="林雪", emotion="温柔带刺", text="姐姐，别闹了。"),
                SceneLine(kind="dialogue", speaker="林晚", emotion="克制", text="我不怕被记住，我怕你们不敢把真相听完。"),
                SceneLine(kind="os", speaker="林晚", text="他们以为我今晚只会哭。可直播还开着，证据也在路上。"),
                SceneLine(kind="action", text="△近景推近林晚垂下的右手，手机被裙摆半遮；拇指连按侧键，红色直播点在黑屏反光里亮起。"),
                SceneLine(kind="action", text="△中景跟拍顾承抬手挡在她面前，保安从画面两侧压入；切到手机屏幕，弹幕一行行冲上来。"),
                SceneLine(kind="dialogue", speaker="顾承", emotion="冷", text="滚出去。"),
                SceneLine(kind="dialogue", speaker="顾承", emotion="压怒", text=hook),
                SceneLine(kind="dialogue", speaker="林雪", emotion="压低威胁", text="再说一个字，你就完了。"),
                SceneLine(kind="dialogue", speaker="林晚", emotion="冷笑", text="你现在护着她，等会儿别求我回头看你。"),
                SceneLine(kind="action", text="△特写推近林雪攥紧的手，半截鉴定编号露在指缝；指甲掐进掌心，血色和红酒杯形成视觉串线。"),
            ],
        ),
        Scene(
            heading=f"{episode}-2 夜-内-宴会厅侧门",
            characters=["林晚", "老管家", "林雪", "顾承"],
            lines=[
                SceneLine(kind="action", text="△全景摇向宴会厅侧门，门缝先漏进雨声；老管家抱着旧木盒冲入，湿鞋在地毯上拖出水痕。"),
                SceneLine(kind="dialogue", speaker="老管家", emotion="颤抖", text="大小姐，这东西我替您守了二十年。"),
                SceneLine(kind="dialogue", speaker="林雪", emotion="慌", text="一个下人说的话，也配当证据？"),
                SceneLine(kind="dialogue", speaker="顾承", emotion="讥冷", text="找人演戏？"),
                SceneLine(kind="dialogue", speaker="林晚", emotion="逼近", text="你亲手打开。"),
                SceneLine(kind="os", speaker="林晚", text="她越怕这个盒子，我越要让所有人看见。"),
                SceneLine(kind="action", text="△中近景跟拍林晚后退半步，避开林雪伸来的手；木盒被推到主桌灯下，盒面裂纹被顶光照清。"),
                SceneLine(kind="action", text="△俯拍特写缓慢推近木盒开启，旧照片、出生牌、半枚玉佩依次入画；声音压低，只剩盒扣弹开的脆响。"),
                SceneLine(kind="dialogue", speaker="顾承", emotion="动摇", text="林雪，你刚才说你从没见过这只盒子。"),
                SceneLine(kind="dialogue", speaker="林雪", emotion="强笑", text="她伪造的。"),
                SceneLine(kind="action", text="△中景横移扫过宾客手机屏幕，嘲笑弹幕被问号刷掉；切回林雪脸部中近景，她的笑僵住。"),
            ],
        ),
        Scene(
            heading=f"{episode}-3 夜-内-宴会厅主屏前",
            characters=["林晚", "林雪", "顾承", "林父"],
            lines=[
                SceneLine(kind="action", text=f"△中景推近林晚把手机贴上投屏器，主屏雪花闪烁后定格证据页；{title} 被白光打到所有人脸上。"),
                SceneLine(kind="dialogue", speaker="林父", emotion="压低", text="关掉屏幕，今天的事到此为止。"),
                SceneLine(kind="dialogue", speaker="林晚", emotion="锋利", text="二十年都能被你们按下去，今天按不住了。"),
                SceneLine(kind="dialogue", speaker="林雪", emotion="失控", text="她是假的！她就是想毁了林家！"),
                SceneLine(kind="dialogue", speaker="林晚", emotion="压住怒意", text="三次机会，你都选错了。"),
                SceneLine(kind="action", text="△仰拍推近主屏，未公开录音波形跳出；J-cut 先听见林雪的声音，再切到她骤白的脸。"),
                SceneLine(kind="dialogue", speaker="录音里的林雪", emotion="阴冷", text=cliffhanger),
                SceneLine(kind="action", text="△全景拉远，宴会灯一盏盏熄灭，只剩主屏白光锁住林雪；前景酒杯晃动，画面停在她僵住的嘴角。"),
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
                SceneLine(kind="action", text="△特写推近金莲端碗的手，黑屏声音先入，药碗轻碰瓷勺；烛光在黑药汁上晃出冷亮反光。"),
                SceneLine(kind="action", text="△中近景拉焦到武植猛地睁眼，前景烛火虚化，后景金莲的脸一点点清晰，冷汗沿额角滑下。"),
                SceneLine(kind="dialogue", speaker="金莲", emotion="温柔", text="大郎，趁热喝了，喝了身子就好了。"),
                SceneLine(kind="os", speaker="武植", text="不是吧？我刚还在交易所敲钟，睁眼就成武大郎？"),
                SceneLine(kind="action", text="△近景推近武植张开的嘴，药勺从画面右侧逼近唇边；黑药汁晃动，反光切到他骤缩的瞳孔。"),
                SceneLine(kind="dialogue", speaker="武植", emotion="惊醒", text="等等！你刚才叫我什么？"),
                SceneLine(kind="dialogue", speaker="金莲", emotion="疑惑", text="大郎，你不认得奴家了？奴家是金莲啊。"),
                SceneLine(kind="os", speaker="武植", text="潘金莲！那这碗不就是送命汤？"),
                SceneLine(kind="action", text="△中景手持甩向武植挥出的手，药碗飞出画面；切到俯拍特写，药汁泼地冒热气，瓷片四散。"),
                SceneLine(kind="dialogue", speaker="武植", emotion="炸毛", text="拿走！我不喝！你想毒死我啊！"),
            ],
        ),
        Scene(
            heading=f"{episode}-2 夜-内-武家楼梯口",
            characters=["武植", "金莲", "张嫂"],
            lines=[
                SceneLine(kind="action", text="△近景推近门缝，武植半张脸被木门遮住；画面下方露出他攥紧剪刀的手，指节发白。"),
                SceneLine(kind="vo", speaker="张嫂", text="小娘子，东西我可备齐了，你这边如何？"),
                SceneLine(kind="dialogue", speaker="金莲", emotion="压低", text="嫂嫂放心，约莫四更天便能妥当。"),
                SceneLine(kind="os", speaker="武植", text="四更天？好啊，这是连夜送我上路！"),
                SceneLine(kind="action", text="△中景手持跟拍武植身体前倾踩空，楼梯扶手在画面里斜切；他猛地捂嘴，剪刀贴着袖口闪光。"),
                SceneLine(kind="dialogue", speaker="张嫂", emotion="催促", text="大官人那边可等不及了，你别误了时辰。"),
                SceneLine(kind="dialogue", speaker="武植", emotion="咬牙低声", text="西门庆是吧？行，老子先送你上路。"),
                SceneLine(kind="action", text="△中近景切到金莲抬头的脸，视线匹配楼梯方向；再切回武植眼部特写定格，呼吸声压住环境声。"),
            ],
        ),
        Scene(
            heading=f"{episode}-3 日-外-武家门口摊子",
            characters=["武植", "金莲", "白胜", "围观百姓"],
            lines=[
                SceneLine(kind="action", text=f"△俯拍快剪面团被摔上案板，近景横移过刷油的手，低角度推近铁锅冒烟；{title} 的香气把街口人群引入画面。"),
                SceneLine(kind="dialogue", speaker="武植", emotion="吆喝", text="武大郎葱油饼！不好吃不要钱，好吃别插队！"),
                SceneLine(kind="dialogue", speaker="白胜", emotion="嚣张", text="三寸丁，谁准你在这条街摆摊？"),
                SceneLine(kind="dialogue", speaker="武植", emotion="笑", text="我摆摊还得问狗？你会说人话吗？"),
                SceneLine(kind="action", text="△中景横移过笑开的围观百姓，声音先热后断；镜头甩向白胜沉下的脸，再跟拍他抬脚踹向油锅。"),
                SceneLine(kind="dialogue", speaker="金莲", emotion="惊呼", text="大郎，小心！"),
                SceneLine(kind="action", text="△中景跟拍武植反手拽锅柄，锅沿从前景划过；切到鞋面特写，热油擦边溅开，白胜惨叫后退。"),
                SceneLine(kind="dialogue", speaker="武植", emotion="压低", text="想砸我的摊？先问问你这双腿够不够硬。"),
                SceneLine(kind="dialogue", speaker="白胜", emotion="暴怒", text=cliffhanger),
                SceneLine(kind="action", text="△长焦全景缓慢推向街角马车，帘子被风掀开一线；切到帘后眼神特写，视线落回武植背影。"),
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


def _episode_drama_plan(episode: int, profile: str = "haomen") -> EpisodeDramaPlan:
    title, hook, emotion, cliffhanger = _beat(episode, profile)
    if profile == "song":
        return EpisodeDramaPlan(
            episode=episode,
            title=title,
            drama_engine="武植用现代认知误判金莲和清河县规则，在误会中快速行动，靠降维认知反打街面压迫。",
            protagonist_misbelief="武植以为自己会按原著死于金莲和西门庆。",
            truth_gap="金莲并非单薄害夫工具人，清河县压迫线才是本轮真正外部敌人。",
            physical_action_chain=["打飞药碗", "攥紧剪刀偷听", "摆摊试探街面规则"],
            scene_dynamics=["卧室内药碗逼近形成近身危机", "楼梯口偷听误会升级", "门口摊子把冲突外化到围观人群"],
            emotional_turns=["惊恐求生", "误会发狠", "护妻/经商反击"],
            audience_information_gap="观众知道武植按水浒知识误判金莲，等待误会反转和现代认知打脸。",
            three_pull_beats=["药碗危机压迫", "张嫂低语让武植误以为毒局坐实", "白胜/西门庆线把个人误会拉成街面压迫"],
            false_payoff="武植以为打飞药碗就躲过死局，但偷听到大官人线索后危机重置。",
            planted_key="剪刀、药碗、守宫砂/饼摊作为后续误会反转和护妻打脸钥匙。",
            strongest_line="想让我死？那就一起死！",
            cliffhanger_design=cliffhanger,
            source_assets_to_keep=[hook, "武植现代 OS", "金莲温柔委屈", "西门庆压迫线"],
            forbidden_shortcuts=["不得把金莲写成主动害夫恶人", "不得用长篇旁白解释世界观", "不得套真假千金模板"],
        )
    return EpisodeDramaPlan(
        episode=episode,
        title=title,
        drama_engine="林晚在公开羞辱中利用直播/旧物/证据制造信息差，让假千金和误判男主一步步失控。",
        protagonist_misbelief="压迫者以为林晚孤立无援，只能被赶出宴会。",
        truth_gap="林晚已经握住证据，且老管家/旧物会把身份线推到台面。",
        physical_action_chain=["打开直播", "逼老管家交出旧木盒", "投屏证据截断宴会"],
        scene_dynamics=["宴会中心被保安推搡形成公开羞辱", "侧门闯入打破权力秩序", "主屏前证据投放完成反压"],
        emotional_turns=["羞辱压迫", "克制反击", "身份悬念升级"],
        audience_information_gap="观众知道林晚在开直播和等证据，反派不知道自己正在公开自爆。",
        three_pull_beats=["林雪先用假温柔压林晚", "顾承护错人让期待落空", "旧盒/录音上屏形成反击但不一次揭完"],
        false_payoff="老管家出现像是打脸成功，但林雪质疑证据，期待被重置到投屏爆点。",
        planted_key="旧木盒、半枚玉佩、录音备份。",
        strongest_line="你现在护着她，等会儿别求我回头看你。",
        cliffhanger_design=cliffhanger,
        source_assets_to_keep=[hook, "宴会公开羞辱", "老管家跪叫大小姐", "真假千金身份线"],
        forbidden_shortcuts=["不得提前公开全部亲子鉴定", "不得新增亲哥哥救场", "不得让林雪无代价退场"],
    )


def demo_episode_plan(
    *,
    episodes: list[EpisodeScript],
    target_range: str,
    profile: str,
    variant: GenerationVariant = GenerationVariant.DRAMA_ENGINE_FIRST,
) -> EpisodePlan:
    return EpisodePlan(
        variant=variant,
        target_episode_range=target_range,
        adaptation_strategy="先锁戏剧引擎、信息差、三波拉扯、假打脸和钥匙预埋，再写可拍摄脚本。",
        episodes=[
            _episode_drama_plan(episode.episode, profile)
            for episode in episodes
        ],
    )


def demo_viral_asset_report(profile: str, source_hint: str) -> ViralAssetReport:
    if profile == "song":
        return ViralAssetReport(
            channel="男频",
            genre_tags=["穿越", "轻喜", "经商打脸", "护妻"],
            core_setting="现代人穿成武植，带着现代商业和剧情认知进入清河县压迫场。",
            core_dilemma="他以为自己会死于金莲和西门庆，却发现真正危险来自街面权力和误会连锁。",
            protagonist_goal="先活下来，再靠做饼经商护住金莲，把西门庆和地痞势力逐层打下去。",
            main_conflict="现代认知与宋代身份/权力压迫的连续碰撞。",
            signature_scenes=["醒来喝药反杀", "葱油饼开张被砸摊", "县衙当众验饼"],
            small_highlights=["药碗落地", "剪刀偷听", "守宫砂误会反转", "热油逼退地痞", "罗真人试探"],
            golden_lines=["想让我死？那就一起死！", "她是我娘子，不是你们的酒菜。"],
            emotion_curve=["惊险求生", "误会拉扯", "轻喜反击", "护妻升级", "权力压迫"],
            adaptation_risks=["套用真假千金模板", "把金莲写成单薄恶女", "用旁白解释大宋设定"],
            risk_treatments=["保留现代 OS 但马上落动作", "金莲保留温软和委屈", "用做饼/砸摊/验饼外化世界规则"],
            low_value_removal_rules=["删除历史科普", "删除赶路寒暄", "删掉没有动作承接的抒情 OS"],
        )
    return ViralAssetReport(
        channel="女频",
        genre_tags=["豪门", "真假千金", "复仇", "身份揭晓"],
        core_setting="真千金在豪门公开场合被假千金压迫，手里藏着能反打的旧物和证据。",
        core_dilemma="她越想拿回身份，假千金和误判男主越在公开场合把她推向绝境。",
        protagonist_goal="用直播、旧物、鉴定和证人逐集拆穿假千金，夺回身份与继承权。",
        main_conflict="真假身份、家族利益和错爱误判叠加成公开打脸循环。",
        signature_scenes=["生日宴被拖走", "老管家跪叫大小姐", "认亲宴公开反击"],
        small_highlights=["邀请函被撕", "旧木盒打开", "玉佩露出", "录音投屏", "直播弹幕反转"],
        golden_lines=["谁敢碰她一下！", "你现在护着她，等会儿别求我回头看你。"],
        emotion_curve=["公开羞辱", "克制反击", "身份逼近", "亲情撕裂", "公开认亲"],
        adaptation_risks=["亲子鉴定过早揭完", "新增亲哥哥机械救场", "水集过渡削弱追更"],
        risk_treatments=["每轮只兑现一部分证据", "用中立证据/管家裁决合法化打脸", "每集必须新增身份或关系信息"],
        low_value_removal_rules=["删除长篇心理独白", "删除宴会背景铺垫", "删掉无冲突的寒暄和赶路"],
    )


def _character_profiles(profile: str) -> list[CharacterProfile]:
    if profile == "song":
        return [
            CharacterProfile(
                name="武植",
                base_identity="现代人穿越成武大郎",
                memory_tag="矮身现代脑",
                contrast="身体弱势，认知强势",
                core_desire="活下来并掌控清河县生意",
                obsession="不能按原著死法认命",
                drama_function="打",
                speech_style="现代吐槽 OS 加短促反击",
                sample_lines=["想让我死？", "先问问你这双腿够不够硬。"],
            ),
            CharacterProfile(
                name="金莲",
                base_identity="被流言困住的妻子",
                memory_tag="温软却不软弱",
                contrast="表面顺从，内里清醒",
                core_desire="在压迫里保住自己和武家",
                obsession="不再被人当成酒菜和筹码",
                drama_function="拉",
                speech_style="温柔短句，委屈里带韧性",
                sample_lines=["大郎，小心！"],
            ),
            CharacterProfile(
                name="西门庆",
                base_identity="清河县权势恶少",
                memory_tag="轻佻压迫",
                contrast="表面风流，实则恶霸",
                core_desire="夺走金莲并压服武植",
                obsession="清河县没人敢拒绝他",
                drama_function="装",
                speech_style="轻佻威胁，几句就压人",
                sample_lines=["清河县的女人，还没人敢拒绝我。"],
            ),
        ]
    return [
        CharacterProfile(
            name="林晚",
            base_identity="被夺身份的真千金",
            memory_tag="冷脸反击",
            contrast="表面孤立无援，实则手握证据",
            core_desire="拿回身份和尊严",
            obsession="让所有公开羞辱她的人公开付出代价",
            drama_function="打",
            speech_style="克制短句，反击锋利",
            sample_lines=["你现在护着她，等会儿别求我。"],
        ),
        CharacterProfile(
            name="林雪",
            base_identity="冒名假千金",
            memory_tag="温柔有刺",
            contrast="表面委屈善良，实则操控证据",
            core_desire="保住假身份和豪门利益",
            obsession="不能让林晚被认回",
            drama_function="压",
            speech_style="每句温柔，每句扎人",
            sample_lines=["姐姐，别让大家难堪。"],
        ),
        CharacterProfile(
            name="顾承",
            base_identity="误判女主的豪门男主",
            memory_tag="高压护错人",
            contrast="表面冷硬掌控，真相前逐步动摇",
            core_desire="维持自己认定的秩序",
            obsession="不承认自己爱错护错",
            drama_function="拉",
            speech_style="命令式短句，少解释",
            sample_lines=["滚出去。", "还要我再说一遍？"],
        ),
    ]


def demo_series_structure_plan(
    *,
    profile: str,
    target_range: str,
    target_episode_count: int | None,
    start: int,
    end: int,
) -> SeriesStructurePlan:
    total = target_episode_count or end
    outline_end = min(total, 40)
    outlines = [
        SeriesEpisodeOutline(
            episode=episode,
            core_event=_beat(episode, profile)[0],
            emotion_node=_beat(episode, profile)[2],
            information_increment=(
                "新增现代认知/清河县压迫规则"
                if profile == "song"
                else "新增身份线证据或关系误判"
            ),
            ending_hook_type="冲突爆发前" if episode % 3 else "真相反转前",
            ending_hook=_beat(episode, profile)[3],
            source_anchor=f"{target_range} 原文高光/上下文锚点",
            climax_role=(
                "小高潮"
                if episode % 3 == 0
                else ("大高潮" if episode % 8 == 0 else "推进")
            ),
        )
        for episode in range(1, outline_end + 1)
    ]
    conflict_stack = (
        ConflictStack(
            surface_event_conflict="武植摆摊经商对抗地痞和西门庆。",
            emotional_conflict="武植误会金莲却又不断被她的善意拉回。",
            deep_value_conflict="现代小人物不认命，对抗宋代身份压迫。",
        )
        if profile == "song"
        else ConflictStack(
            surface_event_conflict="林晚与林雪围绕真假千金证据公开对抗。",
            emotional_conflict="顾承护错人、林家亲情误判持续刺痛林晚。",
            deep_value_conflict="血缘真相、阶层利益和公开尊严的冲突。",
        )
    )
    return SeriesStructurePlan(
        target_episode_count=target_episode_count,
        target_episode_range=target_range,
        structure_rationale="按 SOP 先锁爆款资产，再用每 3 集小高潮、每 8 集大高潮规划连续追更。",
        opening_contract=["抛出强设定", "制造公开困境", "主角立刻行动反击"],
        small_climax_cadence="平均每 3 集兑现一次小爽点或小反转。",
        big_climax_cadence="平均每 8 集兑现一次身份/权力/关系大反转。",
        character_profiles=_character_profiles(profile),
        conflict_stack=conflict_stack,
        global_emotion_curve=(
            ["惊险", "误会", "轻喜", "压迫", "护妻反击"]
            if profile == "song"
            else ["羞辱", "反击", "身份悬念", "亲情撕裂", "公开认亲"]
        ),
        episode_outlines=outlines,
        adaptation_rules=["前 3 秒必须有强画面或强台词", "每集必须有信息增量", "结尾卡在最想看的前一秒"],
        forbidden_slowdowns=["连续三集无新信息", "长篇内心独白", "泛化场景头", "无冲突过渡"],
    )


def demo_round_outputs(
    *,
    source_text: str = "",
    round_number: int = 1,
    previous_context: NextRoundContext | None = None,
    target_episode_count: int | None = None,
    episodes_per_round: int = EPISODES_PER_ROUND,
    include_episode_plan: bool = False,
    include_sop_stack: bool = False,
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
    viral_asset_report = demo_viral_asset_report(profile, source_hint)
    series_structure_plan = demo_series_structure_plan(
        profile=profile,
        target_range=target_range,
        target_episode_count=target_episode_count,
        start=start,
        end=end,
    )
    episode_plan = demo_episode_plan(
        episodes=episodes,
        target_range=target_range,
        profile=profile,
        variant=(
            GenerationVariant.SOP_FULL_STACK
            if include_sop_stack
            else GenerationVariant.DRAMA_ENGINE_FIRST
        ),
    )

    if profile == "song":
        outputs: list[BaseModel] = [
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
        ]
        if include_sop_stack:
            outputs.insert(1, viral_asset_report)
            outputs.append(series_structure_plan)
        if include_episode_plan or include_sop_stack:
            outputs.append(episode_plan)
        outputs.extend(
            [
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
        )
        return outputs

    outputs = [
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
    ]
    if include_sop_stack:
        outputs.insert(1, viral_asset_report)
        outputs.append(series_structure_plan)
    if include_episode_plan or include_sop_stack:
        outputs.append(episode_plan)
    outputs.extend(
        [
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
    )
    return outputs
