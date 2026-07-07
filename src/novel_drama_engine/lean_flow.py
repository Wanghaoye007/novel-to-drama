from __future__ import annotations

import re

from novel_drama_engine.models import (
    EpisodeContext,
    EpisodeCut,
    EpisodeCutTable,
    EpisodeSourcePacket,
    EpisodeSourcePackets,
    ProductionSpec,
    SourceAnalysis,
    SourceAnnotation,
    SourceAnnotationEpisode,
    StoryBible,
)


PSYCHOLOGICAL_MARKERS = (
    "僵",
    "震惊",
    "心碎",
    "屈辱",
    "害怕",
    "克制",
    "冷静",
    "决绝",
    "清醒",
    "委屈",
    "愣",
    "眼眶",
    "泪",
)


def _dedupe(items: list[str]) -> list[str]:
    return [item for item in dict.fromkeys(item.strip() for item in items if item.strip())]


def _sentence_snippets(text: str, markers: tuple[str, ...], *, limit: int = 4) -> list[str]:
    snippets: list[str] = []
    for part in re.split(r"(?<=[。！？!?])|\n+", text):
        cleaned = part.strip()
        if cleaned and any(marker in cleaned for marker in markers):
            snippets.append(cleaned[:120])
        if len(snippets) >= limit:
            break
    return _dedupe(snippets)


def _packet_core_conflict(packet: EpisodeSourcePacket, fallback: str) -> str:
    if packet.source_anchor.strip():
        return packet.source_anchor.strip()
    if packet.c1_must_keep_assets:
        return packet.c1_must_keep_assets[0]
    return fallback


def build_production_spec() -> ProductionSpec:
    return ProductionSpec(
        primary_output="creative_script",
        script_priorities=[
            "创作稿先成立：人物动机、冲突因果、情绪递进和对白真实优先。",
            "原文标注稿与本集 source packet 是首稿最高优先级基准。",
            "执行稿信息后移：景别、运镜、BGM 只补足可拍性，不得污染剧情文本。",
        ],
        format_rules=[
            "第X集 + X-X 日/夜-内/外-具体地点 + 人物 + 正片行。",
            "禁止外露 3秒Hook、主情绪、消费理由、观众要看、本集看点。",
        ],
        vo_os_rules=[
            "OS/VO 必须服务动作或选择，下一行要承接可见动作、沉默决定或关系变化。",
            "屏幕字幕类解释优先转为角色 VO/OS 或短对白，不单独写说明性字幕。",
        ],
        dialogue_rules=[
            "台词短、口语、带潜台词，单句只表达一个动作或情绪。",
            "不得把克制人物写成歇斯底里，不得用解释型长句替代戏。",
        ],
        shooting_rules=[
            "动作行必须可拍，含主体、动作、对象和当场后果。",
            "镜头信息只服务情绪和信息，不为了凑格式增加空镜和水动作。",
        ],
        delivery_rules=[
            "首稿产物是 creative_script；通过质检后再派生 shooting_script/export。",
            "源文相似度低于 5/10 时，必须回到 source_annotation 定向修复。",
        ],
    )


def build_source_annotation(
    *,
    source_text: str,
    source_analysis: SourceAnalysis,
    episode_context: EpisodeContext,
    story_bible: StoryBible,
    episode_source_packets: EpisodeSourcePackets,
) -> SourceAnnotation:
    episodes: list[SourceAnnotationEpisode] = []
    for packet in episode_source_packets.packets:
        must_keep_events = _dedupe([*packet.c0_facts, packet.source_anchor])
        must_keep_assets = _dedupe([*packet.c1_must_keep_assets, *(packet.source_evidence_assets or [])])
        psychological_beats = _sentence_snippets(packet.source_excerpt, PSYCHOLOGICAL_MARKERS)
        removable_passages = _dedupe([*packet.c3_compress_assets, *source_analysis.low_value_passages[:3]])
        episodes.append(
            SourceAnnotationEpisode(
                episode=packet.episode,
                source_anchor=packet.source_anchor,
                source_excerpt=packet.source_excerpt,
                core_conflict=_packet_core_conflict(packet, story_bible.mainline),
                must_keep_events=must_keep_events,
                must_keep_assets=must_keep_assets,
                must_keep_lines=packet.golden_lines,
                psychological_beats=psychological_beats,
                visual_assets=_dedupe(packet.c2_visual_assets),
                removable_passages=removable_passages,
                forbidden_changes=_dedupe(
                    [*packet.c4_forbidden_additions, *story_bible.forbidden_changes]
                ),
                active_party=packet.active_party,
                key_decision_timing=packet.key_decision_timing,
            )
        )

    return SourceAnnotation(
        north_star="原文标注稿是首稿最高优先级基准",
        global_must_keep=_dedupe(story_bible.immutable_facts),
        global_forbidden_changes=story_bible.forbidden_changes,
        removable_passages=source_analysis.low_value_passages,
        episodes=episodes,
    )


def build_episode_cut_table(
    *,
    episode_context: EpisodeContext,
    episode_source_packets: EpisodeSourcePackets,
) -> EpisodeCutTable:
    cuts: list[EpisodeCut] = []
    for packet in episode_source_packets.packets:
        core_conflict = _packet_core_conflict(packet, packet.source_excerpt[:40])
        cuts.append(
            EpisodeCut(
                episode=packet.episode,
                source_anchor=packet.source_anchor,
                core_conflict=core_conflict,
                title_seed=core_conflict[:18],
                ending_hook_seed=packet.handoff_requirement
                or (packet.c1_must_keep_assets[-1] if packet.c1_must_keep_assets else core_conflict),
            )
        )
    return EpisodeCutTable(
        target_episode_range=episode_context.target_episode_range,
        cuts=cuts,
    )
