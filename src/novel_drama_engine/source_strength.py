from __future__ import annotations

from novel_drama_engine.models import (
    AdaptationIntensity,
    SourceAnalysis,
    SourceStrengthLevel,
    SourceStrengthProfile,
    ViralAssetReport,
)

STRONG_HOOK_TOKENS = (
    "羞辱",
    "背叛",
    "当众",
    "镜头",
    "获奖",
    "解约",
    "危险",
    "暧昧",
    "压迫",
    "身份",
    "真相",
    "反转",
)


def _score_count(count: int, *, strong_at: int) -> int:
    if count <= 0:
        return 0
    return min(10, round((count / strong_at) * 10))


def _token_score(items: list[str], tokens: tuple[str, ...]) -> int:
    text = "\n".join(items)
    hits = sum(1 for token in tokens if token in text)
    return min(10, hits * 2)


def classify_source_strength(
    source_analysis: SourceAnalysis,
    viral_asset_report: ViralAssetReport | None = None,
) -> SourceStrengthProfile:
    conflict_strength = max(
        _score_count(len(source_analysis.conflicts), strong_at=4),
        _token_score(source_analysis.conflicts, STRONG_HOOK_TOKENS),
    )
    hook_strength = max(
        _score_count(len(source_analysis.candidate_hooks), strong_at=2),
        _token_score(source_analysis.candidate_hooks, STRONG_HOOK_TOKENS),
    )
    character_tag_strength = _score_count(len(source_analysis.characters), strong_at=4)
    emotion_asset_strength = _score_count(
        len(viral_asset_report.emotion_curve) if viral_asset_report else 0,
        strong_at=5,
    )
    signature_scene_strength = max(
        _score_count(len(source_analysis.visual_moments), strong_at=4),
        _score_count(
            len(viral_asset_report.signature_scenes) if viral_asset_report else 0,
            strong_at=3,
        ),
    )
    visualization_readiness = _score_count(len(source_analysis.visual_moments), strong_at=5)

    average = round(
        (
            conflict_strength
            + hook_strength
            + character_tag_strength
            + emotion_asset_strength
            + signature_scene_strength
            + visualization_readiness
        )
        / 6
    )
    reasons: list[str] = []
    if hook_strength >= 8:
        reasons.append("原文已有强钩子，优先保护核心张力。")
    if signature_scene_strength >= 8:
        reasons.append("原文已有高价值名场面，适合轻改视听化。")
    if conflict_strength >= 8:
        reasons.append("原文冲突密度高，不应重构主动方和因果链。")
    if average >= 7 or (hook_strength >= 8 and signature_scene_strength >= 8):
        level = SourceStrengthLevel.STRONG
        intensity = AdaptationIntensity.LIGHT
    elif average >= 4:
        level = SourceStrengthLevel.MEDIUM
        intensity = AdaptationIntensity.MEDIUM
        reasons.append("原文有可用设定或冲突，但需要节奏优化。")
    else:
        level = SourceStrengthLevel.WEAK
        intensity = AdaptationIntensity.HEAVY
        reasons.append("原文短剧资产不足，需要更强结构重构。")

    return SourceStrengthProfile(
        conflict_strength=conflict_strength,
        hook_strength=hook_strength,
        character_tag_strength=character_tag_strength,
        emotion_asset_strength=emotion_asset_strength,
        signature_scene_strength=signature_scene_strength,
        visualization_readiness=visualization_readiness,
        overall_level=level,
        recommended_intensity=intensity,
        reasons=reasons,
    )
