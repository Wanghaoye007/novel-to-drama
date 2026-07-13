from __future__ import annotations

import re
from collections.abc import Iterable


POSITIVE_QUALITY_HINTS = (
    "no blocking issues detected",
    "accurately map",
    "accurately maps",
    "key highlights maintained",
    "ensure that when filming",
    "all checks passed",
    "no blocking",
)

EPISODE_RANGE_PATTERNS = (
    re.compile(
        r"\bEP\s*0*(\d{1,3})\s*(?:-|~|–|—|至|到)\s*(?:EP\s*)?0*(\d{1,3})\b",
        re.IGNORECASE,
    ),
    re.compile(r"第\s*0*(\d{1,3})\s*(?:-|~|–|—|至|到)\s*0*(\d{1,3})\s*集"),
)

EPISODE_REF_PATTERNS = (
    re.compile(r"\bEP\s*0*(\d{1,3})\b", re.IGNORECASE),
    re.compile(r"第\s*0*(\d{1,3})\s*集"),
)


def _compact_key(text: str) -> str:
    return re.sub(r"\s+", "", text).replace("：", ":").lower()


def _is_positive_advice(text: str) -> bool:
    lowered = text.lower()
    return any(hint in lowered for hint in POSITIVE_QUALITY_HINTS)


def _clean_segment(text: str) -> str:
    text = re.sub(r"\s+", " ", text.strip())
    text = re.sub(r"^[-*•]\s*", "", text)
    return text.strip("；; ")


def _segments(text: str) -> list[str]:
    parts: list[str] = []
    for line in re.split(r"[\r\n]+", text):
        line = _clean_segment(line)
        if not line:
            continue
        parts.extend(_clean_segment(part) for part in re.split(r"[；;]+", line))
    return [part for part in parts if part]


def dedupe_quality_items(
    items: Iterable[str],
    *,
    drop_positive: bool = True,
) -> list[str]:
    cleaned: list[str] = []
    seen: set[str] = set()
    for item in items:
        item = _clean_segment(str(item))
        if not item:
            continue
        if drop_positive and _is_positive_advice(item):
            continue
        key = _compact_key(item)
        if key in seen:
            continue
        seen.add(key)
        cleaned.append(item)
    return cleaned


def merge_rewrite_instructions(
    parts: Iterable[str],
    *,
    blocking: bool,
    max_segments: int = 28,
) -> str:
    merged: list[str] = []
    seen: set[str] = set()
    for part in parts:
        if not str(part).strip():
            continue
        for segment in _segments(str(part)):
            if blocking and _is_positive_advice(segment):
                continue
            key = _compact_key(segment)
            if key in seen:
                continue
            seen.add(key)
            merged.append(segment)
            if len(merged) >= max_segments:
                return "；".join(merged)
    return "；".join(merged)


def _episode_refs(text: str) -> set[int]:
    refs: set[int] = set()
    for pattern in EPISODE_RANGE_PATTERNS:
        for start_text, end_text in pattern.findall(text):
            start, end = int(start_text), int(end_text)
            if end < start:
                start, end = end, start
            refs.update(range(start, end + 1))
    for pattern in EPISODE_REF_PATTERNS:
        refs.update(int(match) for match in pattern.findall(text))
    return refs


def filter_quality_text_for_episode(
    text: str,
    episode_number: int,
    *,
    include_unscoped: bool = True,
) -> str:
    scoped: list[str] = []
    for segment in _segments(text):
        refs = _episode_refs(segment)
        if refs and episode_number not in refs:
            continue
        if not refs and not include_unscoped:
            continue
        scoped.append(segment)
    return merge_rewrite_instructions(scoped, blocking=True)
