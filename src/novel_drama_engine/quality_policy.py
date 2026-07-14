from __future__ import annotations

from collections.abc import Iterable

from novel_drama_engine.models import (
    QualityDecision,
    QualityIssue,
    QualityIssueDisposition,
    QualityReport,
    QualityStatus,
)
from novel_drama_engine.quality_text import (
    dedupe_quality_items,
    merge_rewrite_instructions,
)


def _message(issue: QualityIssue) -> str:
    return issue.message.strip()


def _legacy_requires_human_review(items: Iterable[str]) -> bool:
    """Keep untyped factual alarms visible without granting them repair scope."""
    boundary_markers = (
        "source_",
        "source ",
        "原文",
        "源文",
        "knowledge conflict",
        "timeline conflict",
        "causality conflict",
        "continuity conflict",
        "ooc",
        "人物动机",
        "主动方",
        "事件顺序",
        "forbidden reveal",
        "schema validation",
    )
    return any(
        any(marker in item.lower() for marker in boundary_markers)
        for item in items
    )


def _is_repairable_scope(issue: QualityIssue) -> bool:
    """Only a typed issue with a concrete script node may authorize a Patch."""
    if issue.severity != "hard" or issue.episode is None or not issue.scene_id:
        return False
    if issue.target_ids:
        return True
    # Scene-heading fixes are the sole scene-level operation in Phase 1.
    return issue.code == "STRUCTURE_INVALID"


def _disposition_for_unscoped_issue(
    issue: QualityIssue,
    valid_episode_numbers: set[int] | None,
) -> QualityIssueDisposition:
    if issue.episode is not None and valid_episode_numbers is not None:
        if issue.episode not in valid_episode_numbers:
            return QualityIssueDisposition(
                issue=issue,
                disposition="out_of_range_episode",
                reason="问题集数不在当前轮次，不能把修复误投到别的剧集。",
            )
    if issue.episode is None and issue.code == "STRUCTURE_INVALID":
        return QualityIssueDisposition(
            issue=issue,
            disposition="global_structure_failure",
            reason="结构问题没有对应单集，必须人工确定重建范围。",
        )
    return QualityIssueDisposition(
        issue=issue,
        disposition="missing_scope_metadata",
        reason="硬问题缺少可验证的场次或行节点，不能自动生成 Patch。",
    )


def is_hard_quality_issue(issue: QualityIssue | str) -> bool:
    """Compatibility helper; bare strings are display-only from Phase 1 onward."""
    return isinstance(issue, QualityIssue) and issue.severity == "hard"


def decide_quality(
    issues: Iterable[QualityIssue | str],
    *,
    valid_episode_numbers: Iterable[int] | None = None,
) -> QualityDecision:
    valid = set(valid_episode_numbers) if valid_episode_numbers is not None else None
    typed: list[QualityIssue] = []
    hard_messages: list[str] = []
    advisory_messages: list[str] = []
    repair_targets: set[int] = set()
    dispositions: list[QualityIssueDisposition] = []

    for issue in issues:
        if isinstance(issue, QualityIssue):
            typed.append(issue)
            if issue.severity != "hard":
                advisory_messages.append(_message(issue))
                continue

            hard_messages.append(_message(issue))
            if _is_repairable_scope(issue) and (
                valid is None or issue.episode in valid
            ):
                repair_targets.add(issue.episode)
            else:
                dispositions.append(_disposition_for_unscoped_issue(issue, valid))
            continue

        # Historical reports and ad-hoc LLM prose may be shown to operators,
        # but free text never earns permission to mutate a script.
        text = str(issue).strip()
        if text:
            advisory_messages.append(text)

    return QualityDecision(
        issues=typed,
        hard_issues=dedupe_quality_items(hard_messages),
        advisory_issues=dedupe_quality_items(advisory_messages),
        repair_targets=sorted(repair_targets),
        unscoped_hard_issues=dedupe_quality_items(
            _message(disposition.issue) for disposition in dispositions
        ),
        unscoped_hard_dispositions=dispositions,
    )


def partition_quality_issues(
    issues: Iterable[QualityIssue | str],
) -> QualityDecision:
    """Compatibility alias for callers that only need hard/advisory buckets."""
    return decide_quality(issues)


def apply_quality_policy(
    report: QualityReport,
    *,
    additional_issues: Iterable[QualityIssue | str] = (),
) -> QualityReport:
    decision = decide_quality(
        [
            *report.issues,
            *report.blocking_issues,
            *report.advisory_warnings,
            *additional_issues,
        ]
    )
    rewrite_instruction = ""
    if decision.hard_issues:
        rewrite_instruction = merge_rewrite_instructions(
            [report.rewrite_instruction, *decision.hard_issues],
            blocking=True,
        )

    if decision.hard_issues:
        status = QualityStatus.NEEDS_REWRITE
    elif report.status == QualityStatus.NEEDS_HUMAN_REVIEW:
        # A prior stage may have rejected a Patch or found a hard issue without
        # node scope. A later advisory-only merge must not silently clear it.
        status = QualityStatus.NEEDS_HUMAN_REVIEW
    elif report.status in {
        QualityStatus.NEEDS_REWRITE,
        QualityStatus.CONTEXT_CONFLICT,
    } and _legacy_requires_human_review(report.blocking_issues):
        # Legacy reports can still signal that an operator should look, but
        # they cannot safely select text for an automatic mutation.
        status = QualityStatus.NEEDS_HUMAN_REVIEW
    else:
        status = QualityStatus.USABLE

    return report.model_copy(
        update={
            "status": status,
            "issues": decision.issues,
            "blocking_issues": decision.hard_issues,
            "advisory_warnings": decision.advisory_issues,
            "rewrite_instruction": (
                rewrite_instruction
                if decision.hard_issues
                else (report.rewrite_instruction if status == QualityStatus.NEEDS_HUMAN_REVIEW else "")
            ),
        }
    )
