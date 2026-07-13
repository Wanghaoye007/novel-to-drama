from __future__ import annotations

from hashlib import sha256
import re

from novel_drama_engine.models import (
    EpisodeSourcePacket,
    EpisodeSourcePackets,
    SourceFact,
    SourceFactCandidate,
    SourceFactLedger,
    SourceSpan,
)


_KNOWLEDGE_RE = re.compile(r"(?:知道|不知|不清楚|以为|误会|秘密|真相|身份)")
_TIMELINE_RE = re.compile(r"(?:之前|之后|提前|随后|当场|早就|终于|此时|立刻)")
_ITEM_RE = re.compile(r"(?:戒指|钥匙|合同|协议|蛋糕|照片|录音|手机|玉佩|信|文件)")
_SECRET_RE = re.compile(r"(?:秘密|真相|身份)")
_SENTENCE_RE = re.compile(r"[^。！？!?；;\n]+(?:[。！？!?；;]+|$)")


def build_source_spans(source_text: str) -> list[SourceSpan]:
    """Split immutable full-source evidence before any episode packet exists."""
    spans: list[SourceSpan] = []
    for match in _SENTENCE_RE.finditer(source_text):
        raw = match.group(0)
        text = raw.strip()
        if not text:
            continue
        leading_whitespace = len(raw) - len(raw.lstrip())
        start = match.start() + leading_whitespace
        end = start + len(text)
        text_hash = sha256(text.encode("utf-8")).hexdigest()[:8]
        spans.append(
            SourceSpan(
                span_id=f"S-{start:08d}-{end:08d}-{text_hash}",
                start=start,
                end=end,
                text=text,
            )
        )
    return spans


def _packet_range(source_text: str, packet: EpisodeSourcePacket) -> tuple[int, int] | None:
    source_start = packet.source_start
    source_end = packet.source_end
    if (
        source_start is not None
        and source_end is not None
        and source_start >= 0
        and source_end > source_start
        and source_end <= len(source_text)
    ):
        return source_start, source_end
    excerpt = packet.source_excerpt.strip()
    if not excerpt:
        return None
    start = source_text.find(excerpt)
    if start < 0:
        return None
    return start, start + len(excerpt)


def bind_packets_to_source_spans(
    source_text: str,
    packets: EpisodeSourcePackets,
    *,
    spans: list[SourceSpan] | None = None,
) -> EpisodeSourcePackets:
    """Return packets that refer to stable source spans, never synthetic EP spans."""
    canonical_spans = spans if spans is not None else build_source_spans(source_text)
    bound_packets: list[EpisodeSourcePacket] = []
    for packet in packets.packets:
        source_range = _packet_range(source_text, packet)
        if source_range is None:
            span_ids: list[str] = []
        else:
            start, end = source_range
            span_ids = [
                span.span_id
                for span in canonical_spans
                if span.start < end and start < span.end
            ]
        bound_packets.append(packet.model_copy(update={"source_span_ids": span_ids}))
    return packets.model_copy(update={"packets": bound_packets})


def _fact_types(content: str) -> list[str]:
    types = ["event"]
    if _KNOWLEDGE_RE.search(content):
        types.append("knowledge")
    if _TIMELINE_RE.search(content):
        types.append("timeline")
    if _ITEM_RE.search(content):
        types.append("item")
    if _SECRET_RE.search(content):
        types.append("secret")
    return types


def _packet_candidates(packet: EpisodeSourcePacket) -> list[tuple[str, str]]:
    candidates: list[tuple[str, str]] = [
        *( ("C0", fact) for fact in packet.c0_facts ),
        *( ("C1", asset) for asset in packet.c1_must_keep_assets ),
    ]
    if packet.active_party:
        candidates.append(("ACTIVE", packet.active_party))
    if packet.key_decision_timing:
        candidates.append(("TIMING", packet.key_decision_timing))
    return [
        (category, content.strip())
        for category, content in candidates
        if content and content.strip()
    ]


def build_source_fact_ledger(
    source_text: str,
    packets: EpisodeSourcePackets,
) -> SourceFactLedger:
    spans = build_source_spans(source_text)
    bound_packets = bind_packets_to_source_spans(source_text, packets, spans=spans)
    fact_by_span_id: dict[str, SourceFact] = {}
    for span in spans:
        fact_types = _fact_types(span.text)
        fact = SourceFact(
            fact_id=f"F-{span.span_id.removeprefix('S-')}",
            content=span.text,
            source_span_ids=[span.span_id],
            fact_type=fact_types[0],
            fact_types=fact_types,
            confidence=1.0,
            status="source_confirmed",
            origin="direct_extraction",
            verification_status="semantically_verified",
        )
        fact_by_span_id[span.span_id] = fact

    category_counts: dict[tuple[int, str], int] = {}
    candidates: list[SourceFactCandidate] = []
    episode_fact_ids: dict[int, list[str]] = {}

    for packet in bound_packets.packets:
        episode_fact_ids[packet.episode] = [
            fact_by_span_id[span_id].fact_id
            for span_id in packet.source_span_ids
            if span_id in fact_by_span_id
        ]
        for category, content in _packet_candidates(packet):
            category_counts[(packet.episode, category)] = (
                category_counts.get((packet.episode, category), 0) + 1
            )
            candidates.append(
                SourceFactCandidate(
                    candidate_id=(
                        f"C-EP{packet.episode:02d}-{category}-"
                        f"{category_counts[(packet.episode, category)]:02d}"
                    ),
                    episode=packet.episode,
                    content=content,
                    source_span_ids=packet.source_span_ids,
                    origin="source_packet",
                    verification_status="unverified",
                    status="inferred",
                    confidence=0.6,
                    category=category,
                )
            )

    return SourceFactLedger(
        source_hash=sha256(source_text.encode("utf-8")).hexdigest(),
        spans=spans,
        facts=list(fact_by_span_id.values()),
        candidates=candidates,
        episode_fact_ids=episode_fact_ids,
    )


def facts_for_episode(ledger: SourceFactLedger, episode: int) -> list[SourceFact]:
    if episode in ledger.episode_fact_ids:
        fact_by_id = {fact.fact_id: fact for fact in ledger.facts}
        return [
            fact_by_id[fact_id]
            for fact_id in ledger.episode_fact_ids[episode]
            if fact_id in fact_by_id
        ]
    return [fact for fact in ledger.facts if fact.episode == episode]
