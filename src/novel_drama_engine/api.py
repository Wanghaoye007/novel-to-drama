from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, Query

from novel_drama_engine.status import project_status_payload
from novel_drama_engine.storage import ProjectStore

app = FastAPI(
    title="Novel Drama Engine API",
    version="0.1.0",
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


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
