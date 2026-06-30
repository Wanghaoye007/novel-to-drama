from __future__ import annotations

from pathlib import Path
from typing import Annotated, Optional

import click
import typer

from novel_drama_engine.demo import demo_round_outputs
from novel_drama_engine.llm import LLMResponseError, OpenAIJsonLLM, StaticJsonLLM
from novel_drama_engine.pipeline import EmptySourceError, RoundPipeline
from novel_drama_engine.renderer import render_round_summary
from novel_drama_engine.storage import ProjectStore

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
    latest_round_number = store.latest_round_number()
    resolved_round_number = round_number or ((latest_round_number or 0) + 1)
    resolved_context_path = context_path or store.latest_next_round_context_path()
    return resolved_round_number, resolved_context_path


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
