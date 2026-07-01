from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException, Query

from novel_drama_engine.api_services import (
    BatchRunRequest,
    DeliverableRequest,
    FullRunRequest,
    MockDeliverableRequest,
    MockFullRunRequest,
    MockRunRequest,
    RunRequest,
    VideoBriefRequest,
    build_api_llm,
    project_lock,
    requested_deliverables_payload,
    resolve_completed_round,
    resolve_project_dir,
    round_artifact_payload,
    round_artifacts_payload,
    run_batch_request,
    run_mock_round,
    run_response_payload,
    run_round,
)
from novel_drama_engine.deliverables import generate_project_ad_assets, localize_project_round
from novel_drama_engine.demo import demo_localization_output, demo_marketing_assets, demo_round_outputs
from novel_drama_engine.llm import (
    LLMConfigurationError,
    LLMResponseError,
    StaticJsonLLM,
)
from novel_drama_engine.pipeline import EmptySourceError
from novel_drama_engine.status import project_status_payload, workspace_status_payload
from novel_drama_engine.storage import ProjectStore
from novel_drama_engine.video_brief import export_project_video_brief

app = FastAPI(
    title="Novel Drama Engine API",
    version="0.1.0",
)

@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/projects/batch-run-mock")
def batch_run_mock(request: BatchRunRequest) -> dict[str, object]:
    return run_batch_request(request, mock=True)


@app.post("/projects/batch-run")
def batch_run(request: BatchRunRequest) -> dict[str, object]:
    return run_batch_request(request, mock=False, llm_factory=build_api_llm)


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
            deliverables = requested_deliverables_payload(
                store=store,
                round_number=result.round_number,
                locale=request.locale,
                platform=request.platform,
                localization_guidance=request.localization_guidance,
                marketing_guidance=request.marketing_guidance,
                deliverables=request.deliverables,
                duration_seconds=request.duration_seconds,
                aspect_ratio=request.aspect_ratio,
                llm=llm,
                mock=False,
            )
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

        deliverables = requested_deliverables_payload(
            store=store,
            round_number=result.round_number,
            locale=request.locale,
            platform=request.platform,
            localization_guidance=request.localization_guidance,
            marketing_guidance=request.marketing_guidance,
            deliverables=request.deliverables,
            duration_seconds=request.duration_seconds,
            aspect_ratio=request.aspect_ratio,
            llm=StaticJsonLLM(demo_round_outputs()),
            mock=True,
        )

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


@app.get("/projects/artifacts")
def project_artifacts(
    project_dir: str = Query(
        ".drama_project",
        description="Directory containing project round artifacts.",
    ),
    round_number: int = Query(ge=1),
) -> dict[str, object]:
    with project_lock(project_dir):
        return round_artifacts_payload(ProjectStore(Path(project_dir)), round_number)


@app.get("/projects/artifact")
def project_artifact(
    project_dir: str = Query(
        ".drama_project",
        description="Directory containing project round artifacts.",
    ),
    round_number: int = Query(ge=1),
    name: str = Query(description="Artifact filename inside the round directory."),
) -> dict[str, object]:
    with project_lock(project_dir):
        return round_artifact_payload(ProjectStore(Path(project_dir)), round_number, name)


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
