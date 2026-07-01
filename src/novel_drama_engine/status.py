from __future__ import annotations

from pathlib import Path
from typing import Any

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


def project_status_payload(store: ProjectStore) -> dict[str, Any]:
    results = store.read_round_results()
    rounds = []
    for result in results:
        scores = result.quality_report.scores
        rounds.append(
            {
                "round_number": result.round_number,
                "target_episode_range": result.episode_context.target_episode_range,
                "quality_status": result.quality_report.status.value,
                "scores": scores.model_dump(),
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
            }
        )
    latest_context_path = store.latest_next_round_context_path()
    return {
        "project_dir": str(store.project_dir),
        "round_count": len(results),
        "current_episode": results[-1].next_round_context.current_episode if results else None,
        "rounds": rounds,
        "latest_context": str(latest_context_path) if latest_context_path else None,
    }


def workspace_status_payload(project_root: Path) -> dict[str, Any]:
    project_dirs = discover_project_dirs(project_root)
    projects = []
    total_rounds = 0
    for project_dir in project_dirs:
        status = project_status_payload(ProjectStore(project_dir))
        total_rounds += status["round_count"]
        rounds = status["rounds"]
        projects.append(
            {
                "project_id": project_id_from_dir(project_root, project_dir),
                "project_dir": status["project_dir"],
                "round_count": status["round_count"],
                "current_episode": status["current_episode"],
                "latest_context": status["latest_context"],
                "latest_round": rounds[-1] if rounds else None,
            }
        )
    return {
        "project_root": str(project_root),
        "project_count": len(projects),
        "total_round_count": total_rounds,
        "projects": projects,
    }
