from __future__ import annotations

import re

from novel_drama_engine.models import (
    EpisodeContext,
    EpisodeScript,
    EpisodeSourceMapping,
    EpisodeSourcePacket,
    EpisodeSourcePackets,
    ScriptBatch,
    SourceEvidenceItem,
    SourceEvidenceReport,
)
from novel_drama_engine.renderer import render_line


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


def _line_matches_asset(line: str, asset: str) -> bool:
    compact_line = _compact(line)
    if not compact_line:
        return False
    return any(needle in compact_line for needle in _asset_needles(asset))


def _script_lines(script: EpisodeScript) -> list[str]:
    lines: list[str] = [script.title, script.hook_3s, script.cliffhanger]
    for scene in script.scenes:
        lines.append(scene.heading)
        lines.append("、".join(scene.characters))
        lines.extend(render_line(line) for line in scene.lines)
    return [line.strip() for line in lines if line and line.strip()]


def _evidence_for_asset(lines: list[str], asset: str) -> str | None:
    for line in lines:
        if _line_matches_asset(line, asset):
            return line
    return None


def _packet_assets(packet: EpisodeSourcePacket) -> list[str]:
    return _split_assets(
        [
            *packet.c1_must_keep_assets,
            *packet.c2_visual_assets,
            *packet.golden_lines,
        ]
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

        lines = _script_lines(script)
        assets = _packet_assets(packet)
        if not assets:
            assets = [packet.source_anchor]

        script_evidence: list[str] = []
        for asset in assets:
            evidence = _evidence_for_asset(lines, asset)
            if evidence:
                script_evidence.append(evidence)

        total_count += 1
        unique_evidence = list(dict.fromkeys(script_evidence))[:6]
        if unique_evidence:
            matched_count += 1
            status = "matched"
        else:
            status = "missing"
            missing_items.extend(
                f"EP{packet.episode:02d} 缺少原文资产：{asset}" for asset in assets
            )

        items.append(
            SourceEvidenceItem(
                episode=packet.episode,
                source_anchor=packet.source_anchor,
                adaptation_reason=_packet_reason(packet),
                retained_assets=assets,
                script_evidence=unique_evidence,
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
    if report.missing_items:
        parts.extend(["", "## Missing Items"])
        parts.extend(f"- {item}" for item in report.missing_items)
    return "\n".join(parts).strip() + "\n"
