from __future__ import annotations

from pathlib import Path
from threading import Lock
from typing import Literal

from fastapi import FastAPI, HTTPException, Query
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

app = FastAPI(
    title="Novel Drama Engine API",
    version="0.1.0",
)

_PROJECT_LOCKS_GUARD = Lock()
_PROJECT_LOCKS: dict[Path, Lock] = {}


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


class MockFullRunRequest(MockRunRequest):
    locale: str = "en-US"
    platform: str = "TikTok"
    localization_guidance: str = ""
    marketing_guidance: str = ""
    deliverables: list[Literal["localization", "ad_assets"]] = Field(default_factory=list)


class FullRunRequest(MockFullRunRequest):
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


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/projects/run-mock")
def run_mock_project(request: MockRunRequest) -> dict[str, object]:
    with project_lock(request.project_dir):
        store = ProjectStore(Path(request.project_dir))
        try:
            result = run_mock_round(store, request)
        except EmptySourceError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return run_response_payload(store, result)


@app.post("/projects/run")
def run_project(request: RunRequest) -> dict[str, object]:
    with project_lock(request.project_dir):
        store = ProjectStore(Path(request.project_dir))
        try:
            result = run_round(store, request, build_api_llm(request.model))
        except EmptySourceError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except LLMConfigurationError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc
        except LLMResponseError as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc
        return run_response_payload(store, result)


@app.post("/projects/run-full")
def run_full_project(request: FullRunRequest) -> dict[str, object]:
    with project_lock(request.project_dir):
        store = ProjectStore(Path(request.project_dir))
        try:
            llm = build_api_llm(request.model)
            result = run_round(store, request, llm)
            deliverables: dict[str, dict[str, str]] = {}
            if "localization" in request.deliverables:
                localized, json_path, markdown_path = localize_project_round(
                    store=store,
                    round_number=result.round_number,
                    locale=request.locale,
                    platform=request.platform,
                    guidance=request.localization_guidance,
                    llm=llm,
                )
                deliverables["localization"] = {
                    "locale": localized.locale,
                    "platform": localized.platform,
                    "json": str(json_path),
                    "markdown": str(markdown_path),
                }
            if "ad_assets" in request.deliverables:
                json_path, markdown_path = generate_project_ad_assets(
                    store=store,
                    round_number=result.round_number,
                    locale=request.locale,
                    platform=request.platform,
                    guidance=request.marketing_guidance,
                    llm=llm,
                )
                deliverables["ad_assets"] = {
                    "locale": request.locale,
                    "platform": request.platform,
                    "json": str(json_path),
                    "markdown": str(markdown_path),
                }
        except EmptySourceError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except LLMConfigurationError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc
        except LLMResponseError as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc

        payload = run_response_payload(store, result)
        payload["deliverables"] = deliverables
        payload["project_status"] = project_status_payload(store)
        return payload


@app.post("/projects/run-full-mock")
def run_full_mock_project(request: MockFullRunRequest) -> dict[str, object]:
    with project_lock(request.project_dir):
        store = ProjectStore(Path(request.project_dir))
        try:
            result = run_mock_round(store, request)
        except EmptySourceError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

        deliverables: dict[str, dict[str, str]] = {}
        if "localization" in request.deliverables:
            localized, json_path, markdown_path = localize_project_round(
                store=store,
                round_number=result.round_number,
                locale=request.locale,
                platform=request.platform,
                guidance=request.localization_guidance,
                llm=StaticJsonLLM(
                    [demo_localization_output(request.locale, request.platform)]
                ),
            )
            deliverables["localization"] = {
                "locale": localized.locale,
                "platform": localized.platform,
                "json": str(json_path),
                "markdown": str(markdown_path),
            }
        if "ad_assets" in request.deliverables:
            json_path, markdown_path = generate_project_ad_assets(
                store=store,
                round_number=result.round_number,
                locale=request.locale,
                platform=request.platform,
                guidance=request.marketing_guidance,
                llm=StaticJsonLLM([demo_marketing_assets(request.locale, request.platform)]),
            )
            deliverables["ad_assets"] = {
                "locale": request.locale,
                "platform": request.platform,
                "json": str(json_path),
                "markdown": str(markdown_path),
            }

        payload = run_response_payload(store, result)
        payload["deliverables"] = deliverables
        payload["project_status"] = project_status_payload(store)
        return payload


@app.post("/projects/localize-mock")
def localize_mock_project(request: MockDeliverableRequest) -> dict[str, object]:
    with project_lock(request.project_dir):
        store = ProjectStore(Path(request.project_dir))
        round_number = resolve_completed_round(store, request.round_number)
        try:
            localized, json_path, markdown_path = localize_project_round(
                store=store,
                round_number=round_number,
                locale=request.locale,
                platform=request.platform,
                guidance=request.guidance,
                llm=StaticJsonLLM(
                    [demo_localization_output(request.locale, request.platform)]
                ),
            )
        except FileNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        return {
            "project_dir": str(store.project_dir),
            "round_number": round_number,
            "locale": localized.locale,
            "platform": localized.platform,
            "json": str(json_path),
            "markdown": str(markdown_path),
            "project_status": project_status_payload(store),
        }


@app.post("/projects/localize")
def localize_project(request: DeliverableRequest) -> dict[str, object]:
    with project_lock(request.project_dir):
        store = ProjectStore(Path(request.project_dir))
        round_number = resolve_completed_round(store, request.round_number)
        try:
            localized, json_path, markdown_path = localize_project_round(
                store=store,
                round_number=round_number,
                locale=request.locale,
                platform=request.platform,
                guidance=request.guidance,
                llm=build_api_llm(request.model),
            )
        except FileNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except LLMConfigurationError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc
        except LLMResponseError as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc
        return {
            "project_dir": str(store.project_dir),
            "round_number": round_number,
            "locale": localized.locale,
            "platform": localized.platform,
            "json": str(json_path),
            "markdown": str(markdown_path),
            "project_status": project_status_payload(store),
        }


@app.post("/projects/ad-assets-mock")
def ad_assets_mock_project(request: MockDeliverableRequest) -> dict[str, object]:
    with project_lock(request.project_dir):
        store = ProjectStore(Path(request.project_dir))
        round_number = resolve_completed_round(store, request.round_number)
        try:
            json_path, markdown_path = generate_project_ad_assets(
                store=store,
                round_number=round_number,
                locale=request.locale,
                platform=request.platform,
                guidance=request.guidance,
                llm=StaticJsonLLM(
                    [demo_marketing_assets(request.locale, request.platform)]
                ),
            )
        except FileNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        return {
            "project_dir": str(store.project_dir),
            "round_number": round_number,
            "locale": request.locale,
            "platform": request.platform,
            "json": str(json_path),
            "markdown": str(markdown_path),
            "project_status": project_status_payload(store),
        }


@app.post("/projects/ad-assets")
def ad_assets_project(request: DeliverableRequest) -> dict[str, object]:
    with project_lock(request.project_dir):
        store = ProjectStore(Path(request.project_dir))
        round_number = resolve_completed_round(store, request.round_number)
        try:
            json_path, markdown_path = generate_project_ad_assets(
                store=store,
                round_number=round_number,
                locale=request.locale,
                platform=request.platform,
                guidance=request.guidance,
                llm=build_api_llm(request.model),
            )
        except FileNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except LLMConfigurationError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc
        except LLMResponseError as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc
        return {
            "project_dir": str(store.project_dir),
            "round_number": round_number,
            "locale": request.locale,
            "platform": request.platform,
            "json": str(json_path),
            "markdown": str(markdown_path),
            "project_status": project_status_payload(store),
        }


@app.post("/projects/export-video-brief")
def export_video_brief_project(request: VideoBriefRequest) -> dict[str, object]:
    with project_lock(request.project_dir):
        store = ProjectStore(Path(request.project_dir))
        round_number = resolve_completed_round(store, request.round_number)
        try:
            brief, json_path, markdown_path = export_project_video_brief(
                store=store,
                round_number=round_number,
                duration_seconds=request.duration_seconds,
                aspect_ratio=request.aspect_ratio,
            )
        except FileNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        return {
            "project_dir": str(store.project_dir),
            "round_number": round_number,
            "json": str(json_path),
            "markdown": str(markdown_path),
            "brief": brief.model_dump(),
            "project_status": project_status_payload(store),
        }


@app.get("/projects/status")
def project_status(
    project_dir: str = Query(
        ".drama_project",
        description="Directory containing project round artifacts.",
    ),
) -> dict[str, object]:
    with project_lock(project_dir):
        return project_status_payload(ProjectStore(Path(project_dir)))


@app.get("/projects")
def list_projects(
    project_root: str = Query(
        ".drama_projects",
        description="Root directory containing per-source project folders.",
    ),
) -> dict[str, object]:
    return workspace_status_payload(Path(project_root))


@app.get("/projects/{project_id:path}/status")
def project_status_by_id(
    project_id: str,
    project_root: str = Query(
        ".drama_projects",
        description="Root directory containing per-source project folders.",
    ),
) -> dict[str, object]:
    project_dir = resolve_project_dir(project_root, project_id)
    with project_lock(project_dir):
        return project_status_payload(ProjectStore(project_dir))
