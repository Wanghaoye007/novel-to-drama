from __future__ import annotations

import zipfile
from pathlib import Path

from novel_drama_engine.models import DeliveryFile, DeliveryManifest, RoundResult
from novel_drama_engine.storage import ProjectStore


def delivery_zip_name(round_number: int) -> str:
    return f"delivery_round_{round_number:03d}.zip"


def iter_delivery_files(round_dir: Path) -> list[Path]:
    return sorted(
        path
        for path in round_dir.iterdir()
        if path.is_file() and path.suffix != ".zip"
    )


def build_delivery_manifest(
    result: RoundResult,
    *,
    round_dir: Path,
    files: list[Path],
) -> DeliveryManifest:
    return DeliveryManifest(
        project_id=result.project_id,
        round_number=result.round_number,
        target_episode_range=result.episode_context.target_episode_range,
        quality_status=result.quality_report.status,
        included_files=[
            DeliveryFile(
                path=f"{round_dir.name}/{path.name}",
                bytes=path.stat().st_size,
            )
            for path in files
        ],
    )


def export_delivery_package(
    store: ProjectStore,
    *,
    round_number: int | None = None,
    output_path: Path | None = None,
) -> Path:
    if round_number is None:
        results = store.read_round_results()
        if not results:
            raise FileNotFoundError(f"No completed rounds found in: {store.project_dir}")
        result = results[-1]
    else:
        result = store.read_round_result(round_number)

    round_dir = store.project_dir / f"round_{result.round_number:03d}"
    files = iter_delivery_files(round_dir)
    manifest = build_delivery_manifest(result, round_dir=round_dir, files=files)
    output = output_path or (round_dir / delivery_zip_name(result.round_number))
    output.parent.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(
            "delivery_manifest.json",
            manifest.model_dump_json(indent=2),
        )
        for path in files:
            archive.write(path, arcname=f"{round_dir.name}/{path.name}")

    return output
