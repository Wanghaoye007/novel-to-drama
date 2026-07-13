from __future__ import annotations

from hashlib import sha256
import re

from novel_drama_engine.models import (
    EpisodeSourcePacket,
    EpisodeSourcePackets,
    SourceFact,
    SourceFactLedger,
    SourceSpan,
)


_PUNCTUATION_RE = re.compile(r"[\s\W_]+", flags=re.UNICODE)
_QUALIFIER_RE = re.compile(r"(?:主动|此前|当众|已经|早就|立刻|马上|突然|终于)")
_KNOWLEDGE_RE = re.compile(r"(?:知道|不知|不清楚|以为|误会|秘密|真相|身份)")
_TIMELINE_RE = re.compile(r"(?:之前|之后|提前|随后|当场|早就|终于|此时|立刻)")
_ITEM_RE = re.compile(r"(?:戒指|钥匙|合同|协议|蛋糕|照片|录音|手机|玉佩|信|文件)")


def _normalized(value: str) -> str:
    return _PUNCTUATION_RE.sub("", value).lower()


def _support_ngrams(value: str) -> set[str]:
    compact = _normalized(_QUALIFIER_RE.sub("", value))
    terms: set[str] = set()
    for chunk in re.findall(r"[\u4e00-\u9fff]{2,}", compact):
        for size in (3, 2):
            for index in range(max(0, len(chunk) - size + 1)):
                terms.add(chunk[index : index + size])
    return terms


def _supported_by_span(content: str, span_text: str) -> bool:
    normalized_content = _normalized(content)
    normalized_span = _normalized(span_text)
    if not normalized_content or not normalized_span:
        return False
    if normalized_content in normalized_span:
        return True
    terms = _support_ngrams(content)
    if not terms:
        return False
    matches = {term for term in terms if term in normalized_span}
    return len(matches) >= 2 and len(matches) / len(terms) >= 0.25


def _span_for_packet(source_text: str, packet: EpisodeSourcePacket) -> SourceSpan:
    source_start = packet.source_start
    source_end = packet.source_end
    if (
        source_start is None
        or source_end is None
        or source_start < 0
        or source_end <= source_start
        or source_end > len(source_text)
    ):
        source_start = source_text.find(packet.source_excerpt)
        source_end = (
            source_start + len(packet.source_excerpt)
            if source_start >= 0
            else 0
        )
    text = (
        source_text[source_start:source_end]
        if source_start is not None and source_start >= 0 and source_end is not None
        else packet.source_excerpt
    )
    if not text.strip():
        text = packet.source_excerpt
        source_start = 0
        source_end = len(text)
    return SourceSpan(
        span_id=f"S-EP{packet.episode:02d}",
        episode=packet.episode,
        start=source_start,
        end=source_end,
        text=text,
    )


def _fact_type(category: str, content: str) -> str:
    if _KNOWLEDGE_RE.search(content):
        return "knowledge"
    if _TIMELINE_RE.search(content):
        return "timeline"
    if category == "C1" and _ITEM_RE.search(content):
        return "item"
    return "event"


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
    spans = [_span_for_packet(source_text, packet) for packet in packets.packets]
    span_by_episode = {span.episode: span for span in spans}
    category_counts: dict[tuple[int, str], int] = {}
    facts: list[SourceFact] = []

    for packet in packets.packets:
        span = span_by_episode[packet.episode]
        for category, content in _packet_candidates(packet):
            if not _supported_by_span(content, span.text):
                continue
            category_counts[(packet.episode, category)] = (
                category_counts.get((packet.episode, category), 0) + 1
            )
            facts.append(
                SourceFact(
                    fact_id=(
                        f"F-EP{packet.episode:02d}-{category}-"
                        f"{category_counts[(packet.episode, category)]:02d}"
                    ),
                    episode=packet.episode,
                    content=content,
                    source_span_ids=[span.span_id],
                    fact_type=_fact_type(category, content),
                    confidence=1.0,
                    status="source_confirmed",
                )
            )

    return SourceFactLedger(
        source_hash=sha256(source_text.encode("utf-8")).hexdigest(),
        spans=spans,
        facts=facts,
    )


def facts_for_episode(ledger: SourceFactLedger, episode: int) -> list[SourceFact]:
    return [fact for fact in ledger.facts if fact.episode == episode]
