from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from novel_drama_engine.llm import JsonLLM
from novel_drama_engine.models import (
    NextRoundContext,
    QualitySample,
    QualitySampleEvaluationReport,
    QualitySampleManifest,
    QualitySampleResult,
    QualitySampleRoundReport,
    QualityStatus,
    RoundResult,
)
from novel_drama_engine.pipeline import RoundPipeline
from novel_drama_engine.renderer import render_round_summary
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
    if result.next_round_context.current_episode < 1:
        warnings.append("next round context did not advance current episode")
    return warnings


def build_round_report(result: RoundResult) -> QualitySampleRoundReport:
    scores = result.quality_report.scores
    return QualitySampleRoundReport(
        round_number=result.round_number,
        target_episode_range=result.episode_context.target_episode_range,
        quality_status=result.quality_report.status,
        hook_score=scores.hook,
        conflict_score=scores.conflict,
        cliffhanger_score=scores.cliffhanger,
        continuity_score=scores.continuity,
        video_feasibility_score=scores.video_feasibility,
        warnings=round_warnings(result),
    )


@dataclass
class QualitySampleEvaluator:
    projects_dir: Path
    llm_factory: Callable[[], JsonLLM]
    rounds_per_sample: int = 2

    def run(self, manifest_path: Path) -> QualitySampleEvaluationReport:
        manifest = read_quality_sample_manifest(manifest_path)
        results: list[QualitySampleResult] = []

        for sample in manifest.samples:
            project_dir = self.projects_dir / safe_sample_dir_name(sample)
            store = ProjectStore(project_dir)
            previous_context: NextRoundContext | None = None
            round_reports: list[QualitySampleRoundReport] = []

            for round_number in range(1, self.rounds_per_sample + 1):
                try:
                    result = RoundPipeline(llm=self.llm_factory(), store=store).run(
                        project_id=sample.sample_id,
                        round_number=round_number,
                        source_text=sample.source_text,
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
                    round_reports.append(build_round_report(result))
                except Exception as exc:
                    round_reports.append(
                        QualitySampleRoundReport(
                            round_number=round_number,
                            warnings=[str(exc)],
                        )
                    )

            results.append(
                QualitySampleResult(
                    sample_id=sample.sample_id,
                    label=sample.label,
                    project_dir=str(project_dir),
                    rounds=round_reports,
                )
            )

        report = QualitySampleEvaluationReport(samples=results)
        self.projects_dir.mkdir(parents=True, exist_ok=True)
        (self.projects_dir / "quality_sample_report.json").write_text(
            report.model_dump_json(indent=2),
            encoding="utf-8",
        )
        return report
