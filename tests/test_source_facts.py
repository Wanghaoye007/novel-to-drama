from novel_drama_engine.models import (
    EpisodeSourcePacket,
    EpisodeSourcePackets,
    RepairPatch,
)
from novel_drama_engine.source_facts import (
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
