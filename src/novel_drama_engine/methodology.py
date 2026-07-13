from __future__ import annotations

import json
import re
from pathlib import Path

from novel_drama_engine.models import (
    MethodologyCard,
    MethodologyContext,
    MethodologySource,
    MethodologyStage,
    MethodologyStatus,
    SourceStrengthProfile,
)


_CATEGORY_RULES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("opening_design", ("开场", "前三秒", "前3秒", "3 秒", "3秒", "hook", "钩子")),
    ("cliffhanger", ("断点", "结尾", "追更", "悬念", "下一集")),
    ("visual_translation", ("视听", "镜头", "画面", "分镜", "景别", "运镜", "show", "动作行")),
    ("dialogue", ("台词", "对白", "潜台词", "OS", "VO", "三不原则")),
    ("character_bible", ("人物", "人设", "OOC", "动机", "角色", "功能性配角", "反派")),
    ("series_structure", ("全剧", "结构", "三幕", "情绪曲线", "小高潮", "大高潮")),
    ("episode_plan", ("单集", "每集", "30秒", "三波", "信息增量", "剧情推进")),
    ("production_feasibility", ("拍摄", "成本", "场景", "道具", "制作", "可执行")),
    ("source_fidelity", ("强原文", "轻改", "名场面", "原文资产", "主动方", "因果", "C0", "C1")),
)

_CATEGORY_STAGES: dict[str, list[MethodologyStage]] = {
    "source_fidelity": [
        MethodologyStage.EPISODE_PLAN,
        MethodologyStage.SCRIPT_GENERATION,
        MethodologyStage.QUALITY_GATE,
    ],
    "opening_design": [
        MethodologyStage.EPISODE_PLAN,
        MethodologyStage.SCRIPT_GENERATION,
        MethodologyStage.QUALITY_GATE,
    ],
    "cliffhanger": [
        MethodologyStage.EPISODE_PLAN,
        MethodologyStage.SCRIPT_GENERATION,
        MethodologyStage.QUALITY_GATE,
    ],
    "visual_translation": [
        MethodologyStage.SCRIPT_GENERATION,
        MethodologyStage.QUALITY_GATE,
    ],
    "dialogue": [
        MethodologyStage.SCRIPT_GENERATION,
        MethodologyStage.QUALITY_GATE,
    ],
    "character_bible": [
        MethodologyStage.STORY_BIBLE,
        MethodologyStage.EPISODE_PLAN,
        MethodologyStage.SCRIPT_GENERATION,
        MethodologyStage.QUALITY_GATE,
    ],
    "series_structure": [
        MethodologyStage.SERIES_STRUCTURE,
        MethodologyStage.EPISODE_PLAN,
    ],
    "episode_plan": [
        MethodologyStage.EPISODE_PLAN,
        MethodologyStage.SCRIPT_GENERATION,
        MethodologyStage.QUALITY_GATE,
    ],
    "production_feasibility": [
        MethodologyStage.SCRIPT_GENERATION,
        MethodologyStage.QUALITY_GATE,
    ],
    "general_adaptation": [
        MethodologyStage.EPISODE_CONTEXT,
        MethodologyStage.STORY_BIBLE,
        MethodologyStage.SCRIPT_GENERATION,
        MethodologyStage.QUALITY_GATE,
    ],
}


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def default_methodology_cards_path() -> Path:
    return _repo_root() / "examples" / "methodology_cards.json"


def _normalize_tags(values: list[str]) -> set[str]:
    normalized: set[str] = set()
    aliases = {
        "女频": "female",
        "男频": "male",
        "混合": "mixed",
        "复仇": "revenge",
        "身份": "identity",
        "真假千金": "identity",
        "豪门": "billionaire",
        "穿越": "transmigration",
        "轻喜": "comedy",
        "经商打脸": "business_counterattack",
    }
    for value in values:
        item = value.strip().lower()
        if not item:
            continue
        normalized.add(item)
        normalized.add(aliases.get(value.strip(), item))
    return normalized


_STAGE_CATEGORY_PRIORITIES: dict[MethodologyStage, list[str]] = {
    MethodologyStage.SOURCE_ANALYSIS: [
        "source_analysis",
        "source_fidelity",
    ],
    MethodologyStage.EPISODE_CONTEXT: [
        "source_analysis",
        "adaptation_strategy",
        "information_delivery",
        "source_fidelity",
    ],
    MethodologyStage.STORY_BIBLE: [
        "character_bible",
        "source_analysis",
        "series_structure",
        "source_fidelity",
    ],
    MethodologyStage.SERIES_STRUCTURE: [
        "series_structure",
        "structure_device",
        "plot_pattern",
        "source_analysis",
    ],
    MethodologyStage.EPISODE_PLAN: [
        "source_fidelity",
        "opening_design",
        "episode_plan",
        "cliffhanger",
        "emotion_engine",
        "series_structure",
        "character_bible",
        "adaptation_strategy",
        "structure_device",
        "plot_pattern",
        "male_frequency",
        "female_frequency",
        "information_delivery",
    ],
    MethodologyStage.SCRIPT_GENERATION: [
        "source_fidelity",
        "visual_translation",
        "dialogue",
        "shot_logic",
        "production_feasibility",
        "opening_design",
        "cliffhanger",
        "emotion_engine",
        "adaptation_strategy",
        "information_delivery",
        "structure_device",
        "os_vo",
        "male_frequency",
        "female_frequency",
    ],
    MethodologyStage.QUALITY_GATE: [
        "source_fidelity",
        "visual_translation",
        "dialogue",
        "source_analysis",
        "character_bible",
        "cliffhanger",
        "production_feasibility",
        "adaptation_strategy",
        "emotion_engine",
        "structure_device",
    ],
}


def _category_priority(card: MethodologyCard, stage: MethodologyStage) -> int:
    priorities = _STAGE_CATEGORY_PRIORITIES.get(stage, [])
    if card.category not in priorities:
        return 0
    return len(priorities) - priorities.index(card.category)


def _trim_rule(text: str, *, limit: int = 260) -> str:
    compact = re.sub(r"\s+", " ", text).strip(" -#*`：:")
    if len(compact) <= limit:
        return compact
    return compact[: limit - 1].rstrip("，。；,; ") + "…"


def _clean_heading(value: str) -> str:
    heading = re.sub(r"^#+\s*", "", value).strip()
    heading = re.sub(r"^[一二三四五六七八九十\d]+[、.．]\s*", "", heading)
    heading = re.sub(r"^Step\s*\d+[:：-]?\s*", "", heading, flags=re.IGNORECASE)
    heading = heading.strip(" -#*`：:")
    return heading or "通用改编规则"


def _split_methodology_blocks(raw_text: str, fallback_title: str) -> list[tuple[str, str]]:
    heading_re = re.compile(r"^(#{1,4})\s+(.+?)\s*$")
    blocks: list[tuple[str, list[str]]] = []
    current_title = fallback_title
    current_lines: list[str] = []

    for line in raw_text.splitlines():
        match = heading_re.match(line.strip())
        if match:
            if current_lines:
                blocks.append((current_title, current_lines))
            current_title = _clean_heading(match.group(2))
            current_lines = []
            continue
        current_lines.append(line)
    if current_lines:
        blocks.append((current_title, current_lines))

    cleaned = [
        (title, "\n".join(lines).strip())
        for title, lines in blocks
        if len("\n".join(lines).strip()) >= 30
    ]
    if cleaned:
        return cleaned
    return [(fallback_title, raw_text.strip())]


def _infer_category(text: str, title: str) -> str:
    haystack = f"{title}\n{text}"
    for category, tokens in _CATEGORY_RULES:
        if any(token.lower() in haystack.lower() for token in tokens):
            return category
    return "general_adaptation"


def _infer_channels(text: str) -> list[str]:
    channels: list[str] = []
    if any(token in text for token in ("女频", "现言", "古言", "甜宠", "追妻", "真假千金")):
        channels.append("female")
    if any(token in text for token in ("男频", "玄幻", "历史", "赘婿", "战神", "经商")):
        channels.append("male")
    if not channels:
        channels = ["female", "male", "mixed"]
    elif len(channels) == 2:
        channels.append("mixed")
    return list(dict.fromkeys(channels))


def _infer_genres(text: str, category: str) -> list[str]:
    genres: list[str] = []
    genre_tokens = {
        "identity": ("身份", "真假千金", "马甲", "继承人", "认亲"),
        "revenge": ("复仇", "反击", "打脸", "清算"),
        "billionaire": ("豪门", "霸总", "总裁"),
        "transmigration": ("穿越", "重生", "系统", "预知"),
        "business_counterattack": ("经商", "商战", "创业", "赚钱"),
        "comedy": ("轻喜", "喜剧", "误会"),
    }
    for genre, tokens in genre_tokens.items():
        if any(token in text for token in tokens):
            genres.append(genre)
    if category in {"source_fidelity", "general_adaptation"} and "unknown" not in genres:
        genres.append("unknown")
    return list(dict.fromkeys(genres or ["unknown"]))


def _lines_matching(text: str, tokens: tuple[str, ...], *, limit: int = 3) -> list[str]:
    lines: list[str] = []
    for line in text.splitlines():
        item = line.strip(" -#*`")
        if len(item) < 6:
            continue
        if any(token in item for token in tokens):
            lines.append(_trim_rule(item, limit=140))
        if len(lines) >= limit:
            break
    return lines


def _rule_from_lines(
    text: str,
    *,
    preferred_tokens: tuple[str, ...],
    fallback: str,
) -> str:
    matches = _lines_matching(text, preferred_tokens, limit=4)
    if matches:
        return _trim_rule("；".join(matches), limit=320)
    return _trim_rule(fallback, limit=320)


def _extract_positive_examples(text: str) -> list[str]:
    return _lines_matching(text, ("正例", "示例", "例：", "例如", "正确"), limit=3)


def _extract_negative_examples(text: str) -> list[str]:
    return _lines_matching(text, ("反例", "错误", "常见错误", "坑", "禁止", "不得"), limit=3)


def _fallback_trigger(category: str) -> str:
    if category == "source_fidelity":
        return "原文已具备强冲突、强钩子、强反差或高情绪名场面"
    if category == "opening_design":
        return "本集开场缺少前三秒可见冲突或原文天然钩子需要保护"
    if category == "visual_translation":
        return "小说段落含内心戏、环境描写或抽象情绪，需要转成画面/动作/音效"
    if category == "dialogue":
        return "台词过长、书面化或缺少潜台词时"
    if category == "character_bible":
        return "人物动机、功能或台词风格存在 OOC 风险时"
    if category == "cliffhanger":
        return "单集结尾缺少追更断点或断点说明化时"
    return "当前阶段需要引用内部方法论"


def _fallback_generation_rule(category: str, block_text: str) -> str:
    if category == "source_fidelity":
        return "保留原文主动方、因果顺序、名场面和情绪曲线，只做视听化、压缩、镜头补强和短台词化。"
    return _trim_rule(block_text, limit=320)


def _fallback_quality_rule(category: str) -> str:
    if category == "source_fidelity":
        return "如果脚本删除 C1 名场面、改变 C0 主动方、把克制情绪改成歇斯底里或新增 C4 编造道具/动作/狠话，必须 needs_rewrite。"
    if category == "character_bible":
        return "检查人物动机、主动权、台词风格和功能定位是否与 Story Bible 一致。"
    if category == "visual_translation":
        return "检查抽象心理是否被转成可拍动作、表情、道具、景别、运镜和音效。"
    if category == "dialogue":
        return "检查台词是否短、口语化、有潜台词，且每句都推进剧情或塑造人物。"
    if category == "cliffhanger":
        return "检查结尾是否停在动作、证据、身份、关系或危机爆点前一秒。"
    return "检查输出是否遵守该方法论的触发条件和生成规则。"


def extract_method_cards(source: MethodologySource) -> list[MethodologyCard]:
    raw_text = source.raw_text.strip()
    if not raw_text:
        return []

    cards: list[MethodologyCard] = []
    for index, (title, block_text) in enumerate(
        _split_methodology_blocks(raw_text, source.title)[:12],
        start=1,
    ):
        category = _infer_category(block_text, title)
        name = _clean_heading(title)
        trigger = _rule_from_lines(
            block_text,
            preferred_tokens=("触发", "适用", "场景", "当", "如果", "输入"),
            fallback=_fallback_trigger(category),
        )
        generation_rule = _rule_from_lines(
            block_text,
            preferred_tokens=("方法", "操作", "执行", "生成", "原则", "必须", "要"),
            fallback=_fallback_generation_rule(category, block_text),
        )
        quality_rule = _rule_from_lines(
            block_text,
            preferred_tokens=("质检", "自检", "检查", "验收", "失败", "禁止", "不得", "错误"),
            fallback=_fallback_quality_rule(category),
        )
        cards.append(
            MethodologyCard(
                id=f"{source.id}_card_{index:03d}",
                source_id=source.id,
                name=name,
                category=category,
                applies_to_channel=_infer_channels(block_text),
                applies_to_genre=_infer_genres(block_text, category),
                applies_to_stage=_CATEGORY_STAGES[category],
                trigger=trigger,
                generation_rule=generation_rule,
                quality_rule=quality_rule,
                positive_examples=_extract_positive_examples(block_text),
                negative_examples=_extract_negative_examples(block_text),
                status=MethodologyStatus.DRAFT,
            )
        )

    if cards:
        return cards

    return [
        MethodologyCard(
            id=f"{source.id}_card_001",
            source_id=source.id,
            name=source.title,
            category="general_adaptation",
            applies_to_channel=["female", "male", "mixed"],
            applies_to_genre=["unknown"],
            applies_to_stage=_CATEGORY_STAGES["general_adaptation"],
            trigger=_fallback_trigger("general_adaptation"),
            generation_rule=_trim_rule(raw_text, limit=320),
            quality_rule=_fallback_quality_rule("general_adaptation"),
            status=MethodologyStatus.DRAFT,
        )
    ]


def load_methodology_cards(path: Path | str | None = None) -> list[MethodologyCard]:
    resolved_path = Path(path) if path else default_methodology_cards_path()
    if not resolved_path.exists():
        return []
    raw = json.loads(resolved_path.read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        raise ValueError(f"methodology card file must contain a JSON array: {resolved_path}")
    return [MethodologyCard.model_validate(item) for item in raw]


def _matches(
    card: MethodologyCard,
    *,
    stage: MethodologyStage,
    channel: str | None,
    genre_tags: list[str],
) -> bool:
    if card.status != MethodologyStatus.ACTIVE:
        return False
    if card.applies_to_stage and stage not in card.applies_to_stage:
        return False
    if card.applies_to_channel:
        channel_tags = _normalize_tags([channel or "unknown"])
        if _normalize_tags(card.applies_to_channel).isdisjoint(channel_tags):
            return False
    if card.applies_to_genre:
        requested_genres = _normalize_tags(genre_tags or ["unknown"])
        if _normalize_tags(card.applies_to_genre).isdisjoint(requested_genres):
            return False
    return True


def retrieve_methodology_context(
    cards: list[MethodologyCard],
    *,
    stage: MethodologyStage,
    channel: str | None,
    genre_tags: list[str],
    source_strength_profile: SourceStrengthProfile,
    limit: int = 7,
) -> MethodologyContext:
    matched = [
        card
        for card in cards
        if _matches(card, stage=stage, channel=channel, genre_tags=genre_tags)
    ]

    def score(card: MethodologyCard) -> tuple[int, int, int]:
        source_fidelity_bonus = (
            1
            if card.category == "source_fidelity"
            and source_strength_profile.recommended_intensity.value == "light"
            else 0
        )
        category_priority = _category_priority(card, stage)
        stage_specificity = 1 if card.applies_to_stage else 0
        return (source_fidelity_bonus, category_priority, stage_specificity)

    ranked = sorted(matched, key=score, reverse=True)
    return MethodologyContext(
        source_strength_level=source_strength_profile.overall_level,
        adaptation_intensity=source_strength_profile.recommended_intensity,
        cards=ranked[:limit],
    )


def render_methodology_context(context: MethodologyContext | None) -> str:
    if context is None:
        return "无内部方法论卡。"
    if not context.cards:
        return (
            "内部方法论卡：无匹配卡片。\n"
            f"源文本强度：{context.source_strength_level.value}\n"
            f"改编强度：{context.adaptation_intensity.value}"
        )
    lines = [
        "内部方法论卡：以下规则为系统自动检索，仅用于提升生成质量，不向用户展示为可选项。",
        f"源文本强度：{context.source_strength_level.value}",
        f"改编强度：{context.adaptation_intensity.value}",
    ]
    for index, card in enumerate(context.cards, start=1):
        lines.extend(
            [
                f"{index}. {card.name}",
                f"- 触发条件：{card.trigger}",
                f"- 生成规则：{card.generation_rule}",
                f"- 质检规则：{card.quality_rule}",
            ]
        )
        if card.positive_examples:
            lines.append("- 正例：" + "；".join(card.positive_examples[:2]))
        if card.negative_examples:
            lines.append("- 反例：" + "；".join(card.negative_examples[:2]))
    return "\n".join(lines)
