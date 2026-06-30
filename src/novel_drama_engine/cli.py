from __future__ import annotations

from pathlib import Path
from typing import Annotated, Optional

import click
import typer

from novel_drama_engine.batch import BatchRunner
from novel_drama_engine.demo import demo_round_outputs
from novel_drama_engine.llm import LLMResponseError, OpenAIJsonLLM, StaticJsonLLM
from novel_drama_engine.models import RoundResult
from novel_drama_engine.pipeline import EmptySourceError, RoundPipeline
from novel_drama_engine.renderer import render_round_summary
from novel_drama_engine.storage import ProjectStore
from novel_drama_engine.video_brief import build_video_brief, render_video_brief_markdown

app = typer.Typer(help="Novel-to-short-drama MVP CLI")


@app.callback()
def main() -> None:
    pass


def build_llm(model: str | None = None) -> OpenAIJsonLLM:
    return OpenAIJsonLLM(model=model)


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
    mock: Annotated[
        bool,
        typer.Option("--mock", help="Use deterministic demo outputs instead of OpenAI."),
    ] = False,
    model: Annotated[
        Optional[str],
        typer.Option("--model", help="OpenAI model name. Overrides OPENAI_MODEL."),
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
        llm = StaticJsonLLM(demo_round_outputs()) if mock else build_llm(model)
        pipeline = RoundPipeline(llm=llm, store=store)
        result = pipeline.run(
            project_id=project_id,
            round_number=resolved_round_number,
            source_text=source_text,
            previous_context=previous_context,
        )
    except EmptySourceError as exc:
        raise typer.BadParameter(str(exc)) from exc
    except LLMResponseError as exc:
        raise click.ClickException(str(exc)) from exc

    rendered = render_round_summary(result.script_batch, result.quality_report)
    store.write_text_artifact(resolved_round_number, "rendered_scripts.md", rendered)
    typer.echo(f"Round: {resolved_round_number}")
    if resolved_context_path:
        typer.echo(f"Loaded context: {resolved_context_path}")
    typer.echo(f"Episode range: {result.episode_context.target_episode_range}")
    typer.echo(rendered)
    typer.echo(f"\nArtifacts written to: {store.round_dir(resolved_round_number)}")


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
        return StaticJsonLLM(demo_round_outputs()) if mock else build_llm(model)

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
