from __future__ import annotations

import re
from collections import Counter
from collections.abc import Iterable
from typing import Any, Literal

from novel_drama_engine.models import (
    AdaptationQualityReport,
    AdaptationIntensity,
    ContinuityAuditReport,
    ContinuityLinkReport,
    EpisodeContext,
    EpisodePlan,
    EpisodeScript,
    MethodologyContext,
    MethodologyQualityIssue,
    MethodologyQualityReport,
    NextRoundContext,
    QualityStatus,
    ScriptBatch,
    SeriesStructurePlan,
    SourceAnalysis,
    SourceStrengthLevel,
    SourceStrengthProfile,
    SourceFidelityCheck,
    SourceFidelityReport,
    StoryBible,
    StoryStage,
    StoryStateEntry,
    StoryStateLedger,
    ViralAssetReport,
)
from novel_drama_engine.renderer import render_episode


PUNCTUATION_RE = re.compile(r"[\s，。！？、；：：“”‘’（）()《》【】\[\]·,.!?;:'\"<>-]+")
CHINESE_TOKEN_RE = re.compile(r"[\u4e00-\u9fffA-Za-z0-9]{2,}")
FORBIDDEN_PREFIX_RE = re.compile(
    r"^(?:不得|禁止|不能|不要|严禁|避免|拒绝|不许|不可|不应|不准|别)"
)
WEAK_FORBIDDEN_WORDS = {
    "新增",
    "提前",
    "一次性",
    "全部",
    "完全",
    "无代价",
    "机械",
    "模板",
    "救场",
    "退场",
    "真相",
    "公开",
    "本轮",
    "过早",
    "完整",
    "结果",
    "泄露",
    "揭露",
}
GENERIC_CHARACTER_NAMES = {
    "黑幕",
    "画外",
    "旁白",
    "VO",
    "OS",
    "众人",
    "宾客",
    "围观百姓",
    "录音",
}

INTENT_DRIFT_RULES: tuple[tuple[str, str, str], ...] = (
    (
        r"(?:给你准备了?惊喜|准备了?惊喜|他说[^。！？]{0,16}惊喜)",
        r"(?:你答应过|不是说好|说好的)[^。！？\n]{0,24}(?:影后|女一|新戏|资源|奖)",
        "对手主动承诺/诱导被改成主角主动索取，容易让人物显得功利或 OOC",
    ),
    (
        r"(?:早就|提前|已经|放在|压在|抽屉|办公室)[^。！？\n]{0,40}(?:解约协议|离婚协议|辞职信|退婚书)",
        r"(?:现场|当场|现在|马上|临时|一怒之下)[^。！？\n]{0,24}(?:解约|离婚|辞职|退婚|签字)",
        "深思熟虑的预谋决定被改成现场冲动决定，改变了人物逻辑和关键决定时机",
    ),
    (
        r"(?:沉默|僵住|克制|冷静|冰冷|决绝|平静)[^。！？\n]{0,40}(?:离开|签下|看着|转身|收起)",
        r"(?:我要你们|你们都给我|我跟你们拼了|你们等着|我会让你们后悔|我绝不会放过)",
        "克制决绝型情绪被改成歇斯底里狠话，偏离原文人物气质",
    ),
)

OPENING_TENSION_SOURCE_RE = re.compile(
    r"(?:抱坐|坐在[^。！？\n]{0,12}腿|腿上|手[^。！？\n]{0,16}(?:衣服|腰|领口|裙|衬衫)|"
    r"衣服里|镜头[^。！？\n]{0,16}(?:拍到|扫到|对准)|摄像机|直播)",
)
OPENING_TENSION_SCRIPT_RE = re.compile(
    r"(?:腿|衣服|领口|腰|手(?!机)|手指|手掌|指尖|镜头|摄像|直播|遮|贴近|压住|躲开|拍到|扫过)",
)
SOURCE_VULNERABILITY_RE = re.compile(
    r"(?:僵住|怔住|愣住|震惊|心碎|发抖|手抖|呼吸一滞|沉默|压住|忍住|克制|冷静|"
    r"平静|冰冷|羞辱|狼狈|被迫|被逼|害怕|不敢|无助|清醒|意识到|决定离开|"
    r"早已准备|深思熟虑)"
)
SOURCE_PREEXISTING_POWER_RE = re.compile(
    r"(?:重生|穿越|系统|预知|读档|回档|觉醒|早就知道|提前知道|提前布|早已布|"
    r"早已准备|提前准备|准备好|布好局|掌控全局|扮猪吃虎|隐藏身份|马甲|"
    r"黑卡|银行卡|银行经理|赘婿|龙王|战神归来|大佬回归|带着记忆|"
    r"上辈子|前世)"
)
SCRIPT_OMNISCIENT_COUNTERATTACK_RE = re.compile(
    r"(?:我早就知道|我全都知道|一切都在我掌控|全在我掌控|我已经安排好|"
    r"所有证据都在我手里|证据都在我手里|今天就是你们的死期|你们完了|"
    r"我等这一天很久了|我早就布好局|我已经布好局|我会让你们全部付出代价)"
)
SUPPORT_TAKEOVER_RE = re.compile(
    r"(?:我替你(?:决定|处理|签|解决|报仇|出面|解约|离婚)|替你(?:决定|处理|签|解决|报仇)|"
    r"不用你管|你不用出面|你只要站在我身后|剩下交给我|交给我就行|"
    r"我已经替你(?:签|退|解约|离婚|处理)|从现在起你听我的|这事我说了算|我替你选择)"
)
SUPPORT_CHOICE_RE = re.compile(
    r"(?:你自己决定|你来选|选择权在你|如果你愿意|我只是给你(?:退路|后盾|证据)|"
    r"我给你(?:退路|撑腰|证据|后盾)|你想怎么做|我陪你|你说了算)"
)
OPPONENT_CONTEXT_RE = re.compile(
    r"(?:反派|对手|敌人|压迫|羞辱|陷害|威胁|封杀|抢|夺|骗|背叛|争夺|打压|"
    r"诬陷|假千金|渣男|恶婆婆|仇|死敌|追杀|谋害|设计|冲突)"
)
OPPONENT_ACTIVE_RE = re.compile(
    r"(?:设局|布局|买通|威胁|栽赃|反咬|抢走|扣下|封锁|曝光|造谣|挑拨|"
    r"藏起|毁掉|撕掉|偷走|换掉|下药|绑架|追杀|举报|拉黑|逼迫|拦住|推搡|"
    r"砸向|摔碎|骗|挑衅|命令|安排人|派人|报警|撤资|封杀|夺权|诬陷|陷害|"
    r"反扑|反制|删掉|删除|截断|伪造|串供)"
)
OPPONENT_PASSIVE_RE = re.compile(
    r"(?:反派|对手|敌人|压迫者)[^。！？\n]{0,24}"
    r"(?:慌|惊慌|脸色发白|脸白|发抖|后退|躲在|只会哭|求救|不敢说话|惊恐|愣住)"
)
INTIMACY_RE = re.compile(r"(?:吻|亲吻|拥吻|激吻|吻住|吻上|亲上|抱住|拥抱|贴近)")
PUBLIC_EXPOSURE_RE = re.compile(
    r"(?:直播|曝光|热搜|偷拍|照片|镜头|全网|传出|拍到|上传|流出|公开视频|公开画面)"
)
HIGH_IMPACT_STAGE_RE = re.compile(
    r"(?:雨|雪|烟火|烟花|焰火|婚礼|订婚|生日宴|宴会|颁奖|领奖|发布会|庆典|"
    r"舞台|直播|热搜|镜头|法庭|刑场|城门|大殿|灵堂|产房|手术室|战场|擂台)"
)
IRREVERSIBLE_EXIT_RE = re.compile(
    r"(?=.*(?:解约|离婚|退婚|辞职|断亲|断绝关系|退圈|退赛|离开|分手|休书|和离))"
    r"(?=.*(?:协议|合同|签字|签下|递出|放在|抽屉|办公室|宣布|决定|摊牌|收好))",
    flags=re.S,
)
IDENTITY_REVEAL_RESULT_RE = re.compile(
    r"(?:身份|真相|亲子鉴定|血缘|真千金|假千金|继承人|少主|皇子|公主|"
    r"大佬|战神|神医|首富|凶手|幕后人|卧底|亲生)"
    r"[\s\S]{0,32}(?:公开|公布|揭穿|揭晓|承认|全场知道|被证实|坐实|验明|证明|确认)"
    r"|(?:公开|公布|揭穿|揭晓|承认|全场知道|被证实|坐实|验明|证明|确认)"
    r"[\s\S]{0,32}(?:身份|真相|亲子鉴定|血缘|真千金|假千金|继承人|少主|皇子|公主|"
    r"大佬|战神|神医|首富|凶手|幕后人|卧底|亲生)",
    flags=re.S,
)
INSTITUTIONAL_RECKONING_RE = re.compile(
    r"(?:法务|律师函|公证|警方|警察|法院|法庭|调查组|平台|董事会|家族|宗门|朝廷|"
    r"公司|资本|发布会|热搜|全网|舆论|官方|监管|仲裁|评委|裁判|鉴定机构)"
    r"[\s\S]{0,80}(?:倒台|封杀|解约潮|全面反转|反转|停摆|下架|停职|处罚|认罪|道歉|退圈|"
    r"破产|除名|废黜|判决|宣判|认证|证实|认输|败诉|被抓)"
    r"|(?:倒台|封杀|解约潮|全面反转|反转|停摆|下架|停职|处罚|认罪|道歉|退圈|"
    r"破产|除名|废黜|判决|宣判|认证|证实|认输|败诉|被抓)"
    r"[\s\S]{0,80}(?:法务|律师函|公证|警方|警察|法院|法庭|调查组|平台|董事会|家族|宗门|朝廷|"
    r"公司|资本|发布会|热搜|全网|舆论|官方|监管|仲裁|评委|裁判|鉴定机构)",
    flags=re.S,
)
EVIDENCE_SOURCE_RE = re.compile(
    r"(?:录音|视频|原始视频|监控|照片|合同|协议|账本|转账|流水|聊天记录|邮件|"
    r"诊断书|鉴定书|亲子鉴定|检测报告|数据包|后台记录|证词|证人|物证|印章|玉佩|"
    r"令牌|密信|圣旨|账册|原件|备份|账号|授权书|律师函|法务函|公证|报案回执|"
    r"证据来源|证据链)",
)

EVENT_LABELS = {
    "high_ritual_intimacy": "仪式化/高场面亲密节点",
    "public_intimacy_exposure": "亲密关系公开/曝光节点",
    "irreversible_exit_decision": "不可逆关系/合同决定",
    "identity_reveal_result": "身份/真相结论公开",
    "institutional_reckoning": "机构/法务/舆论清算结果",
}
EVIDENCE_REQUIRED_EVENTS = {
    "identity_reveal_result",
    "institutional_reckoning",
}


def normalize_text(value: str) -> str:
    return PUNCTUATION_RE.sub("", value).lower()


def _tokens(value: str) -> list[str]:
    raw = [token for token in CHINESE_TOKEN_RE.findall(value) if len(token) >= 2]
    expanded: list[str] = []
    for token in raw:
        if token in WEAK_FORBIDDEN_WORDS or token.isdigit():
            continue
        expanded.append(token)
        if re.fullmatch(r"[\u4e00-\u9fff]{4,}", token):
            expanded.extend(
                chunk
                for chunk in (token[index : index + 2] for index in range(0, len(token) - 1))
                if chunk not in WEAK_FORBIDDEN_WORDS
            )
    return list(dict.fromkeys(expanded))


def _loose_contains(haystack: str, needle: str) -> bool:
    normalized_needle = normalize_text(needle)
    if not normalized_needle:
        return True
    normalized_haystack = normalize_text(haystack)
    if normalized_needle in normalized_haystack:
        return True

    tokens = _tokens(needle)
    if not tokens:
        return True
    if len(tokens) == 1:
        return tokens[0].lower() in normalized_haystack
    matched = sum(1 for token in tokens if normalize_text(token) in normalized_haystack)
    return matched >= min(2, len(tokens))


def _evidence_for(haystack: str, needle: str, *, limit: int = 2) -> list[str]:
    evidence: list[str] = []
    lines = [line.strip() for line in haystack.splitlines() if line.strip()]
    tokens = _tokens(needle)
    for line in lines:
        if _loose_contains(line, needle) or any(_loose_contains(line, token) for token in tokens):
            evidence.append(line[:100])
            if len(evidence) >= limit:
                break
    return evidence


def _episode_texts(script_batch: ScriptBatch) -> dict[int, str]:
    return {
        episode.episode: render_episode(episode)
        for episode in script_batch.episodes
    }


def _all_script_text(script_batch: ScriptBatch) -> str:
    return "\n\n".join(_episode_texts(script_batch).values())


def _opening_text(episode: EpisodeScript, line_count: int = 8) -> str:
    lines: list[str] = [episode.title, episode.hook_3s]
    for scene in episode.scenes[:1]:
        lines.append(scene.heading)
        for line in scene.lines[:line_count]:
            if line.speaker:
                lines.append(f"{line.speaker} {line.text}")
            else:
                lines.append(line.text)
    return "\n".join(lines)


def _target_episode_number(value: str | int | None) -> int | None:
    if isinstance(value, int):
        return value
    if not isinstance(value, str):
        return None
    match = re.search(r"(?:EP|第)?\s*0*(\d{1,3})", value, flags=re.IGNORECASE)
    if not match:
        return None
    return int(match.group(1))


def _mapping_assets(mapping: object) -> list[tuple[int | None, str]]:
    if isinstance(mapping, str):
        return [(None, mapping)]
    if not hasattr(mapping, "model_dump"):
        return []
    data = mapping.model_dump()
    episode_number = _target_episode_number(data.get("target_episode"))
    assets: list[str] = []
    for key in ["source", "information_increment", "adaptation_action"]:
        value = data.get(key)
        if isinstance(value, str) and value.strip():
            assets.append(value.strip())
    retained_assets = data.get("retained_assets")
    if isinstance(retained_assets, str):
        assets.extend(asset.strip() for asset in re.split(r"[、,，;；]", retained_assets) if asset.strip())
    elif isinstance(retained_assets, list):
        assets.extend(str(asset).strip() for asset in retained_assets if str(asset).strip())
    return [(episode_number, asset) for asset in assets if asset]


def _forbidden_term(rule: str) -> str:
    term = FORBIDDEN_PREFIX_RE.sub("", rule.strip())
    term = re.sub(r"[，,。；;].*$", "", term).strip()
    for word in sorted(WEAK_FORBIDDEN_WORDS | {"在", "把", "写成", "改成"}, key=len, reverse=True):
        term = term.replace(word, "")
    tokens = [token for token in _tokens(term) if token not in WEAK_FORBIDDEN_WORDS]
    if len(tokens) >= 2:
        return "".join(tokens[:2])
    if tokens:
        return tokens[0]
    return term


def _character_name(value: str) -> str:
    name = re.sub(r"^(?:录音里的|电话里的|年轻|老|小)", "", value.strip())
    name = re.sub(r"(?:OS|VO)$", "", name, flags=re.IGNORECASE)
    return name.strip()


def _script_characters(script_batch: ScriptBatch) -> set[str]:
    names: set[str] = set()
    for episode in script_batch.episodes:
        for scene in episode.scenes:
            names.update(_character_name(character) for character in scene.characters)
            for line in scene.lines:
                if line.speaker:
                    names.add(_character_name(line.speaker))
    return {name for name in names if name and name not in GENERIC_CHARACTER_NAMES}


def _known_character_match(name: str, known_names: Iterable[str]) -> bool:
    normalized = normalize_text(name)
    if not normalized:
        return True
    for known in known_names:
        normalized_known = normalize_text(known)
        if normalized == normalized_known:
            return True
        if normalized in normalized_known or normalized_known in normalized:
            return True
    return False


def _detect_intent_drift(source_text: str, script_text: str) -> list[str]:
    warnings: list[str] = []
    for source_pattern, script_pattern, warning in INTENT_DRIFT_RULES:
        if re.search(source_pattern, source_text, flags=re.S) and re.search(
            script_pattern,
            script_text,
            flags=re.S,
        ):
            warnings.append(warning)
    return warnings


def _early_script_text(script_batch: ScriptBatch, *, max_episodes: int = 2) -> str:
    episodes = sorted(script_batch.episodes, key=lambda item: item.episode)[:max_episodes]
    return "\n\n".join(render_episode(episode) for episode in episodes)


def _detect_agency_ramp_drift(
    *,
    source_text: str,
    episode_context: EpisodeContext,
    script_batch: ScriptBatch,
) -> list[str]:
    early_stages = {
        StoryStage.OPENING_PRESSURE,
        StoryStage.IDENTITY_HOOK,
        StoryStage.FIRST_COUNTERATTACK,
    }
    if episode_context.story_stage not in early_stages:
        return []

    source_sample = source_text[:3000]
    if not SOURCE_VULNERABILITY_RE.search(source_sample):
        return []
    if SOURCE_PREEXISTING_POWER_RE.search(source_sample):
        return []
    if not SCRIPT_OMNISCIENT_COUNTERATTACK_RE.search(_early_script_text(script_batch)):
        return []
    return [
        "主角情绪/主动权递进漂移：原文存在受压、震惊、克制或逐步清醒阶段，"
        "脚本过早写成全知全能式开杀。必须按“承受/识别 -> 决定 -> 行动 -> 反击”递进，"
        "除非原文本身已明确重生、预知、马甲或提前布局。"
    ]


def _detect_support_takeover(script_text: str) -> list[str]:
    if not SUPPORT_TAKEOVER_RE.search(script_text):
        return []
    if SUPPORT_CHOICE_RE.search(script_text):
        return []
    return [
        "支持型角色主动权越界：脚本出现替主角决定、替主角签字/解决冲突或“站我身后”式接管，"
        "但缺少给主角选择权、证据、退路或后盾的表达。必须让支持角色提供资源和安全感，"
        "核心决定与关键反击仍由主角完成。"
    ]


def _has_opponent_pressure(
    source_analysis: SourceAnalysis,
    story_bible: StoryBible,
) -> bool:
    context = "\n".join(
        [
            *source_analysis.events,
            *source_analysis.conflicts,
            story_bible.mainline,
            *story_bible.relationships,
            *story_bible.immutable_facts,
        ]
    )
    return bool(OPPONENT_CONTEXT_RE.search(context))


def _detect_opponent_passivity(
    *,
    source_analysis: SourceAnalysis,
    story_bible: StoryBible,
    script_text: str,
) -> list[str]:
    if not _has_opponent_pressure(source_analysis, story_bible):
        return []
    if OPPONENT_ACTIVE_RE.search(script_text):
        return []
    if not OPPONENT_PASSIVE_RE.search(script_text):
        return []
    return [
        "对手行动线空心：上游资产存在外部压迫/对抗，但脚本只写对手惊慌、后退或陪衬，"
        "没有主动设局、反制、施压、毁证、挑拨或升级动作。必须补一个可拍的对手主动动作，"
        "让主角反击有阻力和代价。"
    ]


def _forbidden_reveal_leaked(haystack: str, reveal: str) -> bool:
    normalized_reveal = normalize_text(reveal)
    if len(normalized_reveal) < 3:
        return False
    normalized_haystack = normalize_text(haystack)
    if normalized_reveal in normalized_haystack:
        return True

    identity_match = re.fullmatch(
        r"(?P<subject>[\u4e00-\u9fffA-Za-z0-9]{2,8})(?:是|才是|就是|为)"
        r"(?P<predicate>[\u4e00-\u9fffA-Za-z0-9]{2,12})",
        normalized_reveal,
    )
    if identity_match:
        subject = identity_match.group("subject")
        predicate = identity_match.group("predicate")
        direct_patterns = (
            rf"{re.escape(subject)}[\u4e00-\u9fffA-Za-z0-9]{{0,8}}"
            rf"(?:是|才是|就是|身份是)[\u4e00-\u9fffA-Za-z0-9]{{0,8}}"
            rf"{re.escape(predicate)}",
            rf"{re.escape(predicate)}[\u4e00-\u9fffA-Za-z0-9]{{0,8}}"
            rf"(?:是|属于|指向)[\u4e00-\u9fffA-Za-z0-9]{{0,8}}"
            rf"{re.escape(subject)}",
        )
        return any(re.search(pattern, normalized_haystack) for pattern in direct_patterns)

    return False


def _is_timing_or_result_forbidden_rule(rule: str) -> bool:
    return any(
        token in rule
        for token in (
            "提前",
            "过早",
            "一次性",
            "全部",
            "完全",
            "公开",
            "完整",
            "结果",
            "真相",
            "揭露",
            "揭晓",
            "坐实",
            "证实",
        )
    )


def _identity_reveal_term(rule: str) -> str:
    for term in (
        "亲子鉴定",
        "真千金",
        "假千金",
        "身份",
        "血缘",
        "亲生",
        "继承人",
        "凶手",
        "幕后人",
    ):
        if term in rule:
            return term
    return _forbidden_term(rule)


def _identity_result_is_performed(script_text: str, term: str) -> bool:
    if len(normalize_text(term)) < 2:
        return False
    if not _loose_contains(script_text, term):
        return False
    if not IDENTITY_REVEAL_RESULT_RE.search(script_text):
        return False
    pending_patterns = (
        rf"{re.escape(term)}[\s\S]{{0,16}}(?:出来前|出结果前|结果出来前|未出|没出|还没出|等待|加急|要四小时)",
        rf"(?:出来前|出结果前|结果出来前|未出|没出|还没出|等待|加急|要四小时)[\s\S]{{0,16}}{re.escape(term)}",
    )
    return not any(re.search(pattern, script_text) for pattern in pending_patterns)


def _forbidden_rule_leaked(script_text: str, rule: str) -> bool:
    if _forbidden_reveal_leaked(script_text, rule):
        return True
    if _is_timing_or_result_forbidden_rule(rule):
        term = _identity_reveal_term(rule)
        return _identity_result_is_performed(script_text, term)
    term = _forbidden_term(rule)
    if len(normalize_text(term)) < 2:
        return False
    return _loose_contains(script_text, term)


def _contains(pattern: re.Pattern[str], text: str) -> bool:
    return bool(pattern.search(text))


def _story_event_markers(text: str) -> list[tuple[str, str]]:
    markers: list[tuple[str, str]] = []
    has_intimacy = _contains(INTIMACY_RE, text)
    if has_intimacy and _contains(HIGH_IMPACT_STAGE_RE, text):
        markers.append(
            (
                "high_ritual_intimacy",
                EVENT_LABELS["high_ritual_intimacy"],
            )
        )
    if has_intimacy and _contains(PUBLIC_EXPOSURE_RE, text):
        markers.append(
            (
                "public_intimacy_exposure",
                EVENT_LABELS["public_intimacy_exposure"],
            )
        )
    if _contains(IRREVERSIBLE_EXIT_RE, text):
        markers.append(
            (
                "irreversible_exit_decision",
                EVENT_LABELS["irreversible_exit_decision"],
            )
        )
    if _contains(IDENTITY_REVEAL_RESULT_RE, text):
        markers.append(
            ("identity_reveal_result", EVENT_LABELS["identity_reveal_result"])
        )
    if _contains(INSTITUTIONAL_RECKONING_RE, text):
        markers.append(
            ("institutional_reckoning", EVENT_LABELS["institutional_reckoning"])
        )
    return markers


def _audit_story_events(
    *,
    script_batch: ScriptBatch,
    previous_context: NextRoundContext | None,
    episode_context: EpisodeContext | None = None,
    episode_plan: EpisodePlan | None = None,
    series_structure_plan: SeriesStructurePlan | None = None,
) -> tuple[list[StoryStateEntry], list[str], list[str]]:
    entries: list[StoryStateEntry] = []
    blocking: list[str] = []
    advisory: list[str] = []
    events_by_key: dict[str, list[int]] = {}
    cumulative_evidence_text = ""
    if previous_context is not None:
        cumulative_evidence_text = "\n".join(
            [
                previous_context.summary,
                *previous_context.prop_states,
                *previous_context.foreshadowing_ledger,
                *previous_context.relationship_changes,
            ]
        )

    for episode in sorted(script_batch.episodes, key=lambda item: item.episode):
        visible_text = render_episode(episode)
        audit_text = visible_text
        episode_markers = _story_event_markers(audit_text)
        for key, label in episode_markers:
            events_by_key.setdefault(key, []).append(episode.episode)
            entries.append(
                StoryStateEntry(
                    episode=episode.episode,
                    kind="story_event",
                    key=key,
                    value=label,
                    status="active",
                    source="local_story_event_audit",
                )
            )

        for key, label in episode_markers:
            if key not in EVIDENCE_REQUIRED_EVENTS:
                continue
            if _contains(
                EVIDENCE_SOURCE_RE,
                "\n".join([cumulative_evidence_text, audit_text]),
            ):
                continue
            blocking.append(
                f"EP{episode.episode:02d} {label} 缺少可见证据链："
                "必须先交代证据来源、保存/验证方式和公开/裁决流程，"
                "再进入身份坐实、机构处罚、舆论反转或对手倒台结果。"
            )
        cumulative_evidence_text = "\n".join([cumulative_evidence_text, audit_text])

    for key, episodes in sorted(events_by_key.items()):
        unique_episodes = sorted(set(episodes))
        if len(unique_episodes) <= 1:
            continue
        label = EVENT_LABELS.get(key, key)
        joined = "、".join(f"EP{episode:02d}" for episode in unique_episodes)
        blocking.append(
            f"故事事件账本阻断：{label} 在 {joined} 重复兑现。"
            "同一高价值名场面只能首次演出一次；后续只能承接后果、反应或反扑，"
            "不能重复写成新的同类公开、裁决、曝光、身份揭晓或关键决定。"
        )

    if len(entries) == 0 and script_batch.episodes:
        advisory.append("story event ledger found no high-impact event markers")
    return entries, blocking, advisory


def build_source_fidelity_report(
    *,
    source_text: str,
    source_analysis: SourceAnalysis,
    episode_context: EpisodeContext,
    story_bible: StoryBible,
    script_batch: ScriptBatch,
    viral_asset_report: ViralAssetReport | None = None,
) -> SourceFidelityReport:
    del viral_asset_report
    checks: list[SourceFidelityCheck] = []
    blocking: list[str] = []
    advisory: list[str] = []
    script_text = _all_script_text(script_batch)
    episode_texts = _episode_texts(script_batch)

    for fact in story_bible.immutable_facts[:8]:
        evidence = _evidence_for(script_text, fact)
        checks.append(
            SourceFidelityCheck(
                category="C0_immutable_fact",
                anchor=fact,
                status="passed" if evidence else "advisory",
                evidence=evidence,
                warning=None if evidence else "immutable fact tracked but not directly surfaced in this round",
            )
        )

    for episode_number, asset in [
        pair
        for mapping in episode_context.source_to_episode_mapping
        for pair in _mapping_assets(mapping)
    ]:
        if len(normalize_text(asset)) < 4:
            continue
        target_text = episode_texts.get(episode_number, script_text) if episode_number else script_text
        if _loose_contains(target_text, asset):
            checks.append(
                SourceFidelityCheck(
                    category="source_mapping",
                    anchor=asset,
                    episode=episode_number,
                    status="passed",
                    evidence=_evidence_for(target_text, asset),
                )
            )
            continue
        warning = f"source anchor not evidenced in script: {asset[:80]}"
        is_generic_planning_anchor = "->" in asset and re.search(
            r"(上一轮|开场|起势|继续|承接|推进)",
            asset,
        )
        if is_generic_planning_anchor:
            advisory.append(warning)
            status = "advisory"
        else:
            blocking.append(warning)
            status = "blocking"
        checks.append(
            SourceFidelityCheck(
                category="source_mapping",
                anchor=asset,
                episode=episode_number,
                status=status,
                warning=warning,
            )
        )

    visual_hits = 0
    for moment in source_analysis.visual_moments[:10]:
        if _loose_contains(script_text, moment):
            visual_hits += 1
            checks.append(
                SourceFidelityCheck(
                    category="C2_visual_asset",
                    anchor=moment,
                    status="passed",
                    evidence=_evidence_for(script_text, moment),
                )
            )
    if source_analysis.visual_moments and visual_hits == 0:
        warning = "no source visual moment is preserved in the visible script"
        advisory.append(warning)
        checks.append(
            SourceFidelityCheck(
                category="C2_visual_asset",
                anchor="; ".join(source_analysis.visual_moments[:3]),
                status="advisory",
                warning=warning,
            )
        )

    first_episode = script_batch.episodes[0] if script_batch.episodes else None
    first_opening = _opening_text(first_episode) if first_episode else ""
    original_hook_preserved = False
    for hook in source_analysis.candidate_hooks[:3]:
        if _loose_contains(first_opening, hook) or _loose_contains(script_text, hook):
            original_hook_preserved = True
            checks.append(
                SourceFidelityCheck(
                    category="hook_preservation",
                    anchor=hook,
                    episode=first_episode.episode if first_episode else None,
                    status="passed",
                    evidence=_evidence_for(first_opening or script_text, hook),
                )
            )
            break
    if source_analysis.candidate_hooks and not original_hook_preserved:
        warning = (
            "original strong hook appears dropped instead of being preserved or visibly upgraded"
        )
        blocking.append(warning)
        checks.append(
            SourceFidelityCheck(
                category="hook_preservation",
                anchor="; ".join(source_analysis.candidate_hooks[:3]),
                episode=first_episode.episode if first_episode else None,
                status="blocking",
                warning=warning,
            )
        )

    source_opening = source_text[:1600]
    if (
        first_episode is not None
        and OPENING_TENSION_SOURCE_RE.search(source_opening)
        and not OPENING_TENSION_SCRIPT_RE.search(first_opening)
    ):
        warning = (
            "source opening tension asset was removed instead of being safely visualized"
        )
        blocking.append(warning)
        checks.append(
            SourceFidelityCheck(
                category="opening_tension_preservation",
                anchor=source_opening[:160],
                episode=first_episode.episode,
                status="blocking",
                warning=warning,
            )
        )

    for warning in _detect_intent_drift(source_text, script_text):
        blocking.append(warning)
        checks.append(
            SourceFidelityCheck(
                category="intent_drift",
                anchor=warning,
                status="blocking",
                warning=warning,
            )
        )

    for warning in _detect_agency_ramp_drift(
        source_text=source_text,
        episode_context=episode_context,
        script_batch=script_batch,
    ):
        blocking.append(warning)
        checks.append(
            SourceFidelityCheck(
                category="agency_ramp",
                anchor=source_text[:160],
                status="blocking",
                evidence=_evidence_for(_early_script_text(script_batch), "早就知道"),
                warning=warning,
            )
        )

    for warning in _detect_support_takeover(script_text):
        blocking.append(warning)
        checks.append(
            SourceFidelityCheck(
                category="support_role_boundary",
                anchor="support_role_agency_boundary",
                status="blocking",
                warning=warning,
            )
        )

    for warning in _detect_opponent_passivity(
        source_analysis=source_analysis,
        story_bible=story_bible,
        script_text=script_text,
    ):
        blocking.append(warning)
        checks.append(
            SourceFidelityCheck(
                category="opponent_agency",
                anchor="opponent_active_countermove",
                status="blocking",
                warning=warning,
            )
        )

    for rule in story_bible.forbidden_changes + episode_context.forbidden_reveals:
        term = _forbidden_term(rule)
        if len(normalize_text(term)) < 2:
            continue
        if _forbidden_rule_leaked(script_text, rule):
            warning = f"forbidden addition/reveal may have leaked into script: {rule}"
            blocking.append(warning)
            checks.append(
                SourceFidelityCheck(
                    category="C4_forbidden_addition",
                    anchor=rule,
                    status="blocking",
                    evidence=_evidence_for(script_text, term),
                    warning=warning,
                )
            )

    known_names = set(source_analysis.characters) | set(story_bible.characters)
    unknown_names = sorted(
        name
        for name in _script_characters(script_batch)
        if not _known_character_match(name, known_names)
    )
    if len(unknown_names) >= 3:
        warning = "script introduced multiple untracked speaking characters: " + "、".join(unknown_names[:6])
        advisory.append(warning)
        checks.append(
            SourceFidelityCheck(
                category="character_integrity",
                anchor="、".join(unknown_names[:6]),
                status="advisory",
                warning=warning,
            )
        )

    if source_text and not any(_loose_contains(script_text, token) for token in _tokens(source_text)[:12]):
        warning = "script has weak lexical overlap with the uploaded source"
        advisory.append(warning)
        checks.append(
            SourceFidelityCheck(
                category="C1_must_keep_scene",
                anchor=source_text[:80],
                status="advisory",
                warning=warning,
            )
        )

    score = max(0, 100 - len(blocking) * 18 - len(advisory) * 6)
    return SourceFidelityReport(
        score=score,
        preserved_original_hook=original_hook_preserved,
        checks=checks,
        blocking_warnings=blocking,
        advisory_warnings=advisory,
    )


def _tail_text(episode: EpisodeScript, line_count: int = 4) -> str:
    lines: list[str] = [episode.cliffhanger]
    if episode.scenes:
        for line in episode.scenes[-1].lines[-line_count:]:
            lines.append(f"{line.speaker or ''} {line.text}".strip())
    return "\n".join(line for line in lines if line.strip())


def _token_overlap(left: str, right: str) -> int:
    left_tokens = Counter(token for token in _tokens(left) if len(token) >= 2)
    right_tokens = Counter(token for token in _tokens(right) if len(token) >= 2)
    return sum((left_tokens & right_tokens).values())


def _token_match_strength(needle: str, haystack: str) -> tuple[int, int]:
    normalized_haystack = normalize_text(haystack)
    tokens = [token for token in _tokens(needle) if len(token) >= 2]
    matched = sum(1 for token in tokens if normalize_text(token) in normalized_haystack)
    return matched, len(tokens)


def _has_late_event_overlap(needle: str, haystack: str) -> bool:
    compact = normalize_text(needle)
    if len(compact) <= 4:
        return True
    late_segment = compact[4:]
    return any(normalize_text(token) in normalize_text(haystack) for token in _tokens(late_segment))


def build_continuity_audit_report(
    *,
    episode_context: EpisodeContext,
    script_batch: ScriptBatch,
    previous_context: NextRoundContext | None,
) -> ContinuityAuditReport:
    del episode_context
    links: list[ContinuityLinkReport] = []
    blocking: list[str] = []
    advisory: list[str] = []
    episodes = sorted(script_batch.episodes, key=lambda item: item.episode)

    if previous_context:
        first_episode = episodes[0] if episodes else None
        first_opening = _opening_text(first_episode) if first_episode else ""
        for hook in previous_context.open_hooks[:4]:
            if not hook.strip():
                continue
            if not _hook_acknowledged(hook, first_opening):
                advisory.append(
                    f"previous open hook is not acknowledged in this round opening: {hook[:80]}"
                )
        all_text = _all_script_text(script_batch)
        for reveal in previous_context.forbidden_reveals[:8]:
            if reveal.strip() and _forbidden_reveal_leaked(all_text, reveal):
                blocking.append(f"forbidden reveal leaked from previous context: {reveal}")

    for previous, current in zip(episodes, episodes[1:]):
        tail = _tail_text(previous)
        opening = _opening_text(current)
        warnings: list[str] = []
        status: Literal["passed", "advisory", "blocking"] = "passed"
        if previous.cliffhanger.strip() and not _hook_acknowledged(
            previous.cliffhanger,
            opening,
        ):
            warnings.append(
                "next episode opening does not visibly acknowledge previous cliffhanger"
            )
            advisory.append(
                f"EP{previous.episode:02d}->EP{current.episode:02d} may need opening linkage"
            )
            status = "advisory"
        links.append(
            ContinuityLinkReport(
                previous_episode=previous.episode,
                next_episode=current.episode,
                previous_cliffhanger=tail[:240],
                next_opening=opening[:240],
                status=status,
                warnings=warnings,
            )
        )

    score = max(0, 100 - len(blocking) * 25 - len(advisory) * 5)
    return ContinuityAuditReport(
        score=score,
        links=links,
        blocking_warnings=blocking,
        advisory_warnings=advisory,
    )


def _entry_value(value: Any) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, (int, float, bool)):
        return str(value)
    return repr(value)


def _hook_acknowledged(hook: str, text: str) -> bool:
    if not (hook.strip() and text.strip()):
        return False
    if normalize_text(hook) in normalize_text(text):
        return True
    matched, total = _token_match_strength(hook, text)
    if total <= 2:
        return matched == total and matched > 0
    return matched >= 3 and (matched / total) >= 0.25 and _has_late_event_overlap(hook, text)


def build_story_state_ledger(
    *,
    script_batch: ScriptBatch,
    next_round_context: NextRoundContext,
    previous_context: NextRoundContext | None,
    episode_context: EpisodeContext | None = None,
    episode_plan: EpisodePlan | None = None,
    series_structure_plan: SeriesStructurePlan | None = None,
) -> StoryStateLedger:
    entries: list[StoryStateEntry] = []
    warnings: list[str] = []
    blocking_warnings: list[str] = []
    episodes = sorted(script_batch.episodes, key=lambda item: item.episode)

    if previous_context:
        first_episode = episodes[0] if episodes else None
        first_opening = _opening_text(first_episode) if first_episode else ""
        for hook in previous_context.open_hooks:
            acknowledged = _hook_acknowledged(hook, first_opening)
            entries.append(
                StoryStateEntry(
                    kind="open_hook",
                    key=hook[:40],
                    value=hook,
                    status="closed" if acknowledged else "open",
                    source="previous_context",
                )
            )
        for reveal in previous_context.forbidden_reveals:
            entries.append(
                StoryStateEntry(
                    kind="forbidden_reveal",
                    key=reveal[:40],
                    value=reveal,
                    status="forbidden",
                    source="previous_context",
                )
            )

    for index, episode in enumerate(episodes):
        if not episode.state_update:
            warnings.append(f"EP{episode.episode:02d} missing state_update")
        next_episode = episodes[index + 1] if index + 1 < len(episodes) else None
        hook_status: Literal["open", "closed"] = "open"
        if next_episode and _hook_acknowledged(
            episode.cliffhanger,
            _opening_text(next_episode),
        ):
            hook_status = "closed"
        entries.append(
            StoryStateEntry(
                episode=episode.episode,
                kind="open_hook",
                key=episode.cliffhanger[:40],
                value=episode.cliffhanger,
                status=hook_status,
                source="episode.cliffhanger",
            )
        )
        for key, value in episode.state_update.items():
            entries.append(
                StoryStateEntry(
                    episode=episode.episode,
                    kind="episode_state",
                    key=str(key),
                    value=_entry_value(value),
                    status="active",
                    source="episode.state_update",
                )
            )

    for reveal in next_round_context.forbidden_reveals:
        entries.append(
            StoryStateEntry(
                kind="forbidden_reveal",
                key=reveal[:40],
                value=reveal,
                status="forbidden",
                source="next_round_context",
            )
        )
    for character, facts in next_round_context.character_knowledge.items():
        for fact in facts:
            entries.append(
                StoryStateEntry(
                    kind="character_knowledge",
                    key=character,
                    value=fact,
                    status="active",
                    source="next_round_context",
                )
            )
    for change in next_round_context.relationship_changes:
        entries.append(
            StoryStateEntry(
                kind="relationship_change",
                key=change[:40],
                value=change,
                status="active",
                source="next_round_context",
            )
        )
    for prop in next_round_context.prop_states:
        entries.append(
            StoryStateEntry(
                kind="prop_state",
                key=prop[:40],
                value=prop,
                status="active",
                source="next_round_context",
            )
        )
    for item in next_round_context.foreshadowing_ledger:
        entries.append(
            StoryStateEntry(
                kind="foreshadowing",
                key=item[:40],
                value=item,
                status="open",
                source="next_round_context",
            )
        )

    (
        story_event_entries,
        story_event_blocking,
        story_event_advisory,
    ) = _audit_story_events(
        script_batch=script_batch,
        previous_context=previous_context,
        episode_context=episode_context,
        episode_plan=episode_plan,
        series_structure_plan=series_structure_plan,
    )
    entries.extend(story_event_entries)
    blocking_warnings.extend(story_event_blocking)
    warnings.extend(story_event_advisory)

    if len(next_round_context.open_hooks) > 8:
        warnings.append("too many open hooks; next round may lose focus")
    final_cliffhanger = episodes[-1].cliffhanger if episodes else ""
    if final_cliffhanger and not any(
        _hook_acknowledged(final_cliffhanger, hook)
        for hook in next_round_context.open_hooks
    ):
        warnings.append(
            "next_round_context open_hooks does not carry the final episode cliffhanger"
        )

    return StoryStateLedger(
        current_episode=next_round_context.current_episode,
        entries=entries,
        open_hooks=next_round_context.open_hooks,
        forbidden_reveals=next_round_context.forbidden_reveals,
        character_knowledge=next_round_context.character_knowledge,
        relationship_changes=next_round_context.relationship_changes,
        prop_states=next_round_context.prop_states,
        foreshadowing_ledger=next_round_context.foreshadowing_ledger,
        blocking_warnings=blocking_warnings,
        warnings=warnings,
    )


def build_adaptation_quality_report(
    *,
    source_text: str,
    source_analysis: SourceAnalysis,
    episode_context: EpisodeContext,
    story_bible: StoryBible,
    script_batch: ScriptBatch,
    next_round_context: NextRoundContext,
    previous_context: NextRoundContext | None,
    viral_asset_report: ViralAssetReport | None = None,
    episode_plan: EpisodePlan | None = None,
    series_structure_plan: SeriesStructurePlan | None = None,
) -> AdaptationQualityReport:
    source_fidelity = build_source_fidelity_report(
        source_text=source_text,
        source_analysis=source_analysis,
        episode_context=episode_context,
        story_bible=story_bible,
        script_batch=script_batch,
        viral_asset_report=viral_asset_report,
    )
    continuity = build_continuity_audit_report(
        episode_context=episode_context,
        script_batch=script_batch,
        previous_context=previous_context,
    )
    ledger = build_story_state_ledger(
        script_batch=script_batch,
        next_round_context=next_round_context,
        previous_context=previous_context,
        episode_context=episode_context,
        episode_plan=episode_plan,
        series_structure_plan=series_structure_plan,
    )
    blocking = [
        *source_fidelity.blocking_warnings,
        *continuity.blocking_warnings,
        *ledger.blocking_warnings,
    ]
    advisory = [
        *source_fidelity.advisory_warnings,
        *continuity.advisory_warnings,
        *ledger.warnings,
    ]
    rewrite_instruction = ""
    if blocking:
        rewrite_instruction = (
            "改编一致性阻断：必须保留原著强钩子/名场面/主动方逻辑，不得泄露 forbidden reveal，"
            "不得新增 story bible 禁止项；必须遵守故事事件账本，同一高价值名场面不得重复兑现，"
            "身份/机构/舆论/权威裁决类结果必须先交代证据来源和流程；"
            "必须守住主角情绪递进、支持角色选择权边界和对手主动反制。具体问题："
            + "；".join(blocking[:6])
        )
    return AdaptationQualityReport(
        source_fidelity=source_fidelity,
        continuity=continuity,
        story_state_ledger=ledger,
        blocking_warnings=blocking,
        advisory_warnings=advisory,
        rewrite_instruction=rewrite_instruction,
    )


def build_methodology_quality_report(
    *,
    source_analysis: SourceAnalysis,
    script_batch: ScriptBatch,
    source_strength_profile: SourceStrengthProfile,
    methodology_context: MethodologyContext | None,
    viral_asset_report: ViralAssetReport | None = None,
) -> MethodologyQualityReport:
    if (
        source_strength_profile.overall_level != SourceStrengthLevel.STRONG
        or source_strength_profile.recommended_intensity != AdaptationIntensity.LIGHT
        or methodology_context is None
    ):
        return MethodologyQualityReport()

    source_fidelity_cards = [
        card
        for card in methodology_context.cards
        if card.category == "source_fidelity"
    ]
    if not source_fidelity_cards:
        return MethodologyQualityReport()

    card = source_fidelity_cards[0]
    script_text = _all_script_text(script_batch)
    first_episode = script_batch.episodes[0] if script_batch.episodes else None
    is_opening_round = first_episode is None or first_episode.episode <= 1
    first_opening = _opening_text(first_episode) if first_episode else ""
    issues: list[MethodologyQualityIssue] = []

    if is_opening_round:
        for hook in source_analysis.candidate_hooks[:3]:
            if not hook.strip():
                continue
            if _loose_contains(first_opening, hook) or _loose_contains(script_text, hook):
                continue
            issues.append(
                MethodologyQualityIssue(
                    card_id=card.id,
                    card_name=card.name,
                    severity="blocking",
                    episode=first_episode.episode if first_episode else None,
                    message=f"强原文轻改失败：原文开场钩子未被保留或视听化：{hook}",
                    evidence=_evidence_for(script_text, hook),
                )
            )

        high_value_assets = list(source_analysis.visual_moments[:8])
        if viral_asset_report is not None:
            high_value_assets.extend(viral_asset_report.signature_scenes[:5])
        high_value_assets = list(
            dict.fromkeys(asset for asset in high_value_assets if asset.strip())
        )
        if high_value_assets and not any(
            _loose_contains(script_text, asset) for asset in high_value_assets
        ):
            issues.append(
                MethodologyQualityIssue(
                    card_id=card.id,
                    card_name=card.name,
                    severity="blocking",
                    episode=first_episode.episode if first_episode else None,
                    message=(
                        "强原文轻改失败：原文高价值画面/名场面没有在正片中被保留，"
                        "不能只重构成泛化冲突。"
                    ),
                    evidence=high_value_assets[:4],
                )
            )

    for negative_example in card.negative_examples[:5]:
        if not negative_example.strip():
            continue
        if _loose_contains(script_text, negative_example):
            issues.append(
                MethodologyQualityIssue(
                    card_id=card.id,
                    card_name=card.name,
                    severity="blocking",
                    episode=None,
                    message=f"强原文轻改失败：脚本疑似命中方法论反例：{negative_example}",
                    evidence=_evidence_for(script_text, negative_example),
                )
            )

    rewrite_instruction = ""
    if issues:
        rewrite_instruction = (
            "方法论阻断：本素材被判定为强原文，只允许轻改。必须回到原文 C0/C1："
            "保留开场钩子、主动方、因果顺序、关键决定时机和名场面；"
            "只做镜头视听化、短台词化、压缩和衔接补强。具体问题："
            + "；".join(issue.message for issue in issues[:6])
        )
    return MethodologyQualityReport(issues=issues, rewrite_instruction=rewrite_instruction)


def merge_methodology_quality_into_report(
    report,
    methodology_report: MethodologyQualityReport,
):
    blocking_issues = [
        issue.message
        for issue in methodology_report.issues
        if issue.severity == "blocking"
    ]
    if not blocking_issues:
        return report

    status = (
        QualityStatus.NEEDS_REWRITE
        if report.status == QualityStatus.USABLE
        else report.status
    )
    rewrite_instruction = "；".join(
        part
        for part in [
            methodology_report.rewrite_instruction,
            report.rewrite_instruction,
        ]
        if part
    )
    return report.model_copy(
        update={
            "status": status,
            "blocking_issues": [*report.blocking_issues, *blocking_issues],
            "rewrite_instruction": rewrite_instruction,
        }
    )


def merge_adaptation_quality_into_report(
    report,
    adaptation_report: AdaptationQualityReport,
):
    if not adaptation_report.blocking_warnings:
        return report

    blocking_issues = [
        *report.blocking_issues,
        *adaptation_report.blocking_warnings,
    ]
    rewrite_instruction = "；".join(
        part
        for part in [
            adaptation_report.rewrite_instruction,
            report.rewrite_instruction,
        ]
        if part
    )
    status = (
        QualityStatus.NEEDS_REWRITE
        if report.status == QualityStatus.USABLE
        else report.status
    )
    return report.model_copy(
        update={
            "status": status,
            "blocking_issues": blocking_issues,
            "rewrite_instruction": rewrite_instruction,
        }
    )
