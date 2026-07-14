from __future__ import annotations

from hashlib import sha256
import re

from novel_drama_engine.models import (
    EpisodePlan,
    EpisodeSourcePacket,
    EpisodeSourcePackets,
    SourceFact,
    SourceFactCandidate,
    SourceFactLedger,
    SourceSpan,
    StoryBible,
)


_KNOWLEDGE_RE = re.compile(r"(?:知道|不知|不清楚|以为|误会|秘密|真相|身份)")
_TIMELINE_RE = re.compile(r"(?:之前|之后|提前|随后|当场|早就|终于|此时|立刻)")
_ITEM_RE = re.compile(r"(?:戒指|钥匙|合同|协议|蛋糕|照片|录音|手机|玉佩|信|文件)")
_SECRET_RE = re.compile(r"(?:秘密|真相|身份)")
# Keep trailing Chinese quotation/bracket marks with the sentence. Leaving a
# closing quote outside the source evidence changes the text hash and makes a
# human audit look like the quoted line was truncated.
_SENTENCE_RE = re.compile(r"[^。！？!?；;\n]+(?:[。！？!?；;]+[”’」』）】\]]*|$)")


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


def _candidate_id(
    *,
    origin: str,
    episode: int,
    category: str,
    content: str,
) -> str:
    digest = sha256(
        f"{origin}|{episode}|{category}|{content}".encode("utf-8")
    ).hexdigest()[:10]
    return f"C-{origin.upper()}-EP{episode:02d}-{category}-{digest}"


def _candidate(
    *,
    origin: str,
    episode: int,
    category: str,
    content: str,
    source_span_ids: list[str] | None = None,
) -> SourceFactCandidate:
    """Create an audit-only upstream claim.

    SourceFactCandidate is intentionally never promoted through lexical overlap.
    Only direct source spans can produce source_confirmed facts.
    """
    return SourceFactCandidate(
        candidate_id=_candidate_id(
            origin=origin,
            episode=episode,
            category=category,
            content=content,
        ),
        episode=episode,
        content=content,
        source_span_ids=source_span_ids or [],
        origin=origin,  # type: ignore[arg-type]
        verification_status="unverified",
        status="inferred",
        confidence=0.4,
        category=category,
    )


def append_inferred_candidates(
    ledger: SourceFactLedger,
    *,
    story_bible: StoryBible | None = None,
    episode_plan: EpisodePlan | None = None,
) -> SourceFactLedger:
    """Append Bible/Plan interpretations without changing source evidence.

    Packets, the Story Bible, and the episode plan are downstream interpretation
    layers. They may cite a SourceSpan, but they never become source-confirmed
    merely because their wording overlaps with the original text.
    """
    candidates = list(ledger.candidates)
    known_ids = {candidate.candidate_id for candidate in candidates}
    episode_numbers = sorted(ledger.episode_fact_ids)

    def add(candidate: SourceFactCandidate) -> None:
        if candidate.candidate_id not in known_ids:
            candidates.append(candidate)
            known_ids.add(candidate.candidate_id)

    if story_bible is not None:
        # A Bible is global, but the consumer is episode-level. Record its
        # assumptions against every episode instead of inventing a synthetic
        # global SourceFact owner.
        for episode in episode_numbers:
            for fact in story_bible.immutable_facts:
                if fact.strip():
                    add(
                        _candidate(
                            origin="story_bible",
                            episode=episode,
                            category="BIBLE_IMMUTABLE",
                            content=fact.strip(),
                        )
                    )
            for rule in story_bible.forbidden_changes:
                if rule.strip():
                    add(
                        _candidate(
                            origin="story_bible",
                            episode=episode,
                            category="BIBLE_FORBIDDEN",
                            content=rule.strip(),
                        )
                    )

    if episode_plan is not None:
        for plan in episode_plan.episodes:
            for beat in plan.beats:
                if beat.event.strip():
                    add(
                        _candidate(
                            origin="episode_plan",
                            episode=plan.episode,
                            category="PLAN_BEAT",
                            content=beat.event.strip(),
                            source_span_ids=list(beat.source_span_ids),
                        )
                    )
            for asset in plan.source_assets_to_keep:
                if asset.strip():
                    add(
                        _candidate(
                            origin="episode_plan",
                            episode=plan.episode,
                            category="PLAN_ASSET",
                            content=asset.strip(),
                        )
                    )
            for category, content in (
                ("PLAN_DRAMA_ENGINE", plan.drama_engine),
                ("PLAN_CLIFFHANGER", plan.cliffhanger_design),
            ):
                if content.strip():
                    add(
                        _candidate(
                            origin="episode_plan",
                            episode=plan.episode,
                            category=category,
                            content=content.strip(),
                        )
                    )

    return ledger.model_copy(update={"candidates": candidates})


def facts_for_episode(ledger: SourceFactLedger, episode: int) -> list[SourceFact]:
    def is_direct_source_fact(fact: SourceFact) -> bool:
        return (
            fact.status == "source_confirmed"
            and fact.origin == "direct_extraction"
            and bool(fact.source_span_ids)
        )

    if episode in ledger.episode_fact_ids:
        fact_by_id = {fact.fact_id: fact for fact in ledger.facts}
        return [
            fact_by_id[fact_id]
            for fact_id in ledger.episode_fact_ids[episode]
            if fact_id in fact_by_id and is_direct_source_fact(fact_by_id[fact_id])
        ]
    return [
        fact
        for fact in ledger.facts
        if fact.episode == episode and is_direct_source_fact(fact)
    ]
