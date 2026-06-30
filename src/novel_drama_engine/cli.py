from __future__ import annotations

from pathlib import Path
from typing import Annotated, Optional

import click
import typer

from novel_drama_engine.demo import demo_round_outputs
from novel_drama_engine.llm import JsonLLM, LLMResponseError, OpenAIJsonLLM, StaticJsonLLM
from novel_drama_engine.models import RoundResult
from novel_drama_engine.pipeline import EmptySourceError, RoundPipeline
from novel_drama_engine.renderer import render_round_summary
from novel_drama_engine.storage import ProjectStore

app = typer.Typer(help="Novel-to-short-drama MVP CLI")


@app.callback()
def main() -> None:
    pass


def build_llm(model: str | None = None) -> OpenAIJsonLLM:
    return OpenAIJsonLLM(model=model)


def build_runtime_llm(mock: bool, model: str | None = None) -> JsonLLM:
    return StaticJsonLLM(demo_round_outputs()) if mock else build_llm(model)


def resolve_run_state(
    store: ProjectStore,
    *,
    context_path: Path | None,
    round_number: int | None,
) -> tuple[int, Path | None]:
    latest_round_number = store.latest_round_number()
    resolved_round_number = round_number or ((latest_round_number or 0) + 1)
    resolved_context_path = context_path or store.latest_next_round_context_path()
    return resolved_round_number, resolved_context_path


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


def discover_source_files(input_dir: Path, pattern: str) -> list[Path]:
    return sorted(path for path in input_dir.glob(pattern) if path.is_file())


def project_relative_stem(input_dir: Path, source_path: Path) -> Path:
    return source_path.relative_to(input_dir).with_suffix("")


def run_project_round(
    *,
    input_path: Path,
    store: ProjectStore,
    project_id: str,
    round_number: int | None,
    context_path: Path | None,
    llm: JsonLLM,
) -> tuple[RoundResult, Path | None]:
    source_text = input_path.read_text(encoding="utf-8")
    resolved_round_number, resolved_context_path = resolve_run_state(
        store,
        context_path=context_path,
        round_number=round_number,
    )
    previous_context = (
        store.read_next_round_context(resolved_context_path)
        if resolved_context_path
        else None
    )
    pipeline = RoundPipeline(llm=llm, store=store)
    result = pipeline.run(
        project_id=project_id,
        round_number=resolved_round_number,
        source_text=source_text,
        previous_context=previous_context,
    )
    rendered = render_round_summary(result.script_batch, result.quality_report)
    store.write_text_artifact(resolved_round_number, "rendered_scripts.md", rendered)
    return result, resolved_context_path


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
    store = ProjectStore(project_dir)
    try:
        llm = build_runtime_llm(mock, model)
        result, resolved_context_path = run_project_round(
            input_path=input,
            store=store,
            project_id=project_id,
            round_number=round_number,
            context_path=context,
            llm=llm,
        )
    except EmptySourceError as exc:
        raise typer.BadParameter(str(exc)) from exc
    except LLMResponseError as exc:
        raise click.ClickException(str(exc)) from exc

    rendered = render_round_summary(result.script_batch, result.quality_report)
    typer.echo(f"Round: {result.round_number}")
    if resolved_context_path:
        typer.echo(f"Loaded context: {resolved_context_path}")
    typer.echo(f"Episode range: {result.episode_context.target_episode_range}")
    typer.echo(rendered)
    typer.echo(f"\nArtifacts written to: {store.round_dir(result.round_number)}")


@app.command()
def batch(
    input_dir: Annotated[
        Path,
        typer.Option(
            "--input-dir",
            "-i",
            exists=True,
            file_okay=False,
            dir_okay=True,
            readable=True,
            help="Directory containing novel source text files.",
        ),
    ],
    project_root: Annotated[
        Path,
        typer.Option("--project-root", help="Root directory for per-source projects."),
    ] = Path(".drama_projects"),
    pattern: Annotated[
        str,
        typer.Option("--pattern", help="Glob pattern under input-dir."),
    ] = "*.txt",
    mock: Annotated[
        bool,
        typer.Option("--mock", help="Use deterministic demo outputs instead of OpenAI."),
    ] = False,
    model: Annotated[
        Optional[str],
        typer.Option("--model", help="OpenAI model name. Overrides OPENAI_MODEL."),
    ] = None,
) -> None:
    source_files = discover_source_files(input_dir, pattern)
    if not source_files:
        raise click.ClickException(f"No source files matched {pattern!r} in {input_dir}")

    try:
        shared_llm = None if mock else build_llm(model)
    except LLMResponseError as exc:
        raise click.ClickException(str(exc)) from exc

    typer.echo(f"Batch sources: {len(source_files)}")
    successes = 0
    failures = 0
    for source_path in source_files:
        relative_stem = project_relative_stem(input_dir, source_path)
        project_dir = project_root / relative_stem
        project_id = relative_stem.as_posix()
        llm = StaticJsonLLM(demo_round_outputs()) if mock else shared_llm
        if llm is None:
            raise click.ClickException("LLM is not configured")

        try:
            result, _ = run_project_round(
                input_path=source_path,
                store=ProjectStore(project_dir),
                project_id=project_id,
                round_number=None,
                context_path=None,
                llm=llm,
            )
        except (EmptySourceError, LLMResponseError, OSError) as exc:
            failures += 1
            typer.echo(f"[failed] {source_path}: {exc}")
            continue

        successes += 1
        typer.echo(
            f"[ok] {source_path} -> {project_dir / f'round_{result.round_number:03d}'} "
            f"{result.quality_report.status.value}"
        )

    if failures:
        raise click.ClickException(
            f"Batch completed with {failures} failure(s), {successes} succeeded."
        )
    typer.echo(f"Batch complete: {successes} succeeded, 0 failed")


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
