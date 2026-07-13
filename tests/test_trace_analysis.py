import json

from novel_drama_engine.trace_analysis import (
    analyze_round_trace_artifacts,
    render_prompt_trace_analysis,
)


def test_trace_analysis_identifies_first_failed_llm_stage(tmp_path):
    round_dir = tmp_path / "round_001"
    round_dir.mkdir()
    (round_dir / "run_manifest.json").write_text(
        json.dumps(
            {
                "cache_status": "completed",
                "cache_status_reason": "fresh run completed",
                "experiment_mode": True,
                "trace_prompts": True,
            }
        ),
        encoding="utf-8",
    )
    (round_dir / "runtime_report.json").write_text(
        json.dumps(
            {
                "llm_calls": [
                    {
                        "stage": "source_analysis",
                        "response_model": "SourceAnalysis",
                        "duration_ms": 120,
                        "status": "succeeded",
                    },
                    {
                        "stage": "script_batch",
                        "response_model": "ScriptBatch",
                        "duration_ms": 980,
                        "status": "failed",
                        "error": "invalid json",
                    },
                ]
            }
        ),
        encoding="utf-8",
    )
    (round_dir / "prompt_trace.json").write_text(
        json.dumps(
            [
                {
                    "call_index": 0,
                    "stage": "source_analysis",
                    "response_model": "SourceAnalysis",
                    "system_prompt_chars": 10,
                    "user_prompt_chars": 20,
                    "system_prompt_sha256": "a",
                    "user_prompt_sha256": "b",
                },
                {
                    "call_index": 1,
                    "stage": "script_batch",
                    "response_model": "ScriptBatch",
                    "system_prompt_chars": 100,
                    "user_prompt_chars": 200,
                    "system_prompt_sha256": "c",
                    "user_prompt_sha256": "d",
                },
            ]
        ),
        encoding="utf-8",
    )
    (round_dir / "raw_llm_output.jsonl").write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "call_index": 0,
                        "stage": "source_analysis",
                        "response_model": "SourceAnalysis",
                        "status": "succeeded",
                        "raw_response_sha256": "ok",
                        "raw_response": {"value": "ok"},
                    }
                ),
                json.dumps(
                    {
                        "call_index": 1,
                        "stage": "script_batch",
                        "response_model": "ScriptBatch",
                        "status": "failed",
                        "error": "invalid json",
                        "raw_response_sha256": "bad",
                        "raw_response": "not json",
                    }
                ),
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    (round_dir / "quality_report.json").write_text(
        json.dumps({"status": "red", "blocking_issues": ["script too thin"]}),
        encoding="utf-8",
    )
    (round_dir / "drama_quality_report.json").write_text(
        json.dumps({"overall_score": 5.5, "blocking_issues": ["dialogue is flat"]}),
        encoding="utf-8",
    )

    report = analyze_round_trace_artifacts(round_dir, round_number=1)
    rendered = render_prompt_trace_analysis(report)

    assert report.cache_status == "completed"
    assert report.suspected_failure_stage == "script_batch"
    assert report.failed_llm_calls == 1
    assert report.max_prompt_chars == 300
    assert "script too thin" in report.blocking_issues
    assert "script_batch" in rendered
    assert "drama 5.5" in rendered


def test_trace_analysis_reports_missing_optional_prompt_trace(tmp_path):
    round_dir = tmp_path / "round_001"
    round_dir.mkdir()
    (round_dir / "run_manifest.json").write_text(
        json.dumps({"cache_status": "completed", "trace_prompts": False}),
        encoding="utf-8",
    )
    (round_dir / "runtime_report.json").write_text(
        json.dumps(
            {
                "llm_calls": [
                    {
                        "stage": "source_analysis",
                        "response_model": "SourceAnalysis",
                        "status": "succeeded",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    (round_dir / "raw_llm_output.jsonl").write_text(
        json.dumps(
            {
                "call_index": 0,
                "stage": "source_analysis",
                "response_model": "SourceAnalysis",
                "status": "succeeded",
                "raw_response": {"ok": True},
            }
        )
        + "\n",
        encoding="utf-8",
    )

    report = analyze_round_trace_artifacts(round_dir, round_number=1)

    assert report.artifacts_present["prompt_trace.json"] is False
    assert report.stage_summaries[0].notes == ["missing prompt trace"]
    assert "NOVEL_DRAMA_TRACE_PROMPTS=1" in report.recommendations[0]
