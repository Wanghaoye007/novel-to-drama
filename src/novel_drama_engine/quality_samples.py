from __future__ import annotations

import json
from pathlib import Path
from typing import Callable

from novel_drama_engine.llm import JsonLLM
from novel_drama_engine.models import (
    QualityCriterionResult,
    QualitySampleCase,
    QualitySampleCaseResult,
    QualitySampleManifest,
    QualitySampleReport,
    QualitySampleRoundResult,
    RoundResult,
)
from novel_drama_engine.pipeline import RoundPipeline
from novel_drama_engine.renderer import render_round_summary
from novel_drama_engine.storage import ProjectStore

QUALITY_SAMPLE_REPORT_NAME = "quality_sample_report.json"


def load_quality_sample_manifest(path: Path | str) -> QualitySampleManifest:
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    return QualitySampleManifest.model_validate(raw)


def round_average_score(result: RoundResult) -> float:
    scores = result.quality_report.scores
    values = [
        scores.hook,
        scores.conflict,
        scores.cliffhanger,
        scores.continuity,
        scores.video_feasibility,
    ]
    return round(sum(values) / len(values), 2)


def script_text(result: RoundResult) -> str:
    parts: list[str] = []
    for episode in result.script_batch.episodes:
        parts.extend(
            [
                episode.hook_3s,
                episode.title,
                episode.watch_reason,
                episode.cliffhanger,
            ]
        )
        for scene in episode.scenes:
            parts.append(scene.heading)
            parts.extend(scene.characters)
            for line in scene.lines:
                if line.speaker:
                    parts.append(line.speaker)
                parts.append(line.text)
    return "\n".join(parts)


def has_shootable_scene(result: RoundResult) -> bool:
    for episode in result.script_batch.episodes:
        if not episode.scenes:
            return False
        for scene in episode.scenes:
            has_action = any(line.kind == "action" for line in scene.lines)
            has_dialogue = any(line.kind == "dialogue" for line in scene.lines)
            if not scene.heading or not scene.characters or not (has_action or has_dialogue):
                return False
    return True


def evaluate_round_result(
    result: RoundResult,
    *,
    min_score: int = 7,
) -> QualitySampleRoundResult:
    scores = result.quality_report.scores
    text = script_text(result)
    forbidden_reveals = set(result.episode_context.forbidden_reveals)
    forbidden_reveals.update(result.next_round_context.forbidden_reveals)
    revealed = sorted(secret for secret in forbidden_reveals if secret and secret in text)

    criteria = [
        QualityCriterionResult(
            name="hook",
            passed=bool(result.script_batch.episodes)
            and all(episode.hook_3s.strip() for episode in result.script_batch.episodes)
            and scores.hook >= min_score,
            detail=f"hook score {scores.hook}, episodes {len(result.script_batch.episodes)}",
        ),
        QualityCriterionResult(
            name="conflict",
            passed=bool(result.source_analysis.conflicts) and scores.conflict >= min_score,
            detail=f"conflict score {scores.conflict}, conflicts {len(result.source_analysis.conflicts)}",
        ),
        QualityCriterionResult(
            name="cliffhanger",
            passed=all(episode.cliffhanger.strip() for episode in result.script_batch.episodes)
            and scores.cliffhanger >= min_score
            and bool(result.next_round_context.open_hooks),
            detail=(
                f"cliffhanger score {scores.cliffhanger}, "
                f"open hooks {len(result.next_round_context.open_hooks)}"
            ),
        ),
        QualityCriterionResult(
            name="character_knowledge",
            passed=bool(result.next_round_context.character_knowledge)
            and scores.continuity >= min_score,
            detail=(
                f"continuity score {scores.continuity}, "
                f"tracked characters {len(result.next_round_context.character_knowledge)}"
            ),
        ),
        QualityCriterionResult(
            name="secret_reveal_control",
            passed=not revealed,
            detail=(
                "no forbidden reveal leaked"
                if not revealed
                else f"premature reveal: {', '.join(revealed)}"
            ),
        ),
        QualityCriterionResult(
            name="shootability",
            passed=has_shootable_scene(result) and scores.video_feasibility >= min_score,
            detail=f"video feasibility score {scores.video_feasibility}",
        ),
    ]
    warnings = [criterion.detail for criterion in criteria if not criterion.passed]
    return QualitySampleRoundResult(
        round_number=result.round_number,
        target_episode_range=result.episode_context.target_episode_range,
        quality_status=result.quality_report.status,
        average_score=round_average_score(result),
        criteria=criteria,
        warnings=warnings,
    )


def run_quality_sample_case(
    sample: QualitySampleCase,
    *,
    project_dir: Path,
    llm_factory: Callable[[], JsonLLM],
    min_score: int = 7,
) -> QualitySampleCaseResult:
    store = ProjectStore(project_dir)
    round_results: list[QualitySampleRoundResult] = []
    for index, round_input in enumerate(sample.rounds, start=1):
        context_path = store.latest_next_round_context_path()
        previous_context = (
            store.read_next_round_context(context_path) if context_path else None
        )
        result = RoundPipeline(llm=llm_factory(), store=store).run(
            project_id=sample.sample_id,
            round_number=index,
            source_text=round_input.source_text,
            previous_context=previous_context,
        )
        rendered = render_round_summary(result.script_batch, result.quality_report)
        store.write_text_artifact(index, "rendered_scripts.md", rendered)
        round_results.append(evaluate_round_result(result, min_score=min_score))

    return QualitySampleCaseResult(
        sample_id=sample.sample_id,
        genre=sample.genre,
        project_dir=str(project_dir),
        round_count=len(round_results),
        passed=all(not round_result.warnings for round_result in round_results),
        rounds=round_results,
    )


def run_quality_sample_manifest(
    manifest: QualitySampleManifest,
    *,
    projects_dir: Path | str,
    llm_factory: Callable[[], JsonLLM],
    min_score: int = 7,
) -> QualitySampleReport:
    root = Path(projects_dir)
    root.mkdir(parents=True, exist_ok=True)
    cases = [
        run_quality_sample_case(
            sample,
            project_dir=root / sample.sample_id,
            llm_factory=llm_factory,
            min_score=min_score,
        )
        for sample in manifest.samples
    ]
    report = QualitySampleReport(
        projects_dir=str(root),
        sample_count=len(cases),
        round_count=sum(case.round_count for case in cases),
        passed=all(case.passed for case in cases),
        min_score=min_score,
        cases=cases,
    )
    (root / QUALITY_SAMPLE_REPORT_NAME).write_text(
        report.model_dump_json(indent=2),
        encoding="utf-8",
    )
    return report
