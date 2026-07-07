from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass
from inspect import signature
from pathlib import Path

from novel_drama_engine.baseline import run_direct_free_rewrite_baseline
from novel_drama_engine.drama_quality import (
    build_drama_quality_report,
    render_drama_quality_report,
)
from novel_drama_engine.llm import JsonLLM
from novel_drama_engine.llm import LLMProviderAuthError, LLMProviderLimitError
from novel_drama_engine.models import (
    NextRoundContext,
    QualitySample,
    QualitySampleEvaluationReport,
    QualitySampleManifest,
    QualitySampleResult,
    QualitySampleRoundReport,
    QualityStatus,
    GenerationVariant,
    RoundResult,
    quality_sample_warning_is_blocking,
)
from novel_drama_engine.pipeline import RoundPipeline
from novel_drama_engine.renderer import render_creative_round, render_round_summary
from novel_drama_engine.script_quality import episode_quality_warnings
from novel_drama_engine.storage import ProjectStore


def read_quality_sample_manifest(path: Path) -> QualitySampleManifest:
    raw = json.loads(path.read_text(encoding="utf-8"))
    return QualitySampleManifest.model_validate(raw)


def safe_sample_dir_name(sample: QualitySample) -> str:
    return "".join(
        character if character.isalnum() or character in {"-", "_"} else "_"
        for character in sample.sample_id
    )


def round_warnings(result: RoundResult) -> list[str]:
    warnings: list[str] = []
    if not result.episode_context.target_episode_range.startswith("EP"):
        warnings.append("target episode range does not start with EP")
    if result.quality_report.status != QualityStatus.USABLE:
        warnings.append(f"quality status is {result.quality_report.status.value}")
    if not result.script_batch.episodes:
        warnings.append("no episodes generated")
    for episode in result.script_batch.episodes:
        if not episode.hook_3s.strip():
            warnings.append(f"EP{episode.episode:02d} missing 3s hook")
        if not episode.cliffhanger.strip():
            warnings.append(f"EP{episode.episode:02d} missing cliffhanger")
        if not episode.scenes:
            warnings.append(f"EP{episode.episode:02d} has no scenes")
        warnings.extend(episode_quality_warnings(episode))
    if result.next_round_context.current_episode < 1:
        warnings.append("next round context did not advance current episode")
    if result.adaptation_quality_report:
        warnings.extend(result.adaptation_quality_report.blocking_warnings)
    comparison = (
        result.drama_quality_report.baseline_comparison
        if result.drama_quality_report
        else None
    )
    if comparison and comparison.verdict != "pipeline_clearly_better":
        warnings.append(
            "pipeline is not clearly better than direct baseline: "
            f"{comparison.verdict} (delta {comparison.delta})"
        )
    return warnings


def build_round_report(
    result: RoundResult,
    generation_variant: GenerationVariant,
) -> QualitySampleRoundReport:
    scores = result.quality_report.scores
    adaptation_report = result.adaptation_quality_report
    comparison = (
        result.drama_quality_report.baseline_comparison
        if result.drama_quality_report
        else None
    )
    source_fidelity_warnings = (
        [
            *adaptation_report.source_fidelity.blocking_warnings,
            *adaptation_report.source_fidelity.advisory_warnings,
        ]
        if adaptation_report
        else []
    )
    continuity_warnings = (
        [
            *adaptation_report.continuity.blocking_warnings,
            *adaptation_report.continuity.advisory_warnings,
        ]
        if adaptation_report
        else []
    )
    ledger_warnings = (
        adaptation_report.story_state_ledger.warnings
        if adaptation_report
        else []
    )
    structured_warnings = [
        *source_fidelity_warnings,
        *continuity_warnings,
        *ledger_warnings,
    ]
    warnings = list(
        dict.fromkeys(
            [
                *round_warnings(result),
                *[
                    warning
                    for warning in structured_warnings
                    if quality_sample_warning_is_blocking(warning)
                ],
            ]
        )
    )

    return QualitySampleRoundReport(
        round_number=result.round_number,
        generation_variant=generation_variant,
        target_episode_range=result.episode_context.target_episode_range,
        quality_status=result.quality_report.status,
        hook_score=scores.hook,
        conflict_score=scores.conflict,
        cliffhanger_score=scores.cliffhanger,
        continuity_score=scores.continuity,
        video_feasibility_score=scores.video_feasibility,
        source_fidelity_score=(
            adaptation_report.source_fidelity.score if adaptation_report else None
        ),
        continuity_audit_score=(
            adaptation_report.continuity.score if adaptation_report else None
        ),
        baseline_overall_score=(
            comparison.baseline_overall_score if comparison else None
        ),
        pipeline_overall_score=(
            comparison.pipeline_overall_score if comparison else None
        ),
        baseline_delta=comparison.delta if comparison else None,
        baseline_verdict=comparison.verdict if comparison else None,
        baseline_reason=comparison.reason if comparison else None,
        source_fidelity_warnings=source_fidelity_warnings,
        continuity_warnings=continuity_warnings,
        ledger_warnings=ledger_warnings,
        warnings=warnings,
    )


def is_provider_hard_failure(exc: Exception) -> bool:
    return isinstance(exc, (LLMProviderAuthError, LLMProviderLimitError))


@dataclass
class QualitySampleEvaluator:
    projects_dir: Path
    llm_factory: Callable[..., JsonLLM]
    baseline_llm_factory: Callable[..., JsonLLM] | None = None
    rounds_per_sample: int = 2
    generation_variant: GenerationVariant = GenerationVariant.CURRENT_DENSITY
    generation_variants: list[GenerationVariant] | None = None
    repair_budget: str | None = None
    include_direct_baseline: bool = False

    def variants(self) -> list[GenerationVariant]:
        if not self.generation_variants:
            return [self.generation_variant]
        return list(dict.fromkeys(self.generation_variants))

    def make_llm(
        self,
        round_number: int,
        previous_context: NextRoundContext | None,
        sample: QualitySample,
        generation_variant: GenerationVariant,
    ) -> JsonLLM:
        parameters = signature(self.llm_factory).parameters
        accepts_variant = (
            any(param.kind == param.VAR_POSITIONAL for param in parameters.values())
            or len(parameters) >= 4
        )
        if accepts_variant:
            return self.llm_factory(
                round_number,
                previous_context,
                sample,
                generation_variant,
            )
        return self.llm_factory(round_number, previous_context, sample)

    def make_baseline_llm(
        self,
        round_number: int,
        previous_context: NextRoundContext | None,
        sample: QualitySample,
        generation_variant: GenerationVariant,
    ) -> JsonLLM:
        factory = self.baseline_llm_factory or self.llm_factory
        parameters = signature(factory).parameters
        accepts_variant = (
            any(param.kind == param.VAR_POSITIONAL for param in parameters.values())
            or len(parameters) >= 4
        )
        if accepts_variant:
            return factory(
                round_number,
                previous_context,
                sample,
                generation_variant,
            )
        return factory(round_number, previous_context, sample)

    def attach_direct_baseline(
        self,
        *,
        result: RoundResult,
        store: ProjectStore,
        sample: QualitySample,
        generation_variant: GenerationVariant,
        previous_context: NextRoundContext | None,
    ) -> RoundResult:
        if not self.include_direct_baseline or result.round_number != 1:
            return result
        direct_baseline = run_direct_free_rewrite_baseline(
            self.make_baseline_llm(
                result.round_number,
                previous_context,
                sample,
                generation_variant,
            ),
            source_text=sample.source_text,
        )
        store.write_round_artifact(
            result.round_number,
            "baseline_direct_free_rewrite",
            direct_baseline,
        )
        store.write_text_artifact(
            result.round_number,
            "baseline_direct_free_rewrite.md",
            render_creative_round(direct_baseline),
        )
        comparison_report = build_drama_quality_report(
            script_batch=result.script_batch,
            quality_report=result.quality_report,
            adaptation_quality_report=result.adaptation_quality_report,
            baseline_script_batch=direct_baseline,
        )
        store.write_round_artifact(
            result.round_number,
            "baseline_comparison_report",
            comparison_report,
        )
        store.write_text_artifact(
            result.round_number,
            "baseline_comparison_report.md",
            render_drama_quality_report(comparison_report),
        )
        return result.model_copy(update={"drama_quality_report": comparison_report})

    def run(self, manifest_path: Path) -> QualitySampleEvaluationReport:
        manifest = read_quality_sample_manifest(manifest_path)
        results: list[QualitySampleResult] = []
        variants = self.variants()

        def write_report() -> QualitySampleEvaluationReport:
            report = QualitySampleEvaluationReport(samples=results, variants=variants)
            self.projects_dir.mkdir(parents=True, exist_ok=True)
            (self.projects_dir / "quality_sample_report.json").write_text(
                report.model_dump_json(indent=2),
                encoding="utf-8",
            )
            return report

        for sample in manifest.samples:
            for generation_variant in variants:
                project_dir = self.projects_dir / safe_sample_dir_name(sample)
                if len(variants) > 1:
                    project_dir = project_dir / generation_variant.value
                store = ProjectStore(project_dir)
                previous_context: NextRoundContext | None = None
                round_reports: list[QualitySampleRoundReport] = []

                for round_number in range(1, self.rounds_per_sample + 1):
                    try:
                        result = RoundPipeline(
                            llm=self.make_llm(
                                round_number,
                                previous_context,
                                sample,
                                generation_variant,
                            ),
                            store=store,
                        ).run(
                            project_id=sample.sample_id,
                            round_number=round_number,
                            source_text=sample.source_text,
                            previous_context=previous_context,
                            generation_variant=generation_variant,
                            repair_budget=self.repair_budget,
                        )
                        result = self.attach_direct_baseline(
                            result=result,
                            store=store,
                            sample=sample,
                            generation_variant=generation_variant,
                            previous_context=previous_context,
                        )
                        rendered = render_round_summary(
                            result.script_batch,
                            result.quality_report,
                        )
                        store.write_text_artifact(
                            round_number,
                            "rendered_scripts.md",
                            rendered,
                        )
                        previous_context = result.next_round_context
                        round_reports.append(
                            build_round_report(result, generation_variant)
                        )
                    except Exception as exc:
                        round_reports.append(
                            QualitySampleRoundReport(
                                round_number=round_number,
                                generation_variant=generation_variant,
                                warnings=[str(exc)],
                            )
                        )
                        if is_provider_hard_failure(exc):
                            results.append(
                                QualitySampleResult(
                                    sample_id=sample.sample_id,
                                    label=sample.label,
                                    variant=generation_variant,
                                    project_dir=str(project_dir),
                                    rounds=round_reports,
                                )
                            )
                            write_report()
                            raise

                results.append(
                    QualitySampleResult(
                        sample_id=sample.sample_id,
                        label=sample.label,
                        variant=generation_variant,
                        project_dir=str(project_dir),
                        rounds=round_reports,
                    )
                )

        return write_report()
