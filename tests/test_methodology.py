import json

from novel_drama_engine.methodology import (
    extract_method_cards,
    load_methodology_cards,
    render_methodology_context,
    retrieve_methodology_context,
)
from novel_drama_engine.models import (
    AdaptationIntensity,
    MethodologyCard,
    MethodologySource,
    MethodologyStage,
    MethodologyStatus,
    SourceStrengthLevel,
    SourceStrengthProfile,
)


def strong_profile() -> SourceStrengthProfile:
    return SourceStrengthProfile(
        conflict_strength=9,
        hook_strength=9,
        character_tag_strength=8,
        emotion_asset_strength=9,
        signature_scene_strength=10,
        visualization_readiness=8,
        overall_level=SourceStrengthLevel.STRONG,
        recommended_intensity=AdaptationIntensity.LIGHT,
        reasons=["原文已有强钩子。"],
    )


def test_extract_method_cards_keeps_new_cards_draft_by_default():
    source = MethodologySource(
        id="method_source_001",
        title="强原文轻改 SOP",
        source_type="sop",
        raw_text="强原文要轻改，保留名场面、主动方和因果顺序。",
    )

    cards = extract_method_cards(source)

    assert len(cards) == 1
    assert cards[0].status == MethodologyStatus.DRAFT
    assert cards[0].category == "source_fidelity"
    assert MethodologyStage.SCRIPT_GENERATION in cards[0].applies_to_stage


def test_load_methodology_cards_reads_json_array(tmp_path):
    path = tmp_path / "cards.json"
    path.write_text(
        json.dumps(
            [
                {
                    "id": "card_001",
                    "source_id": "source_001",
                    "name": "强原文轻改规则",
                    "category": "source_fidelity",
                    "applies_to_channel": ["female"],
                    "applies_to_genre": ["identity"],
                    "applies_to_stage": ["script_generation"],
                    "trigger": "强原文",
                    "generation_rule": "轻改。",
                    "quality_rule": "改主动方则阻断。",
                    "status": "active",
                }
            ],
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    cards = load_methodology_cards(path)

    assert cards[0].status == MethodologyStatus.ACTIVE
    assert cards[0].applies_to_stage == [MethodologyStage.SCRIPT_GENERATION]


def test_default_methodology_cards_include_dj_project_cards():
    cards = load_methodology_cards()
    ids = {card.id for card in cards}

    assert "method_card_strong_source_light_v1" in ids
    assert "dj_project_channel_mainline_assets_v1" in ids
    assert "dj_project_dialogue_progression_v1" in ids
    assert "dj_project_action_line_micro_arc_v1" in ids
    assert "dj_project_female_script_pattern_v1" in ids
    assert all(card.status == MethodologyStatus.ACTIVE for card in cards)


def test_retrieve_methodology_context_filters_active_stage_channel_and_genre():
    active_card = MethodologyCard(
        id="card_active",
        source_id="source_001",
        name="强原文轻改规则",
        category="source_fidelity",
        applies_to_channel=["female"],
        applies_to_genre=["identity"],
        applies_to_stage=[MethodologyStage.SCRIPT_GENERATION],
        trigger="强原文",
        generation_rule="轻改。",
        quality_rule="改主动方则阻断。",
        status=MethodologyStatus.ACTIVE,
    )
    draft_card = active_card.model_copy(
        update={"id": "card_draft", "status": MethodologyStatus.DRAFT},
    )

    context = retrieve_methodology_context(
        [draft_card, active_card],
        stage=MethodologyStage.SCRIPT_GENERATION,
        channel="女频",
        genre_tags=["真假千金"],
        source_strength_profile=strong_profile(),
    )

    assert [card.id for card in context.cards] == ["card_active"]
    assert context.source_strength_level == SourceStrengthLevel.STRONG
    assert context.adaptation_intensity == AdaptationIntensity.LIGHT


def test_retrieve_methodology_context_prioritizes_script_level_dj_cards():
    cards = load_methodology_cards()

    context = retrieve_methodology_context(
        cards,
        stage=MethodologyStage.SCRIPT_GENERATION,
        channel="female",
        genre_tags=["identity"],
        source_strength_profile=strong_profile(),
    )

    names = [card.name for card in context.cards]
    assert names[0] == "强原文轻改规则"
    assert "动作行三层结构与微型叙事弧" in names
    assert "功能台词与递进论证弧" in names


def test_render_methodology_context_is_internal_and_actionable():
    card = MethodologyCard(
        id="card_active",
        source_id="source_001",
        name="强原文轻改规则",
        category="source_fidelity",
        applies_to_channel=["female"],
        applies_to_genre=["identity"],
        applies_to_stage=[MethodologyStage.SCRIPT_GENERATION],
        trigger="强原文",
        generation_rule="轻改。",
        quality_rule="改主动方则阻断。",
        status=MethodologyStatus.ACTIVE,
    )
    context = retrieve_methodology_context(
        [card],
        stage=MethodologyStage.SCRIPT_GENERATION,
        channel="female",
        genre_tags=["identity"],
        source_strength_profile=strong_profile(),
    )

    rendered = render_methodology_context(context)

    assert "内部方法论卡" in rendered
    assert "强原文轻改规则" in rendered
    assert "生成规则" in rendered
    assert "质检规则" in rendered
    assert "用户选择方法论" not in rendered
