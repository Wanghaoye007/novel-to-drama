from __future__ import annotations

from typing import Any

from novel_drama_engine.storage import ProjectStore


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
