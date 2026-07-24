from __future__ import annotations

MAX_ACTION_LINE_CHARS = 32
MAX_VOICED_LINE_CHARS = 22

_BOUNDARY_LEVELS = (
    "。！？!?；;",
    "，,：:",
    "、",
)
_CLOSING_PUNCTUATION = frozenset("”’」』）》】")


def _split_preserving_boundaries(text: str, boundaries: str) -> list[str]:
    boundary_set = frozenset(boundaries)
    parts: list[str] = []
    start = 0
    index = 0
    while index < len(text):
        if text[index] not in boundary_set:
            index += 1
            continue
        end = index + 1
        while end < len(text) and text[end] in _CLOSING_PUNCTUATION:
            end += 1
        parts.append(text[start:end])
        start = end
        index = end
    if start < len(text):
        parts.append(text[start:])
    return [part for part in parts if part]


def split_visible_line(text: str, *, max_chars: int) -> list[str]:
    """Split one visible script line without rewriting its content.

    Strong punctuation is preferred, then clause/list boundaries. A final
    fixed-width split is only used when the provider returned a long segment
    with no usable boundary. Joining the returned parts always recreates the
    stripped input exactly.
    """

    stripped = text.strip()
    if not stripped or len(stripped) <= max_chars:
        return [stripped]

    parts = [stripped]
    for boundaries in _BOUNDARY_LEVELS:
        next_parts: list[str] = []
        for part in parts:
            if len(part) <= max_chars:
                next_parts.append(part)
                continue
            next_parts.extend(_split_preserving_boundaries(part, boundaries))
        parts = next_parts

    result: list[str] = []
    for part in parts:
        if len(part) <= max_chars:
            result.append(part)
            continue
        result.extend(
            part[index : index + max_chars]
            for index in range(0, len(part), max_chars)
        )
    return result
