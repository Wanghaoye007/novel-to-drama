from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Annotated, Optional

import click
import typer

from novel_drama_engine.batch import BatchRunner
from novel_drama_engine.demo import (
    demo_localization_output,
    demo_marketing_assets,
    demo_round_outputs,
)
from novel_drama_engine.delivery import (
    DeliveryValidationError,
    build_delivery_preflight_report,
    export_delivery_package,
)
from novel_drama_engine.deliverables import (
    generate_project_ad_assets,
    localize_project_round,
    localization_artifact_prefix,
)
from novel_drama_engine.localization import (
    build_localization_package,
    render_localization_package_markdown,
    rewrite_localization_package_with_llm,
)
from novel_drama_engine.localization_profiles import (
    localization_profile_payload,
    localization_profiles_payload,
    resolve_localization_profile,
)
from novel_drama_engine.llm import JsonLLM, LLMResponseError, OpenAIJsonLLM, StaticJsonLLM
from novel_drama_engine.models import RoundResult
from novel_drama_engine.pipeline import EmptySourceError, RoundPipeline
from novel_drama_engine.quality_samples import (
    QUALITY_SAMPLE_REPORT_NAME,
    load_quality_sample_manifest,
    run_quality_sample_manifest,
)
from novel_drama_engine.renderer import render_round_summary
from novel_drama_engine.status import project_status_payload, round_artifact_labels
from novel_drama_engine.storage import ProjectStore
from novel_drama_engine.video_brief import export_project_video_brief

app = typer.Typer(help="Novel-to-short-drama MVP CLI")


@dataclass(frozen=True)
class BatchJob:
    source_path: Path
    project_dir: Path
    project_id: str
    context_path: Path | None = None
    round_number: int | None = None
    locale: str = "en-US"
    platform: str = "TikTok"
    localization_guidance: str = ""
    marketing_guidance: str = ""
    deliverables: tuple[str, ...] = ()


@app.callback()
def main() -> None:
    pass


def build_llm(model: str | None = None) -> OpenAIJsonLLM:
    return OpenAIJsonLLM(model=model)


def build_runtime_llm(mock: bool, model: str | None = None) -> JsonLLM:
    return StaticJsonLLM(demo_round_outputs()) if mock else build_llm(model)


def run_api_server(host: str, port: int, reload: bool) -> None:
    import uvicorn

    uvicorn.run(
        "novel_drama_engine.api:app",
        host=host,
        port=port,
        reload=reload,
    )


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


def discover_source_files(input_dir: Path, pattern: str) -> list[Path]:
    return sorted(path for path in input_dir.glob(pattern) if path.is_file())


def project_relative_stem(input_dir: Path, source_path: Path) -> Path:
    return source_path.relative_to(input_dir).with_suffix("")


def resolve_manifest_path(base_dir: Path, raw_path: object) -> Path:
    path = Path(str(raw_path))
    if path.is_absolute():
        return path
    return base_dir / path


def default_manifest_project_id(raw_source: object, source_path: Path) -> str:
    raw_source_path = Path(str(raw_source))
    if raw_source_path.is_absolute():
        return source_path.with_suffix("").name
    return raw_source_path.with_suffix("").as_posix()


def parse_manifest_round_number(raw_round_number: object, job_index: int) -> int | None:
    if raw_round_number is None:
        return None
    try:
        round_number = int(raw_round_number)
    except (TypeError, ValueError) as exc:
        raise click.ClickException(
            f"Manifest job {job_index} has invalid round_number: {raw_round_number!r}"
        ) from exc
    if round_number < 1:
        raise click.ClickException(
            f"Manifest job {job_index} round_number must be greater than 0"
        )
    return round_number


def parse_manifest_deliverables(raw_deliverables: object, job_index: int) -> tuple[str, ...]:
    if raw_deliverables is None:
        return ()
    if isinstance(raw_deliverables, str):
        candidates = [raw_deliverables]
    elif isinstance(raw_deliverables, list):
        candidates = raw_deliverables
    else:
        raise click.ClickException(f"Manifest job {job_index} deliverables must be a list")

    allowed = {"localization", "ad_assets"}
    deliverables: list[str] = []
    for raw_deliverable in candidates:
        deliverable = str(raw_deliverable)
        if deliverable not in allowed:
            raise click.ClickException(
                f"Manifest job {job_index} has unsupported deliverable: {deliverable!r}"
            )
        if deliverable not in deliverables:
            deliverables.append(deliverable)
    return tuple(deliverables)


def load_manifest_jobs(manifest_path: Path, project_root: Path) -> list[BatchJob]:
    try:
        raw_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise click.ClickException(f"Manifest is not valid JSON: {exc}") from exc
    if isinstance(raw_manifest, list):
        raw_jobs = raw_manifest
    elif isinstance(raw_manifest, dict):
        raw_jobs = raw_manifest.get("jobs")
    else:
        raw_jobs = None
    if not isinstance(raw_jobs, list) or not raw_jobs:
        raise click.ClickException("Manifest must contain a non-empty jobs list")

    jobs: list[BatchJob] = []
    base_dir = manifest_path.parent
    for index, raw_job in enumerate(raw_jobs, start=1):
        if not isinstance(raw_job, dict):
            raise click.ClickException(f"Manifest job {index} must be an object")
        raw_source = raw_job.get("source")
        if not raw_source:
            raise click.ClickException(f"Manifest job {index} is missing source")

        source_path = resolve_manifest_path(base_dir, raw_source)
        project_id = str(
            raw_job.get("project_id")
            or default_manifest_project_id(raw_source, source_path)
        )
        raw_project_dir = raw_job.get("project_dir")
        if raw_project_dir:
            project_dir_path = Path(str(raw_project_dir))
            project_dir = (
                project_dir_path
                if project_dir_path.is_absolute()
                else project_root / project_dir_path
            )
        else:
            project_dir = project_root / project_id

        raw_context = raw_job.get("context")
        context_path = resolve_manifest_path(base_dir, raw_context) if raw_context else None
        locale = str(raw_job.get("locale") or "en-US")
        platform = str(raw_job.get("platform") or "TikTok")
        jobs.append(
            BatchJob(
                source_path=source_path,
                project_dir=project_dir,
                project_id=project_id,
                context_path=context_path,
                round_number=parse_manifest_round_number(
                    raw_job.get("round_number"),
                    index,
                ),
                locale=locale,
                platform=platform,
                localization_guidance=str(raw_job.get("localization_guidance") or ""),
                marketing_guidance=str(raw_job.get("marketing_guidance") or ""),
                deliverables=parse_manifest_deliverables(
                    raw_job.get("deliverables"),
                    index,
                ),
            )
        )
    return jobs


def build_directory_jobs(
    input_dir: Path,
    project_root: Path,
    pattern: str,
) -> list[BatchJob]:
    source_files = discover_source_files(input_dir, pattern)
    if not source_files:
        raise click.ClickException(f"No source files matched {pattern!r} in {input_dir}")

    jobs: list[BatchJob] = []
    for source_path in source_files:
        relative_stem = project_relative_stem(input_dir, source_path)
        jobs.append(
            BatchJob(
                source_path=source_path,
                project_dir=project_root / relative_stem,
                project_id=relative_stem.as_posix(),
            )
        )
    return jobs


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
def serve(
    host: Annotated[
        str,
        typer.Option("--host", help="API server host."),
    ] = "127.0.0.1",
    port: Annotated[
        int,
        typer.Option("--port", min=1, max=65535, help="API server port."),
    ] = 8000,
    reload: Annotated[
        bool,
        typer.Option("--reload", help="Reload the API server on code changes."),
    ] = False,
) -> None:
    run_api_server(host=host, port=port, reload=reload)


def safe_artifact_name(value: str) -> str:
    return "".join(
        character if character.isalnum() or character in {"-", "_"} else "_"
        for character in value
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
        Optional[Path],
        typer.Option(
            "--input-dir",
            "-i",
            exists=True,
            file_okay=False,
            dir_okay=True,
            readable=True,
            help="Directory containing novel source text files.",
        ),
    ] = None,
    manifest: Annotated[
        Optional[Path],
        typer.Option(
            "--manifest",
            exists=True,
            file_okay=True,
            dir_okay=False,
            readable=True,
            help="JSON manifest containing batch jobs.",
        ),
    ] = None,
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
    if (input_dir is None) == (manifest is None):
        raise click.ClickException("Pass exactly one of --input-dir or --manifest")

    jobs = (
        load_manifest_jobs(manifest, project_root)
        if manifest
        else build_directory_jobs(input_dir, project_root, pattern)
    )

    try:
        shared_llm = None if mock else build_llm(model)
    except LLMResponseError as exc:
        raise click.ClickException(str(exc)) from exc

    typer.echo(f"Batch sources: {len(jobs)}")
    successes = 0
    failures = 0
    for job in jobs:
        llm = StaticJsonLLM(demo_round_outputs()) if mock else shared_llm
        if llm is None:
            raise click.ClickException("LLM is not configured")

        try:
            store = ProjectStore(job.project_dir)
            result, _ = run_project_round(
                input_path=job.source_path,
                store=store,
                project_id=job.project_id,
                round_number=job.round_number,
                context_path=job.context_path,
                llm=llm,
            )
            if "localization" in job.deliverables:
                localization_llm = (
                    StaticJsonLLM([demo_localization_output(job.locale, job.platform)])
                    if mock
                    else shared_llm
                )
                if localization_llm is None:
                    raise click.ClickException("LLM is not configured")
                localize_project_round(
                    store=store,
                    round_number=result.round_number,
                    locale=job.locale,
                    platform=job.platform,
                    guidance=job.localization_guidance,
                    llm=localization_llm,
                )
            if "ad_assets" in job.deliverables:
                marketing_llm = (
                    StaticJsonLLM([demo_marketing_assets(job.locale, job.platform)])
                    if mock
                    else shared_llm
                )
                if marketing_llm is None:
                    raise click.ClickException("LLM is not configured")
                generate_project_ad_assets(
                    store=store,
                    round_number=result.round_number,
                    locale=job.locale,
                    platform=job.platform,
                    guidance=job.marketing_guidance,
                    llm=marketing_llm,
                )
        except (EmptySourceError, LLMResponseError, OSError) as exc:
            failures += 1
            typer.echo(f"[failed] {job.source_path}: {exc}")
            continue

        successes += 1
        deliverable_suffix = (
            f" deliverables={','.join(job.deliverables)}" if job.deliverables else ""
        )
        typer.echo(
            f"[ok] {job.source_path} -> {job.project_dir / f'round_{result.round_number:03d}'} "
            f"{result.quality_report.status.value}{deliverable_suffix}"
        )

    if failures:
        raise click.ClickException(
            f"Batch completed with {failures} failure(s), {successes} succeeded."
        )
    typer.echo(f"Batch complete: {successes} succeeded, 0 failed")


@app.command()
def localize(
    project_dir: Annotated[
        Path,
        typer.Option("--project-dir", help="Directory containing round artifacts."),
    ] = Path(".drama_project"),
    round_number: Annotated[
        Optional[int],
        typer.Option(
            "--round-number",
            min=1,
            help="Round number to localize. Defaults to latest completed round.",
        ),
    ] = None,
    locale: Annotated[
        str,
        typer.Option("--locale", help="Target locale, for example en-US."),
    ] = "en-US",
    platform: Annotated[
        str,
        typer.Option("--platform", help="Target platform, for example TikTok."),
    ] = "TikTok",
    guidance: Annotated[
        str,
        typer.Option("--guidance", help="Extra localization guidance."),
    ] = "",
    mock: Annotated[
        bool,
        typer.Option("--mock", help="Use deterministic demo localization output."),
    ] = False,
    model: Annotated[
        Optional[str],
        typer.Option("--model", help="OpenAI model name. Overrides OPENAI_MODEL."),
    ] = None,
) -> None:
    store = ProjectStore(project_dir)
    resolved_round_number = round_number or store.latest_round_number()
    if resolved_round_number is None:
        raise click.ClickException(f"No completed rounds found in: {project_dir}")

    try:
        llm = (
            StaticJsonLLM([demo_localization_output(locale, platform)])
            if mock
            else build_llm(model)
        )
        localized, json_path, markdown_path = localize_project_round(
            store=store,
            round_number=resolved_round_number,
            locale=locale,
            platform=platform,
            guidance=guidance,
            llm=llm,
        )
    except (FileNotFoundError, OSError) as exc:
        raise click.ClickException(str(exc)) from exc
    except LLMResponseError as exc:
        raise click.ClickException(str(exc)) from exc

    typer.echo(f"Localized round: {resolved_round_number}")
    typer.echo(f"Locale: {localized.locale}")
    typer.echo(f"Platform: {localized.platform}")
    typer.echo(f"JSON: {json_path}")
    typer.echo(f"Markdown: {markdown_path}")


@app.command("ad-assets")
def ad_assets(
    project_dir: Annotated[
        Path,
        typer.Option("--project-dir", help="Directory containing round artifacts."),
    ] = Path(".drama_project"),
    round_number: Annotated[
        Optional[int],
        typer.Option(
            "--round-number",
            min=1,
            help="Round number to generate ad assets for. Defaults to latest completed round.",
        ),
    ] = None,
    locale: Annotated[
        str,
        typer.Option("--locale", help="Target locale, for example en-US."),
    ] = "en-US",
    platform: Annotated[
        str,
        typer.Option("--platform", help="Target platform, for example TikTok."),
    ] = "TikTok",
    guidance: Annotated[
        str,
        typer.Option("--guidance", help="Extra ad copy guidance."),
    ] = "",
    mock: Annotated[
        bool,
        typer.Option("--mock", help="Use deterministic demo marketing assets."),
    ] = False,
    model: Annotated[
        Optional[str],
        typer.Option("--model", help="OpenAI model name. Overrides OPENAI_MODEL."),
    ] = None,
) -> None:
    store = ProjectStore(project_dir)
    resolved_round_number = round_number or store.latest_round_number()
    if resolved_round_number is None:
        raise click.ClickException(f"No completed rounds found in: {project_dir}")

    try:
        llm = (
            StaticJsonLLM([demo_marketing_assets(locale, platform)])
            if mock
            else build_llm(model)
        )
        json_path, markdown_path = generate_project_ad_assets(
            store=store,
            round_number=resolved_round_number,
            locale=locale,
            platform=platform,
            guidance=guidance,
            llm=llm,
        )
    except (FileNotFoundError, OSError) as exc:
        raise click.ClickException(str(exc)) from exc
    except LLMResponseError as exc:
        raise click.ClickException(str(exc)) from exc

    typer.echo(f"Ad assets round: {resolved_round_number}")
    typer.echo(f"Locale: {locale}")
    typer.echo(f"Platform: {platform}")
    typer.echo(f"JSON: {json_path}")
    typer.echo(f"Markdown: {markdown_path}")


@app.command("export-video-brief")
def export_video_brief(
    project_dir: Annotated[
        Path,
        typer.Option("--project-dir", help="Directory containing round artifacts."),
    ] = Path(".drama_project"),
    round_number: Annotated[
        Optional[int],
        typer.Option(
            "--round-number",
            min=1,
            help="Round number to export. Defaults to latest completed round.",
        ),
    ] = None,
    duration_seconds: Annotated[
        int,
        typer.Option(
            "--duration-seconds",
            min=1,
            help="Target duration per episode brief.",
        ),
    ] = 75,
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
    resolved_round_number = round_number or store.latest_round_number()
    if resolved_round_number is None:
        raise click.ClickException(f"No completed rounds found in: {project_dir}")

    try:
        brief, json_path, markdown_path = export_project_video_brief(
            store=store,
            round_number=resolved_round_number,
            duration_seconds=duration_seconds,
            aspect_ratio=aspect_ratio,
            profile=profile,
        )
    except FileNotFoundError as exc:
        raise click.ClickException(str(exc)) from exc

    typer.echo(f"Video brief round: {resolved_round_number}")
    typer.echo(f"Video brief exported for round {resolved_round_number}")
    typer.echo(f"Episodes: {len(brief.episodes)}")
    typer.echo(f"JSON: {json_path}")
    typer.echo(f"Markdown: {markdown_path}")


@app.command()
def status(
    project_dir: Annotated[
        Path,
        typer.Option("--project-dir", help="Directory for JSON artifacts."),
    ] = Path(".drama_project"),
    json_output: Annotated[
        bool,
        typer.Option("--json-output", help="Print machine-readable project status JSON."),
    ] = False,
) -> None:
    store = ProjectStore(project_dir)
    if json_output:
        typer.echo(json.dumps(project_status_payload(store), ensure_ascii=False, indent=2))
        return

    status_payload = project_status_payload(store)
    results = store.read_round_results()
    if not results:
        typer.echo(f"No completed rounds found in: {project_dir}")
        return

    round_payloads = {
        round_payload["round_number"]: round_payload
        for round_payload in status_payload["rounds"]
    }
    latest = results[-1]
    typer.echo(f"Project: {project_dir}")
    typer.echo(f"Rounds: {len(results)}")
    typer.echo(f"Current episode: {latest.next_round_context.current_episode}")
    for result in results:
        typer.echo(render_status_line(result))
        if result.next_round_context.open_hooks:
            hooks = "；".join(result.next_round_context.open_hooks)
            typer.echo(f"  Open hooks: {hooks}")
        localizations = round_artifact_labels(
            store,
            result.round_number,
            "localization",
        )
        if localizations:
            typer.echo(f"  Localizations: {', '.join(localizations)}")
        marketing_assets = round_artifact_labels(
            store,
            result.round_number,
            "marketing_assets",
        )
        if marketing_assets:
            typer.echo(f"  Marketing assets: {', '.join(marketing_assets)}")
        if (
            store.project_dir / f"round_{result.round_number:03d}" / "video_brief.json"
        ).exists():
            typer.echo("  Video brief: video_brief")
        round_payload = round_payloads.get(result.round_number)
        if round_payload:
            delivery = round_payload["delivery"]
            typer.echo(
                f"  Delivery ready: {'yes' if delivery['ready'] else 'no'} "
                f"({delivery['file_count']} files)"
            )
            for warning in delivery["warnings"]:
                typer.echo(f"  Delivery warning: {warning}")
    latest_context_path = store.latest_next_round_context_path()
    if latest_context_path:
        typer.echo(f"Latest context: {latest_context_path}")


@app.command("quality-samples")
def quality_samples(
    manifest: Annotated[
        Path,
        typer.Option(
            "--manifest",
            "-m",
            exists=True,
            readable=True,
            help="Quality sample manifest JSON.",
        ),
    ] = Path("examples/quality_samples.json"),
    projects_dir: Annotated[
        Path,
        typer.Option(
            "--projects-dir",
            help="Directory that will contain per-sample artifacts and report.",
        ),
    ] = Path(".drama_quality_samples"),
    min_score: Annotated[
        int,
        typer.Option(
            "--min-score",
            min=0,
            max=10,
            help="Minimum score required for scored quality criteria.",
        ),
    ] = 7,
    mock: Annotated[
        bool,
        typer.Option("--mock", help="Use deterministic demo outputs instead of OpenAI."),
    ] = False,
    model: Annotated[
        Optional[str],
        typer.Option("--model", help="OpenAI model name. Overrides OPENAI_MODEL."),
    ] = None,
    json_output: Annotated[
        bool,
        typer.Option("--json-output", help="Print machine-readable report JSON."),
    ] = False,
    strict: Annotated[
        bool,
        typer.Option("--strict", help="Exit with an error when any sample check fails."),
    ] = False,
) -> None:
    try:
        sample_manifest = load_quality_sample_manifest(manifest)
        if mock:
            llm_factory = lambda: StaticJsonLLM(demo_round_outputs())
        else:
            shared_llm = build_llm(model)
            llm_factory = lambda: shared_llm
        report = run_quality_sample_manifest(
            sample_manifest,
            projects_dir=projects_dir,
            llm_factory=llm_factory,
            min_score=min_score,
        )
    except (OSError, LLMResponseError, ValueError) as exc:
        raise click.ClickException(str(exc)) from exc

    if json_output:
        typer.echo(report.model_dump_json(indent=2))
    else:
        typer.echo(f"Quality samples: {report.sample_count}")
        typer.echo(f"Rounds: {report.round_count}")
        typer.echo(f"Passed: {'yes' if report.passed else 'no'}")
        for case in report.cases:
            typer.echo(
                f"{'passed' if case.passed else 'failed'}: "
                f"{case.sample_id} ({case.genre}) rounds={case.round_count}"
            )
            for round_result in case.rounds:
                if round_result.warnings:
                    typer.echo(
                        f"  Round {round_result.round_number} warnings: "
                        f"{'; '.join(round_result.warnings)}"
                    )
        typer.echo(f"Report written to: {projects_dir / QUALITY_SAMPLE_REPORT_NAME}")

    if strict and not report.passed:
        raise click.ClickException("Quality sample checks failed.")


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
) -> None:
    store = ProjectStore(project_dir)
    try:
        report = build_delivery_preflight_report(store, round_number=round_number)
    except FileNotFoundError as exc:
        raise click.ClickException(str(exc)) from exc

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


@app.command("localization-profiles")
def localization_profiles(
    profiles_dir: Annotated[
        Path,
        typer.Option("--profiles-dir", help="Directory containing localization profiles."),
    ] = Path("examples/localization_profiles"),
    profile_id: Annotated[
        Optional[str],
        typer.Option("--profile-id", help="Show one profile instead of the list."),
    ] = None,
    json_output: Annotated[
        bool,
        typer.Option("--json-output", help="Print machine-readable profile JSON."),
    ] = False,
) -> None:
    try:
        payload = (
            localization_profile_payload(profiles_dir, profile_id)
            if profile_id
            else localization_profiles_payload(profiles_dir)
        )
    except (FileNotFoundError, ValueError) as exc:
        raise click.ClickException(str(exc)) from exc

    if json_output:
        typer.echo(json.dumps(payload, ensure_ascii=False, indent=2))
        return

    if profile_id:
        profile = payload["profile"]
        typer.echo(f"Profile: {profile['profile_id']}")
        typer.echo(f"Locale: {profile['locale']}")
        typer.echo(f"Platform: {profile['platform']}")
        typer.echo(f"Target language: {profile['target_language']}")
        return

    typer.echo(f"Localization profiles: {payload['profile_count']}")
    for profile in payload["profiles"]:
        typer.echo(
            f"{profile['profile_id']} | {profile['locale']} | "
            f"{profile['platform']} | {profile['target_language']}"
        )


@app.command("export-localization")
def export_localization(
    profile_path: Annotated[
        Optional[Path],
        typer.Option(
            "--profile",
            help="Localization profile JSON.",
        ),
    ] = None,
    profile_id: Annotated[
        Optional[str],
        typer.Option("--profile-id", help="Localization profile id from profiles-dir."),
    ] = None,
    profiles_dir: Annotated[
        Path,
        typer.Option("--profiles-dir", help="Directory containing localization profiles."),
    ] = Path("examples/localization_profiles"),
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
        profile = resolve_localization_profile(
            profile_path=profile_path,
            profile_id=profile_id,
            profiles_dir=profiles_dir,
        )
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
