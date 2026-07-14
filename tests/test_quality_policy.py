from novel_drama_engine.models import (
    QualityIssue,
    QualityReport,
    QualityScores,
    QualityStatus,
)
from novel_drama_engine.quality_policy import (
    apply_quality_policy,
    decide_quality,
    partition_quality_issues,
)


def _report(*issues: str) -> QualityReport:
    return QualityReport(
        status=QualityStatus.NEEDS_REWRITE,
        scores=QualityScores(
            hook=4,
            conflict=6,
            cliffhanger=5,
            continuity=8,
            video_feasibility=8,
        ),
        blocking_issues=list(issues),
        rewrite_instruction="旧版要求整集重写。",
    )


def test_quality_policy_demotes_style_and_density_issues_to_advisory():
    result = apply_quality_policy(
        _report(
            "EP01 too short: 664 chars, expected >= 750",
            "EP01 opening does not explode in the first 8 beats",
            "script_novelty: EP01/EP02 场景骨架重复",
            "EP01 cliffhanger is too soft",
        )
    )

    assert result.status == QualityStatus.USABLE
    assert result.blocking_issues == []
    assert len(result.advisory_warnings) == 4
    assert result.rewrite_instruction == ""


def test_quality_policy_treats_legacy_free_text_as_display_only():
    decision = partition_quality_issues(
        [
            "source_evidence: EP02 缺少原文资产：雪地烟火激吻",
            "EP03 character knowledge conflict: 提前知道秘密",
            "script episodes mismatch target range EP01-EP05",
            "EP01 hook is too weak",
        ]
    )

    assert decision.hard_issues == []
    assert decision.repair_targets == []
    assert decision.advisory_issues == [
        "source_evidence: EP02 缺少原文资产：雪地烟火激吻",
        "EP03 character knowledge conflict: 提前知道秘密",
        "script episodes mismatch target range EP01-EP05",
        "EP01 hook is too weak",
    ]


def test_quality_decision_requires_structured_node_scope_for_automatic_repair():
    decision = decide_quality(
        [
            QualityIssue(
                code="MISSING_REQUIRED_FACT",
                severity="hard",
                episode=1,
                scene_id="EP01-S01",
                target_ids=["EP01-S01-L02"],
                evidence=["原文：林晚不知道秘密"],
                message="EP01 台词把未知秘密改成已知。",
            ),
            QualityIssue(
                code="KNOWLEDGE_CONFLICT",
                severity="hard",
                episode=3,
                scene_id=None,
                evidence=["人物知识状态没有可定位节点"],
                message="EP03 提前知道秘密。",
            ),
            "EP02 hook is too weak",
        ],
        valid_episode_numbers=[1, 2, 3, 4],
    )

    assert decision.repair_targets == [1]
    assert decision.hard_issues == ["EP01 台词把未知秘密改成已知。", "EP03 提前知道秘密。"]
    assert decision.unscoped_hard_issues == ["EP03 提前知道秘密。"]
    assert decision.unscoped_hard_dispositions[0].disposition == "missing_scope_metadata"


def test_quality_policy_blocks_only_structural_collapse_not_normal_density_gaps():
    result = apply_quality_policy(
        _report("EP01 too short: 320 chars, expected >= 750").model_copy(
            update={
                "issues": [
                    QualityIssue(
                        code="STRUCTURE_INVALID",
                        severity="hard",
                        episode=1,
                        scene_id=None,
                        evidence=["only one scene"],
                        message="EP01 has 1 scenes, expected >= 2",
                    )
                ]
            }
        )
    )

    assert result.status == QualityStatus.NEEDS_REWRITE
    assert result.blocking_issues == ["EP01 has 1 scenes, expected >= 2"]
    assert "EP01 too short: 320 chars, expected >= 750" in result.advisory_warnings


def test_quality_policy_routes_legacy_blocking_reports_to_human_review_not_repair():
    report = _report("source_evidence: EP01 缺少原文资产：雪地烟火")

    result = apply_quality_policy(report)

    assert result.status == QualityStatus.NEEDS_HUMAN_REVIEW
    assert result.blocking_issues == []
    assert result.advisory_warnings == ["source_evidence: EP01 缺少原文资产：雪地烟火"]


def test_quality_policy_accepts_structured_fact_boundaries_without_keyword_matching():
    decision = decide_quality(
        [
            QualityIssue(
                code="CAUSALITY_CONFLICT",
                severity="hard",
                episode=3,
                scene_id="EP03-S02",
                target_ids=["EP03-S02-L03"],
                evidence=["原文：她早已准备解约协议"],
                message="EP03 把预谋解约改成了现场赌气。",
            ),
            "source_unverified: 上游锚点未能从原文证实",
        ],
        valid_episode_numbers=[1, 2, 3, 4],
    )

    assert decision.hard_issues == ["EP03 把预谋解约改成了现场赌气。"]
    assert decision.repair_targets == [3]
    assert decision.advisory_issues == ["source_unverified: 上游锚点未能从原文证实"]
