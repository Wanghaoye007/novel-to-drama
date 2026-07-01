from __future__ import annotations

from pathlib import Path
from threading import Lock

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field

from novel_drama_engine.deliverables import generate_project_ad_assets, localize_project_round
from novel_drama_engine.demo import demo_localization_output, demo_marketing_assets, demo_round_outputs
from novel_drama_engine.llm import StaticJsonLLM
from novel_drama_engine.pipeline import EmptySourceError, RoundPipeline
from novel_drama_engine.renderer import render_round_summary
from novel_drama_engine.status import project_status_payload, workspace_status_payload
from novel_drama_engine.storage import ProjectStore

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


class MockDeliverableRequest(BaseModel):
    project_dir: str = ".drama_project"
    round_number: int | None = Field(default=None, ge=1)
    locale: str = "en-US"
    platform: str = "TikTok"
    guidance: str = ""


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


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/projects/run-mock")
def run_mock_project(request: MockRunRequest) -> dict[str, object]:
    with project_lock(request.project_dir):
        store = ProjectStore(Path(request.project_dir))
        latest_round_number = store.latest_round_number()
        resolved_round_number = request.round_number or ((latest_round_number or 0) + 1)
        latest_context_path = store.latest_next_round_context_path()
        previous_context = (
            store.read_next_round_context(latest_context_path)
            if latest_context_path
            else None
        )
        pipeline = RoundPipeline(llm=StaticJsonLLM(demo_round_outputs()), store=store)
        try:
            result = pipeline.run(
                project_id=request.project_id,
                round_number=resolved_round_number,
                source_text=request.source_text,
                previous_context=previous_context,
            )
        except EmptySourceError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

        rendered = render_round_summary(result.script_batch, result.quality_report)
        store.write_text_artifact(result.round_number, "rendered_scripts.md", rendered)
        return {
            "project_dir": str(store.project_dir),
            "round_number": result.round_number,
            "target_episode_range": result.episode_context.target_episode_range,
            "quality_status": result.quality_report.status.value,
            "project_status": project_status_payload(store),
        }


@app.post("/projects/localize-mock")
def localize_mock_project(request: MockDeliverableRequest) -> dict[str, object]:
    with project_lock(request.project_dir):
        store = ProjectStore(Path(request.project_dir))
        round_number = resolve_completed_round(store, request.round_number)
        localized, json_path, markdown_path = localize_project_round(
            store=store,
            round_number=round_number,
            locale=request.locale,
            platform=request.platform,
            guidance=request.guidance,
            llm=StaticJsonLLM([demo_localization_output(request.locale, request.platform)]),
        )
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
        json_path, markdown_path = generate_project_ad_assets(
            store=store,
            round_number=round_number,
            locale=request.locale,
            platform=request.platform,
            guidance=request.guidance,
            llm=StaticJsonLLM([demo_marketing_assets(request.locale, request.platform)]),
        )
        return {
            "project_dir": str(store.project_dir),
            "round_number": round_number,
            "locale": request.locale,
            "platform": request.platform,
            "json": str(json_path),
            "markdown": str(markdown_path),
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
