from __future__ import annotations

import re
from collections import Counter
from collections.abc import Iterable
from typing import Any, Literal

from novel_drama_engine.models import (
    AdaptationQualityReport,
    ContinuityAuditReport,
    ContinuityLinkReport,
    EpisodeContext,
    EpisodeScript,
    NextRoundContext,
    ScriptBatch,
    SourceAnalysis,
    SourceFidelityCheck,
    SourceFidelityReport,
    StoryBible,
    StoryStateEntry,
    StoryStateLedger,
    ViralAssetReport,
)
from novel_drama_engine.renderer import render_episode


PUNCTUATION_RE = re.compile(r"[\s，。！？、；：：“”‘’（）()《》【】\[\]·,.!?;:'\"<>-]+")
CHINESE_TOKEN_RE = re.compile(r"[\u4e00-\u9fffA-Za-z0-9]{2,}")
FORBIDDEN_PREFIX_RE = re.compile(
    r"^(?:不得|禁止|不能|不要|严禁|避免|拒绝|不许|不可|不应|不准|别)"
)
WEAK_FORBIDDEN_WORDS = {
    "新增",
    "提前",
    "一次性",
    "全部",
    "完全",
    "无代价",
    "机械",
    "模板",
    "救场",
    "退场",
    "真相",
    "公开",
    "本轮",
    "过早",
    "完整",
    "结果",
    "泄露",
    "揭露",
}
GENERIC_CHARACTER_NAMES = {
    "黑幕",
    "画外",
    "旁白",
    "VO",
    "OS",
    "众人",
    "宾客",
    "围观百姓",
    "录音",
}


def normalize_text(value: str) -> str:
    return PUNCTUATION_RE.sub("", value).lower()


def _tokens(value: str) -> list[str]:
    raw = [token for token in CHINESE_TOKEN_RE.findall(value) if len(token) >= 2]
    expanded: list[str] = []
    for token in raw:
        if token in WEAK_FORBIDDEN_WORDS or token.isdigit():
            continue
        expanded.append(token)
        if re.fullmatch(r"[\u4e00-\u9fff]{4,}", token):
            expanded.extend(
                chunk
                for chunk in (token[index : index + 2] for index in range(0, len(token) - 1))
                if chunk not in WEAK_FORBIDDEN_WORDS
            )
    return list(dict.fromkeys(expanded))


def _loose_contains(haystack: str, needle: str) -> bool:
    normalized_needle = normalize_text(needle)
    if not normalized_needle:
        return True
    normalized_haystack = normalize_text(haystack)
    if normalized_needle in normalized_haystack:
        return True

    tokens = _tokens(needle)
    if not tokens:
        return True
    if len(tokens) == 1:
        return tokens[0].lower() in normalized_haystack
    matched = sum(1 for token in tokens if normalize_text(token) in normalized_haystack)
    return matched >= min(2, len(tokens))


def _evidence_for(haystack: str, needle: str, *, limit: int = 2) -> list[str]:
    evidence: list[str] = []
    lines = [line.strip() for line in haystack.splitlines() if line.strip()]
    tokens = _tokens(needle)
    for line in lines:
        if _loose_contains(line, needle) or any(_loose_contains(line, token) for token in tokens):
            evidence.append(line[:100])
            if len(evidence) >= limit:
                break
    return evidence


def _episode_texts(script_batch: ScriptBatch) -> dict[int, str]:
    return {
        episode.episode: render_episode(episode)
        for episode in script_batch.episodes
    }


def _all_script_text(script_batch: ScriptBatch) -> str:
    return "\n\n".join(_episode_texts(script_batch).values())


def _opening_text(episode: EpisodeScript, line_count: int = 8) -> str:
    lines: list[str] = [episode.title, episode.hook_3s]
    for scene in episode.scenes[:1]:
        lines.append(scene.heading)
        for line in scene.lines[:line_count]:
            if line.speaker:
                lines.append(f"{line.speaker} {line.text}")
            else:
                lines.append(line.text)
    return "\n".join(lines)


def _target_episode_number(value: str | int | None) -> int | None:
    if isinstance(value, int):
        return value
    if not isinstance(value, str):
        return None
    match = re.search(r"(?:EP|第)?\s*0*(\d{1,3})", value, flags=re.IGNORECASE)
    if not match:
        return None
    return int(match.group(1))


def _mapping_assets(mapping: object) -> list[tuple[int | None, str]]:
    if isinstance(mapping, str):
        return [(None, mapping)]
    if not hasattr(mapping, "model_dump"):
        return []
    data = mapping.model_dump()
    episode_number = _target_episode_number(data.get("target_episode"))
    assets: list[str] = []
    for key in ["source", "information_increment", "adaptation_action"]:
        value = data.get(key)
        if isinstance(value, str) and value.strip():
            assets.append(value.strip())
    retained_assets = data.get("retained_assets")
    if isinstance(retained_assets, str):
        assets.extend(asset.strip() for asset in re.split(r"[、,，;；]", retained_assets) if asset.strip())
    elif isinstance(retained_assets, list):
        assets.extend(str(asset).strip() for asset in retained_assets if str(asset).strip())
    return [(episode_number, asset) for asset in assets if asset]


def _forbidden_term(rule: str) -> str:
    term = FORBIDDEN_PREFIX_RE.sub("", rule.strip())
    term = re.sub(r"[，,。；;].*$", "", term).strip()
    for word in sorted(WEAK_FORBIDDEN_WORDS | {"在", "把", "写成", "改成"}, key=len, reverse=True):
        term = term.replace(word, "")
    tokens = [token for token in _tokens(term) if token not in WEAK_FORBIDDEN_WORDS]
    if len(tokens) >= 2:
        return "".join(tokens[:2])
    if tokens:
        return tokens[0]
    return term


def _character_name(value: str) -> str:
    name = re.sub(r"^(?:录音里的|电话里的|年轻|老|小)", "", value.strip())
    name = re.sub(r"(?:OS|VO)$", "", name, flags=re.IGNORECASE)
    return name.strip()


def _script_characters(script_batch: ScriptBatch) -> set[str]:
    names: set[str] = set()
    for episode in script_batch.episodes:
        for scene in episode.scenes:
            names.update(_character_name(character) for character in scene.characters)
            for line in scene.lines:
                if line.speaker:
                    names.add(_character_name(line.speaker))
    return {name for name in names if name and name not in GENERIC_CHARACTER_NAMES}


def _known_character_match(name: str, known_names: Iterable[str]) -> bool:
    normalized = normalize_text(name)
    if not normalized:
        return True
    for known in known_names:
        normalized_known = normalize_text(known)
        if normalized == normalized_known:
            return True
        if normalized in normalized_known or normalized_known in normalized:
            return True
    return False


def build_source_fidelity_report(
    *,
    source_text: str,
    source_analysis: SourceAnalysis,
    episode_context: EpisodeContext,
    story_bible: StoryBible,
    script_batch: ScriptBatch,
    viral_asset_report: ViralAssetReport | None = None,
) -> SourceFidelityReport:
    del viral_asset_report
    checks: list[SourceFidelityCheck] = []
    blocking: list[str] = []
    advisory: list[str] = []
    script_text = _all_script_text(script_batch)
    episode_texts = _episode_texts(script_batch)

    for fact in story_bible.immutable_facts[:8]:
        evidence = _evidence_for(script_text, fact)
        checks.append(
            SourceFidelityCheck(
                category="C0_immutable_fact",
                anchor=fact,
                status="passed" if evidence else "advisory",
                evidence=evidence,
                warning=None if evidence else "immutable fact tracked but not directly surfaced in this round",
            )
        )

    for episode_number, asset in [
        pair
        for mapping in episode_context.source_to_episode_mapping
        for pair in _mapping_assets(mapping)
    ]:
        if len(normalize_text(asset)) < 4:
            continue
        target_text = episode_texts.get(episode_number, script_text) if episode_number else script_text
        if _loose_contains(target_text, asset):
            checks.append(
                SourceFidelityCheck(
                    category="source_mapping",
                    anchor=asset,
                    episode=episode_number,
                    status="passed",
                    evidence=_evidence_for(target_text, asset),
                )
            )
            continue
        warning = f"source anchor not evidenced in script: {asset[:80]}"
        is_generic_planning_anchor = "->" in asset and re.search(
            r"(上一轮|开场|起势|继续|承接|推进)",
            asset,
        )
        if is_generic_planning_anchor:
            advisory.append(warning)
            status = "advisory"
        else:
            blocking.append(warning)
            status = "blocking"
        checks.append(
            SourceFidelityCheck(
                category="source_mapping",
                anchor=asset,
                episode=episode_number,
                status=status,
                warning=warning,
            )
        )

    visual_hits = 0
    for moment in source_analysis.visual_moments[:10]:
        if _loose_contains(script_text, moment):
            visual_hits += 1
            checks.append(
                SourceFidelityCheck(
                    category="C2_visual_asset",
                    anchor=moment,
                    status="passed",
                    evidence=_evidence_for(script_text, moment),
                )
            )
    if source_analysis.visual_moments and visual_hits == 0:
        warning = "no source visual moment is preserved in the visible script"
        advisory.append(warning)
        checks.append(
            SourceFidelityCheck(
                category="C2_visual_asset",
                anchor="; ".join(source_analysis.visual_moments[:3]),
                status="advisory",
                warning=warning,
            )
        )

    first_episode = script_batch.episodes[0] if script_batch.episodes else None
    first_opening = _opening_text(first_episode) if first_episode else ""
    original_hook_preserved = False
    for hook in source_analysis.candidate_hooks[:3]:
        if _loose_contains(first_opening, hook) or _loose_contains(script_text, hook):
            original_hook_preserved = True
            checks.append(
                SourceFidelityCheck(
                    category="hook_preservation",
                    anchor=hook,
                    episode=first_episode.episode if first_episode else None,
                    status="passed",
                    evidence=_evidence_for(first_opening or script_text, hook),
                )
            )
            break
    if source_analysis.candidate_hooks and not original_hook_preserved:
        warning = (
            "original strong hook appears dropped instead of being preserved or visibly upgraded"
        )
        blocking.append(warning)
        checks.append(
            SourceFidelityCheck(
                category="hook_preservation",
                anchor="; ".join(source_analysis.candidate_hooks[:3]),
                episode=first_episode.episode if first_episode else None,
                status="blocking",
                warning=warning,
            )
        )

    for rule in story_bible.forbidden_changes + episode_context.forbidden_reveals:
        term = _forbidden_term(rule)
        if len(normalize_text(term)) < 2:
            continue
        if _loose_contains(script_text, term):
            warning = f"forbidden addition/reveal may have leaked into script: {rule}"
            blocking.append(warning)
            checks.append(
                SourceFidelityCheck(
                    category="C4_forbidden_addition",
                    anchor=rule,
                    status="blocking",
                    evidence=_evidence_for(script_text, term),
                    warning=warning,
                )
            )

    known_names = set(source_analysis.characters) | set(story_bible.characters)
    unknown_names = sorted(
        name
        for name in _script_characters(script_batch)
        if not _known_character_match(name, known_names)
    )
    if len(unknown_names) >= 3:
        warning = "script introduced multiple untracked speaking characters: " + "、".join(unknown_names[:6])
        advisory.append(warning)
        checks.append(
            SourceFidelityCheck(
                category="character_integrity",
                anchor="、".join(unknown_names[:6]),
                status="advisory",
                warning=warning,
            )
        )

    if source_text and not any(_loose_contains(script_text, token) for token in _tokens(source_text)[:12]):
        warning = "script has weak lexical overlap with the uploaded source"
        advisory.append(warning)
        checks.append(
            SourceFidelityCheck(
                category="C1_must_keep_scene",
                anchor=source_text[:80],
                status="advisory",
                warning=warning,
            )
        )

    score = max(0, 100 - len(blocking) * 18 - len(advisory) * 6)
    return SourceFidelityReport(
        score=score,
        preserved_original_hook=original_hook_preserved,
        checks=checks,
        blocking_warnings=blocking,
        advisory_warnings=advisory,
    )


def _tail_text(episode: EpisodeScript, line_count: int = 4) -> str:
    lines: list[str] = [episode.cliffhanger]
    if episode.scenes:
        for line in episode.scenes[-1].lines[-line_count:]:
            lines.append(f"{line.speaker or ''} {line.text}".strip())
    return "\n".join(line for line in lines if line.strip())


def _token_overlap(left: str, right: str) -> int:
    left_tokens = Counter(token for token in _tokens(left) if len(token) >= 2)
    right_tokens = Counter(token for token in _tokens(right) if len(token) >= 2)
    return sum((left_tokens & right_tokens).values())


def build_continuity_audit_report(
    *,
    episode_context: EpisodeContext,
    script_batch: ScriptBatch,
    previous_context: NextRoundContext | None,
) -> ContinuityAuditReport:
    del episode_context
    links: list[ContinuityLinkReport] = []
    blocking: list[str] = []
    advisory: list[str] = []
    episodes = sorted(script_batch.episodes, key=lambda item: item.episode)

    if previous_context:
        first_episode = episodes[0] if episodes else None
        first_opening = _opening_text(first_episode) if first_episode else ""
        for hook in previous_context.open_hooks[:4]:
            if not hook.strip():
                continue
            if not _loose_contains(first_opening, hook) and _token_overlap(hook, first_opening) == 0:
                advisory.append(
                    f"previous open hook is not acknowledged in this round opening: {hook[:80]}"
                )
        all_text = _all_script_text(script_batch)
        for reveal in previous_context.forbidden_reveals[:8]:
            if reveal.strip() and _loose_contains(all_text, reveal):
                blocking.append(f"forbidden reveal leaked from previous context: {reveal}")

    for previous, current in zip(episodes, episodes[1:]):
        tail = _tail_text(previous)
        opening = _opening_text(current)
        warnings: list[str] = []
        status: Literal["passed", "advisory", "blocking"] = "passed"
        if previous.cliffhanger.strip() and _token_overlap(previous.cliffhanger, opening) == 0:
            warnings.append(
                "next episode opening does not visibly acknowledge previous cliffhanger"
            )
            advisory.append(
                f"EP{previous.episode:02d}->EP{current.episode:02d} may need opening linkage"
            )
            status = "advisory"
        links.append(
            ContinuityLinkReport(
                previous_episode=previous.episode,
                next_episode=current.episode,
                previous_cliffhanger=tail[:240],
                next_opening=opening[:240],
                status=status,
                warnings=warnings,
            )
        )

    score = max(0, 100 - len(blocking) * 25 - len(advisory) * 5)
    return ContinuityAuditReport(
        score=score,
        links=links,
        blocking_warnings=blocking,
        advisory_warnings=advisory,
    )


def _entry_value(value: Any) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, (int, float, bool)):
        return str(value)
    return repr(value)


def build_story_state_ledger(
    *,
    script_batch: ScriptBatch,
    next_round_context: NextRoundContext,
    previous_context: NextRoundContext | None,
) -> StoryStateLedger:
    entries: list[StoryStateEntry] = []
    warnings: list[str] = []

    if previous_context:
        for hook in previous_context.open_hooks:
            entries.append(
                StoryStateEntry(
                    kind="open_hook",
                    key=hook[:40],
                    value=hook,
                    status="open",
                    source="previous_context",
                )
            )
        for reveal in previous_context.forbidden_reveals:
            entries.append(
                StoryStateEntry(
                    kind="forbidden_reveal",
                    key=reveal[:40],
                    value=reveal,
                    status="forbidden",
                    source="previous_context",
                )
            )

    for episode in sorted(script_batch.episodes, key=lambda item: item.episode):
        if not episode.state_update:
            warnings.append(f"EP{episode.episode:02d} missing state_update")
        entries.append(
            StoryStateEntry(
                episode=episode.episode,
                kind="open_hook",
                key=episode.cliffhanger[:40],
                value=episode.cliffhanger,
                status="open",
                source="episode.cliffhanger",
            )
        )
        for key, value in episode.state_update.items():
            entries.append(
                StoryStateEntry(
                    episode=episode.episode,
                    kind="episode_state",
                    key=str(key),
                    value=_entry_value(value),
                    status="active",
                    source="episode.state_update",
                )
            )

    for reveal in next_round_context.forbidden_reveals:
        entries.append(
            StoryStateEntry(
                kind="forbidden_reveal",
                key=reveal[:40],
                value=reveal,
                status="forbidden",
                source="next_round_context",
            )
        )
    for character, facts in next_round_context.character_knowledge.items():
        for fact in facts:
            entries.append(
                StoryStateEntry(
                    kind="character_knowledge",
                    key=character,
                    value=fact,
                    status="active",
                    source="next_round_context",
                )
            )
    for change in next_round_context.relationship_changes:
        entries.append(
            StoryStateEntry(
                kind="relationship_change",
                key=change[:40],
                value=change,
                status="active",
                source="next_round_context",
            )
        )
    for prop in next_round_context.prop_states:
        entries.append(
            StoryStateEntry(
                kind="prop_state",
                key=prop[:40],
                value=prop,
                status="active",
                source="next_round_context",
            )
        )
    for item in next_round_context.foreshadowing_ledger:
        entries.append(
            StoryStateEntry(
                kind="foreshadowing",
                key=item[:40],
                value=item,
                status="open",
                source="next_round_context",
            )
        )

    if len(next_round_context.open_hooks) > 8:
        warnings.append("too many open hooks; next round may lose focus")

    return StoryStateLedger(
        current_episode=next_round_context.current_episode,
        entries=entries,
        open_hooks=next_round_context.open_hooks,
        forbidden_reveals=next_round_context.forbidden_reveals,
        character_knowledge=next_round_context.character_knowledge,
        relationship_changes=next_round_context.relationship_changes,
        prop_states=next_round_context.prop_states,
        foreshadowing_ledger=next_round_context.foreshadowing_ledger,
        warnings=warnings,
    )


def build_adaptation_quality_report(
    *,
    source_text: str,
    source_analysis: SourceAnalysis,
    episode_context: EpisodeContext,
    story_bible: StoryBible,
    script_batch: ScriptBatch,
    next_round_context: NextRoundContext,
    previous_context: NextRoundContext | None,
    viral_asset_report: ViralAssetReport | None = None,
) -> AdaptationQualityReport:
    source_fidelity = build_source_fidelity_report(
        source_text=source_text,
        source_analysis=source_analysis,
        episode_context=episode_context,
        story_bible=story_bible,
        script_batch=script_batch,
        viral_asset_report=viral_asset_report,
    )
    continuity = build_continuity_audit_report(
        episode_context=episode_context,
        script_batch=script_batch,
        previous_context=previous_context,
    )
    ledger = build_story_state_ledger(
        script_batch=script_batch,
        next_round_context=next_round_context,
        previous_context=previous_context,
    )
    blocking = [
        *source_fidelity.blocking_warnings,
        *continuity.blocking_warnings,
    ]
    advisory = [
        *source_fidelity.advisory_warnings,
        *continuity.advisory_warnings,
        *ledger.warnings,
    ]
    rewrite_instruction = ""
    if blocking:
        rewrite_instruction = (
            "改编一致性阻断：必须保留原著强钩子/名场面/主动方逻辑，不得泄露 forbidden reveal，"
            "不得新增 story bible 禁止项。具体问题："
            + "；".join(blocking[:6])
        )
    return AdaptationQualityReport(
        source_fidelity=source_fidelity,
        continuity=continuity,
        story_state_ledger=ledger,
        blocking_warnings=blocking,
        advisory_warnings=advisory,
        rewrite_instruction=rewrite_instruction,
    )


def merge_adaptation_quality_into_report(
    report,
    adaptation_report: AdaptationQualityReport,
):
    if not adaptation_report.blocking_warnings:
        return report
    from novel_drama_engine.models import QualityStatus

    blocking_issues = [
        *report.blocking_issues,
        *adaptation_report.blocking_warnings,
    ]
    rewrite_instruction = "；".join(
        part
        for part in [
            adaptation_report.rewrite_instruction,
            report.rewrite_instruction,
        ]
        if part
    )
    status = (
        QualityStatus.NEEDS_REWRITE
        if report.status == QualityStatus.USABLE
        else report.status
    )
    return report.model_copy(
        update={
            "status": status,
            "blocking_issues": blocking_issues,
            "rewrite_instruction": rewrite_instruction,
        }
    )
