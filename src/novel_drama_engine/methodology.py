from __future__ import annotations

import json
from pathlib import Path

from novel_drama_engine.models import (
    MethodologyCard,
    MethodologyContext,
    MethodologySource,
    MethodologyStage,
    MethodologyStatus,
    SourceStrengthProfile,
)


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


def extract_method_cards(source: MethodologySource) -> list[MethodologyCard]:
    raw_text = source.raw_text.strip()
    if not raw_text:
        return []

    source_fidelity_tokens = ("强原文", "轻改", "名场面", "主动方", "因果")
    category = (
        "source_fidelity"
        if any(token in raw_text for token in source_fidelity_tokens)
        else "general_adaptation"
    )
    name = "强原文轻改规则" if category == "source_fidelity" else source.title
    trigger = (
        "原文已具备强冲突、强钩子、强反差或高情绪名场面"
        if category == "source_fidelity"
        else "当前阶段需要引用内部方法论"
    )
    generation_rule = (
        "保留原文主动方、因果顺序、名场面和情绪曲线，只做视听化、压缩、镜头补强和短台词化。"
        if category == "source_fidelity"
        else raw_text[:240]
    )
    quality_rule = (
        "如果脚本删除 C1 名场面、改变 C0 主动方、把克制情绪改成歇斯底里或新增 C4 编造道具/动作/狠话，必须 needs_rewrite。"
        if category == "source_fidelity"
        else "检查输出是否遵守该方法论的触发条件和生成规则。"
    )
    stages = (
        [
            MethodologyStage.EPISODE_PLAN,
            MethodologyStage.SCRIPT_GENERATION,
            MethodologyStage.QUALITY_GATE,
        ]
        if category == "source_fidelity"
        else [
            MethodologyStage.EPISODE_CONTEXT,
            MethodologyStage.STORY_BIBLE,
            MethodologyStage.SCRIPT_GENERATION,
            MethodologyStage.QUALITY_GATE,
        ]
    )
    return [
        MethodologyCard(
            id=f"{source.id}_card_001",
            source_id=source.id,
            name=name,
            category=category,
            applies_to_channel=["female", "male", "mixed"],
            applies_to_genre=["revenge", "identity", "billionaire", "unknown"],
            applies_to_stage=stages,
            trigger=trigger,
            generation_rule=generation_rule,
            quality_rule=quality_rule,
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
    limit: int = 5,
) -> MethodologyContext:
    matched = [
        card
        for card in cards
        if _matches(card, stage=stage, channel=channel, genre_tags=genre_tags)
    ]

    def score(card: MethodologyCard) -> tuple[int, int]:
        source_fidelity_bonus = (
            1
            if card.category == "source_fidelity"
            and source_strength_profile.recommended_intensity.value == "light"
            else 0
        )
        stage_specificity = 1 if card.applies_to_stage else 0
        return (source_fidelity_bonus, stage_specificity)

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
