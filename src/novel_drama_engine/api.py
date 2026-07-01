from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field

from novel_drama_engine.demo import demo_round_outputs
from novel_drama_engine.llm import StaticJsonLLM
from novel_drama_engine.pipeline import EmptySourceError, RoundPipeline
from novel_drama_engine.renderer import render_round_summary
from novel_drama_engine.status import project_status_payload
from novel_drama_engine.storage import ProjectStore

app = FastAPI(
    title="Novel Drama Engine API",
    version="0.1.0",
)


class MockRunRequest(BaseModel):
    project_dir: str = ".drama_project"
    project_id: str = "api"
    source_text: str = Field(min_length=1)
    round_number: int | None = Field(default=None, ge=1)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/projects/run-mock")
def run_mock_project(request: MockRunRequest) -> dict[str, object]:
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


@app.get("/projects/status")
def project_status(
    project_dir: str = Query(
        ".drama_project",
        description="Directory containing project round artifacts.",
    ),
) -> dict[str, object]:
    return project_status_payload(ProjectStore(Path(project_dir)))


@app.get("/projects/{project_id}/status")
def project_status_by_id(
    project_id: str,
    project_root: str = Query(
        ".drama_projects",
        description="Root directory containing per-source project folders.",
    ),
) -> dict[str, object]:
    return project_status_payload(ProjectStore(Path(project_root) / project_id))
