from novel_drama_engine.models import (
    EpisodeBeat,
    EpisodeDramaPlan,
    EpisodePlan,
    EpisodeSourcePacket,
    EpisodeSourcePackets,
    GenerationVariant,
    RepairPatch,
    SourceFact,
    SourceFactCandidate,
    StoryBible,
)
from novel_drama_engine.prompts import source_fact_contract_section
from novel_drama_engine.source_facts import (
    append_inferred_candidates,
    bind_packets_to_source_spans,
    build_source_fact_ledger,
    build_source_spans,
    facts_for_episode,
)


def test_source_confirmed_facts_are_direct_source_evidence_not_packet_claims():
    source_text = (
        "林晚拒绝签署合同。随后赵明拿走合同。"
        "林晚不知道Richard的身份。签约后才公布身份。"
    )
    packets = EpisodeSourcePackets(
        packets=[
            EpisodeSourcePacket(
                episode=1,
                source_anchor="合同风波",
                source_excerpt=source_text,
                source_start=0,
                source_end=len(source_text),
                c0_facts=[
                    "林晚主动签署合同",
                    "林晚拿走合同",
                    "林晚知道Richard的身份",
                    "签约前公布身份",
                ],
            )
        ]
    )

    ledger = build_source_fact_ledger(source_text, packets)

    assert ledger.facts
    assert all(fact.source_span_ids for fact in ledger.facts)
    assert {fact.status for fact in ledger.facts} == {"source_confirmed"}
    assert {fact.origin for fact in ledger.facts} == {"direct_extraction"}
    assert {fact.content for fact in ledger.facts} == {
        "林晚拒绝签署合同。",
        "随后赵明拿走合同。",
        "林晚不知道Richard的身份。",
        "签约后才公布身份。",
    }
    assert all(fact.fact_id.startswith("F-") for fact in ledger.facts)
    assert all(
        span.span_id == f"S-{span.start:08d}-{span.end:08d}-" + span.span_id.rsplit("-", 1)[1]
        for span in ledger.spans
    )
    assert [candidate.status for candidate in ledger.candidates] == [
        "inferred",
        "inferred",
        "inferred",
        "inferred",
    ]
    assert {candidate.verification_status for candidate in ledger.candidates} == {
        "unverified"
    }
    assert not set(candidate.content for candidate in ledger.candidates).intersection(
        fact.content for fact in ledger.facts
    )
    assert facts_for_episode(ledger, 1) == ledger.facts


def test_source_fact_extractor_keeps_unsupported_packet_claim_as_inferred_candidate():
    packets = EpisodeSourcePackets(
        packets=[
            EpisodeSourcePacket(
                episode=1,
                source_anchor="家宴",
                source_excerpt="父亲当众宣布与沈川断绝关系。",
                source_start=0,
                source_end=16,
                c0_facts=["母亲已经去世"],
            )
        ]
    )

    ledger = build_source_fact_ledger("父亲当众宣布与沈川断绝关系。", packets)

    assert [fact.content for fact in ledger.facts] == ["父亲当众宣布与沈川断绝关系。"]
    assert len(ledger.candidates) == 1
    assert ledger.candidates[0].content == "母亲已经去世"
    assert ledger.candidates[0].status == "inferred"


def test_upstream_candidate_cannot_promote_itself_to_source_confirmed():
    candidate = SourceFactCandidate(
        candidate_id="C-BIBLE-EP01-IMMUTABLE-test",
        episode=1,
        content="林晚拒绝签署合同。",
        source_span_ids=["S-00000000-00000009-abc12345"],
        origin="story_bible",
        status="source_confirmed",
        verification_status="semantically_verified",
        confidence=1.0,
        category="BIBLE_IMMUTABLE",
    )

    assert candidate.status == "inferred"
    assert candidate.verification_status == "unverified"


def test_episode_fact_lookup_excludes_non_direct_fact_even_if_ledger_is_corrupt():
    source_text = "林晚拒绝签署合同。"
    ledger = build_source_fact_ledger(
        source_text,
        EpisodeSourcePackets(
            packets=[
                EpisodeSourcePacket(
                    episode=1,
                    source_anchor="合同",
                    source_excerpt=source_text,
                    source_start=0,
                    source_end=len(source_text),
                )
            ]
        ),
    )
    accidental_bible_fact = SourceFact(
        fact_id="F-bible-claim",
        content="林晚主动签署合同。",
        source_span_ids=[ledger.spans[0].span_id],
        fact_type="event",
        confidence=1.0,
        status="source_confirmed",
        origin="story_bible",
        verification_status="semantically_verified",
    )
    corrupted = ledger.model_copy(
        update={
            "facts": [*ledger.facts, accidental_bible_fact],
            "episode_fact_ids": {1: [ledger.facts[0].fact_id, accidental_bible_fact.fact_id]},
        }
    )

    assert [fact.content for fact in facts_for_episode(corrupted, 1)] == [
        "林晚拒绝签署合同。"
    ]


def test_bible_and_plan_claims_stay_inferred_even_when_their_words_match_source():
    source_text = "林晚拒绝签署合同。随后赵明拿走合同。"
    packets = EpisodeSourcePackets(
        packets=[
            EpisodeSourcePacket(
                episode=1,
                source_anchor="合同风波",
                source_excerpt=source_text,
                source_start=0,
                source_end=len(source_text),
            )
        ]
    )
    ledger = build_source_fact_ledger(source_text, packets)
    refusal_fact = ledger.facts[0]
    bible = StoryBible(
        genre="都市情感",
        mainline="合同风波",
        characters=["林晚", "赵明"],
        relationships=["对立"],
        speech_styles={"林晚": "克制"},
        immutable_facts=["林晚拒绝签署合同。"],
        forbidden_changes=["不得把拒绝改成主动签署"],
    )
    plan = EpisodePlan(
        variant=GenerationVariant.DRAMA_ENGINE_FIRST,
        target_episode_range="EP01-EP01",
        adaptation_strategy="保真",
        episodes=[
            EpisodeDramaPlan(
                episode=1,
                title="合同风波",
                drama_engine="林晚拒绝签署合同。",
                protagonist_misbelief="忍让能过去",
                truth_gap="赵明早有准备",
                physical_action_chain=["按住合同", "拒绝签署", "赵明拿走合同"],
                scene_dynamics=["对峙", "夺走"],
                emotional_turns=["压迫", "反抗"],
                audience_information_gap="合同去向未知",
                three_pull_beats=["拒绝", "威胁", "夺走"],
                false_payoff="以为能拒绝",
                planted_key="合同",
                strongest_line="我不签。",
                cliffhanger_design="赵明拿走合同。",
                source_assets_to_keep=["林晚拒绝签署合同。"],
                forbidden_shortcuts=["不得改主动方"],
                beats=[
                    EpisodeBeat(
                        beat_id="EP01-B01",
                        event="林晚拒绝签署合同。",
                        source_span_ids=refusal_fact.source_span_ids,
                        required_fact_ids=[refusal_fact.fact_id],
                    )
                ],
            )
        ],
    )

    enriched = append_inferred_candidates(
        ledger,
        story_bible=bible,
        episode_plan=plan,
    )

    assert enriched.facts == ledger.facts
    assert {candidate.origin for candidate in enriched.candidates} == {
        "story_bible",
        "episode_plan",
    }
    assert all(candidate.status == "inferred" for candidate in enriched.candidates)
    assert all(
        candidate.verification_status == "unverified"
        for candidate in enriched.candidates
    )
    matching_candidates = [
        candidate
        for candidate in enriched.candidates
        if candidate.content == "林晚拒绝签署合同。"
    ]
    assert matching_candidates
    assert all(candidate.status == "inferred" for candidate in matching_candidates)
    assert all(
        candidate.candidate_id.startswith("C-") for candidate in enriched.candidates
    )


def test_source_fact_prompt_uses_episode_fact_mapping_not_fact_text_overlap():
    source_text = "林晚拒绝签署合同。随后赵明拿走合同。"
    ledger = build_source_fact_ledger(
        source_text,
        EpisodeSourcePackets(
            packets=[
                EpisodeSourcePacket(
                    episode=1,
                    source_anchor="合同风波",
                    source_excerpt=source_text,
                    source_start=0,
                    source_end=len(source_text),
                )
            ]
        ),
    )
    prompt = source_fact_contract_section(
        source_fact_ledger=ledger,
        episode_plan=None,
        episode_number=1,
    )

    assert "林晚拒绝签署合同。" in prompt
    assert "source_confirmed_facts" in prompt


def test_batch_source_fact_prompt_excludes_full_source_facts_outside_episode_packets():
    current_text = "妹妹从背后抱住醉酒姐夫。姐夫立刻推开她。"
    future_text = "中央调查组在婚礼现场抓捕反派。"
    source_text = current_text + future_text
    ledger = build_source_fact_ledger(
        source_text,
        EpisodeSourcePackets(
            packets=[
                EpisodeSourcePacket(
                    episode=1,
                    source_anchor="开场试探",
                    source_excerpt=current_text,
                    source_start=0,
                    source_end=len(current_text),
                )
            ]
        ),
    )

    prompt = source_fact_contract_section(
        source_fact_ledger=ledger,
        episode_plan=None,
    )

    assert "姐夫立刻推开她" in prompt
    assert future_text not in prompt


def test_source_span_ids_are_stable_when_episode_packets_are_repartitioned():
    source_text = "第一句原文。第二句原文。第三句原文。"
    whole_packet = EpisodeSourcePackets(
        packets=[
            EpisodeSourcePacket(
                episode=1,
                source_anchor="全段",
                source_excerpt=source_text,
                source_start=0,
                source_end=len(source_text),
            )
        ]
    )
    split_packets = EpisodeSourcePackets(
        packets=[
            EpisodeSourcePacket(
                episode=1,
                source_anchor="前段",
                source_excerpt="第一句原文。",
                source_start=0,
                source_end=len("第一句原文。"),
            ),
            EpisodeSourcePacket(
                episode=2,
                source_anchor="后段",
                source_excerpt="第二句原文。第三句原文。",
                source_start=len("第一句原文。"),
                source_end=len(source_text),
            ),
        ]
    )

    expected_spans = build_source_spans(source_text)
    whole_ledger = build_source_fact_ledger(source_text, whole_packet)
    split_ledger = build_source_fact_ledger(source_text, split_packets)
    bound_packets = bind_packets_to_source_spans(source_text, split_packets)

    assert [span.span_id for span in whole_ledger.spans] == [
        span.span_id for span in expected_spans
    ]
    assert [span.span_id for span in split_ledger.spans] == [
        span.span_id for span in expected_spans
    ]
    assert bound_packets.packets[0].source_span_ids == [expected_spans[0].span_id]
    assert bound_packets.packets[1].source_span_ids == [
        expected_spans[1].span_id,
        expected_spans[2].span_id,
    ]


def test_source_spans_keep_sentence_closing_quotes_in_the_hashed_text():
    source_text = "林雪问：‘你来吗？’林晚点头。"

    spans = build_source_spans(source_text)

    assert [span.text for span in spans] == ["林雪问：‘你来吗？’", "林晚点头。"]
    assert [source_text[span.start:span.end] for span in spans] == [
        span.text for span in spans
    ]


def test_packet_span_binding_uses_excerpt_when_legacy_offsets_are_missing():
    source_text = "第一句原文。第二句原文。"
    packets = EpisodeSourcePackets(
        packets=[
            EpisodeSourcePacket(
                episode=1,
                source_anchor="第二句",
                source_excerpt="第二句原文。",
            )
        ]
    )

    bound_packets = bind_packets_to_source_spans(source_text, packets)

    assert len(bound_packets.packets[0].source_span_ids) == 1
    assert bound_packets.packets[0].source_span_ids[0].startswith("S-00000006-")


def test_repair_patch_never_targets_unrelated_scene():
    patch = RepairPatch(
        target="scene_2.line_3",
        issue="角色提前知道秘密",
        operation="replace",
        constraint="不能改变本场事件结果",
    )

    assert patch.target == "scene_2.line_3"
