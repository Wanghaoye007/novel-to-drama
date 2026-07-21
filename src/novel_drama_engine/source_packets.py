from __future__ import annotations

import os
import re
import hashlib
from collections.abc import Iterable

from novel_drama_engine.models import (
    EpisodeBeat,
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
    SourcePacketConfidenceItem,
    SourcePacketConfidenceReport,
    StoryBible,
    SourceFactLedger,
)
from novel_drama_engine.source_facts import facts_for_episode


DEFAULT_EXCERPT_CHARS = 12000
DEFAULT_CONFIDENCE_MIN_SOURCE_CHARS = 2000
DEFAULT_MIN_SOURCE_CHARS_PER_TARGET_EPISODE = 160
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
SOURCE_BOUNDARY_ADAPTATION_STRATEGY = (
    "强原文轻改：逐集以当前 source packet/source_excerpt 为唯一剧情边界，"
    "只做视听化、短台词化、压缩和衔接补强；不得跨集前置后文名场面。"
)
SOURCE_BOUNDARY_FORBIDDEN_SHORTCUTS = (
    "不得跨集前置当前 source packet 未出现的名场面、关系进展、证据流程或公开结果。",
    "不得为了爽点改写当前集原文的主动方、因果顺序和决定时机。",
)


def _max_excerpt_chars() -> int:
    raw = os.environ.get("NOVEL_DRAMA_SOURCE_PACKET_CHARS", str(DEFAULT_EXCERPT_CHARS))
    try:
        return max(2000, int(raw))
    except ValueError:
        return DEFAULT_EXCERPT_CHARS


class SourcePacketConfidenceError(ValueError):
    pass


def _confidence_min_source_chars() -> int:
    raw = os.environ.get(
        "NOVEL_DRAMA_SOURCE_PACKET_CONFIDENCE_MIN_CHARS",
        str(DEFAULT_CONFIDENCE_MIN_SOURCE_CHARS),
    )
    try:
        return max(500, int(raw))
    except ValueError:
        return DEFAULT_CONFIDENCE_MIN_SOURCE_CHARS


def _min_source_chars_per_target_episode() -> int:
    raw = os.environ.get(
        "NOVEL_DRAMA_MIN_SOURCE_CHARS_PER_TARGET_EPISODE",
        str(DEFAULT_MIN_SOURCE_CHARS_PER_TARGET_EPISODE),
    )
    try:
        return max(40, int(raw))
    except ValueError:
        return DEFAULT_MIN_SOURCE_CHARS_PER_TARGET_EPISODE


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


GENERIC_CJK_TERMS = {
    "当前",
    "原文",
    "动作",
    "场面",
    "调度",
    "保留",
    "使用",
    "只用",
    "本集",
    "可见",
    "事件",
    "不要",
    "不得",
    "不能",
    "禁止",
    "提前",
    "新增",
    "改成",
    "成为",
    "通过",
    "结果",
    "观众",
    "以为",
}


def _cjk_terms(value: str) -> list[str]:
    terms: set[str] = set()
    for chunk in re.findall(r"[\u4e00-\u9fff]{2,}", value):
        if len(chunk) >= 4 and chunk not in GENERIC_CJK_TERMS:
            terms.add(chunk)
        max_size = min(4, len(chunk))
        for size in range(2, max_size + 1):
            for index in range(0, len(chunk) - size + 1):
                term = chunk[index : index + size]
                if term in GENERIC_CJK_TERMS:
                    continue
                terms.add(term)
    return sorted(terms, key=lambda item: (-len(item), item))


def _supported_by_excerpt(asset: str, source_excerpt: str) -> bool:
    normalized_asset = _normalize_for_match(asset)
    if len(normalized_asset) < 2:
        return False
    normalized_excerpt = _normalize_for_match(source_excerpt)
    if normalized_asset in normalized_excerpt:
        return True
    cjk_terms = _cjk_terms(asset)
    if not cjk_terms:
        return False
    hits = [term for term in cjk_terms if term in source_excerpt]
    return any(len(term) >= 4 for term in hits) or (
        len(hits) / max(len(cjk_terms), 1)
    ) >= 0.2


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
    if _supported_by_excerpt(asset, packet.source_excerpt):
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


def _filter_excerpt_assets(
    assets: list[str],
    source_excerpt: str,
) -> list[str]:
    return [asset for asset in assets if _supported_by_excerpt(asset, source_excerpt)]


def _filter_source_confirmed_assets(
    assets: list[str],
    source_excerpt: str,
) -> list[str]:
    """Keep hard evidence only when the complete normalized claim is in source."""
    normalized_excerpt = _normalize_for_match(source_excerpt)
    return [
        asset
        for asset in assets
        if len(_normalize_for_match(asset)) >= 2
        and _normalize_for_match(asset) in normalized_excerpt
    ]


def _source_snippets(packet: EpisodeSourcePacket) -> list[str]:
    raw_candidates = [
        *packet.c1_must_keep_assets,
        *packet.c0_facts,
        *re.split(r"[。！？!?；;\n]+", packet.source_excerpt),
        packet.source_anchor,
    ]
    candidates: list[str] = []
    for candidate in raw_candidates:
        stripped = candidate.strip(" \t\r\n。！？!?；;")
        if not stripped:
            continue
        if EPISODE_HEADING_RE.match(stripped) or CHAPTER_HEADING_RE.match(stripped):
            continue
        if re.fullmatch(r"#*\s*(?:EP|E|Episode|第)\s*0*\d{1,3}\s*(?:集|章)?", stripped, re.IGNORECASE):
            continue
        candidates.append(stripped)
    return [
        item
        for item in _dedupe(candidates)
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
        candidate = snippet
        if candidate not in filled:
            filled.append(candidate)
        if len(filled) >= min_length:
            break
    while len(filled) < min_length:
        fallback = f"{label}：只使用当前集原文可见事件，不借用后续集资产。"
        candidate = fallback if fallback not in filled else f"{fallback}#{len(filled) + 1}"
        filled.append(candidate)
    return filled


def _first_source_snippet(packet: EpisodeSourcePacket) -> str:
    for snippet in _source_snippets(packet):
        if snippet:
            return snippet
    return f"EP{packet.episode:02d} 当前集原文。"


def _source_grounded_scalar(
    value: str,
    *,
    packet: EpisodeSourcePacket | None,
    label: str,
) -> str:
    if packet is None or _supported_by_packet(value, packet):
        return value
    return f"{label}：{_first_source_snippet(packet)}。"


def _source_grounded_title(
    value: str,
    *,
    packet: EpisodeSourcePacket | None,
    episode: int,
) -> str:
    if packet is None or _supported_by_packet(value, packet):
        return value
    snippet = _first_source_snippet(packet)
    title = re.split(r"[，,。！？!?；;：:\n]", snippet, maxsplit=1)[0].strip()
    return title[:20] or f"第{episode}集"


def _source_grounded_forbidden_shortcuts(
    shortcuts: list[str],
    packet: EpisodeSourcePacket | None,
) -> list[str]:
    supported = _filter_plan_assets(shortcuts, packet)
    return _dedupe([*supported, *SOURCE_BOUNDARY_FORBIDDEN_SHORTCUTS])


EPISODE_HEADING_RE = re.compile(
    r"(?im)^(?:[ \t]{0,3}(?:#{1,6}[ \t]*)?)"
    r"(?:(?:EP|E|Episode)\s*0*(?P<latin>\d{1,3})|"
    r"第\s*0*(?P<chinese>\d{1,3})\s*集)"
    r"(?=$|[：:.\-、\s])"
)
SCENE_HEADING_RE = re.compile(
    r"(?im)^[ \t]{0,3}(?P<episode>\d{1,3})\s*[-—－]\s*"
    r"(?P<scene>\d{1,3})(?=$|[：:.、\s])"
)
CHAPTER_HEADING_RE = re.compile(
    r"(?im)^(?:[ \t]{0,3}(?:#{1,6}[ \t]*)?)"
    r"第\s*0*(?P<chapter>\d{1,4})\s*(?:章|回|节)"
    r"(?=$|[：:.\-、\s])"
)
BARE_CHAPTER_HEADING_RE = re.compile(
    r"(?im)^[ \t\u3000]{0,6}(?P<chapter>\d{1,4})\s*[.．、]\s*$"
)
CHAPTER_RANGE_RE = re.compile(
    r"第\s*0*(?P<start>\d{1,4})\s*(?:章|回|节)?"
    r"(?:\s*[-—－~～至到]\s*(?:第\s*)?0*(?P<end>\d{1,4})\s*(?:章|回|节)?)?"
)


def _heading_sections(source_text: str) -> dict[int, tuple[int, int]]:
    matches = list(EPISODE_HEADING_RE.finditer(source_text))
    if not matches:
        matches = list(SCENE_HEADING_RE.finditer(source_text))
    sections: dict[int, tuple[int, int]] = {}
    for index, match in enumerate(matches):
        episode = int(
            match.groupdict().get("latin")
            or match.groupdict().get("chinese")
            or match.groupdict()["episode"]
        )
        start = match.start()
        if episode in sections:
            continue
        end = next(
            (
                later.start()
                for later in matches[index + 1 :]
                if int(
                    later.groupdict().get("latin")
                    or later.groupdict().get("chinese")
                    or later.groupdict()["episode"]
                )
                != episode
            ),
            len(source_text),
        )
        sections[episode] = (start, end)
    return sections


def _first_source_heading(source_excerpt: str) -> str:
    return next(
        (line.strip() for line in source_excerpt.splitlines() if line.strip()),
        "",
    )


def _chapter_heading_matches(source_text: str) -> list[re.Match[str]]:
    matches = list(CHAPTER_HEADING_RE.finditer(source_text))
    if not matches:
        matches = list(BARE_CHAPTER_HEADING_RE.finditer(source_text))
    return matches


def _chapter_sections(source_text: str) -> list[tuple[int, int]]:
    matches = _chapter_heading_matches(source_text)
    return [
        (
            match.start(),
            matches[index + 1].start() if index + 1 < len(matches) else len(source_text),
        )
        for index, match in enumerate(matches)
    ]


def _chapter_anchor_span(
    source_text: str,
    source_anchor: str,
) -> tuple[int, int] | None:
    range_match = CHAPTER_RANGE_RE.search(source_anchor)
    if range_match is None:
        return None
    start_chapter = int(range_match.group("start"))
    end_chapter = int(range_match.group("end") or start_chapter)
    if end_chapter < start_chapter:
        return None

    matches = _chapter_heading_matches(source_text)
    sections = {
        int(match.group("chapter")): (
            match.start(),
            matches[index + 1].start() if index + 1 < len(matches) else len(source_text),
        )
        for index, match in enumerate(matches)
    }
    if start_chapter not in sections or end_chapter not in sections:
        return None
    return sections[start_chapter][0], sections[end_chapter][1]


def _chapter_partition_span(
    sections: list[tuple[int, int]],
    *,
    episode: int,
    target_episode_count: int,
) -> tuple[int, int] | None:
    if not sections or target_episode_count <= 0:
        return None
    section_count = len(sections)
    start_index = min(section_count - 1, (episode - 1) * section_count // target_episode_count)
    end_index = min(section_count, episode * section_count // target_episode_count)
    if end_index <= start_index:
        end_index = min(section_count, start_index + 1)
    return sections[start_index][0], sections[end_index - 1][1]


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


def _window(
    source_text: str,
    start: int,
    end: int,
    max_chars: int,
) -> tuple[int, int, str]:
    if end <= start:
        end = start + 1
    span = end - start
    if span >= max_chars:
        return start, end, _compact(source_text[start:end], max_chars)
    padding = max(0, (max_chars - span) // 2)
    left = max(0, start - padding)
    right = min(len(source_text), end + padding)
    return left, right, _compact(source_text[left:right], max_chars)


def _find_asset_window(
    source_text: str,
    assets: list[str],
    max_chars: int,
) -> tuple[int, int, str] | None:
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
    asset_start = min(pos[0] for pos in positions)
    asset_end = max(pos[1] for pos in positions)
    return _window(source_text, asset_start, asset_end, max_chars)


def _proportional_excerpt(
    source_text: str,
    *,
    episode: int,
    target_episode_count: int | None,
    fallback_episode_count: int,
    max_chars: int,
) -> tuple[int, int, str]:
    total_episodes = max(target_episode_count or fallback_episode_count, episode, 1)
    length = len(source_text)
    start = int(length * (episode - 1) / total_episodes)
    end = int(length * episode / total_episodes)
    overlap = min(1200, max_chars // 5)
    excerpt_start = max(0, start - overlap)
    excerpt_end = min(length, end + overlap)
    excerpt = _compact(source_text[excerpt_start:excerpt_end], max_chars)
    return excerpt_start, excerpt_end, excerpt


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
    chapter_sections = _chapter_sections(source_text)
    fallback_count = len(episode_numbers)
    packets: list[EpisodeSourcePacket] = []
    seen_fallback_required_assets: set[str] = set()

    for episode in episode_numbers:
        mapping = _mapping_for_episode(episode_context.source_to_episode_mapping, episode)
        outline = _outline_for_episode(series_structure_plan, episode)
        retained_assets = _split_assets(mapping.retained_assets if mapping else None)
        c1_assets = _dedupe(retained_assets)
        requested_source_anchor = (
            (outline.source_anchor if outline else "")
            or (mapping.source if mapping else "")
            or f"EP{episode:02d}"
        )

        selection_method = "unknown"
        selection_warnings: list[str] = []
        source_start = 0
        source_end = len(source_text)
        chapter_anchor_span = _chapter_anchor_span(
            source_text,
            requested_source_anchor,
        )
        if episode in heading_sections:
            start, end = heading_sections[episode]
            source_excerpt = _compact(source_text[start:end], max_chars)
            source_start, source_end = start, end
            selection_method = "heading"
        elif chapter_anchor_span is not None:
            source_start, source_end = chapter_anchor_span
            source_excerpt = _compact(
                source_text[source_start:source_end],
                max_chars,
            )
            selection_method = "chapter_partition"
        else:
            asset_window = _find_asset_window(
                source_text,
                [requested_source_anchor, *(c1_assets or [])],
                max_chars,
            )
            if asset_window:
                source_start, source_end, source_excerpt = asset_window
                selection_method = "asset_window"
            elif chapter_sections:
                total_episode_count = max(
                    target_episode_count or len(chapter_sections),
                    episode,
                    1,
                )
                chapter_span = _chapter_partition_span(
                    chapter_sections,
                    episode=episode,
                    target_episode_count=total_episode_count,
                )
                if chapter_span is None:
                    raise SourcePacketConfidenceError("小说章节索引为空，无法建立逐集原文包。")
                source_start, source_end = chapter_span
                source_excerpt = _compact(
                    source_text[source_start:source_end],
                    max_chars,
                )
                selection_method = "chapter_partition"
            else:
                source_start, source_end, source_excerpt = _proportional_excerpt(
                    source_text,
                    episode=episode,
                    target_episode_count=target_episode_count
                    or series_structure_plan.target_episode_count
                    if series_structure_plan
                    else target_episode_count,
                    fallback_episode_count=fallback_count,
                    max_chars=max_chars,
                )
                selection_method = "proportional_fallback"
                selection_warnings.append(
                    "未命中章节标题或原文资产窗口，暂按集数比例截取原文候选。"
                )

        if _supported_by_excerpt(requested_source_anchor, source_excerpt):
            source_anchor = requested_source_anchor
        elif selection_method in {"heading", "chapter_partition"}:
            source_anchor = _first_source_heading(source_excerpt)
        else:
            source_anchor = f"EP{episode:02d} 当前集原文"
        filtered_c1_assets = _filter_source_confirmed_assets(c1_assets, source_excerpt)
        if c1_assets and not filtered_c1_assets:
            selection_warnings.append("episode_context retained_assets 未在当前原文包中命中。")
        source_confidence = (
            "high"
            if selection_method == "heading"
            else "medium"
            if selection_method == "asset_window" or filtered_c1_assets
            else "low"
            if selection_method == "proportional_fallback"
            else "medium"
        )
        source_window_is_reliable = episode in heading_sections or len(
            _normalize_for_match(source_excerpt)
        ) >= 80
        grounded_c1_assets = (
            _fill_with_source_grounded_items(
                filtered_c1_assets,
                packet=EpisodeSourcePacket(
                    episode=episode,
                    source_anchor=source_anchor,
                    source_excerpt=source_excerpt,
                ),
                min_length=1,
                label="当前集原文必留",
            )
            if filtered_c1_assets or source_window_is_reliable
            else []
        )
        if not filtered_c1_assets:
            unique_fallback_c1_assets: list[str] = []
            for asset in grounded_c1_assets:
                normalized_asset = _normalize_for_match(asset)
                if normalized_asset in seen_fallback_required_assets:
                    continue
                seen_fallback_required_assets.add(normalized_asset)
                unique_fallback_c1_assets.append(asset)
            grounded_c1_assets = unique_fallback_c1_assets
        grounded_c0_facts = _fill_with_source_grounded_items(
            _filter_excerpt_assets(
                _dedupe(
                    [
                        mapping.information_increment if mapping else "",
                        outline.information_increment if outline else "",
                    ]
                ),
                source_excerpt,
            ),
            packet=EpisodeSourcePacket(
                episode=episode,
                source_anchor=source_anchor,
                source_excerpt=source_excerpt,
                source_start=source_start,
                source_end=source_end,
                source_hash=hashlib.sha256(
                    source_text[source_start:source_end].encode("utf-8")
                ).hexdigest(),
            ),
            min_length=1,
            label="当前集原文事实",
        )
        grounded_c2_assets = _fill_with_source_grounded_items(
            _filter_excerpt_assets(
                _dedupe([mapping.adaptation_action if mapping else ""]),
                source_excerpt,
            ),
            packet=EpisodeSourcePacket(
                episode=episode,
                source_anchor=source_anchor,
                source_excerpt=source_excerpt,
            ),
            min_length=1,
            label="当前集原文可视听",
        )
        grounded_golden_lines = _filter_excerpt_assets(
            _dedupe([outline.ending_hook if outline else ""]),
            source_excerpt,
        )

        packets.append(
            EpisodeSourcePacket(
                episode=episode,
                source_anchor=source_anchor,
                source_excerpt=source_excerpt,
                source_start=source_start,
                source_end=source_end,
                source_hash=hashlib.sha256(
                    source_text[source_start:source_end].encode("utf-8")
                ).hexdigest(),
                c0_facts=grounded_c0_facts,
                c1_must_keep_assets=grounded_c1_assets,
                source_evidence_assets=filtered_c1_assets,
                c2_visual_assets=grounded_c2_assets,
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
                golden_lines=grounded_golden_lines,
                handoff_requirement=grounded_golden_lines[0]
                if grounded_golden_lines
                else None,
                source_selection_method=selection_method,
                source_confidence=source_confidence,
                source_confidence_warnings=selection_warnings,
            )
        )

    return EpisodeSourcePackets(packets=packets)


def build_source_packet_confidence_report(
    packets: EpisodeSourcePackets,
    *,
    source_text: str,
    target_episode_count: int | None = None,
) -> SourcePacketConfidenceReport:
    min_source_chars = _confidence_min_source_chars()
    normalized_source_chars = len(_normalize_for_match(source_text))
    long_source = normalized_source_chars >= min_source_chars
    multi_episode = (target_episode_count or len(packets.packets)) > 1 or len(packets.packets) > 1

    items: list[SourcePacketConfidenceItem] = []
    blocking_warnings: list[str] = []
    advisory_warnings: list[str] = []
    seen_excerpts: dict[str, int] = {}
    planned_episode_count = max(
        target_episode_count or len(packets.packets),
        1,
    )
    minimum_source_chars = planned_episode_count * _min_source_chars_per_target_episode()
    if normalized_source_chars < minimum_source_chars:
        blocking_warnings.append(
            "原文信息预算不足："
            f"目标 {planned_episode_count} 集至少需要约 {minimum_source_chars} 个有效字符，"
            f"当前仅 {normalized_source_chars}；禁止靠模型自由扩写补足集数。"
        )

    for packet in packets.packets:
        hard_assets = _split_assets(packet.source_evidence_assets)
        warnings = list(packet.source_confidence_warnings)
        is_placeholder = re.fullmatch(
            r"EP\d{2,3}\s+当前集原文",
            packet.source_anchor.strip(),
            flags=re.IGNORECASE,
        )
        if packet.source_selection_method == "proportional_fallback":
            warnings.append("source packet 使用 proportional_fallback，未证明与当前集锚点匹配。")
        if is_placeholder:
            warnings.append("source_anchor 是系统占位锚点，缺少可追溯原文定位。")
        if not hard_assets:
            warnings.append("source_evidence_assets 为空，当前集缺少必须回填到剧本的硬证据。")

        excerpt_fingerprint = _normalize_for_match(packet.source_excerpt[:2000])
        duplicate_previous = seen_excerpts.get(excerpt_fingerprint)
        if excerpt_fingerprint and duplicate_previous is not None:
            warnings.append(
                f"source_excerpt 与 EP{duplicate_previous:02d} 高度重复，可能多集复用同一段原文。"
            )
        elif excerpt_fingerprint:
            seen_excerpts[excerpt_fingerprint] = packet.episode

        should_block = (
            long_source
            and multi_episode
            and packet.source_selection_method == "proportional_fallback"
            and (is_placeholder or not hard_assets)
        )
        status = "blocking" if should_block else "advisory" if warnings else "passed"
        episode_warning = (
            f"EP{packet.episode:02d} source packet 低置信度："
            + "；".join(dict.fromkeys(warnings))
        )
        if status == "blocking":
            blocking_warnings.append(episode_warning)
        elif status == "advisory":
            advisory_warnings.append(episode_warning)

        items.append(
            SourcePacketConfidenceItem(
                episode=packet.episode,
                source_anchor=packet.source_anchor,
                selection_method=packet.source_selection_method,
                source_confidence=packet.source_confidence,
                evidence_asset_count=len(hard_assets),
                status=status,
                warnings=list(dict.fromkeys(warnings)),
            )
        )

    if blocking_warnings:
        score = 0
        status = "blocking"
        rewrite_instruction = (
            "逐集原文包低置信度：必须先重新做章节/场景切分或 episode-to-source 映射，"
            "为每集绑定可追溯原文片段和 C0/C1 硬证据；禁止在弱原文包上继续生成剧本。"
        )
    elif advisory_warnings:
        score = 70
        status = "advisory"
        rewrite_instruction = "部分逐集原文包证据偏弱，写作时必须以当前 source_excerpt 为边界轻改。"
    else:
        score = 100
        status = "passed"
        rewrite_instruction = ""

    return SourcePacketConfidenceReport(
        score=score,
        status=status,
        items=items,
        blocking_warnings=blocking_warnings,
        advisory_warnings=advisory_warnings,
        rewrite_instruction=rewrite_instruction,
    )


def ensure_source_packet_confidence(report: SourcePacketConfidenceReport) -> None:
    if report.status != "blocking":
        return
    preview = "；".join(report.blocking_warnings[:3])
    raise SourcePacketConfidenceError(
        "逐集原文包低置信度，已阻断生成。"
        f"{preview} 请先重建章节切分/episode-to-source 映射后再生成。"
    )


def render_source_packet_confidence_report(report: SourcePacketConfidenceReport) -> str:
    parts = [
        "# Source Packet Confidence Report",
        "",
        f"- Status: {report.status}",
        f"- Score: {report.score}",
    ]
    if report.rewrite_instruction:
        parts.extend(["", f"Rewrite: {report.rewrite_instruction}"])
    for item in report.items:
        parts.extend(
            [
                "",
                f"## EP{item.episode:02d} · {item.status}",
                f"- Anchor: {item.source_anchor}",
                f"- Method: {item.selection_method}",
                f"- Confidence: {item.source_confidence}",
                f"- Evidence Assets: {item.evidence_asset_count}",
            ]
        )
        if item.warnings:
            parts.append("- Warnings:")
            parts.extend(f"  - {warning}" for warning in item.warnings)
    if report.blocking_warnings:
        parts.extend(["", "## Blocking Warnings"])
        parts.extend(f"- {warning}" for warning in report.blocking_warnings)
    if report.advisory_warnings:
        parts.extend(["", "## Advisory Warnings"])
        parts.extend(f"- {warning}" for warning in report.advisory_warnings)
    return "\n".join(parts).strip() + "\n"


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
                "title": _source_grounded_title(
                    plan.title,
                    packet=packet,
                    episode=plan.episode,
                ),
                "drama_engine": _source_grounded_scalar(
                    plan.drama_engine,
                    packet=packet,
                    label="当前集戏剧引擎",
                ),
                "protagonist_misbelief": _source_grounded_scalar(
                    plan.protagonist_misbelief,
                    packet=packet,
                    label="当前集主角认知",
                ),
                "truth_gap": _source_grounded_scalar(
                    plan.truth_gap,
                    packet=packet,
                    label="当前集真相差",
                ),
                "audience_information_gap": _source_grounded_scalar(
                    plan.audience_information_gap,
                    packet=packet,
                    label="当前集信息差",
                ),
                "source_assets_to_keep": _filter_plan_assets(
                    plan.source_assets_to_keep,
                    packet,
                ),
                "physical_action_chain": physical_action_chain,
                "scene_dynamics": scene_dynamics,
                "emotional_turns": _fill_with_source_grounded_items(
                    _filter_plan_assets(plan.emotional_turns, packet),
                    packet=packet,
                    min_length=2,
                    label="当前集情绪递进",
                ),
                "three_pull_beats": _fill_with_source_grounded_items(
                    _filter_plan_assets(plan.three_pull_beats, packet),
                    packet=packet,
                    min_length=3,
                    label="当前集三波拉扯",
                ),
                "false_payoff": _source_grounded_scalar(
                    plan.false_payoff,
                    packet=packet,
                    label="当前集假兑现",
                ),
                "planted_key": _source_grounded_scalar(
                    plan.planted_key,
                    packet=packet,
                    label="当前集钥匙",
                ),
                "strongest_line": _source_grounded_scalar(
                    plan.strongest_line,
                    packet=packet,
                    label="当前集短台词",
                ),
                "cliffhanger_design": _source_grounded_scalar(
                    plan.cliffhanger_design,
                    packet=packet,
                    label="当前集断点",
                ),
                "forbidden_shortcuts": _source_grounded_forbidden_shortcuts(
                    plan.forbidden_shortcuts,
                    packet,
                ),
            }
        )
        episodes.append(EpisodeDramaPlan.model_validate(plan_data))
    episode_plan_data = episode_plan.model_dump()
    episode_plan_data["adaptation_strategy"] = SOURCE_BOUNDARY_ADAPTATION_STRATEGY
    episode_plan_data["episodes"] = [episode.model_dump() for episode in episodes]
    return EpisodePlan.model_validate(episode_plan_data)


def bind_episode_plan_to_facts(
    episode_plan: EpisodePlan,
    packets: EpisodeSourcePackets,
    ledger: SourceFactLedger,
) -> EpisodePlan:
    """Make episode beats a verified view of the current source packet facts."""
    packet_by_episode = {packet.episode: packet for packet in packets.packets}
    fact_by_id = {fact.fact_id: fact for fact in ledger.facts}
    bound_episodes: list[EpisodeDramaPlan] = []

    for plan in episode_plan.episodes:
        packet = packet_by_episode.get(plan.episode)
        episode_facts = facts_for_episode(ledger, plan.episode)
        allowed_spans = {
            span_id
            for fact in episode_facts
            for span_id in fact.source_span_ids
        }
        allowed_fact_ids = {fact.fact_id for fact in episode_facts}
        verified_beats: list[EpisodeBeat] = []

        for beat in plan.beats:
            if not set(beat.source_span_ids).issubset(allowed_spans):
                continue
            if not set(beat.required_fact_ids).issubset(allowed_fact_ids):
                continue
            if any(
                not set(fact_by_id[fact_id].source_span_ids).intersection(
                    beat.source_span_ids
                )
                for fact_id in beat.required_fact_ids
            ):
                continue
            verified_beats.append(
                beat.model_copy(
                    update={
                        "forbidden_changes": _dedupe(
                            [
                                *beat.forbidden_changes,
                                *(packet.c4_forbidden_additions if packet else []),
                            ]
                        )
                    }
                )
            )

        if not verified_beats:
            verified_beats = [
                EpisodeBeat(
                    beat_id=f"EP{plan.episode:02d}-B{index:02d}",
                    event=fact.content,
                    source_span_ids=fact.source_span_ids,
                    required_fact_ids=[fact.fact_id],
                    forbidden_changes=(
                        list(packet.c4_forbidden_additions) if packet else []
                    ),
                )
                for index, fact in enumerate(episode_facts[:3], start=1)
            ]

        bound_episodes.append(
            plan.model_copy(update={"beats": verified_beats})
        )

    return episode_plan.model_copy(update={"episodes": bound_episodes})


def episode_drama_plan_for_episode(
    episode_plan: EpisodePlan | None,
    episode: int,
) -> EpisodeDramaPlan | None:
    """Return the only plan slice a single-episode writer may see."""
    return _plan_for_episode(episode_plan, episode)


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
