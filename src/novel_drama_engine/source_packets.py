from __future__ import annotations

import os
import re
from collections.abc import Iterable

from novel_drama_engine.models import (
    EpisodeContext,
    EpisodeDramaPlan,
    EpisodeHandoff,
    EpisodeScript,
    EpisodeSourceMapping,
    EpisodeSourcePacket,
    EpisodeSourcePackets,
    SeriesEpisodeOutline,
    SeriesStructurePlan,
    EpisodePlan,
    StoryBible,
)


DEFAULT_EXCERPT_CHARS = 12000
FORBIDDEN_RULE_NOISE = (
    "不得",
    "不能",
    "禁止",
    "不要",
    "新增",
    "加入",
    "添加",
    "改成",
    "提前",
    "泄露",
    "公开",
)


def _max_excerpt_chars() -> int:
    raw = os.environ.get("NOVEL_DRAMA_SOURCE_PACKET_CHARS", str(DEFAULT_EXCERPT_CHARS))
    try:
        return max(2000, int(raw))
    except ValueError:
        return DEFAULT_EXCERPT_CHARS


def _episode_numbers_from_range(target_episode_range: str) -> list[int]:
    match = re.fullmatch(r"EP(\d+)(?:-EP(\d+))?", target_episode_range.strip())
    if not match:
        return []
    start = int(match.group(1))
    end = int(match.group(2) or match.group(1))
    if end < start:
        return []
    return list(range(start, end + 1))


def _target_episode_number(value: str | int | None) -> int | None:
    if isinstance(value, int):
        return value
    if not isinstance(value, str):
        return None
    match = re.search(r"(?:EP|E|第)?\s*0*(\d{1,3})\s*(?:集)?", value, re.IGNORECASE)
    if not match:
        return None
    return int(match.group(1))


def _split_assets(value: list[str] | str | None) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    return [
        item.strip()
        for item in re.split(r"[、,，;；\n]", value)
        if item.strip()
    ]


def _dedupe(items: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        normalized = " ".join(str(item).split())
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        result.append(normalized)
    return result


def _normalize_for_match(value: str) -> str:
    return re.sub(r"[\W_]+", "", value, flags=re.UNICODE).lower()


def _packet_support_terms(packet: EpisodeSourcePacket) -> list[str]:
    terms = [
        packet.source_anchor,
        *packet.c0_facts,
        *packet.c1_must_keep_assets,
        *packet.golden_lines,
    ]
    normalized: list[str] = []
    for term in terms:
        item = _normalize_for_match(term)
        if len(item) >= 2:
            normalized.append(item)
    return _dedupe(normalized)


def _supported_by_packet(asset: str, packet: EpisodeSourcePacket) -> bool:
    normalized_asset = _normalize_for_match(asset)
    if len(normalized_asset) < 2:
        return False
    normalized_excerpt = _normalize_for_match(packet.source_excerpt)
    if normalized_asset in normalized_excerpt:
        return True
    return any(
        term in normalized_asset or normalized_asset in term
        for term in _packet_support_terms(packet)
    )


def _filter_plan_assets(
    assets: list[str],
    packet: EpisodeSourcePacket | None,
) -> list[str]:
    if packet is None:
        return assets
    return [asset for asset in assets if _supported_by_packet(asset, packet)]


def _source_snippets(packet: EpisodeSourcePacket) -> list[str]:
    candidates = [
        *packet.c1_must_keep_assets,
        *packet.c0_facts,
        packet.source_anchor,
        *re.split(r"[。！？!?；;\n]+", packet.source_excerpt),
    ]
    return [
        item
        for item in _dedupe(candidate.strip(" \t\r\n。！？!?；;") for candidate in candidates)
        if item
    ]


def _fill_with_source_grounded_items(
    items: list[str],
    *,
    packet: EpisodeSourcePacket | None,
    min_length: int,
    label: str,
) -> list[str]:
    if len(items) >= min_length or packet is None:
        return items
    filled = list(items)
    for snippet in _source_snippets(packet):
        candidate = f"{label}：{snippet}。"
        if candidate not in filled:
            filled.append(candidate)
        if len(filled) >= min_length:
            break
    while len(filled) < min_length:
        fallback = f"{label}：只使用当前集原文可见事件，不借用后续集资产。"
        candidate = fallback if fallback not in filled else f"{fallback}#{len(filled) + 1}"
        filled.append(candidate)
    return filled


EPISODE_HEADING_RE = re.compile(
    r"(?im)^(?:\s{0,3}(?:#{1,6}\s*)?)"
    r"(?:EP|E|Episode|第)\s*0*(\d{1,3})\s*(?:集|章)?(?:\b|[：:.\-、\s])"
)


def _heading_sections(source_text: str) -> dict[int, tuple[int, int]]:
    matches = list(EPISODE_HEADING_RE.finditer(source_text))
    sections: dict[int, tuple[int, int]] = {}
    for index, match in enumerate(matches):
        episode = int(match.group(1))
        start = match.start()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(source_text)
        sections.setdefault(episode, (start, end))
    return sections


def _compact(text: str, max_chars: int) -> str:
    stripped = text.strip()
    if len(stripped) <= max_chars:
        return stripped
    head = max_chars * 2 // 3
    tail = max_chars - head
    return (
        stripped[:head].rstrip()
        + "\n\n...[中间原文已压缩，保留首尾承接]...\n\n"
        + stripped[-tail:].lstrip()
    )


def _window(source_text: str, start: int, end: int, max_chars: int) -> str:
    if end <= start:
        end = start + 1
    span = end - start
    if span >= max_chars:
        return _compact(source_text[start:end], max_chars)
    padding = max(0, (max_chars - span) // 2)
    left = max(0, start - padding)
    right = min(len(source_text), end + padding)
    return _compact(source_text[left:right], max_chars)


def _find_asset_window(
    source_text: str,
    assets: list[str],
    max_chars: int,
) -> str | None:
    positions: list[tuple[int, int]] = []
    for asset in assets:
        candidate = asset.strip()
        if len(candidate) < 4:
            continue
        found = source_text.find(candidate)
        if found >= 0:
            positions.append((found, found + len(candidate)))
    if not positions:
        return None
    return _window(source_text, min(pos[0] for pos in positions), max(pos[1] for pos in positions), max_chars)


def _proportional_excerpt(
    source_text: str,
    *,
    episode: int,
    target_episode_count: int | None,
    fallback_episode_count: int,
    max_chars: int,
) -> str:
    total_episodes = max(target_episode_count or fallback_episode_count, episode, 1)
    length = len(source_text)
    start = int(length * (episode - 1) / total_episodes)
    end = int(length * episode / total_episodes)
    overlap = min(1200, max_chars // 5)
    return _compact(source_text[max(0, start - overlap) : min(length, end + overlap)], max_chars)


def _mapping_for_episode(
    mappings: list[EpisodeSourceMapping],
    episode: int,
) -> EpisodeSourceMapping | None:
    explicit = [
        mapping
        for mapping in mappings
        if _target_episode_number(mapping.target_episode) == episode
    ]
    if explicit:
        return explicit[0]
    for mapping in mappings:
        if re.search(rf"\bEP\s*0*{episode}\b|第\s*{episode}\s*集", mapping.source, re.IGNORECASE):
            return mapping
    return None


def _normalized_contract_text(text: str) -> str:
    normalized = re.sub(r"\s+", "", text.strip())
    for token in FORBIDDEN_RULE_NOISE:
        normalized = normalized.replace(token, "")
    return re.sub(r"[，。、“”‘’：:；;,.!?！？\-—_（）()《》<>]", "", normalized)


def _source_packet_required_assets(
    episode_source_packets: EpisodeSourcePackets,
) -> list[str]:
    assets: list[str] = []
    for packet in episode_source_packets.packets:
        assets.extend(
            [
                *packet.c1_must_keep_assets,
                *packet.c2_visual_assets,
                *packet.golden_lines,
            ]
        )
    return list(dict.fromkeys(asset.strip() for asset in assets if asset.strip()))


def _rule_overlaps_required_asset(rule: str, required_assets: list[str]) -> bool:
    normalized_rule = _normalized_contract_text(rule)
    if len(normalized_rule) < 2:
        return False
    for asset in required_assets:
        normalized_asset = _normalized_contract_text(asset)
        if len(normalized_asset) < 2:
            continue
        if normalized_asset in normalized_rule or normalized_rule in normalized_asset:
            return True
    return False


def story_bible_source_packet_conflicts(
    story_bible: StoryBible,
    episode_source_packets: EpisodeSourcePackets,
) -> list[str]:
    required_assets = _source_packet_required_assets(episode_source_packets)
    return [
        rule
        for rule in story_bible.forbidden_changes
        if _rule_overlaps_required_asset(rule, required_assets)
    ]


def normalize_story_bible_against_source_packets(
    story_bible: StoryBible,
    episode_source_packets: EpisodeSourcePackets,
) -> StoryBible:
    conflicts = set(
        story_bible_source_packet_conflicts(story_bible, episode_source_packets)
    )
    if not conflicts:
        return story_bible
    return story_bible.model_copy(
        update={
            "forbidden_changes": [
                rule for rule in story_bible.forbidden_changes if rule not in conflicts
            ]
        }
    )


def _outline_for_episode(
    series_structure_plan: SeriesStructurePlan | None,
    episode: int,
) -> SeriesEpisodeOutline | None:
    if series_structure_plan is None:
        return None
    return next(
        (outline for outline in series_structure_plan.episode_outlines if outline.episode == episode),
        None,
    )


def _plan_for_episode(
    episode_plan: EpisodePlan | None,
    episode: int,
) -> EpisodeDramaPlan | None:
    if episode_plan is None:
        return None
    return next((plan for plan in episode_plan.episodes if plan.episode == episode), None)


def build_episode_source_packets(
    *,
    source_text: str,
    episode_context: EpisodeContext,
    episode_plan: EpisodePlan | None = None,
    series_structure_plan: SeriesStructurePlan | None = None,
    target_episode_count: int | None = None,
) -> EpisodeSourcePackets:
    episode_numbers = _episode_numbers_from_range(episode_context.target_episode_range)
    if not episode_numbers:
        episode_numbers = list(range(1, 2))
    max_chars = _max_excerpt_chars()
    heading_sections = _heading_sections(source_text)
    fallback_count = len(episode_numbers)
    packets: list[EpisodeSourcePacket] = []

    for episode in episode_numbers:
        mapping = _mapping_for_episode(episode_context.source_to_episode_mapping, episode)
        outline = _outline_for_episode(series_structure_plan, episode)
        retained_assets = _split_assets(mapping.retained_assets if mapping else None)
        c1_assets = _dedupe(retained_assets)
        source_anchor = (
            (outline.source_anchor if outline else "")
            or (mapping.source if mapping else "")
            or f"EP{episode:02d}"
        )

        if episode in heading_sections:
            start, end = heading_sections[episode]
            source_excerpt = _compact(source_text[start:end], max_chars)
        else:
            source_excerpt = _find_asset_window(
                source_text,
                [source_anchor, *(c1_assets or [])],
                max_chars,
            ) or _proportional_excerpt(
                source_text,
                episode=episode,
                target_episode_count=target_episode_count
                or series_structure_plan.target_episode_count
                if series_structure_plan
                else target_episode_count,
                fallback_episode_count=fallback_count,
                max_chars=max_chars,
            )

        packets.append(
            EpisodeSourcePacket(
                episode=episode,
                source_anchor=source_anchor,
                source_excerpt=source_excerpt,
                c0_facts=_dedupe(
                    [
                        mapping.information_increment if mapping else "",
                        outline.information_increment if outline else "",
                    ]
                ),
                c1_must_keep_assets=c1_assets,
                c2_visual_assets=_dedupe(
                    [
                        mapping.adaptation_action if mapping else "",
                    ]
                ),
                c3_compress_assets=_dedupe(
                    [
                        *(episode_context.adaptation_actions or []),
                        *(series_structure_plan.forbidden_slowdowns if series_structure_plan else []),
                    ]
                ),
                c4_forbidden_additions=_dedupe(
                    [
                        *(episode_context.forbidden_reveals or []),
                    ]
                ),
                golden_lines=_dedupe(
                    [
                        outline.ending_hook if outline else "",
                    ]
                ),
                handoff_requirement=(
                    outline.ending_hook
                    if outline
                    else None
                ),
            )
        )

    return EpisodeSourcePackets(packets=packets)


def sanitize_episode_plan_against_source_packets(
    episode_plan: EpisodePlan,
    packets: EpisodeSourcePackets,
) -> EpisodePlan:
    """Drop plan assets that cannot be traced to the current episode source packet."""
    packets_by_episode = {packet.episode: packet for packet in packets.packets}
    episodes: list[EpisodeDramaPlan] = []
    for plan in episode_plan.episodes:
        packet = packets_by_episode.get(plan.episode)
        physical_action_chain = _fill_with_source_grounded_items(
            _filter_plan_assets(plan.physical_action_chain, packet),
            packet=packet,
            min_length=3,
            label="当前集原文动作",
        )
        scene_dynamics = _fill_with_source_grounded_items(
            _filter_plan_assets(plan.scene_dynamics, packet),
            packet=packet,
            min_length=2,
            label="当前集场面调度",
        )
        plan_data = plan.model_dump()
        plan_data.update(
            {
                "source_assets_to_keep": _filter_plan_assets(
                    plan.source_assets_to_keep,
                    packet,
                ),
                "physical_action_chain": physical_action_chain,
                "scene_dynamics": scene_dynamics,
            }
        )
        episodes.append(EpisodeDramaPlan.model_validate(plan_data))
    episode_plan_data = episode_plan.model_dump()
    episode_plan_data["episodes"] = [episode.model_dump() for episode in episodes]
    return EpisodePlan.model_validate(episode_plan_data)


def packet_for_episode(
    packets: EpisodeSourcePackets | None,
    episode: int,
) -> EpisodeSourcePacket | None:
    if packets is None:
        return None
    return next((packet for packet in packets.packets if packet.episode == episode), None)


def handoff_from_episode(episode: EpisodeScript | None) -> EpisodeHandoff | None:
    if episode is None:
        return None
    final_lines = [
        line.text
        for scene in episode.scenes[-1:]
        for line in scene.lines[-10:]
        if line.text.strip()
    ]
    return EpisodeHandoff(
        previous_episode=episode.episode,
        previous_title=episode.title,
        previous_cliffhanger=episode.cliffhanger,
        previous_final_lines=final_lines,
        previous_state_update=episode.state_update,
    )
