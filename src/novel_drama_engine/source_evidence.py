from __future__ import annotations

import re

from novel_drama_engine.models import (
    EpisodeContext,
    EpisodeScript,
    EpisodeSourceMapping,
    EpisodeSourcePacket,
    EpisodeSourcePackets,
    QualityReport,
    QualityStatus,
    ScriptBatch,
    SourceEvidenceItem,
    SourceEvidenceReport,
    SourceEvidenceSpan,
)
from novel_drama_engine.quality_text import (
    dedupe_quality_items,
    merge_rewrite_instructions,
)
from novel_drama_engine.renderer import render_shooting_episode


def _compact(text: str) -> str:
    compact = re.sub(r"\s+", "", text.strip())
    replacements = {
        "聚光灯": "灯光",
        "汇聚": "聚焦",
        "打在": "聚焦",
        "获得影后的是": "宣布",
        "获奖的是": "宣布",
    }
    for old, new in replacements.items():
        compact = compact.replace(old, new)
    return compact


def _split_assets(value: list[str] | str | None) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        parts = re.split(r"[、,，；;|\n]+", value)
    else:
        parts = value
    ignored = {"none", "null", "nil", "-", "无", "暂无"}
    return [
        part.strip()
        for part in parts
        if part and part.strip() and part.strip().lower() not in ignored
    ]


def _asset_needles(asset: str) -> list[str]:
    compact = _compact(asset)
    if not compact:
        return []
    needles = [compact]
    cjk_runs = re.findall(r"[\u4e00-\u9fff]{3,}", compact)
    for run in cjk_runs:
        for size in (4, 3):
            for index in range(0, len(run) - size + 1):
                needles.append(run[index : index + size])
    return list(dict.fromkeys(needles))


def _asset_tokens(asset: str) -> list[str]:
    compact = _compact(asset)
    tokens: list[str] = []
    for run in re.findall(r"[\u4e00-\u9fffA-Za-z0-9]{2,}", compact):
        tokens.append(run)
        if re.fullmatch(r"[\u4e00-\u9fff]{4,}", run):
            tokens.extend(run[index : index + 2] for index in range(0, len(run) - 1))
    return list(dict.fromkeys(token for token in tokens if len(token) >= 2))


ABSTRACT_ASSET_WORDS = {
    "情感",
    "关联",
    "情绪",
    "氛围",
    "感觉",
    "戏剧",
    "节点",
    "张力",
    "反差",
    "压迫",
    "压迫感",
    "羞辱感",
    "决绝",
    "对峙",
    "互动",
    "铺排",
    "悬疑",
    "背景",
    "关系",
}

CRITICAL_ASSET_TOKENS = {
    "主持人",
    "林挽清",
    "路淮北",
    "许念念",
    "霍雅",
    "霍庭琛",
}

CRITICAL_ACTION_SYNONYMS = {
    "举起": ("举",),
    "拿出": ("拿出", "抽出", "掏出", "递出", "拍在", "拍到"),
    "宣布": ("宣布",),
}

KEY_ASSET_ACTION_TOKENS = {
    "靠近",
    "疑惑",
    "半步",
    "宣布",
    "聚焦",
    "举",
    "解约",
    "快门",
    "抬头",
    "蛋糕",
    "围裙",
    "红酒",
    "飞机",
}


def _concrete_asset_tokens(asset: str) -> list[str]:
    concrete_asset = asset
    for abstract_word in sorted(ABSTRACT_ASSET_WORDS, key=len, reverse=True):
        concrete_asset = concrete_asset.replace(f"的{abstract_word}", "")
        concrete_asset = concrete_asset.replace(abstract_word, "")
    tokens: list[str] = []
    for token in _asset_tokens(concrete_asset):
        compact = _compact(token)
        if not compact or "的" in compact:
            continue
        if compact in ABSTRACT_ASSET_WORDS:
            continue
        tokens.append(compact)
    return list(dict.fromkeys(tokens))


def _has_specific_asset_overlap(line: str, asset: str) -> bool:
    compact_asset = _compact(asset)
    if len(compact_asset) <= 4:
        return False
    compact_line = _compact(line)
    concrete_tokens = _concrete_asset_tokens(asset)
    if any(len(token) >= 4 and token in compact_line for token in concrete_tokens):
        return True
    matched_concrete = [token for token in concrete_tokens if token in compact_line]
    if len(concrete_tokens) >= 8 and len(matched_concrete) >= 4:
        asset_key_actions = [
            token for token in KEY_ASSET_ACTION_TOKENS if token in compact_asset
        ]
        if asset_key_actions and any(token in compact_line for token in asset_key_actions):
            return True
    if 1 < len(concrete_tokens) <= 3:
        return all(token in compact_line for token in concrete_tokens)
    if len(compact_asset) <= 6:
        return compact_asset[:3] in compact_line and compact_asset[-2:] in compact_line
    late_tokens = _asset_tokens(compact_asset[4:])
    return any(token in compact_line for token in late_tokens)


def _line_matches_asset(
    line: str,
    asset: str,
    *,
    require_critical_actor: bool = True,
) -> bool:
    compact_line = _compact(line)
    if not compact_line:
        return False
    compact_asset = _compact(asset)
    critical_tokens = [
        token for token in CRITICAL_ASSET_TOKENS if token in compact_asset
    ]
    if (
        require_critical_actor
        and critical_tokens
        and not any(token in compact_line for token in critical_tokens)
    ):
        return False
    for action, synonyms in CRITICAL_ACTION_SYNONYMS.items():
        if action in compact_asset and not any(
            synonym in compact_line for synonym in synonyms
        ):
            return False
    if compact_asset and compact_asset in compact_line:
        return True
    if len(compact_asset) <= 4:
        return any(needle in compact_line for needle in _asset_needles(asset))

    tokens = _concrete_asset_tokens(asset) or _asset_tokens(asset)
    if not tokens:
        return False
    matched = sum(1 for token in tokens if token in compact_line)
    coverage = matched / max(1, len(tokens))
    if len(tokens) <= 2:
        return matched == len(tokens) and _has_specific_asset_overlap(line, asset)
    if len(tokens) >= 8 and matched >= 4 and _has_specific_asset_overlap(line, asset):
        return True
    return matched >= 3 and coverage >= 0.25 and _has_specific_asset_overlap(line, asset)


def _asset_match_score(
    line: str,
    asset: str,
    *,
    require_critical_actor: bool = True,
) -> float:
    compact_line = _compact(line)
    compact_asset = _compact(asset)
    if not compact_line:
        return 0
    if compact_asset and compact_asset in compact_line:
        return 1000 + len(compact_asset)
    tokens = _concrete_asset_tokens(asset) or _asset_tokens(asset)
    if not tokens:
        return 0
    matched = sum(1 for token in tokens if token in compact_line)
    coverage = matched / max(1, len(tokens))
    if not _line_matches_asset(
        line,
        asset,
        require_critical_actor=require_critical_actor,
    ):
        return 0
    late_bonus = 2 if _has_specific_asset_overlap(line, asset) else 0
    return matched + coverage + late_bonus


def _script_line_entries(script: EpisodeScript) -> list[tuple[int, str]]:
    rendered = render_shooting_episode(script)
    return [
        (index, line.strip())
        for index, line in enumerate(rendered.splitlines(), start=1)
        if line.strip()
    ]


def _script_lines(script: EpisodeScript) -> list[str]:
    return [line for _, line in _script_line_entries(script)]


def _line_entry_for_asset(
    entries: list[tuple[int, str]],
    asset: str,
) -> tuple[int | None, str | None]:
    single_candidates: list[tuple[float, int, str]] = []
    joined_candidates: list[tuple[float, int, str]] = []
    for offset, (index, line) in enumerate(entries):
        single_candidates.append((_asset_match_score(line, asset), index, line))
        if offset + 1 < len(entries):
            _, next_line = entries[offset + 1]
            joined = f"{line} / {next_line}"
            joined_candidates.append((_asset_match_score(joined, asset), index, joined))
    single_candidates = [candidate for candidate in single_candidates if candidate[0] > 0]
    joined_candidates = [candidate for candidate in joined_candidates if candidate[0] > 0]
    candidates = single_candidates
    if joined_candidates:
        best_single_score = max((candidate[0] for candidate in single_candidates), default=0)
        best_joined = max(joined_candidates, key=lambda item: item[0])
        if best_joined[0] > best_single_score + 0.5:
            candidates = joined_candidates
    if not candidates:
        return None, None
    _, index, line = max(candidates, key=lambda item: item[0])
    return index, line


def _source_line_for_asset(
    packet: EpisodeSourcePacket,
    asset: str,
) -> tuple[int | None, str | None]:
    lines = [line.strip() for line in packet.source_excerpt.splitlines() if line.strip()]
    single_candidates: list[tuple[float, int, str]] = []
    joined_candidates: list[tuple[float, int, str]] = []
    for offset, line in enumerate(lines, start=1):
        single_candidates.append(
            (
                _asset_match_score(line, asset, require_critical_actor=False),
                offset,
                line,
            )
        )
        if offset < len(lines):
            joined = f"{line} / {lines[offset]}"
            joined_candidates.append(
                (
                    _asset_match_score(joined, asset, require_critical_actor=False),
                    offset,
                    joined,
                )
            )
    candidates = [candidate for candidate in single_candidates if candidate[0] > 0]
    if not candidates:
        candidates = [candidate for candidate in joined_candidates if candidate[0] > 0]
    if candidates:
        _, index, line = max(candidates, key=lambda item: item[0])
        return index, line
    anchor = packet.source_anchor.strip()
    if anchor and _line_matches_asset(anchor, asset, require_critical_actor=False):
        return 1, anchor
    return None, None


def _evidence_span_for_asset(
    packet: EpisodeSourcePacket,
    asset: str,
    script_entries: list[tuple[int, str]],
    adaptation_reason: str,
) -> SourceEvidenceSpan:
    source_line_index, source_line = _source_line_for_asset(packet, asset)
    script_line_index, script_line = _line_entry_for_asset(script_entries, asset)
    if source_line and script_line:
        status = "matched"
    elif source_line:
        status = "script_missing"
    elif script_line:
        status = "source_missing"
    else:
        status = "missing"
    return SourceEvidenceSpan(
        asset=asset,
        source_anchor=packet.source_anchor,
        source_excerpt=packet.source_excerpt,
        source_line=source_line,
        source_line_index=source_line_index,
        script_line=script_line,
        script_line_index=script_line_index,
        adaptation_reason=adaptation_reason,
        status=status,
    )


def _packet_assets(packet: EpisodeSourcePacket) -> list[str]:
    evidence_assets = _split_assets(packet.source_evidence_assets)
    if evidence_assets:
        return evidence_assets
    c1_assets = _split_assets(packet.c1_must_keep_assets)
    if c1_assets:
        return c1_assets
    return []


def _is_system_placeholder_anchor(anchor: str) -> bool:
    return bool(
        re.fullmatch(
            r"EP\d{2,3}\s+当前集原文",
            anchor.strip(),
            flags=re.IGNORECASE,
        )
    )


def _packet_reason(packet: EpisodeSourcePacket) -> str:
    if packet.c1_must_keep_assets:
        return "保留原文必留资产：" + "、".join(packet.c1_must_keep_assets[:4])
    if packet.c0_facts:
        return "承接原文关键信息：" + "、".join(packet.c0_facts[:3])
    return "追踪原文锚点是否落到正片。"


def _episode_number_from_mapping(mapping: EpisodeSourceMapping) -> int | None:
    value = mapping.target_episode
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        match = re.search(r"\d+", value)
        if match:
            return int(match.group(0))
    return None


def _mapping_packets(episode_context: EpisodeContext) -> list[EpisodeSourcePacket]:
    packets: list[EpisodeSourcePacket] = []
    fallback_episode = 1
    for mapping in episode_context.source_to_episode_mapping:
        episode = _episode_number_from_mapping(mapping) or fallback_episode
        fallback_episode = episode + 1
        retained_assets = _split_assets(mapping.retained_assets)
        packets.append(
            EpisodeSourcePacket(
                episode=episode,
                source_anchor=mapping.source,
                source_excerpt=mapping.source,
                c0_facts=_split_assets(mapping.information_increment),
                c1_must_keep_assets=retained_assets,
                c2_visual_assets=_split_assets(mapping.adaptation_action),
            )
        )
    return packets


def build_source_evidence_report(
    script_batch: ScriptBatch,
    *,
    episode_source_packets: EpisodeSourcePackets | None = None,
    episode_context: EpisodeContext | None = None,
) -> SourceEvidenceReport:
    scripts = {script.episode: script for script in script_batch.episodes}
    packets = (
        episode_source_packets.packets
        if episode_source_packets is not None
        else _mapping_packets(episode_context)
        if episode_context is not None
        else []
    )

    items: list[SourceEvidenceItem] = []
    missing_items: list[str] = []
    matched_count = 0
    total_count = 0
    for packet in packets:
        script = scripts.get(packet.episode)
        if script is None:
            continue
        hard_assets = _packet_assets(packet)
        assets = hard_assets
        if not assets:
            assets = _split_assets(packet.c0_facts)
        if not assets and not _is_system_placeholder_anchor(packet.source_anchor):
            assets = [packet.source_anchor]

        adaptation_reason = _packet_reason(packet)
        line_entries = _script_line_entries(script) if script is not None else []
        evidence_spans = [
            _evidence_span_for_asset(
                packet,
                asset,
                line_entries,
                adaptation_reason,
            )
            for asset in assets
        ]

        source_unverified_spans = [
            span for span in evidence_spans if span.status == "source_missing"
        ]
        total_count += len(evidence_spans)
        matched_spans = [span for span in evidence_spans if span.status == "matched"]
        missing_spans = [
            span
            for span in evidence_spans
            if span.status in {"missing", "script_missing"}
        ]
        matched_count += len(matched_spans)
        script_evidence = [
            span.script_line for span in matched_spans if span.script_line
        ]
        unique_evidence = list(dict.fromkeys(script_evidence))[:6]
        if missing_spans and hard_assets:
            for span in missing_spans:
                missing_items.append(
                    f"EP{packet.episode:02d} 缺少原文资产：{span.asset}"
                )
        if source_unverified_spans and hard_assets:
            for span in source_unverified_spans:
                missing_items.append(
                    f"EP{packet.episode:02d} 原文未证明资产：{span.asset}"
                )

        if matched_spans and (missing_spans or source_unverified_spans):
            status = "partial"
        elif matched_spans:
            status = "matched"
        elif source_unverified_spans and not missing_spans:
            status = "source_unverified"
        else:
            status = "missing"

        items.append(
            SourceEvidenceItem(
                episode=packet.episode,
                source_anchor=packet.source_anchor,
                adaptation_reason=adaptation_reason,
                retained_assets=assets,
                script_evidence=unique_evidence,
                evidence_spans=evidence_spans,
                status=status,
            )
        )

    coverage_score = (
        round((matched_count / total_count) * 100)
        if total_count
        else 0
        if items
        else 100
    )
    rewrite_instruction = ""
    if missing_items:
        rewrite_instruction = (
            "原文证据未落到正片或资产无源文证明：先删除原文无法证明的新增资产，再把缺失的必留资产转成"
            "可见动作、道具、关系反应或短对白；强原文本身已有爆款冲突时，只做"
            "视听化增强，不要另起新冲突。"
        )

    return SourceEvidenceReport(
        coverage_score=coverage_score,
        items=items,
        missing_items=missing_items,
        rewrite_instruction=rewrite_instruction,
    )


def merge_source_evidence_into_quality_report(
    quality_report: QualityReport,
    source_evidence_report: SourceEvidenceReport,
) -> QualityReport:
    if not source_evidence_report.missing_items:
        return quality_report
    missing_preview = "；".join(source_evidence_report.missing_items[:5])
    blocking_issue = f"source_evidence: {missing_preview}"
    blocking_issues = dedupe_quality_items([*quality_report.blocking_issues, blocking_issue])
    rewrite_instruction = merge_rewrite_instructions(
        [
            quality_report.rewrite_instruction,
            source_evidence_report.rewrite_instruction,
            missing_preview,
        ],
        blocking=True,
    )
    return quality_report.model_copy(
        update={
            "status": QualityStatus.NEEDS_REWRITE,
            "blocking_issues": blocking_issues,
            "rewrite_instruction": rewrite_instruction,
        }
    )


def render_source_evidence_report(report: SourceEvidenceReport) -> str:
    parts = [
        "# Source Evidence Report",
        "",
        f"- Coverage: {report.coverage_score}%",
        f"- Missing: {len(report.missing_items)}",
    ]
    if report.rewrite_instruction:
        parts.extend(["", f"Rewrite: {report.rewrite_instruction}"])
    for item in report.items:
        parts.extend(
            [
                "",
                f"## EP{item.episode:02d} · {item.status}",
                f"- Source: {item.source_anchor}",
                f"- Reason: {item.adaptation_reason}",
                f"- Assets: {'、'.join(item.retained_assets) if item.retained_assets else '-'}",
            ]
        )
        if item.script_evidence:
            parts.append("- Script Evidence:")
            parts.extend(f"  - {line}" for line in item.script_evidence)
        if item.evidence_spans:
            parts.append("- Source Span Evidence:")
            for span in item.evidence_spans:
                source_ref = (
                    f"source L{span.source_line_index}: {span.source_line}"
                    if span.source_line_index and span.source_line
                    else "source missing"
                )
                script_ref = (
                    f"script L{span.script_line_index}: {span.script_line}"
                    if span.script_line_index and span.script_line
                    else "script missing"
                )
                parts.append(
                    f"  - {span.status} · {span.asset} · {source_ref} -> {script_ref}"
                )
    if report.missing_items:
        parts.extend(["", "## Missing Items"])
        parts.extend(f"- {item}" for item in report.missing_items)
    return "\n".join(parts).strip() + "\n"
