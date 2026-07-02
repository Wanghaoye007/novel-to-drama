from novel_drama_engine.models import (
    AdaptationIntensity,
    SourceAnalysis,
    SourceStrengthLevel,
    ViralAssetReport,
)
from novel_drama_engine.source_strength import classify_source_strength


def viral_report(signature_scenes=None, small_highlights=None):
    return ViralAssetReport(
        channel="female",
        genre_tags=["revenge", "identity"],
        core_setting="娱乐圈颁奖礼背叛",
        core_dilemma="女主台下被羞辱，台上替身获奖",
        protagonist_goal="体面离开并完成反击",
        main_conflict="情人背叛与公开羞辱",
        signature_scenes=signature_scenes
        or ["危险暧昧开场", "台上光鲜台下狼狈", "提前准备解约协议"],
        small_highlights=small_highlights
        or ["镜头扫过手", "害怕被拍", "获奖僵住", "心碎 OS", "冷静离开"],
        golden_lines=["给你准备了惊喜"],
        emotion_curve=["危险", "期待", "羞辱", "心碎", "决绝"],
        adaptation_risks=[],
        risk_treatments=[],
        low_value_removal_rules=[],
    )


def test_classify_strong_source_recommends_light_adaptation():
    analysis = SourceAnalysis(
        characters=["林挽清", "路淮北", "许念念"],
        events=["颁奖礼后台暧昧压迫", "许念念获奖", "林挽清早已准备解约"],
        conflicts=["公开背叛", "台上台下强反差", "情人主动羞辱"],
        visual_moments=["抱坐腿上害怕镜头拍到", "台上光鲜台下狼狈", "解约协议放在办公室"],
        low_value_passages=["日常寒暄"],
        candidate_hooks=["谁敢碰她一下", "镜头快扫到两人"],
    )

    profile = classify_source_strength(analysis, viral_report())

    assert profile.overall_level == SourceStrengthLevel.STRONG
    assert profile.recommended_intensity == AdaptationIntensity.LIGHT
    assert profile.hook_strength >= 8
    assert any("强钩子" in reason for reason in profile.reasons)


def test_classify_weak_source_recommends_heavy_adaptation():
    analysis = SourceAnalysis(
        characters=["小夏"],
        events=["她回到家"],
        conflicts=[],
        visual_moments=[],
        low_value_passages=["大量日常吃饭聊天"],
        candidate_hooks=[],
    )

    profile = classify_source_strength(analysis, None)

    assert profile.overall_level == SourceStrengthLevel.WEAK
    assert profile.recommended_intensity == AdaptationIntensity.HEAVY
