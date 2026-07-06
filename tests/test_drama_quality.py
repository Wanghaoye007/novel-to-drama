from novel_drama_engine.demo import demo_round_outputs
from novel_drama_engine.drama_quality import (
    build_drama_quality_report,
    merge_drama_quality_into_report,
)
from novel_drama_engine.models import (
    EpisodeScript,
    QualityReport,
    QualityScores,
    QualityStatus,
    Scene,
    SceneLine,
    ScriptBatch,
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


def test_merge_drama_quality_marks_usable_report_for_review_when_drama_fails():
    weak_batch = ScriptBatch(
        episodes=[
            EpisodeScript(
                episode=1,
                title="弱戏",
                hook_3s="她来了。",
                main_emotion="平",
                watch_reason="信息不足。",
                scenes=[
                    Scene(
                        heading="1-1 日-内-屋内",
                        characters=["甲", "乙"],
                        lines=[
                            SceneLine(kind="action", text="△甲站着。"),
                            SceneLine(kind="dialogue", speaker="甲", text="你好。"),
                            SceneLine(kind="dialogue", speaker="乙", text="嗯。"),
                        ],
                    )
                ],
                cliffhanger="她来了。",
                state_update={},
            )
        ]
    )
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

    drama_report = build_drama_quality_report(
        script_batch=weak_batch,
        quality_report=quality_report,
    )
    merged = merge_drama_quality_into_report(quality_report, drama_report)

    assert merged.status == QualityStatus.NEEDS_HUMAN_REVIEW
    assert any("drama_quality" in issue for issue in merged.blocking_issues)
