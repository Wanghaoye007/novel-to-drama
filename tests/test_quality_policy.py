from novel_drama_engine.models import QualityReport, QualityScores, QualityStatus
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


def test_quality_policy_preserves_source_continuity_and_structure_as_hard_issues():
    decision = partition_quality_issues(
        [
            "source_evidence: EP02 缺少原文资产：雪地烟火激吻",
            "EP03 character knowledge conflict: 提前知道秘密",
            "script episodes mismatch target range EP01-EP05",
            "EP01 hook is too weak",
        ]
    )

    assert len(decision.hard_issues) == 3
    assert decision.advisory_issues == ["EP01 hook is too weak"]


def test_quality_decision_extracts_only_precisely_located_repair_targets():
    decision = decide_quality(
        [
            "EP01 source_evidence: 缺少原文资产：生日宴羞辱",
            "EP03-EP04 character knowledge conflict: 提前知道秘密",
            "source_asset_preservation：关键资产缺失，未定位具体集数",
            "EP02 hook is too weak",
        ],
        valid_episode_numbers=[1, 2, 3, 4],
    )

    assert decision.repair_targets == [1, 3, 4]
    assert decision.unscoped_hard_issues == [
        "source_asset_preservation：关键资产缺失，未定位具体集数"
    ]


def test_quality_policy_blocks_only_structural_collapse_not_normal_density_gaps():
    result = apply_quality_policy(
        _report(
            "EP01 too short: 320 chars, expected >= 750",
            "EP01 has 1 scenes, expected >= 2",
            "EP01 has 3 visible scene lines, expected >= 28",
        )
    )

    assert result.status == QualityStatus.NEEDS_REWRITE
    assert result.blocking_issues == [
        "EP01 has 1 scenes, expected >= 2",
        "EP01 has 3 visible scene lines, expected >= 28",
    ]
    assert result.advisory_warnings == ["EP01 too short: 320 chars, expected >= 750"]


def test_quality_policy_reopens_hard_issue_for_a_single_repair_pass():
    report = _report("source_evidence: EP01 缺少原文资产：雪地烟火")
    report = report.model_copy(update={"status": QualityStatus.NEEDS_HUMAN_REVIEW})

    result = apply_quality_policy(report)

    assert result.status == QualityStatus.NEEDS_REWRITE
    assert result.blocking_issues == ["source_evidence: EP01 缺少原文资产：雪地烟火"]


def test_quality_policy_preserves_known_source_integrity_blockers():
    decision = decide_quality(
        [
            "adaptation_quality: original strong hook appears dropped instead of being preserved or visibly upgraded",
            "adaptation_quality: 主角情绪/主动权递进漂移：脚本过早写成全知全能式开杀。",
            "adaptation_quality: 故事事件账本阻断：身份揭晓在 EP03、EP04 重复兑现。",
            "source anchor not evidenced in script: 雪地烟火激吻",
            "source_unverified: 上游锚点未能从原文证实",
        ],
        valid_episode_numbers=[1, 2, 3, 4],
    )

    assert len(decision.hard_issues) == 4
    assert decision.repair_targets == [3, 4]
    assert decision.advisory_issues == ["source_unverified: 上游锚点未能从原文证实"]
