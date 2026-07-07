from __future__ import annotations

from collections import Counter

from novel_drama_engine.models import (
    AdaptationQualityReport,
    DramaQualityComparison,
    DramaQualityDimension,
    DramaQualityReport,
    EpisodeScript,
    QualityReport,
    QualityStatus,
    ScriptBatch,
)
from novel_drama_engine.script_quality import (
    episode_quality_metrics,
    episode_quality_warnings,
    has_explanatory_or_value_summary,
)


SOURCE_FIDELITY_BLOCKING_WARNING_TOKENS = (
    "未追踪",
    "新增多个",
    "替模型补剧情",
    "原文偏离",
    "OOC",
    "主动方",
    "主动权",
    "动机",
    "全知全能",
    "证据链",
    "时间线",
    "现场冲动",
    "主动索取",
    "开场张力",
    "opening tension",
    "untracked",
    "introduced multiple",
    "speaking characters",
)


def _clamp(value: int) -> int:
    return max(0, min(10, value))


def _dimension_status(score: int, *, blocking_at: int = 5) -> str:
    if score <= blocking_at:
        return "blocking"
    if score <= 7:
        return "advisory"
    return "passed"


def _dimension(
    name,
    score: int,
    *,
    evidence: list[str] | None = None,
    suggestion: str = "",
    blocking_at: int = 5,
) -> DramaQualityDimension:
    score = _clamp(score)
    return DramaQualityDimension(
        name=name,
        score=score,
        status=_dimension_status(score, blocking_at=blocking_at),
        evidence=evidence or [],
        suggestion=suggestion,
    )


def _all_episode_warnings(script_batch: ScriptBatch) -> list[str]:
    return [
        warning
        for episode in script_batch.episodes
        for warning in episode_quality_warnings(episode)
    ]


def _line_texts(episode: EpisodeScript, *, kinds: set[str] | None = None) -> list[str]:
    texts: list[str] = []
    for scene in episode.scenes:
        for line in scene.lines:
            if kinds is not None and line.kind not in kinds:
                continue
            if line.speaker:
                texts.append(f"{line.speaker} {line.emotion or ''} {line.text}".strip())
            else:
                texts.append(line.text)
    return texts


def _dialogue_samples(script_batch: ScriptBatch, limit: int = 4) -> list[str]:
    samples: list[str] = []
    for episode in script_batch.episodes:
        for text in _line_texts(episode, kinds={"dialogue", "os", "vo"}):
            if has_explanatory_or_value_summary(text) or len(text) > 34:
                samples.append(f"EP{episode.episode:02d} {text[:80]}")
                if len(samples) >= limit:
                    return samples
    return samples


def _emotion_turn_count(episode: EpisodeScript) -> int:
    emotions = [episode.main_emotion.strip()] if episode.main_emotion.strip() else []
    for scene in episode.scenes:
        for line in scene.lines:
            if line.emotion and line.emotion.strip():
                emotions.append(line.emotion.strip())
    return len(set(emotions))


def _score_from_metrics(script_batch: ScriptBatch, quality_report: QualityReport | None) -> tuple[list[DramaQualityDimension], list[str]]:
    warnings = _all_episode_warnings(script_batch)
    warning_text = "\n".join(warnings)
    metrics = [episode_quality_metrics(episode) for episode in script_batch.episodes]
    episode_count = max(1, len(metrics))

    avg_long_voiced = sum(item.long_voiced_lines for item in metrics) / episode_count
    avg_explanatory = sum(item.explanatory_voiced_lines for item in metrics) / episode_count
    avg_strong_lines = sum(item.strong_lines for item in metrics) / episode_count
    avg_opening_conflict = sum(item.opening_conflict_lines for item in metrics) / episode_count
    avg_action_lines = sum(item.action_lines for item in metrics) / episode_count
    avg_voiced_lines = sum(item.voiced_lines for item in metrics) / episode_count
    avg_emotion_turns = sum(_emotion_turn_count(ep) for ep in script_batch.episodes) / episode_count
    critically_underfilled = avg_action_lines < 3 or avg_voiced_lines < 5

    character_penalty = 0
    for token in ["intent_drift", "character", "OOC", "动机", "主动方", "人物"]:
        if token in warning_text:
            character_penalty += 1
    character_score = 8 - character_penalty

    conflict_base = quality_report.scores.conflict if quality_report else 7
    conflict_score = conflict_base
    if avg_action_lines < 6 or avg_voiced_lines < 8:
        conflict_score -= 2
    if critically_underfilled:
        conflict_score = min(conflict_score, 4)
    if avg_opening_conflict < 1:
        conflict_score -= 1

    emotion_score = 6 + min(3, int(avg_emotion_turns))
    if any("OS at" in warning for warning in warnings):
        emotion_score -= 1
    if avg_strong_lines < 1:
        emotion_score -= 1
    if critically_underfilled:
        emotion_score = min(emotion_score, 4)

    dialogue_score = 9 - int(avg_long_voiced) - int(avg_explanatory)
    if avg_voiced_lines < 5:
        dialogue_score = min(dialogue_score, 5)
    if _dialogue_samples(script_batch):
        dialogue_score -= 1

    hook_score = (
        round((quality_report.scores.hook + quality_report.scores.cliffhanger) / 2)
        if quality_report
        else 7
    )
    if any("cliffhanger" in warning for warning in warnings):
        hook_score -= 1
    if critically_underfilled:
        hook_score = min(hook_score, 5)

    dimensions = [
        _dimension(
            "character_integrity",
            character_score,
            evidence=[warning for warning in warnings if "character" in warning or "动机" in warning][:3],
            suggestion="回到 Story Bible 和 C0 事实，修正人物主动方、动机和说话气质。",
        ),
        _dimension(
            "conflict_causality",
            conflict_score,
            evidence=[
                f"avg_action_lines={avg_action_lines:.1f}",
                f"avg_voiced_lines={avg_voiced_lines:.1f}",
            ],
            suggestion="补清楚谁主动做了什么、对手如何反制、当场后果是什么。",
        ),
        _dimension(
            "emotional_progression",
            emotion_score,
            evidence=[f"avg_emotion_turns={avg_emotion_turns:.1f}"],
            suggestion="补足震惊、克制、反击、失落或爽点的递进，不要一上来全知全能开杀。",
        ),
        _dimension(
            "dialogue_naturalness",
            dialogue_score,
            evidence=_dialogue_samples(script_batch),
            suggestion="删掉解释型长句，把信息藏进短对白、停顿、动作和潜台词。",
        ),
        _dimension(
            "hook_and_cliffhanger",
            hook_score,
            evidence=[warning for warning in warnings if "cliffhanger" in warning][:3],
            suggestion="把开场钩子和结尾钩子写成已经演出来的动作/道具/短台词。",
        ),
    ]
    return dimensions, warnings


def _source_asset_dimension(
    adaptation_quality_report: AdaptationQualityReport | None,
) -> DramaQualityDimension:
    if adaptation_quality_report is None:
        return _dimension(
            "source_asset_preservation",
            7,
            evidence=["no adaptation_quality_report"],
            suggestion="需要结合原文 C0/C1 和 source fidelity report 复核。",
            blocking_at=4,
        )

    fidelity = adaptation_quality_report.source_fidelity
    score = round(fidelity.score / 10)
    evidence = [
        *fidelity.blocking_warnings[:2],
        *fidelity.advisory_warnings[:2],
    ]
    if fidelity.score < 50:
        evidence.insert(0, f"source similarity below 5/10: {fidelity.score}/100")
        score = min(score, 4)
    evidence_text = "\n".join(evidence)
    has_source_blocker = bool(fidelity.blocking_warnings) or any(
        token in evidence_text for token in SOURCE_FIDELITY_BLOCKING_WARNING_TOKENS
    )
    if has_source_blocker:
        score = min(score, 4)
    return _dimension(
        "source_asset_preservation",
        score,
        evidence=evidence,
        suggestion="恢复原文强冲突、关键情绪和不可改事实，避免为了爽点改掉核心逻辑。",
        blocking_at=4,
    )


def _overall(dimensions: list[DramaQualityDimension]) -> int:
    if not dimensions:
        return 0
    weights = Counter(
        {
            "character_integrity": 2,
            "conflict_causality": 2,
            "emotional_progression": 2,
            "dialogue_naturalness": 1,
            "source_asset_preservation": 2,
            "hook_and_cliffhanger": 1,
        }
    )
    weighted_total = sum(item.score * weights[item.name] for item in dimensions)
    total_weight = sum(weights[item.name] for item in dimensions)
    return _clamp(round(weighted_total / total_weight))


def _baseline_score(script_batch: ScriptBatch) -> int:
    dimensions, _ = _score_from_metrics(script_batch, None)
    dimensions.append(_dimension("source_asset_preservation", 7, blocking_at=4))
    return _overall(dimensions)


def _comparison(
    *,
    pipeline_score: int,
    baseline_script_batch: ScriptBatch | None,
) -> DramaQualityComparison | None:
    if baseline_script_batch is None:
        return None
    baseline_score = _baseline_score(baseline_script_batch)
    delta = pipeline_score - baseline_score
    if delta >= 2:
        verdict = "pipeline_clearly_better"
        reason = "pipeline overall score is at least 2 points above the direct baseline."
    elif delta == 1:
        verdict = "pipeline_slightly_better"
        reason = "pipeline is better, but the margin is not yet a clear win."
    elif delta == 0:
        verdict = "tie"
        reason = "pipeline did not beat the direct baseline."
    else:
        verdict = "baseline_better"
        reason = "direct baseline scored higher than the pipeline output."
    return DramaQualityComparison(
        baseline_overall_score=baseline_score,
        pipeline_overall_score=pipeline_score,
        delta=delta,
        verdict=verdict,
        reason=reason,
    )


def _blocking_issue_text(dimension: DramaQualityDimension) -> str:
    issue = f"{dimension.name}: {dimension.suggestion}"
    if dimension.evidence:
        issue += " 证据：" + "；".join(dimension.evidence[:3])
    return issue


def build_drama_quality_report(
    *,
    script_batch: ScriptBatch,
    quality_report: QualityReport | None = None,
    adaptation_quality_report: AdaptationQualityReport | None = None,
    baseline_script_batch: ScriptBatch | None = None,
) -> DramaQualityReport:
    dimensions, warnings = _score_from_metrics(script_batch, quality_report)
    source_asset_dimension = _source_asset_dimension(adaptation_quality_report)
    dimensions.append(source_asset_dimension)
    overall = _overall(dimensions)
    if source_asset_dimension.status == "blocking":
        overall = min(overall, 5 if source_asset_dimension.score <= 2 else 6)
    blocking_issues = [
        _blocking_issue_text(dimension)
        for dimension in dimensions
        if dimension.status == "blocking"
    ]
    advisory_warnings = [
        f"{dimension.name}: {dimension.suggestion}"
        for dimension in dimensions
        if dimension.status == "advisory"
    ]
    if overall < 7 and not blocking_issues:
        advisory_warnings.append("overall drama quality below delivery target")
    comparison = _comparison(
        pipeline_score=overall,
        baseline_script_batch=baseline_script_batch,
    )
    if comparison and comparison.verdict in {"tie", "baseline_better"}:
        blocking_issues.append(
            "pipeline output is not better than the direct LLM baseline"
        )
    elif comparison and comparison.verdict == "pipeline_slightly_better":
        advisory_warnings.append(
            "pipeline output only slightly beats the direct LLM baseline"
        )

    rewrite_parts = [
        issue.replace(": ", "：") for issue in [*blocking_issues, *advisory_warnings]
    ]
    if warnings:
        rewrite_parts.append("本地戏剧质检证据：" + "；".join(warnings[:5]))

    return DramaQualityReport(
        overall_score=overall,
        dimensions=dimensions,
        blocking_issues=blocking_issues,
        advisory_warnings=advisory_warnings,
        rewrite_instruction="；".join(rewrite_parts),
        baseline_comparison=comparison,
    )


def merge_drama_quality_into_report(
    quality_report: QualityReport,
    drama_quality_report: DramaQualityReport,
) -> QualityReport:
    if not drama_quality_report.blocking_issues and drama_quality_report.overall_score >= 7:
        return quality_report
    if not drama_quality_report.blocking_issues:
        return quality_report
    issues = [*quality_report.blocking_issues]
    issues.extend(
        f"drama_quality: {issue}"
        for issue in drama_quality_report.blocking_issues
    )
    if drama_quality_report.overall_score < 7:
        issues.append(
            f"drama_quality overall below target: {drama_quality_report.overall_score}/10"
        )
    rewrite_instruction = "；".join(
        part
        for part in [
            quality_report.rewrite_instruction,
            drama_quality_report.rewrite_instruction,
        ]
        if part.strip()
    )
    status = quality_report.status
    if status == QualityStatus.USABLE:
        status = QualityStatus.NEEDS_HUMAN_REVIEW
    return quality_report.model_copy(
        update={
            "status": status,
            "blocking_issues": issues,
            "rewrite_instruction": rewrite_instruction,
        }
    )


def render_drama_quality_report(report: DramaQualityReport) -> str:
    lines = [f"戏剧质量总分：{report.overall_score}/10"]
    if report.baseline_comparison:
        comparison = report.baseline_comparison
        lines.append(
            "Baseline 对照："
            f"pipeline {comparison.pipeline_overall_score}/10 vs "
            f"direct {comparison.baseline_overall_score}/10，"
            f"delta={comparison.delta}，{comparison.verdict}"
        )
    lines.append("")
    for dimension in report.dimensions:
        lines.append(
            f"- {dimension.name}: {dimension.score}/10 {dimension.status}"
        )
        if dimension.evidence:
            lines.append(f"  证据：{'；'.join(dimension.evidence[:3])}")
        if dimension.suggestion:
            lines.append(f"  建议：{dimension.suggestion}")
    if report.blocking_issues:
        lines.append("")
        lines.append("阻断：")
        lines.extend(f"- {item}" for item in report.blocking_issues)
    if report.advisory_warnings:
        lines.append("")
        lines.append("建议关注：")
        lines.extend(f"- {item}" for item in report.advisory_warnings)
    return "\n".join(lines)
