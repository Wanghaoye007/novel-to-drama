from __future__ import annotations

from novel_drama_engine.llm import JsonLLM
from novel_drama_engine.models import DramaQualityReport, ScriptBatch
from novel_drama_engine.renderer import render_creative_round


BASELINE_DIRECT_SYSTEM = (
    "你是短剧编剧。把小说直接改成竖屏短剧分集脚本。"
    "这是 baseline：不要调用多 agent 链路，不要做复杂结构工程，只根据原文自由改写。"
    "仍需输出合法 ScriptBatch JSON。"
)


def baseline_direct_user(
    source_text: str,
    *,
    target_episode_count: int | None = None,
    episodes_per_round: int = 5,
) -> str:
    target = str(target_episode_count) if target_episode_count else "未指定"
    return "\n\n".join(
        [
            f"目标总集数：{target}",
            f"本次输出集数：{episodes_per_round}",
            "要求：直接改写，不要解释，不要输出分析字段到 scene lines；保留原文最强冲突、人物动机和关键情绪。",
            "小说原文：",
            source_text,
        ]
    )


def run_direct_free_rewrite_baseline(
    llm: JsonLLM,
    *,
    source_text: str,
    target_episode_count: int | None = None,
    episodes_per_round: int = 5,
) -> ScriptBatch:
    return llm.complete(
        system=BASELINE_DIRECT_SYSTEM,
        user=baseline_direct_user(
            source_text,
            target_episode_count=target_episode_count,
            episodes_per_round=episodes_per_round,
        ),
        response_model=ScriptBatch,
    )


def render_baseline_comparison(
    *,
    direct_baseline: ScriptBatch,
    pipeline_batch: ScriptBatch,
    drama_quality_report: DramaQualityReport | None = None,
) -> str:
    parts = []
    if drama_quality_report and drama_quality_report.baseline_comparison:
        comparison = drama_quality_report.baseline_comparison
        parts.extend(
            [
                "# Drama Quality Verdict",
                (
                    f"Pipeline {comparison.pipeline_overall_score}/10 vs "
                    f"Direct baseline {comparison.baseline_overall_score}/10 "
                    f"(delta {comparison.delta})"
                ),
                comparison.verdict,
                comparison.reason,
            ]
        )
    parts.extend(
        [
            "# Direct LLM Baseline",
            render_creative_round(direct_baseline),
            "# Current Pipeline",
            render_creative_round(pipeline_batch),
        ]
    )
    return "\n\n".join(parts)
