from __future__ import annotations

from pathlib import Path
from typing import Any

from novel_drama_engine.delivery import build_delivery_preflight_report
from novel_drama_engine.jobs import JobRecord, JobStore, record_counts
from novel_drama_engine.storage import ProjectStore


def project_id_from_dir(project_root: Path, project_dir: Path) -> str:
    relative = project_dir.relative_to(project_root)
    if relative == Path("."):
        return project_dir.name
    return relative.as_posix()


def discover_project_dirs(project_root: Path) -> list[Path]:
    if not project_root.exists():
        return []

    candidates = [project_root]
    candidates.extend(path for path in project_root.rglob("*") if path.is_dir())
    project_dirs = []
    for candidate in candidates:
        if ProjectStore(candidate).read_round_results():
            project_dirs.append(candidate)
    return sorted(project_dirs, key=lambda path: path.relative_to(project_root).as_posix())


def round_artifact_labels(store: ProjectStore, round_number: int, prefix: str) -> list[str]:
    round_dir = store.project_dir / f"round_{round_number:03d}"
    if not round_dir.exists():
        return []
    labels = []
    for path in sorted(round_dir.glob(f"{prefix}_*.json")):
        labels.append(path.stem.removeprefix(f"{prefix}_"))
    return labels


def artifact_content_type(path: Path) -> str:
    if path.suffix == ".json":
        return "application/json"
    if path.suffix == ".md":
        return "text/markdown"
    if path.suffix == ".zip":
        return "application/zip"
    return "text/plain"


def artifact_kind(path: Path) -> str:
    name = path.name
    stem = path.stem
    if name == "round_result.json":
        return "round_result"
    if name == "rendered_scripts.md":
        return "script"
    if name == "next_round_context.json":
        return "next_round_context"
    if stem == "video_brief":
        return "video_brief"
    if stem.startswith("localization_") or stem.startswith("localized_scripts_"):
        return "localization"
    if stem.startswith("marketing_assets_"):
        return "marketing_assets"
    if name.startswith("delivery_round_") and path.suffix == ".zip":
        return "delivery_package"
    return "other"


def artifact_label(path: Path) -> str | None:
    stem = path.stem
    for prefix in [
        "localization_",
        "localized_scripts_",
        "marketing_assets_",
    ]:
        if stem.startswith(prefix):
            return stem.removeprefix(prefix)
    if stem == "video_brief":
        return "video_brief"
    if stem.startswith("delivery_round_"):
        return stem
    return None


def round_artifacts_status(store: ProjectStore, round_number: int) -> list[dict[str, Any]]:
    round_dir = store.project_dir / f"round_{round_number:03d}"
    if not round_dir.is_dir():
        return []

    artifacts = []
    for path in sorted(child for child in round_dir.iterdir() if child.is_file()):
        artifacts.append(
            {
                "name": path.name,
                "path": str(path),
                "relative_path": f"{round_dir.name}/{path.name}",
                "size_bytes": path.stat().st_size,
                "content_type": artifact_content_type(path),
                "kind": artifact_kind(path),
                "label": artifact_label(path),
            }
        )
    return artifacts


def artifact_kind_counts(artifacts: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for artifact in artifacts:
        kind = str(artifact["kind"])
        counts[kind] = counts.get(kind, 0) + 1
    return dict(sorted(counts.items()))


def delivery_status_payload(store: ProjectStore, round_number: int) -> dict[str, Any]:
    try:
        report = build_delivery_preflight_report(store, round_number=round_number)
    except Exception as exc:  # pragma: no cover - status must stay observable
        return {
            "ready": False,
            "quality_status": None,
            "warnings": [f"delivery preflight unavailable: {exc}"],
            "file_count": 0,
            "files": [],
        }

    files = [file.model_dump(mode="json") for file in report.files]
    return {
        "ready": report.ready,
        "quality_status": report.quality_status.value,
        "warnings": report.warnings,
        "file_count": len(files),
        "files": files,
    }


def resolve_job_project_dir(project_root: Path, raw_job: dict[str, Any]) -> Path | None:
    project_id = raw_job.get("project_id")
    raw_project_dir = raw_job.get("project_dir")
    if raw_project_dir:
        path = Path(str(raw_project_dir)).expanduser()
        return (path if path.is_absolute() else project_root / path).resolve()
    if project_id:
        return (project_root / str(project_id)).resolve()
    return None


def job_targets_project(record: JobRecord, project_dir: Path) -> bool:
    request = record.request
    raw_project_dir = request.get("project_dir")
    if raw_project_dir and Path(str(raw_project_dir)).expanduser().resolve() == project_dir:
        return True

    raw_project_root = request.get("project_root")
    raw_jobs = request.get("jobs")
    if raw_project_root is None or not isinstance(raw_jobs, list):
        return False

    project_root = Path(str(raw_project_root)).expanduser().resolve()
    for raw_job in raw_jobs:
        if not isinstance(raw_job, dict):
            continue
        if resolve_job_project_dir(project_root, raw_job) == project_dir:
            return True
    return False


def project_jobs_payload(store: ProjectStore, jobs_dir: Path | str | None) -> dict[str, Any] | None:
    if jobs_dir is None:
        return None

    job_store = JobStore(jobs_dir)
    project_dir = store.project_dir.expanduser().resolve()
    records = [
        record
        for record in job_store.list()
        if job_targets_project(record, project_dir)
    ]
    return {
        "jobs_dir": str(job_store.jobs_dir),
        "job_count": len(records),
        "status_counts": record_counts(records, "status"),
        "kind_counts": record_counts(records, "kind"),
        "jobs": [
            {
                "job_id": record.job_id,
                "kind": record.kind,
                "status": record.status,
                "attempt": record.attempt,
                "parent_job_id": record.parent_job_id,
                "created_at": record.created_at,
                "updated_at": record.updated_at,
            }
            for record in records
        ],
    }


def project_status_payload(
    store: ProjectStore,
    *,
    jobs_dir: Path | str | None = None,
) -> dict[str, Any]:
    results = store.read_round_results()
    rounds = []
    for result in results:
        scores = result.quality_report.scores
        artifacts = round_artifacts_status(store, result.round_number)
        rounds.append(
            {
                "round_number": result.round_number,
                "target_episode_range": result.episode_context.target_episode_range,
                "quality_status": result.quality_report.status.value,
                "scores": scores.model_dump(),
                "episode_count": len(result.script_batch.episodes),
                "episode_titles": [
                    {
                        "episode": episode.episode,
                        "title": episode.title,
                    }
                    for episode in result.script_batch.episodes
                ],
                "open_hooks": result.next_round_context.open_hooks,
                "localizations": round_artifact_labels(
                    store,
                    result.round_number,
                    "localization",
                ),
                "marketing_assets": round_artifact_labels(
                    store,
                    result.round_number,
                    "marketing_assets",
                ),
                "video_brief": (
                    store.project_dir
                    / f"round_{result.round_number:03d}"
                    / "video_brief.json"
                ).exists(),
                "artifact_count": len(artifacts),
                "artifact_counts": artifact_kind_counts(artifacts),
                "artifacts": artifacts,
                "delivery": delivery_status_payload(store, result.round_number),
            }
        )
    latest_context_path = store.latest_next_round_context_path()
    payload = {
        "schema_version": "project_status.v1",
        "project_dir": str(store.project_dir),
        "round_count": len(results),
        "current_episode": results[-1].next_round_context.current_episode if results else None,
        "rounds": rounds,
        "latest_round": rounds[-1] if rounds else None,
        "latest_context": str(latest_context_path) if latest_context_path else None,
    }
    jobs = project_jobs_payload(store, jobs_dir)
    if jobs is not None:
        payload["jobs"] = jobs
    return payload


def workspace_status_payload(
    project_root: Path,
    *,
    jobs_dir: Path | str | None = None,
) -> dict[str, Any]:
    project_dirs = discover_project_dirs(project_root)
    projects = []
    total_rounds = 0
    for project_dir in project_dirs:
        status = project_status_payload(ProjectStore(project_dir), jobs_dir=jobs_dir)
        total_rounds += status["round_count"]
        rounds = status["rounds"]
        project = {
            "project_id": project_id_from_dir(project_root, project_dir),
            "project_dir": status["project_dir"],
            "round_count": status["round_count"],
            "current_episode": status["current_episode"],
            "latest_context": status["latest_context"],
            "latest_round": rounds[-1] if rounds else None,
        }
        if "jobs" in status:
            project["jobs"] = status["jobs"]
        projects.append(project)
    return {
        "schema_version": "workspace_status.v1",
        "project_root": str(project_root),
        "project_count": len(projects),
        "total_round_count": total_rounds,
        "projects": projects,
    }
