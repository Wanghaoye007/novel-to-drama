from novel_drama_engine.demo import demo_round_outputs
from novel_drama_engine.drama_quality import (
    build_drama_quality_report,
    merge_drama_quality_into_report,
)
from novel_drama_engine.models import (
    AdaptationQualityReport,
    ContinuityAuditReport,
    DramaQualityReport,
    EpisodeScript,
    QualityReport,
    QualityScores,
    QualityStatus,
    Scene,
    SceneLine,
    ScriptBatch,
    SourceFidelityReport,
    StoryStateLedger,
)


def test_drama_quality_report_scores_demo_script_as_deliverable():
    source, context, bible, script_batch, quality_report = demo_round_outputs()[:5]

    report = build_drama_quality_report(
        script_batch=script_batch,
        quality_report=quality_report,
    )

    assert report.overall_score >= 7
    assert not report.blocking_issues
    assert {dimension.name for dimension in report.dimensions} >= {
        "character_integrity",
        "conflict_causality",
        "emotional_progression",
        "dialogue_naturalness",
        "source_asset_preservation",
        "hook_and_cliffhanger",
    }


def test_drama_quality_comparison_requires_pipeline_to_beat_baseline():
    outputs = demo_round_outputs()
    pipeline_batch = outputs[3]
    baseline_batch = ScriptBatch(episodes=[pipeline_batch.episodes[0]])

    report = build_drama_quality_report(
        script_batch=baseline_batch,
        baseline_script_batch=pipeline_batch,
    )

    assert report.baseline_comparison is not None
    assert report.baseline_comparison.verdict in {"tie", "baseline_better"}
    assert any("direct LLM baseline" in issue for issue in report.blocking_issues)


def test_merge_drama_quality_keeps_usable_report_clean_when_only_drama_score_is_low():
    quality_report = QualityReport(
        status=QualityStatus.USABLE,
        scores=QualityScores(
            hook=9,
            conflict=9,
            cliffhanger=9,
            continuity=9,
            video_feasibility=9,
        ),
        blocking_issues=[],
        rewrite_instruction="",
    )
    drama_report = DramaQualityReport(
        overall_score=6,
        blocking_issues=[],
        advisory_warnings=["情绪递进偏弱"],
        rewrite_instruction="加强情绪递进，但不阻断交付。",
    )
    merged = merge_drama_quality_into_report(quality_report, drama_report)

    assert merged.status == QualityStatus.USABLE
    assert merged.blocking_issues == []
    assert merged.rewrite_instruction == ""


def test_drama_quality_blocks_source_fidelity_warning_even_when_score_is_high(
    happy_round_outputs,
):
    script_batch = happy_round_outputs[3]
    quality_report = happy_round_outputs[4]
    adaptation_report = AdaptationQualityReport(
        source_fidelity=SourceFidelityReport(
            score=92,
            preserved_original_hook=True,
            advisory_warnings=["新增多个未追踪说话角色，疑似替模型补剧情"],
        ),
        continuity=ContinuityAuditReport(score=90),
        story_state_ledger=StoryStateLedger(current_episode=5),
    )

    report = build_drama_quality_report(
        script_batch=script_batch,
        quality_report=quality_report,
        adaptation_quality_report=adaptation_report,
    )

    assert any("source_asset_preservation" in issue for issue in report.blocking_issues)

    merged = merge_drama_quality_into_report(quality_report, report)

    assert merged.status == QualityStatus.NEEDS_HUMAN_REVIEW
    assert any("新增多个未追踪说话角色" in issue for issue in merged.blocking_issues)


def test_drama_quality_blocks_english_untracked_character_warning(
    happy_round_outputs,
):
    script_batch = happy_round_outputs[3]
    quality_report = happy_round_outputs[4]
    adaptation_report = AdaptationQualityReport(
        source_fidelity=SourceFidelityReport(
            score=94,
            preserved_original_hook=True,
            advisory_warnings=[
                "script introduced multiple untracked speaking characters: 值班医生、护士、档案员"
            ],
        ),
        continuity=ContinuityAuditReport(score=90),
        story_state_ledger=StoryStateLedger(current_episode=5),
    )

    report = build_drama_quality_report(
        script_batch=script_batch,
        quality_report=quality_report,
        adaptation_quality_report=adaptation_report,
    )

    assert any("source_asset_preservation" in issue for issue in report.blocking_issues)


def test_source_similarity_below_five_blocks_quality_gate(happy_round_outputs):
    script_batch = happy_round_outputs[3]
    quality_report = happy_round_outputs[4]
    adaptation_report = AdaptationQualityReport(
        source_fidelity=SourceFidelityReport(
            score=49,
            preserved_original_hook=True,
        ),
        continuity=ContinuityAuditReport(score=90),
        story_state_ledger=StoryStateLedger(current_episode=5),
    )

    report = build_drama_quality_report(
        script_batch=script_batch,
        quality_report=quality_report,
        adaptation_quality_report=adaptation_report,
    )
    source_dimension = next(
        dimension
        for dimension in report.dimensions
        if dimension.name == "source_asset_preservation"
    )

    assert source_dimension.score == 4
    assert source_dimension.status == "blocking"
    assert any("source_asset_preservation" in issue for issue in report.blocking_issues)

    merged = merge_drama_quality_into_report(quality_report, report)

    assert merged.status == QualityStatus.NEEDS_HUMAN_REVIEW


def test_source_asset_zero_caps_overall_drama_quality_score(happy_round_outputs):
    script_batch = happy_round_outputs[3]
    quality_report = happy_round_outputs[4]
    adaptation_report = AdaptationQualityReport(
        source_fidelity=SourceFidelityReport(
            score=0,
            preserved_original_hook=False,
            blocking_warnings=["原文关键情绪和当前集资产全部缺失"],
        ),
        continuity=ContinuityAuditReport(score=90),
        story_state_ledger=StoryStateLedger(current_episode=5),
    )

    report = build_drama_quality_report(
        script_batch=script_batch,
        quality_report=quality_report,
        adaptation_quality_report=adaptation_report,
    )

    assert report.overall_score <= 5
    assert any("source_asset_preservation" in issue for issue in report.blocking_issues)
