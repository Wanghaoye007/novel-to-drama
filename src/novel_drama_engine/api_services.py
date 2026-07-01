from __future__ import annotations

import json
from pathlib import Path
from tempfile import NamedTemporaryFile
from threading import Lock
from typing import Literal

from fastapi import HTTPException
from pydantic import BaseModel, Field

from novel_drama_engine.deliverables import generate_project_ad_assets, localize_project_round
from novel_drama_engine.demo import demo_localization_output, demo_marketing_assets, demo_round_outputs
from novel_drama_engine.llm import (
    JsonLLM,
    LLMConfigurationError,
    LLMResponseError,
    OpenAIJsonLLM,
    StaticJsonLLM,
)
from novel_drama_engine.models import RoundResult
from novel_drama_engine.pipeline import EmptySourceError, RoundPipeline
from novel_drama_engine.renderer import render_round_summary
from novel_drama_engine.status import project_status_payload, workspace_status_payload
from novel_drama_engine.storage import ProjectStore
from novel_drama_engine.video_brief import export_project_video_brief

_PROJECT_LOCKS_GUARD = Lock()
_PROJECT_LOCKS: dict[Path, Lock] = {}
DeliverableName = Literal["localization", "ad_assets", "video_brief"]


class MockRunRequest(BaseModel):
    project_dir: str = ".drama_project"
    project_id: str = "api"
    source_text: str = Field(min_length=1)
    round_number: int | None = Field(default=None, ge=1)


class RunRequest(MockRunRequest):
    model: str | None = None


class MockDeliverableRequest(BaseModel):
    project_dir: str = ".drama_project"
    round_number: int | None = Field(default=None, ge=1)
    locale: str = "en-US"
    platform: str = "TikTok"
    guidance: str = ""


class DeliverableRequest(MockDeliverableRequest):
    model: str | None = None


class VideoBriefRequest(BaseModel):
    project_dir: str = ".drama_project"
    round_number: int | None = Field(default=None, ge=1)
    duration_seconds: int = Field(default=75, ge=1)
    aspect_ratio: str = "9:16"


class DeliveryExportRequest(BaseModel):
    project_dir: str = ".drama_project"
    round_number: int | None = Field(default=None, ge=1)
    output: str | None = None
    allow_issues: bool = False


class MockFullRunRequest(MockRunRequest):
    locale: str = "en-US"
    platform: str = "TikTok"
    localization_guidance: str = ""
    marketing_guidance: str = ""
    deliverables: list[DeliverableName] = Field(default_factory=list)
    duration_seconds: int = Field(default=75, ge=1)
    aspect_ratio: str = "9:16"


class FullRunRequest(MockFullRunRequest):
    model: str | None = None


class BatchJobRequest(BaseModel):
    project_id: str
    source_text: str = Field(min_length=1)
    project_dir: str | None = None
    round_number: int | None = Field(default=None, ge=1)
    locale: str = "en-US"
    platform: str = "TikTok"
    localization_guidance: str = ""
    marketing_guidance: str = ""
    deliverables: list[DeliverableName] = Field(default_factory=list)
    duration_seconds: int = Field(default=75, ge=1)
    aspect_ratio: str = "9:16"


class BatchRunRequest(BaseModel):
    project_root: str = ".drama_projects"
    jobs: list[BatchJobRequest] = Field(min_length=1)
    continue_on_error: bool = True
    model: str | None = None


def project_lock(project_dir: str | Path) -> Lock:
    key = Path(project_dir).expanduser().resolve()
    with _PROJECT_LOCKS_GUARD:
        lock = _PROJECT_LOCKS.get(key)
        if lock is None:
            lock = Lock()
            _PROJECT_LOCKS[key] = lock
        return lock


def resolve_completed_round(store: ProjectStore, round_number: int | None) -> int:
    resolved_round_number = round_number or store.latest_round_number()
    if resolved_round_number is None:
        raise HTTPException(status_code=404, detail="No completed rounds found")
    return resolved_round_number


def resolve_project_dir(project_root: str | Path, project_id: str) -> Path:
    root = Path(project_root).expanduser().resolve()
    project_dir = (root / project_id).resolve()
    try:
        project_dir.relative_to(root)
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail="project_id must stay inside project_root",
        ) from exc
    return project_dir


def resolve_batch_project_dir(project_root: str | Path, job: BatchJobRequest) -> Path:
    root = Path(project_root).expanduser().resolve()
    if job.project_dir:
        raw_project_dir = Path(job.project_dir).expanduser()
        project_dir = (
            raw_project_dir
            if raw_project_dir.is_absolute()
            else root / raw_project_dir
        ).resolve()
    else:
        project_dir = (root / job.project_id).resolve()
    try:
        project_dir.relative_to(root)
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail="project_dir must stay inside project_root",
        ) from exc
    return project_dir


def round_artifact_dir(store: ProjectStore, round_number: int) -> Path:
    return store.project_dir / f"round_{round_number:03d}"


def artifact_content_type(path: Path) -> str:
    if path.suffix == ".json":
        return "application/json"
    if path.suffix == ".md":
        return "text/markdown"
    return "text/plain"


def resolve_round_artifact_path(
    store: ProjectStore,
    round_number: int,
    name: str,
) -> Path:
    raw_name = Path(name)
    if raw_name.name != name or name in {"", ".", ".."}:
        raise HTTPException(
            status_code=400,
            detail="artifact name must be a filename inside the round directory",
        )
    round_dir = round_artifact_dir(store, round_number).resolve()
    path = (round_dir / name).resolve()
    try:
        path.relative_to(round_dir)
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail="artifact name must stay inside the round directory",
        ) from exc
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Artifact not found")
    return path


def round_artifacts_payload(store: ProjectStore, round_number: int) -> dict[str, object]:
    round_dir = round_artifact_dir(store, round_number)
    if not round_dir.is_dir():
        raise HTTPException(status_code=404, detail="Round not found")
    artifacts = []
    for path in sorted(child for child in round_dir.iterdir() if child.is_file()):
        artifacts.append(
            {
                "name": path.name,
                "path": str(path),
                "size_bytes": path.stat().st_size,
                "content_type": artifact_content_type(path),
            }
        )
    return {
        "project_dir": str(store.project_dir),
        "round_number": round_number,
        "artifacts": artifacts,
    }


def round_artifact_payload(
    store: ProjectStore,
    round_number: int,
    name: str,
) -> dict[str, object]:
    path = resolve_round_artifact_path(store, round_number, name)
    return {
        "project_dir": str(store.project_dir),
        "round_number": round_number,
        "name": path.name,
        "path": str(path),
        "content_type": artifact_content_type(path),
        "content": path.read_text(encoding="utf-8"),
    }


def write_text_atomic(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = None
    try:
        with NamedTemporaryFile(
            "w",
            delete=False,
            dir=path.parent,
            encoding="utf-8",
            prefix=f".{path.name}.",
            suffix=".tmp",
        ) as temp_file:
            temp_file.write(text)
            temp_path = Path(temp_file.name)
        temp_path.replace(path)
    finally:
        if temp_path is not None and temp_path.exists():
            temp_path.unlink()


def write_batch_report(project_root: Path, report: dict[str, object]) -> Path:
    path = project_root / "batch_report.json"
    report["report_path"] = str(path)
    write_text_atomic(path, json.dumps(report, ensure_ascii=False, indent=2))
    return path


def build_api_llm(model: str | None = None) -> OpenAIJsonLLM:
    return OpenAIJsonLLM(model=model)


def run_round(store: ProjectStore, request: MockRunRequest, llm: JsonLLM) -> RoundResult:
    latest_round_number = store.latest_round_number()
    resolved_round_number = request.round_number or ((latest_round_number or 0) + 1)
    latest_context_path = store.latest_next_round_context_path()
    previous_context = (
        store.read_next_round_context(latest_context_path)
        if latest_context_path
        else None
    )
    pipeline = RoundPipeline(llm=llm, store=store)
    result = pipeline.run(
        project_id=request.project_id,
        round_number=resolved_round_number,
        source_text=request.source_text,
        previous_context=previous_context,
    )
    rendered = render_round_summary(result.script_batch, result.quality_report)
    store.write_text_artifact(result.round_number, "rendered_scripts.md", rendered)
    return result


def run_mock_round(store: ProjectStore, request: MockRunRequest) -> RoundResult:
    return run_round(store, request, StaticJsonLLM(demo_round_outputs()))


def run_response_payload(store: ProjectStore, result: RoundResult) -> dict[str, object]:
    return {
        "project_dir": str(store.project_dir),
        "round_number": result.round_number,
        "target_episode_range": result.episode_context.target_episode_range,
        "quality_status": result.quality_report.status.value,
        "project_status": project_status_payload(store),
    }


def requested_deliverables_payload(
    *,
    store: ProjectStore,
    round_number: int,
    locale: str,
    platform: str,
    localization_guidance: str,
    marketing_guidance: str,
    deliverables: list[DeliverableName],
    duration_seconds: int,
    aspect_ratio: str,
    llm: JsonLLM,
    mock: bool,
) -> dict[str, dict[str, object]]:
    payload: dict[str, dict[str, object]] = {}
    if "localization" in deliverables:
        localized, json_path, markdown_path = localize_project_round(
            store=store,
            round_number=round_number,
            locale=locale,
            platform=platform,
            guidance=localization_guidance,
            llm=(
                StaticJsonLLM([demo_localization_output(locale, platform)])
                if mock
                else llm
            ),
        )
        payload["localization"] = {
            "locale": localized.locale,
            "platform": localized.platform,
            "json": str(json_path),
            "markdown": str(markdown_path),
        }
    if "ad_assets" in deliverables:
        json_path, markdown_path = generate_project_ad_assets(
            store=store,
            round_number=round_number,
            locale=locale,
            platform=platform,
            guidance=marketing_guidance,
            llm=(
                StaticJsonLLM([demo_marketing_assets(locale, platform)])
                if mock
                else llm
            ),
        )
        payload["ad_assets"] = {
            "locale": locale,
            "platform": platform,
            "json": str(json_path),
            "markdown": str(markdown_path),
        }
    if "video_brief" in deliverables:
        brief, json_path, markdown_path = export_project_video_brief(
            store=store,
            round_number=round_number,
            duration_seconds=duration_seconds,
            aspect_ratio=aspect_ratio,
        )
        payload["video_brief"] = {
            "json": str(json_path),
            "markdown": str(markdown_path),
            "episode_count": len(brief.episodes),
        }
    return payload


def batch_job_payload(
    *,
    index: int,
    job: BatchJobRequest,
    project_dir: Path,
    result: RoundResult,
    deliverables: dict[str, dict[str, object]],
) -> dict[str, object]:
    return {
        "index": index,
        "status": "ok",
        "project_id": job.project_id,
        "project_dir": str(project_dir),
        "round_number": result.round_number,
        "quality_status": result.quality_report.status.value,
        "target_episode_range": result.episode_context.target_episode_range,
        "deliverables": deliverables,
    }


def batch_failure_payload(
    *,
    index: int,
    job: BatchJobRequest,
    error: str,
) -> dict[str, object]:
    return {
        "index": index,
        "status": "failed",
        "project_id": job.project_id,
        "error": error,
    }


def run_batch_request(
    request: BatchRunRequest,
    *,
    mock: bool,
    llm_factory=build_api_llm,
) -> dict[str, object]:
    project_root = Path(request.project_root).expanduser().resolve()
    try:
        shared_llm = None if mock else llm_factory(request.model)
    except LLMConfigurationError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except LLMResponseError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    results: list[dict[str, object]] = []
    successes = 0
    failures = 0
    for index, job in enumerate(request.jobs, start=1):
        try:
            project_dir = resolve_batch_project_dir(project_root, job)
            with project_lock(project_dir):
                store = ProjectStore(project_dir)
                run_request = MockRunRequest(
                    project_dir=str(project_dir),
                    project_id=job.project_id,
                    source_text=job.source_text,
                    round_number=job.round_number,
                )
                llm = StaticJsonLLM(demo_round_outputs()) if mock else shared_llm
                if llm is None:
                    raise LLMConfigurationError("LLM is not configured")
                result = run_round(store, run_request, llm)
                deliverables = requested_deliverables_payload(
                    store=store,
                    round_number=result.round_number,
                    locale=job.locale,
                    platform=job.platform,
                    localization_guidance=job.localization_guidance,
                    marketing_guidance=job.marketing_guidance,
                    deliverables=job.deliverables,
                    duration_seconds=job.duration_seconds,
                    aspect_ratio=job.aspect_ratio,
                    llm=llm,
                    mock=mock,
                )
            successes += 1
            results.append(
                batch_job_payload(
                    index=index,
                    job=job,
                    project_dir=project_dir,
                    result=result,
                    deliverables=deliverables,
                )
            )
        except HTTPException as exc:
            failures += 1
            results.append(
                batch_failure_payload(
                    index=index,
                    job=job,
                    error=str(exc.detail),
                )
            )
        except (EmptySourceError, FileNotFoundError, LLMResponseError, OSError) as exc:
            failures += 1
            results.append(
                batch_failure_payload(
                    index=index,
                    job=job,
                    error=str(exc),
                )
            )
        if failures and not request.continue_on_error:
            break

    status = "ok" if failures == 0 else "failed" if successes == 0 else "partial"
    report: dict[str, object] = {
        "status": status,
        "project_root": str(project_root),
        "job_count": len(request.jobs),
        "successes": successes,
        "failures": failures,
        "results": results,
        "workspace_status": workspace_status_payload(project_root),
    }
    write_batch_report(project_root, report)
    return report
