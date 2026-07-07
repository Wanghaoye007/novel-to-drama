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
from novel_drama_engine.renderer import render_shooting_episode


def _compact(text: str) -> str:
    return re.sub(r"\s+", "", text.strip())


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


def _has_specific_asset_overlap(line: str, asset: str) -> bool:
    compact_asset = _compact(asset)
    if len(compact_asset) <= 4:
        return False
    compact_line = _compact(line)
    late_tokens = _asset_tokens(compact_asset[4:])
    return any(token in compact_line for token in late_tokens)


def _line_matches_asset(line: str, asset: str) -> bool:
    compact_line = _compact(line)
    if not compact_line:
        return False
    compact_asset = _compact(asset)
    if compact_asset and compact_asset in compact_line:
        return True
    if len(compact_asset) <= 4:
        return any(needle in compact_line for needle in _asset_needles(asset))

    tokens = _asset_tokens(asset)
    if not tokens:
        return False
    matched = sum(1 for token in tokens if token in compact_line)
    coverage = matched / max(1, len(tokens))
    return matched >= 3 and coverage >= 0.25 and _has_specific_asset_overlap(line, asset)


def _asset_match_score(line: str, asset: str) -> float:
    compact_line = _compact(line)
    compact_asset = _compact(asset)
    if not compact_line:
        return 0
    if compact_asset and compact_asset in compact_line:
        return 1000 + len(compact_asset)
    tokens = _asset_tokens(asset)
    if not tokens:
        return 0
    matched = sum(1 for token in tokens if token in compact_line)
    coverage = matched / max(1, len(tokens))
    if not _line_matches_asset(line, asset):
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
    candidates = [
        (_asset_match_score(line, asset), index, line)
        for index, line in entries
    ]
    candidates = [candidate for candidate in candidates if candidate[0] > 0]
    if not candidates:
        return None, None
    _, index, line = max(candidates, key=lambda item: item[0])
    return index, line


def _source_line_for_asset(
    packet: EpisodeSourcePacket,
    asset: str,
) -> tuple[int | None, str | None]:
    lines = [line.strip() for line in packet.source_excerpt.splitlines() if line.strip()]
    candidates = [
        (_asset_match_score(line, asset), index, line)
        for index, line in enumerate(lines, start=1)
    ]
    candidates = [candidate for candidate in candidates if candidate[0] > 0]
    if candidates:
        _, index, line = max(candidates, key=lambda item: item[0])
        return index, line
    anchor = packet.source_anchor.strip()
    if anchor and _line_matches_asset(anchor, asset):
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
    return SourceEvidenceSpan(
        asset=asset,
        source_anchor=packet.source_anchor,
        source_excerpt=packet.source_excerpt,
        source_line=source_line,
        source_line_index=source_line_index,
        script_line=script_line,
        script_line_index=script_line_index,
        adaptation_reason=adaptation_reason,
        status="matched" if script_line else "missing",
    )


def _packet_assets(packet: EpisodeSourcePacket) -> list[str]:
    if packet.source_evidence_assets is not None:
        return _split_assets(packet.source_evidence_assets)
    return _split_assets(packet.c1_must_keep_assets)


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
        hard_assets = _packet_assets(packet)
        assets = hard_assets
        if not assets:
            assets = _split_assets(packet.c1_must_keep_assets)
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

        total_count += len(evidence_spans)
        matched_spans = [span for span in evidence_spans if span.status == "matched"]
        missing_spans = [span for span in evidence_spans if span.status == "missing"]
        matched_count += len(matched_spans)
        script_evidence = [
            span.script_line for span in matched_spans if span.script_line
        ]
        unique_evidence = list(dict.fromkeys(script_evidence))[:6]
        if missing_spans and hard_assets:
            missing_items.extend(
                f"EP{packet.episode:02d} 缺少原文资产：{span.asset}"
                for span in missing_spans
            )

        if matched_spans and missing_spans:
            status = "partial"
        elif matched_spans:
            status = "matched"
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

    coverage_score = round((matched_count / total_count) * 100) if total_count else 100
    rewrite_instruction = ""
    if missing_items:
        rewrite_instruction = (
            "原文证据未落到正片：请优先把缺失的必留资产转成可见动作、道具、"
            "关系反应或短对白；强原文本身已有爆款冲突时，只做视听化增强，不要另起新冲突。"
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
    blocking_issues = list(dict.fromkeys([*quality_report.blocking_issues, blocking_issue]))
    rewrite_instruction = "；".join(
        item
        for item in [
            quality_report.rewrite_instruction,
            source_evidence_report.rewrite_instruction,
            missing_preview,
        ]
        if item
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
