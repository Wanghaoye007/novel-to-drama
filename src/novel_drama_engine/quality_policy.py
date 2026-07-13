from __future__ import annotations

from collections.abc import Iterable
import re

from novel_drama_engine.models import QualityDecision, QualityReport, QualityStatus
from novel_drama_engine.quality_text import dedupe_quality_items, merge_rewrite_instructions


HARD_FACT_TOKENS = (
    "adaptation_quality:",
    "methodology_quality:",
    "source_evidence:",
    "source_evidence",
    "source evidence",
    "source_asset_preservation",
    "source asset preservation",
    "source fidelity",
    "source_fact",
    "source fact",
    "source_similarity",
    "source similarity",
    "source anchor not evidenced",
    "original strong hook appears dropped",
    "source opening tension asset",
    "forbidden addition/reveal",
    "故事事件账本阻断",
    "缺少可见证据链",
    "源文相似",
    "原文相似",
    "原文偏离",
    "原文事实",
    "原文资产",
    "强原文",
    "方法论阻断",
    "c0/c1",
    "c0",
    "c1",
    "intent_drift",
    "ooc",
    "人设偏离",
    "人物动机",
    "主动方",
    "主动权",
    "关键决定",
    "证据来源",
    "提前知道",
    "knowledge conflict",
    "character knowledge",
    "forbidden reveal",
    "泄露",
    "时间线",
    "timeline conflict",
    "timeline mismatch",
    "因果错误",
    "因果冲突",
    "因果断裂",
    "因果颠倒",
    "causality conflict",
    "causality mismatch",
    "causal contradiction",
    "事件顺序",
    "continuity conflict",
    "continuity mismatch",
    "跨集承接",
    "状态冲突",
    "context conflict",
    "handoff",
    "missing required fact",
    "主动索取",
    "现场冲动决定",
    "全知全能式开杀",
    "支持型角色主动权越界",
    "对手行动线空心",
)

HARD_STRUCTURE_TOKENS = (
    "script episodes mismatch",
    "duplicate episode",
    "target_episode_range is malformed",
    "missing episode",
    "non-shooting scene headings",
    "invalid scene heading",
    "output structure",
    "schema validation",
    "malformed json",
    "episode changed from",
    "empty script",
    "no scenes",
)

ADVISORY_TOKENS = (
    "hook",
    "opening does not explode",
    "high-pressure dialogue",
    "too short",
    "too long",
    "action lines",
    "voiced lines",
    "camera direction",
    "shot language",
    "shot-to-shot",
    "cliffhanger",
    "novelty",
    "重复",
    "重复句",
    "情绪",
    "drama quality",
    "overall drama quality",
    "pipeline output is not better",
    "baseline",
    "source_missing",
    "source missing",
    "source_unverified",
    "source unverified",
)


_SCENE_COUNT_RE = re.compile(r"\bhas\s+(\d+)\s+scenes\b", re.IGNORECASE)
_VISIBLE_LINE_COUNT_RE = re.compile(
    r"\bhas\s+(\d+)\s+visible scene lines\b", re.IGNORECASE
)
_EPISODE_RANGE_RE = re.compile(
    r"(?:\bEP\s*0*|第\s*0*)(\d{1,3})(?:\s*集)?\s*"
    r"(?:-|~|–|—|至|到)\s*(?:EP\s*)?0*(\d{1,3})",
    re.IGNORECASE,
)
_EPISODE_REF_RES = (
    re.compile(r"\bEP\s*0*(\d{1,3})\b", re.IGNORECASE),
    re.compile(r"第\s*0*(\d{1,3})\s*集"),
)


def _normalized(issue: str) -> str:
    return " ".join(issue.lower().split())


def _is_structural_collapse(normalized: str) -> bool:
    scene_match = _SCENE_COUNT_RE.search(normalized)
    if scene_match and int(scene_match.group(1)) < 2:
        return True
    line_match = _VISIBLE_LINE_COUNT_RE.search(normalized)
    return bool(line_match and int(line_match.group(1)) < 8)


def is_hard_quality_issue(issue: str) -> bool:
    normalized = _normalized(issue)
    if not normalized:
        return False
    if _is_structural_collapse(normalized):
        return True
    # Drama scoring reports include recommendations such as "补足人物动机".
    # Those are not proof that a factual boundary is broken. Only explicit
    # source/knowledge-state evidence from that producer can trigger repair.
    if normalized.startswith("drama_quality:"):
        return any(
            token in normalized
            for token in (
                "source_asset_preservation",
                "source_evidence",
                "source fidelity",
                "intent_drift",
                "ooc",
                "knowledge conflict",
                "character knowledge",
            )
        )
    if any(token in normalized for token in HARD_FACT_TOKENS):
        return True
    if any(token in normalized for token in HARD_STRUCTURE_TOKENS):
        return True
    if any(token in normalized for token in ADVISORY_TOKENS):
        return False
    # A quality producer may use a new wording. Unknown findings are visible,
    # but never earn a destructive automatic rewrite until classified.
    return False


def _episode_targets_in_text(text: str) -> set[int]:
    targets: set[int] = set()
    for start_text, end_text in _EPISODE_RANGE_RE.findall(text):
        start, end = sorted((int(start_text), int(end_text)))
        targets.update(range(start, end + 1))
    for pattern in _EPISODE_REF_RES:
        targets.update(int(value) for value in pattern.findall(text))
    return targets


def decide_quality(
    issues: Iterable[str],
    *,
    valid_episode_numbers: Iterable[int] | None = None,
) -> QualityDecision:
    hard: list[str] = []
    advisory: list[str] = []
    repair_targets: set[int] = set()
    unscoped_hard: list[str] = []
    valid = set(valid_episode_numbers) if valid_episode_numbers is not None else None
    for issue in issues:
        text = str(issue).strip()
        if not text:
            continue
        if is_hard_quality_issue(text):
            hard.append(text)
            targets = _episode_targets_in_text(text)
            if valid is not None:
                targets &= valid
            if targets:
                repair_targets.update(targets)
            else:
                unscoped_hard.append(text)
        else:
            advisory.append(text)
    return QualityDecision(
        hard_issues=dedupe_quality_items(hard),
        advisory_issues=dedupe_quality_items(advisory),
        repair_targets=sorted(repair_targets),
        unscoped_hard_issues=dedupe_quality_items(unscoped_hard),
    )


def partition_quality_issues(issues: Iterable[str]) -> QualityDecision:
    """Compatibility alias for consumers that only need hard/advisory buckets."""
    return decide_quality(issues)


def apply_quality_policy(
    report: QualityReport,
    *,
    additional_issues: Iterable[str] = (),
) -> QualityReport:
    issues = [
        *report.blocking_issues,
        *report.advisory_warnings,
        *additional_issues,
    ]
    if report.status == QualityStatus.CONTEXT_CONFLICT:
        issues.append("context conflict")
    decision = decide_quality(issues)
    rewrite_instruction = ""
    if decision.hard_issues:
        rewrite_instruction = merge_rewrite_instructions(
            [report.rewrite_instruction, *decision.hard_issues],
            blocking=True,
        )
    # This policy is used before repair as well as at terminal gates. It only
    # classifies the finding; the terminal pipeline decides when a used repair
    # budget must become human review.
    status = (
        QualityStatus.NEEDS_REWRITE
        if decision.hard_issues
        else QualityStatus.USABLE
    )
    return report.model_copy(
        update={
            "status": status,
            "blocking_issues": decision.hard_issues,
            "advisory_warnings": decision.advisory_issues,
            "rewrite_instruction": rewrite_instruction,
        }
    )
