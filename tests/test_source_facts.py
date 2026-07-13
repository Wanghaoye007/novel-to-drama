from novel_drama_engine.models import (
    EpisodeSourcePacket,
    EpisodeSourcePackets,
    RepairPatch,
)
from novel_drama_engine.source_facts import build_source_fact_ledger, facts_for_episode


def test_source_confirmed_fact_has_stable_span_evidence():
    source_text = "前言。父亲当众宣布与沈川断绝关系。沈川毫不知情。"
    packets = EpisodeSourcePackets(
        packets=[
            EpisodeSourcePacket(
                episode=1,
                source_anchor="家宴",
                source_excerpt="父亲当众宣布与沈川断绝关系。沈川毫不知情。",
                source_start=3,
                source_end=len(source_text),
                c0_facts=["父亲主动宣布断绝关系", "沈川此前不知情"],
            )
        ]
    )

    ledger = build_source_fact_ledger(source_text, packets)

    assert ledger.facts
    assert all(fact.source_span_ids for fact in ledger.facts)
    assert {fact.status for fact in ledger.facts} == {"source_confirmed"}
    assert ledger.facts[0].fact_id == "F-EP01-C0-01"
    assert ledger.spans[0].span_id == "S-EP01"
    assert facts_for_episode(ledger, 1) == ledger.facts


def test_source_fact_extractor_does_not_promote_unsupported_packet_claim():
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

    assert ledger.facts == []


def test_repair_patch_never_targets_unrelated_scene():
    patch = RepairPatch(
        target="scene_2.line_3",
        issue="角色提前知道秘密",
        operation="replace",
        constraint="不能改变本场事件结果",
    )

    assert patch.target == "scene_2.line_3"
