from __future__ import annotations

import os
from pathlib import Path
from typing import Annotated, Optional

import click
import typer

from novel_drama_engine.batch import BatchRunner
from novel_drama_engine.baseline import (
    render_baseline_comparison,
    run_direct_free_rewrite_baseline,
)
from novel_drama_engine.demo import demo_round_outputs
from novel_drama_engine.delivery import (
    DeliveryValidationError,
    build_delivery_preflight_report,
    export_delivery_package,
)
from novel_drama_engine.drama_quality import (
    build_drama_quality_report,
    render_drama_quality_report,
)
from novel_drama_engine.evaluation import QualitySampleEvaluator
from novel_drama_engine.localization import (
    build_localization_package,
    read_localization_profile,
    render_localization_package_markdown,
    rewrite_localization_package_with_llm,
)
from novel_drama_engine.llm import LLMResponseError, OpenAIJsonLLM, StaticJsonLLM
from novel_drama_engine.models import GenerationVariant, RoundResult, ScriptBatch, StoryBible
from novel_drama_engine.pipeline import (
    EmptySourceError,
    EpisodesPerRoundError,
    RepairBudgetError,
    RoundPipeline,
    normalize_episodes_per_round,
    resume_artifacts_enabled,
    use_episode_first_script_generation,
)
from novel_drama_engine.renderer import render_creative_round, render_round_summary
from novel_drama_engine.storage import ProjectStore
from novel_drama_engine.trace_analysis import (
    analyze_round_trace_artifacts,
    render_prompt_trace_analysis,
)
from novel_drama_engine.video_brief import build_video_brief, render_video_brief_markdown

app = typer.Typer(help="Novel-to-short-drama MVP CLI")


@app.callback()
def main() -> None:
    pass


def build_llm(model: str | None = None) -> OpenAIJsonLLM:
    return OpenAIJsonLLM(model=model)


def maybe_expand_mock_episode_first(outputs: list[object]) -> list[object]:
    if not use_episode_first_script_generation():
        return outputs
    expanded: list[object] = []
    for item in outputs:
        if isinstance(item, ScriptBatch):
            expanded.extend(item.episodes)
        else:
            expanded.append(item)
    return expanded


def resolve_run_state(
    store: ProjectStore,
    *,
    context_path: Path | None,
    round_number: int | None,
) -> tuple[int, Path | None]:
    return store.resolve_run_state(context_path=context_path, round_number=round_number)


def render_status_line(result: RoundResult) -> str:
    scores = result.quality_report.scores
    titles = "、".join(
        f"EP{episode.episode:02d} {episode.title}"
        for episode in result.script_batch.episodes
    )
    return (
        f"Round {result.round_number} | "
        f"{result.episode_context.target_episode_range} | "
        f"{result.quality_report.status.value} | "
        f"hook {scores.hook}/conflict {scores.conflict}/cliffhanger {scores.cliffhanger} | "
        f"{titles}"
    )


def safe_artifact_name(value: str) -> str:
    return "".join(
        character if character.isalnum() or character in {"-", "_"} else "_"
        for character in value
    )


def variant_includes_episode_plan(generation_variant: GenerationVariant) -> bool:
    return generation_variant in {
        GenerationVariant.DRAMA_ENGINE_FIRST,
        GenerationVariant.SOP_FULL_STACK,
    }


def parse_generation_variants(
    value: str | None,
    fallback: GenerationVariant,
) -> list[GenerationVariant]:
    if not value:
        return [fallback]
    variants: list[GenerationVariant] = []
    for raw in value.split(","):
        item = raw.strip()
        if not item:
            continue
        variants.append(GenerationVariant(item))
    return list(dict.fromkeys(variants)) or [fallback]


def mock_needs_story_bible(store: ProjectStore, round_number: int) -> bool:
    if not resume_artifacts_enabled():
        return True
    candidate_rounds = [
        candidate
        for candidate in store.existing_round_numbers()
        if candidate <= round_number
    ]
    for candidate_round in reversed(candidate_rounds):
        if store.read_round_artifact(candidate_round, "story_bible", StoryBible) is not None:
            return False
    return True


@app.command()
def run(
    input: Annotated[
        Path,
        typer.Option("--input", "-i", exists=True, readable=True, help="Novel source text file."),
    ],
    context: Annotated[
        Optional[Path],
        typer.Option(
            "--context",
            "-c",
            exists=True,
            readable=True,
            help="Previous next_round_context JSON.",
        ),
    ] = None,
    project_dir: Annotated[
        Path,
        typer.Option("--project-dir", help="Directory for JSON artifacts."),
    ] = Path(".drama_project"),
    project_id: Annotated[
        str,
        typer.Option("--project-id", help="Project identifier stored in round_result.json."),
    ] = "local",
    round_number: Annotated[
        Optional[int],
        typer.Option(
            "--round-number",
            min=1,
            help="Generation round number. Defaults to latest project round + 1.",
        ),
    ] = None,
    target_episode_count: Annotated[
        Optional[int],
        typer.Option(
            "--target-episode-count",
            min=1,
            help="Target total episode count for range planning.",
        ),
    ] = None,
    episodes_per_round: Annotated[
        Optional[int],
        typer.Option(
            "--episodes-per-round",
            min=1,
            max=5,
            help="Episodes to generate in this round. Must be 1-5.",
        ),
    ] = None,
    mock: Annotated[
        bool,
        typer.Option("--mock", help="Use deterministic demo outputs instead of OpenAI."),
    ] = False,
    model: Annotated[
        Optional[str],
        typer.Option("--model", help="OpenAI model name. Overrides OPENAI_MODEL."),
    ] = None,
    generation_variant: Annotated[
        GenerationVariant,
        typer.Option(
            "--generation-variant",
            help="Script generation strategy for A/B testing.",
        ),
    ] = GenerationVariant(os.environ.get("NOVEL_DRAMA_GENERATION_VARIANT", "drama_engine_first")),
    repair_budget: Annotated[
        str,
        typer.Option(
            "--repair-budget",
            help="Quality repair budget: none, rewrite, or episode.",
        ),
    ] = os.environ.get("NOVEL_DRAMA_REPAIR_BUDGET", "episode"),
    methodology_cards: Annotated[
        Optional[Path],
        typer.Option(
            "--methodology-cards",
            exists=True,
            readable=True,
            help="Optional methodology card JSON file.",
        ),
    ] = None,
) -> None:
    source_text = input.read_text(encoding="utf-8")
    store = ProjectStore(project_dir)
    resolved_round_number, resolved_context_path = resolve_run_state(
        store,
        context_path=context,
        round_number=round_number,
    )
    previous_context = (
        store.read_next_round_context(resolved_context_path)
        if resolved_context_path
        else None
    )
    try:
        resolved_episodes_per_round = normalize_episodes_per_round(episodes_per_round)
        llm = (
            StaticJsonLLM(
                maybe_expand_mock_episode_first(
                    demo_round_outputs(
                        source_text=source_text,
                        round_number=resolved_round_number,
                        previous_context=previous_context,
                        target_episode_count=target_episode_count,
                        episodes_per_round=resolved_episodes_per_round,
                        include_episode_plan=variant_includes_episode_plan(
                            generation_variant,
                        ),
                        include_sop_stack=(
                            generation_variant == GenerationVariant.SOP_FULL_STACK
                        ),
                        include_story_bible=mock_needs_story_bible(
                            store,
                            resolved_round_number,
                        ),
                    )
                )
            )
            if mock
            else build_llm(model)
        )
        pipeline = RoundPipeline(llm=llm, store=store)
        result = pipeline.run(
            project_id=project_id,
            round_number=resolved_round_number,
            source_text=source_text,
            previous_context=previous_context,
            target_episode_count=target_episode_count,
            episodes_per_round=resolved_episodes_per_round,
            generation_variant=generation_variant,
            repair_budget=repair_budget,
            methodology_cards_path=methodology_cards,
        )
    except EmptySourceError as exc:
        raise typer.BadParameter(str(exc)) from exc
    except EpisodesPerRoundError as exc:
        raise typer.BadParameter(str(exc)) from exc
    except RepairBudgetError as exc:
        raise typer.BadParameter(str(exc)) from exc
    except LLMResponseError as exc:
        raise click.ClickException(str(exc)) from exc

    rendered = render_round_summary(result.script_batch, result.quality_report)
    store.write_text_artifact(resolved_round_number, "rendered_scripts.md", rendered)
    typer.echo(f"Round: {resolved_round_number}")
    if resolved_context_path:
        typer.echo(f"Loaded context: {resolved_context_path}")
    typer.echo(f"Episode range: {result.episode_context.target_episode_range}")
    typer.echo(f"Episodes per round: {resolved_episodes_per_round}")
    typer.echo(f"Generation variant: {generation_variant.value}")
    typer.echo(f"Repair budget: {repair_budget}")
    if result.source_strength_profile:
        typer.echo(
            "Source strength: "
            f"{result.source_strength_profile.overall_level.value} / "
            f"{result.source_strength_profile.recommended_intensity.value}"
        )
    if result.methodology_context:
        card_names = ", ".join(card.name for card in result.methodology_context.cards)
        typer.echo(f"Methodology cards: {card_names or '-'}")
    if result.runtime_report:
        typer.echo(
            "Runtime: "
            f"{result.runtime_report.total_duration_ms} ms | "
            f"LLM calls: {result.runtime_report.total_llm_calls}"
        )
    typer.echo(rendered)
    typer.echo(f"\nArtifacts written to: {store.round_dir(resolved_round_number)}")


@app.command("compare-baseline")
def compare_baseline(
    input: Annotated[
        Path,
        typer.Option("--input", "-i", exists=True, readable=True, help="Novel source text file."),
    ],
    project_dir: Annotated[
        Path,
        typer.Option("--project-dir", help="Directory for JSON artifacts."),
    ] = Path(".drama_baseline"),
    project_id: Annotated[
        str,
        typer.Option("--project-id", help="Project identifier stored in round_result.json."),
    ] = "baseline",
    round_number: Annotated[
        int,
        typer.Option("--round-number", min=1, help="Round number for pipeline comparison."),
    ] = 1,
    target_episode_count: Annotated[
        Optional[int],
        typer.Option("--target-episode-count", min=1, help="Target total episode count."),
    ] = None,
    episodes_per_round: Annotated[
        Optional[int],
        typer.Option("--episodes-per-round", min=1, max=5, help="Episodes to compare."),
    ] = None,
    mock: Annotated[
        bool,
        typer.Option("--mock", help="Use deterministic demo outputs instead of OpenAI."),
    ] = False,
    model: Annotated[
        Optional[str],
        typer.Option("--model", help="OpenAI model name. Overrides OPENAI_MODEL."),
    ] = None,
    generation_variant: Annotated[
        GenerationVariant,
        typer.Option("--generation-variant", help="Pipeline strategy to compare."),
    ] = GenerationVariant(os.environ.get("NOVEL_DRAMA_GENERATION_VARIANT", "drama_engine_first")),
    repair_budget: Annotated[
        str,
        typer.Option("--repair-budget", help="Pipeline repair budget: none, rewrite, or episode."),
    ] = os.environ.get("NOVEL_DRAMA_REPAIR_BUDGET", "episode"),
) -> None:
    source_text = input.read_text(encoding="utf-8")
    resolved_episodes_per_round = normalize_episodes_per_round(episodes_per_round)
    store = ProjectStore(project_dir)
    demo_outputs = demo_round_outputs(
        source_text=source_text,
        round_number=round_number,
        target_episode_count=target_episode_count,
        episodes_per_round=resolved_episodes_per_round,
        include_episode_plan=variant_includes_episode_plan(generation_variant),
        include_sop_stack=(generation_variant == GenerationVariant.SOP_FULL_STACK),
    )
    demo_script_batch = next(
        item for item in demo_outputs if isinstance(item, ScriptBatch)
    )
    direct_llm = StaticJsonLLM([demo_script_batch]) if mock else build_llm(model)
    pipeline_llm = (
        StaticJsonLLM(maybe_expand_mock_episode_first(demo_outputs))
        if mock
        else build_llm(model)
    )
    direct_baseline = run_direct_free_rewrite_baseline(
        direct_llm,
        source_text=source_text,
        target_episode_count=target_episode_count,
        episodes_per_round=resolved_episodes_per_round,
    )
    store.write_round_artifact(
        round_number,
        "baseline_direct_free_rewrite",
        direct_baseline,
    )
    store.write_text_artifact(
        round_number,
        "baseline_direct_free_rewrite.md",
        render_creative_round(direct_baseline),
    )
    result = RoundPipeline(llm=pipeline_llm, store=store).run(
        project_id=project_id,
        round_number=round_number,
        source_text=source_text,
        target_episode_count=target_episode_count,
        episodes_per_round=resolved_episodes_per_round,
        generation_variant=generation_variant,
        repair_budget=repair_budget,
    )
    baseline_drama_quality = build_drama_quality_report(
        script_batch=direct_baseline,
    )
    store.write_round_artifact(
        round_number,
        "baseline_drama_quality_report",
        baseline_drama_quality,
    )
    store.write_text_artifact(
        round_number,
        "baseline_drama_quality_report.md",
        render_drama_quality_report(baseline_drama_quality),
    )
    comparison_report = build_drama_quality_report(
        script_batch=result.script_batch,
        quality_report=result.quality_report,
        adaptation_quality_report=result.adaptation_quality_report,
        baseline_script_batch=direct_baseline,
    )
    store.write_round_artifact(
        round_number,
        "baseline_comparison_report",
        comparison_report,
    )
    store.write_text_artifact(
        round_number,
        "baseline_comparison_report.md",
        render_drama_quality_report(comparison_report),
    )
    comparison = render_baseline_comparison(
        direct_baseline=direct_baseline,
        pipeline_batch=result.script_batch,
        drama_quality_report=comparison_report,
    )
    store.write_text_artifact(round_number, "baseline_comparison.md", comparison)
    typer.echo(f"Baseline comparison written to: {store.round_dir(round_number)}")


@app.command("analyze-trace")
def analyze_trace(
    project_dir: Annotated[
        Path,
        typer.Option("--project-dir", help="Directory for JSON artifacts."),
    ] = Path(".drama_project"),
    round_number: Annotated[
        Optional[int],
        typer.Option("--round-number", min=1, help="Round number to analyze."),
    ] = None,
) -> None:
    store = ProjectStore(project_dir)
    resolved_round_number = round_number or store.latest_round_number()
    if resolved_round_number is None:
        raise click.ClickException(f"No round artifacts found in: {project_dir}")
    round_dir = project_dir / f"round_{resolved_round_number:03d}"
    if not round_dir.exists():
        raise click.ClickException(f"Round artifacts not found: {round_dir}")

    report = analyze_round_trace_artifacts(
        round_dir,
        round_number=resolved_round_number,
    )
    store.write_text_artifact(
        resolved_round_number,
        "prompt_trace_analysis.json",
        report.model_dump_json(indent=2),
    )
    store.write_text_artifact(
        resolved_round_number,
        "prompt_trace_analysis.md",
        render_prompt_trace_analysis(report),
    )
    typer.echo(
        "Trace analysis written to: "
        f"{store.round_dir(resolved_round_number) / 'prompt_trace_analysis.md'}"
    )
    if report.suspected_failure_stage:
        typer.echo(f"Suspected failure stage: {report.suspected_failure_stage}")


@app.command()
def status(
    project_dir: Annotated[
        Path,
        typer.Option("--project-dir", help="Directory for JSON artifacts."),
    ] = Path(".drama_project"),
) -> None:
    store = ProjectStore(project_dir)
    results = store.read_round_results()
    if not results:
        typer.echo(f"No completed rounds found in: {project_dir}")
        return

    latest = results[-1]
    typer.echo(f"Project: {project_dir}")
    typer.echo(f"Rounds: {len(results)}")
    typer.echo(f"Current episode: {latest.next_round_context.current_episode}")
    for result in results:
        typer.echo(render_status_line(result))
        if result.next_round_context.open_hooks:
            hooks = "；".join(result.next_round_context.open_hooks)
            typer.echo(f"  Open hooks: {hooks}")
    latest_context_path = store.latest_next_round_context_path()
    if latest_context_path:
        typer.echo(f"Latest context: {latest_context_path}")


@app.command("batch-run")
def batch_run(
    manifest: Annotated[
        Path,
        typer.Option("--manifest", "-m", exists=True, readable=True, help="Batch manifest JSON."),
    ],
    projects_dir: Annotated[
        Path,
        typer.Option("--projects-dir", help="Directory that will contain per-project artifacts."),
    ] = Path(".drama_projects"),
    mock: Annotated[
        bool,
        typer.Option("--mock", help="Use deterministic demo outputs instead of OpenAI."),
    ] = False,
    model: Annotated[
        Optional[str],
        typer.Option("--model", help="OpenAI model name. Overrides OPENAI_MODEL."),
    ] = None,
    continue_on_error: Annotated[
        bool,
        typer.Option(
            "--continue-on-error/--stop-on-error",
            help="Continue running remaining manifest items after a failure.",
        ),
    ] = True,
) -> None:
    def make_llm() -> OpenAIJsonLLM | StaticJsonLLM:
        return (
            StaticJsonLLM(maybe_expand_mock_episode_first(demo_round_outputs()))
            if mock
            else build_llm(model)
        )

    try:
        report = BatchRunner(
            projects_dir=projects_dir,
            llm_factory=make_llm,
            continue_on_error=continue_on_error,
        ).run(manifest)
    except Exception as exc:
        raise click.ClickException(str(exc)) from exc

    for item in report.items:
        typer.echo(f"{item.status.value}: {item.project_id} -> {item.project_dir}")
        if item.round_number:
            typer.echo(f"  Round: {item.round_number}")
        if item.target_episode_range:
            typer.echo(f"  Episode range: {item.target_episode_range}")
        if item.quality_status:
            typer.echo(f"  Quality: {item.quality_status.value}")
        if item.error:
            typer.echo(f"  Error: {item.error}")

    report_path = projects_dir / "batch_report.json"
    typer.echo(
        f"Batch summary: {report.completed_count} completed, {report.failed_count} failed"
    )
    typer.echo(f"Report written to: {report_path}")
    if report.failed_count:
        raise click.ClickException(
            f"Batch completed with {report.failed_count} failed item(s)."
        )


@app.command("evaluate-samples")
def evaluate_samples(
    samples: Annotated[
        Path,
        typer.Option(
            "--samples",
            "-s",
            exists=True,
            readable=True,
            help="Quality sample manifest JSON.",
        ),
    ] = Path("examples/quality_samples.json"),
    projects_dir: Annotated[
        Path,
        typer.Option("--projects-dir", help="Directory for evaluation artifacts."),
    ] = Path(".drama_quality_eval"),
    rounds: Annotated[
        int,
        typer.Option("--rounds", min=1, help="Rounds to run per sample."),
    ] = 2,
    mock: Annotated[
        bool,
        typer.Option("--mock", help="Use deterministic demo outputs instead of OpenAI."),
    ] = False,
    direct_baseline: Annotated[
        bool,
        typer.Option(
            "--direct-baseline/--no-direct-baseline",
            help=(
                "Also run a direct free-rewrite baseline for round 1 and fail the "
                "sample unless the pipeline is clearly better."
            ),
        ),
    ] = False,
    model: Annotated[
        Optional[str],
        typer.Option("--model", help="OpenAI model name. Overrides OPENAI_MODEL."),
    ] = None,
    generation_variant: Annotated[
        GenerationVariant,
        typer.Option(
            "--generation-variant",
            help="Script generation strategy for A/B testing.",
        ),
    ] = GenerationVariant(os.environ.get("NOVEL_DRAMA_GENERATION_VARIANT", "drama_engine_first")),
    generation_variants: Annotated[
        Optional[str],
        typer.Option(
            "--generation-variants",
            help="Comma-separated generation strategies for A/B testing.",
        ),
    ] = None,
    repair_budget: Annotated[
        str,
        typer.Option(
            "--repair-budget",
            help="Quality repair budget: none, rewrite, or episode.",
        ),
    ] = os.environ.get("NOVEL_DRAMA_REPAIR_BUDGET", "episode"),
) -> None:
    resolved_generation_variants = parse_generation_variants(
        generation_variants,
        generation_variant,
    )

    def make_llm(
        round_number: int,
        previous_context,
        sample,
        active_generation_variant: GenerationVariant = generation_variant,
    ) -> OpenAIJsonLLM | StaticJsonLLM:
        if not mock:
            return build_llm(model)
        return StaticJsonLLM(
            maybe_expand_mock_episode_first(
                demo_round_outputs(
                    source_text=sample.source_text,
                    round_number=round_number,
                    previous_context=previous_context,
                    include_episode_plan=variant_includes_episode_plan(
                        active_generation_variant,
                    ),
                    include_sop_stack=(
                        active_generation_variant == GenerationVariant.SOP_FULL_STACK
                    ),
                    include_story_bible=mock_needs_story_bible(
                        ProjectStore(
                            projects_dir
                            / safe_artifact_name(sample.sample_id)
                            / (
                                active_generation_variant.value
                                if len(resolved_generation_variants) > 1
                                else ""
                            )
                        ),
                        round_number,
                    ),
                )
            )
        )

    def make_baseline_llm(
        round_number: int,
        previous_context,
        sample,
        active_generation_variant: GenerationVariant = generation_variant,
    ) -> OpenAIJsonLLM | StaticJsonLLM:
        if not mock:
            return build_llm(model)
        demo_outputs = demo_round_outputs(
            source_text=sample.source_text,
            round_number=round_number,
            previous_context=previous_context,
            include_episode_plan=variant_includes_episode_plan(
                active_generation_variant,
            ),
            include_sop_stack=(
                active_generation_variant == GenerationVariant.SOP_FULL_STACK
            ),
            include_story_bible=False,
        )
        demo_script_batch = next(
            item for item in demo_outputs if isinstance(item, ScriptBatch)
        )
        return StaticJsonLLM([demo_script_batch])

    try:
        report = QualitySampleEvaluator(
            projects_dir=projects_dir,
            llm_factory=make_llm,
            baseline_llm_factory=make_baseline_llm,
            rounds_per_sample=rounds,
            generation_variant=generation_variant,
            generation_variants=resolved_generation_variants,
            repair_budget=repair_budget,
            include_direct_baseline=direct_baseline,
        ).run(samples)
    except Exception as exc:
        raise click.ClickException(str(exc)) from exc

    for sample in report.samples:
        typer.echo(
            f"{'passed' if sample.passed else 'failed'}: "
            f"{sample.sample_id} ({sample.label}) · {sample.variant.value}"
        )
        for round_report in sample.rounds:
            status = (
                round_report.quality_status.value
                if round_report.quality_status
                else "missing"
            )
            typer.echo(
                f"  Round {round_report.round_number}: "
                f"{round_report.target_episode_range or '-'} | {status}"
            )
            for warning in round_report.warnings:
                typer.echo(f"    warning: {warning}")
            if round_report.baseline_verdict:
                typer.echo(
                    "    baseline: "
                    f"{round_report.pipeline_overall_score}/10 vs "
                    f"{round_report.baseline_overall_score}/10 "
                    f"({round_report.baseline_verdict}, "
                    f"delta {round_report.baseline_delta})"
                )
    typer.echo(
        f"Quality samples: {report.passed_count} passed, {report.failed_count} failed"
    )
    typer.echo(f"Report written to: {projects_dir / 'quality_sample_report.json'}")
    if report.failed_count:
        raise click.ClickException(
            f"{report.failed_count} quality sample(s) failed."
        )


@app.command("export-video-brief")
def export_video_brief(
    project_dir: Annotated[
        Path,
        typer.Option("--project-dir", help="Directory for JSON artifacts."),
    ] = Path(".drama_project"),
    round_number: Annotated[
        Optional[int],
        typer.Option(
            "--round-number",
            min=1,
            help="Round number to export. Defaults to the latest completed round.",
        ),
    ] = None,
    duration_seconds: Annotated[
        int,
        typer.Option(
            "--duration-seconds",
            min=1,
            help="Target duration per episode for the video brief.",
        ),
    ] = 90,
    aspect_ratio: Annotated[
        str,
        typer.Option("--aspect-ratio", help="Target video aspect ratio."),
    ] = "9:16",
    profile: Annotated[
        str,
        typer.Option("--profile", help="Downstream video generation profile name."),
    ] = "vertical_short_drama",
) -> None:
    store = ProjectStore(project_dir)
    if round_number is None:
        results = store.read_round_results()
        if not results:
            raise click.ClickException(f"No completed rounds found in: {project_dir}")
        result = results[-1]
    else:
        try:
            result = store.read_round_result(round_number)
        except FileNotFoundError as exc:
            raise click.ClickException(
                f"No round_result.json found for round {round_number} in: {project_dir}"
            ) from exc

    brief = build_video_brief(
        result,
        target_duration_seconds=duration_seconds,
        aspect_ratio=aspect_ratio,
        profile=profile,
    )
    json_path = store.write_round_artifact(result.round_number, "video_brief", brief)
    markdown_path = store.write_text_artifact(
        result.round_number,
        "video_brief.md",
        render_video_brief_markdown(brief),
    )
    typer.echo(f"Video brief exported for round {result.round_number}")
    typer.echo(f"JSON: {json_path}")
    typer.echo(f"Markdown: {markdown_path}")


@app.command("export-delivery")
def export_delivery(
    project_dir: Annotated[
        Path,
        typer.Option("--project-dir", help="Directory for JSON artifacts."),
    ] = Path(".drama_project"),
    round_number: Annotated[
        Optional[int],
        typer.Option(
            "--round-number",
            min=1,
            help="Round number to export. Defaults to the latest completed round.",
        ),
    ] = None,
    output: Annotated[
        Optional[Path],
        typer.Option("--output", "-o", help="Optional output zip path."),
    ] = None,
    allow_issues: Annotated[
        bool,
        typer.Option(
            "--allow-issues",
            help="Export even when quality or localization review warnings are present.",
        ),
    ] = False,
) -> None:
    store = ProjectStore(project_dir)
    try:
        package_path = export_delivery_package(
            store,
            round_number=round_number,
            output_path=output,
            allow_issues=allow_issues,
        )
    except FileNotFoundError as exc:
        raise click.ClickException(str(exc)) from exc
    except DeliveryValidationError as exc:
        raise click.ClickException(str(exc)) from exc

    typer.echo(f"Delivery package exported: {package_path}")


@app.command("check-delivery")
def check_delivery(
    project_dir: Annotated[
        Path,
        typer.Option("--project-dir", help="Directory for JSON artifacts."),
    ] = Path(".drama_project"),
    round_number: Annotated[
        Optional[int],
        typer.Option(
            "--round-number",
            min=1,
            help="Round number to check. Defaults to the latest completed round.",
        ),
    ] = None,
    strict: Annotated[
        bool,
        typer.Option("--strict", help="Exit with an error when delivery is not ready."),
    ] = False,
    json_output: Annotated[
        bool,
        typer.Option("--json", help="Print a machine-readable preflight report."),
    ] = False,
) -> None:
    store = ProjectStore(project_dir)
    try:
        report = build_delivery_preflight_report(store, round_number=round_number)
    except FileNotFoundError as exc:
        raise click.ClickException(str(exc)) from exc

    if json_output:
        typer.echo(report.model_dump_json(indent=2))
        if strict and not report.ready:
            raise click.ClickException("Delivery preflight failed.")
        return

    typer.echo(f"Delivery ready: {'yes' if report.ready else 'no'}")
    typer.echo(f"Project: {report.project_id}")
    typer.echo(f"Round: {report.round_number}")
    typer.echo(f"Episode range: {report.target_episode_range}")
    typer.echo(f"Quality: {report.quality_status.value}")
    typer.echo(f"Files: {len(report.files)}")
    if report.warnings:
        typer.echo("Warnings:")
        for warning in report.warnings:
            typer.echo(f"- {warning}")
    if strict and not report.ready:
        raise click.ClickException("Delivery preflight failed.")


@app.command("export-localization")
def export_localization(
    profile_path: Annotated[
        Path,
        typer.Option(
            "--profile",
            exists=True,
            readable=True,
            help="Localization profile JSON.",
        ),
    ],
    project_dir: Annotated[
        Path,
        typer.Option("--project-dir", help="Directory for JSON artifacts."),
    ] = Path(".drama_project"),
    round_number: Annotated[
        Optional[int],
        typer.Option(
            "--round-number",
            min=1,
            help="Round number to export. Defaults to the latest completed round.",
        ),
    ] = None,
    rewrite_with_llm: Annotated[
        bool,
        typer.Option(
            "--rewrite-with-llm",
            help="Use the configured OpenAI model to rewrite localized episodes.",
        ),
    ] = False,
    model: Annotated[
        Optional[str],
        typer.Option("--model", help="OpenAI model name. Overrides OPENAI_MODEL."),
    ] = None,
) -> None:
    store = ProjectStore(project_dir)
    if round_number is None:
        results = store.read_round_results()
        if not results:
            raise click.ClickException(f"No completed rounds found in: {project_dir}")
        result = results[-1]
    else:
        try:
            result = store.read_round_result(round_number)
        except FileNotFoundError as exc:
            raise click.ClickException(
                f"No round_result.json found for round {round_number} in: {project_dir}"
            ) from exc

    try:
        profile = read_localization_profile(profile_path)
    except Exception as exc:
        raise click.ClickException(f"Invalid localization profile: {exc}") from exc

    package = build_localization_package(result, profile)
    if rewrite_with_llm:
        try:
            package = rewrite_localization_package_with_llm(package, build_llm(model))
        except LLMResponseError as exc:
            raise click.ClickException(str(exc)) from exc

    suffix = "_llm" if rewrite_with_llm else ""
    artifact_name = f"localization_{safe_artifact_name(profile.profile_id)}{suffix}"
    json_path = store.write_round_artifact(result.round_number, artifact_name, package)
    markdown_path = store.write_text_artifact(
        result.round_number,
        f"{artifact_name}.md",
        render_localization_package_markdown(package),
    )
    typer.echo(f"Localization package exported for round {result.round_number}")
    typer.echo(f"Profile: {profile.profile_id}")
    if rewrite_with_llm:
        typer.echo("Rewrite: llm")
    typer.echo(f"Review issues: {len(package.issues)}")
    typer.echo(f"JSON: {json_path}")
    typer.echo(f"Markdown: {markdown_path}")


if __name__ == "__main__":
    app()
