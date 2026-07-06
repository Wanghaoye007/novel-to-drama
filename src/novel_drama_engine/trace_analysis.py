from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field


TRACE_ANALYSIS_SCHEMA_VERSION = "prompt_trace_analysis.v1"


class PromptTraceStageSummary(BaseModel):
    call_index: int | None = None
    stage: str
    response_model: str | None = None
    status: str = "unknown"
    duration_ms: int | None = None
    prompt_chars: int | None = None
    system_prompt_sha256: str | None = None
    user_prompt_sha256: str | None = None
    raw_response_sha256: str | None = None
    raw_response_chars: int | None = None
    error: str | None = None
    notes: list[str] = Field(default_factory=list)


class PromptTraceAnalysisReport(BaseModel):
    schema_version: str = TRACE_ANALYSIS_SCHEMA_VERSION
    round_number: int | None = None
    cache_status: str | None = None
    cache_status_reason: str | None = None
    experiment_mode: bool | None = None
    trace_prompts: bool | None = None
    trace_raw_outputs: bool | None = None
    artifacts_present: dict[str, bool] = Field(default_factory=dict)
    missing_artifacts: list[str] = Field(default_factory=list)
    total_llm_calls: int = 0
    failed_llm_calls: int = 0
    max_prompt_chars: int = 0
    quality_status: str | None = None
    drama_quality_score: float | None = None
    blocking_issues: list[str] = Field(default_factory=list)
    suspected_failure_stage: str | None = None
    stage_summaries: list[PromptTraceStageSummary] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)


def _read_json(path: Path) -> Any | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            parsed = json.loads(line)
        except json.JSONDecodeError:
            rows.append({"status": "invalid_jsonl", "error": line[:500]})
            continue
        if isinstance(parsed, dict):
            rows.append(parsed)
    return rows


def _dict_list(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def _safe_int(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    return None


def _safe_float(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    return None


def _raw_response_chars(value: Any) -> int | None:
    if value is None:
        return None
    return len(json.dumps(value, ensure_ascii=False, default=str))


def _calls_by_index(rows: list[dict[str, Any]]) -> dict[int, dict[str, Any]]:
    result: dict[int, dict[str, Any]] = {}
    for fallback_index, row in enumerate(rows):
        index = _safe_int(row.get("call_index"))
        result[index if index is not None else fallback_index] = row
    return result


def _runtime_calls(runtime_report: Any) -> list[dict[str, Any]]:
    if not isinstance(runtime_report, dict):
        return []
    return _dict_list(runtime_report.get("llm_calls"))


def _quality_blocking_issues(quality_report: Any, drama_quality_report: Any) -> list[str]:
    issues: list[str] = []
    if isinstance(quality_report, dict):
        issues.extend(
            str(issue)
            for issue in quality_report.get("blocking_issues", [])
            if str(issue).strip()
        )
    if isinstance(drama_quality_report, dict):
        issues.extend(
            str(issue)
            for issue in drama_quality_report.get("blocking_issues", [])
            if str(issue).strip()
        )
    return list(dict.fromkeys(issues))


def _artifact_presence(round_dir: Path) -> dict[str, bool]:
    names = [
        "run_manifest.json",
        "runtime_report.json",
        "prompt_trace.json",
        "raw_llm_output.jsonl",
        "quality_report.json",
        "drama_quality_report.json",
        "creative_script.md",
        "shooting_script.md",
        "round_result.json",
    ]
    return {name: (round_dir / name).exists() for name in names}


def analyze_round_trace_artifacts(
    round_dir: Path | str,
    *,
    round_number: int | None = None,
) -> PromptTraceAnalysisReport:
    round_path = Path(round_dir)
    artifacts_present = _artifact_presence(round_path)
    missing_artifacts = [
        name
        for name, present in artifacts_present.items()
        if not present
        and name
        in {
            "run_manifest.json",
            "runtime_report.json",
            "raw_llm_output.jsonl",
            "quality_report.json",
            "drama_quality_report.json",
        }
    ]

    run_manifest = _read_json(round_path / "run_manifest.json")
    runtime_report = _read_json(round_path / "runtime_report.json")
    prompt_trace = _dict_list(_read_json(round_path / "prompt_trace.json"))
    raw_outputs = _read_jsonl(round_path / "raw_llm_output.jsonl")
    quality_report = _read_json(round_path / "quality_report.json")
    drama_quality_report = _read_json(round_path / "drama_quality_report.json")

    prompt_by_index = _calls_by_index(prompt_trace)
    raw_by_index = _calls_by_index(raw_outputs)
    runtime_calls = _runtime_calls(runtime_report)
    runtime_by_index = _calls_by_index(runtime_calls)
    indices = sorted(
        set(prompt_by_index)
        | set(raw_by_index)
        | set(runtime_by_index)
    )

    stage_summaries: list[PromptTraceStageSummary] = []
    for index in indices:
        prompt = prompt_by_index.get(index, {})
        raw = raw_by_index.get(index, {})
        runtime_call = runtime_by_index.get(index, {})
        system_chars = _safe_int(prompt.get("system_prompt_chars")) or 0
        user_chars = _safe_int(prompt.get("user_prompt_chars")) or 0
        prompt_chars = system_chars + user_chars if prompt else None
        status = (
            raw.get("status")
            or runtime_call.get("status")
            or ("prompt_only" if prompt else "unknown")
        )
        stage = str(
            prompt.get("stage")
            or raw.get("stage")
            or runtime_call.get("stage")
            or "unknown"
        )
        notes: list[str] = []
        if not prompt:
            notes.append("missing prompt trace")
        if not raw:
            notes.append("missing raw output trace")
        if str(status) in {"failed", "invalid_jsonl"}:
            notes.append("LLM call failed or raw trace invalid")
        if prompt_chars is not None and prompt_chars >= 35000:
            notes.append("prompt is very large; consider smaller episode batches")
        stage_summaries.append(
            PromptTraceStageSummary(
                call_index=index,
                stage=stage,
                response_model=str(
                    prompt.get("response_model")
                    or raw.get("response_model")
                    or runtime_call.get("response_model")
                    or ""
                )
                or None,
                status=str(status),
                duration_ms=_safe_int(runtime_call.get("duration_ms")),
                prompt_chars=prompt_chars,
                system_prompt_sha256=(
                    str(prompt.get("system_prompt_sha256"))
                    if prompt.get("system_prompt_sha256")
                    else None
                ),
                user_prompt_sha256=(
                    str(prompt.get("user_prompt_sha256"))
                    if prompt.get("user_prompt_sha256")
                    else None
                ),
                raw_response_sha256=(
                    str(raw.get("raw_response_sha256"))
                    if raw.get("raw_response_sha256")
                    else None
                ),
                raw_response_chars=_raw_response_chars(raw.get("raw_response")),
                error=str(raw.get("error") or runtime_call.get("error") or "")
                or None,
                notes=notes,
            )
        )

    failed_summaries = [
        summary
        for summary in stage_summaries
        if summary.status not in {"succeeded", "prompt_only"}
        or any("failed" in note for note in summary.notes)
    ]
    blocking_issues = _quality_blocking_issues(quality_report, drama_quality_report)
    quality_status = (
        str(quality_report.get("status"))
        if isinstance(quality_report, dict) and quality_report.get("status")
        else None
    )
    drama_quality_score = (
        _safe_float(drama_quality_report.get("overall_score"))
        if isinstance(drama_quality_report, dict)
        else None
    )
    suspected_failure_stage: str | None = None
    if failed_summaries:
        suspected_failure_stage = failed_summaries[0].stage
    elif blocking_issues:
        suspected_failure_stage = "quality_gate"
    elif isinstance(run_manifest, dict) and run_manifest.get("cache_status") == "round_result_cache_hit":
        suspected_failure_stage = "cache_reuse"

    max_prompt_chars = max(
        [summary.prompt_chars or 0 for summary in stage_summaries] or [0]
    )
    recommendations: list[str] = []
    if not artifacts_present["prompt_trace.json"]:
        recommendations.append(
            "下次质量实验请开启 NOVEL_DRAMA_TRACE_PROMPTS=1 或 NOVEL_DRAMA_EXPERIMENT_MODE=1，才能复盘每个 agent 的实际 system/user prompt。"
        )
    if not artifacts_present["raw_llm_output.jsonl"]:
        recommendations.append(
            "缺少 raw_llm_output.jsonl，无法判断是模型原始输出差，还是 validator/renderer 后处理改差。"
        )
    if isinstance(run_manifest, dict) and run_manifest.get("cache_status") == "round_result_cache_hit":
        recommendations.append(
            "当前结果来自 round_result 缓存；prompt、模型或质检实验时应使用 NOVEL_DRAMA_EXPERIMENT_MODE=1 或关闭 NOVEL_DRAMA_RESUME_ARTIFACTS。"
        )
    if failed_summaries:
        first = failed_summaries[0]
        recommendations.append(
            f"优先检查 {first.stage} / {first.response_model or 'unknown model'} 的 raw 输出和 prompt；这是第一处失败或异常调用。"
        )
    if drama_quality_score is not None and drama_quality_score < 7:
        recommendations.append(
            "戏剧质量低于 7 分，先看 drama_quality_report.md 的人物、冲突、情绪、对白维度，不要只按格式指标修。"
        )
    if max_prompt_chars >= 35000:
        recommendations.append(
            "最大 prompt 已超过 35000 字符，建议降低单轮集数或把镜头工程化要求后移到 shooting_script 阶段。"
        )
    if not recommendations:
        recommendations.append(
            "本轮关键追踪产物齐全；如脚本仍差，可直接对照 prompt_trace_analysis.md、drama_quality_report.md 和 raw_llm_output.jsonl 定位具体环节。"
        )

    return PromptTraceAnalysisReport(
        round_number=round_number,
        cache_status=str(run_manifest.get("cache_status"))
        if isinstance(run_manifest, dict) and run_manifest.get("cache_status")
        else None,
        cache_status_reason=str(run_manifest.get("cache_status_reason"))
        if isinstance(run_manifest, dict) and run_manifest.get("cache_status_reason")
        else None,
        experiment_mode=(
            bool(run_manifest.get("experiment_mode"))
            if isinstance(run_manifest, dict)
            and isinstance(run_manifest.get("experiment_mode"), bool)
            else None
        ),
        trace_prompts=(
            bool(run_manifest.get("trace_prompts"))
            if isinstance(run_manifest, dict)
            and isinstance(run_manifest.get("trace_prompts"), bool)
            else None
        ),
        trace_raw_outputs=artifacts_present["raw_llm_output.jsonl"],
        artifacts_present=artifacts_present,
        missing_artifacts=missing_artifacts,
        total_llm_calls=len(stage_summaries) or len(runtime_calls),
        failed_llm_calls=len(failed_summaries),
        max_prompt_chars=max_prompt_chars,
        quality_status=quality_status,
        drama_quality_score=drama_quality_score,
        blocking_issues=blocking_issues,
        suspected_failure_stage=suspected_failure_stage,
        stage_summaries=stage_summaries,
        recommendations=recommendations,
    )


def render_prompt_trace_analysis(report: PromptTraceAnalysisReport) -> str:
    lines = [
        "# Prompt Trace Analysis",
        "",
        f"- Round: {report.round_number or '-'}",
        f"- Cache: {report.cache_status or '-'}"
        + (f" ({report.cache_status_reason})" if report.cache_status_reason else ""),
        f"- Experiment mode: {report.experiment_mode if report.experiment_mode is not None else '-'}",
        f"- Prompt trace: {'yes' if report.artifacts_present.get('prompt_trace.json') else 'no'}",
        f"- Raw outputs: {'yes' if report.artifacts_present.get('raw_llm_output.jsonl') else 'no'}",
        f"- LLM calls: {report.total_llm_calls} total / {report.failed_llm_calls} abnormal",
        f"- Quality: {report.quality_status or '-'}"
        + (
            f" / drama {report.drama_quality_score:.1f}"
            if report.drama_quality_score is not None
            else ""
        ),
        f"- Suspected failure stage: {report.suspected_failure_stage or '-'}",
        "",
        "## Artifact Coverage",
        "",
    ]
    for name, present in report.artifacts_present.items():
        lines.append(f"- {'OK' if present else 'MISSING'} {name}")
    if report.blocking_issues:
        lines.extend(["", "## Blocking Issues", ""])
        lines.extend(f"- {issue}" for issue in report.blocking_issues)
    lines.extend(
        [
            "",
            "## LLM Call Map",
            "",
            "| Call | Stage | Response | Status | Prompt chars | Duration | Notes |",
            "|---:|---|---|---|---:|---:|---|",
        ]
    )
    for summary in report.stage_summaries:
        lines.append(
            "| "
            + " | ".join(
                [
                    str(summary.call_index if summary.call_index is not None else "-"),
                    summary.stage,
                    summary.response_model or "-",
                    summary.status,
                    str(summary.prompt_chars if summary.prompt_chars is not None else "-"),
                    str(summary.duration_ms if summary.duration_ms is not None else "-"),
                    "；".join(summary.notes) if summary.notes else "-",
                ]
            )
            + " |"
        )
    lines.extend(["", "## Recommendations", ""])
    lines.extend(f"- {item}" for item in report.recommendations)
    lines.append("")
    return "\n".join(lines)
