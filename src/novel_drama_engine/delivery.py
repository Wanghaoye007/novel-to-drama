from __future__ import annotations

import zipfile
from pathlib import Path

from pydantic import ValidationError

from novel_drama_engine.models import (
    DeliveryFile,
    DeliveryManifest,
    DeliveryPreflightReport,
    LocalizationPackage,
    QualityStatus,
    RoundResult,
)
from novel_drama_engine.storage import ProjectStore


class DeliveryValidationError(RuntimeError):
    def __init__(self, warnings: list[str]) -> None:
        self.warnings = warnings
        super().__init__("Delivery package blocked: " + "; ".join(warnings))


def delivery_zip_name(round_number: int) -> str:
    return f"delivery_round_{round_number:03d}.zip"


def iter_delivery_files(round_dir: Path) -> list[Path]:
    return sorted(
        path
        for path in round_dir.iterdir()
        if path.is_file() and path.suffix != ".zip"
    )


def collect_delivery_warnings(
    result: RoundResult,
    *,
    files: list[Path],
) -> list[str]:
    warnings: list[str] = []
    if result.quality_report.status != QualityStatus.USABLE:
        warnings.append(f"quality status is {result.quality_report.status.value}")

    names = {path.name for path in files}
    for required in ["rendered_scripts.md", "round_result.json"]:
        if required not in names:
            warnings.append(f"missing required artifact: {required}")

    for path in files:
        if not path.name.startswith("localization_") or path.suffix != ".json":
            continue
        raw = path.read_text(encoding="utf-8")
        try:
            package = LocalizationPackage.model_validate_json(raw)
        except ValidationError:
            warnings.append(f"{path.name} is not a delivery localization package")
            continue
        if package.issues:
            warnings.append(
                f"{path.name} has {len(package.issues)} localization review issue(s)"
            )
    return warnings


def build_delivery_manifest(
    result: RoundResult,
    *,
    round_dir: Path,
    files: list[Path],
    warnings: list[str] | None = None,
) -> DeliveryManifest:
    return DeliveryManifest(
        project_id=result.project_id,
        round_number=result.round_number,
        target_episode_range=result.episode_context.target_episode_range,
        quality_status=result.quality_report.status,
        warnings=warnings or [],
        included_files=[
            DeliveryFile(
                path=f"{round_dir.name}/{path.name}",
                bytes=path.stat().st_size,
            )
            for path in files
        ],
    )


def read_delivery_round(
    store: ProjectStore,
    round_number: int | None,
) -> RoundResult:
    if round_number is None:
        results = store.read_round_results()
        if not results:
            raise FileNotFoundError(f"No completed rounds found in: {store.project_dir}")
        return results[-1]
    return store.read_round_result(round_number)


def build_delivery_preflight_report(
    store: ProjectStore,
    *,
    round_number: int | None = None,
) -> DeliveryPreflightReport:
    result = read_delivery_round(store, round_number)
    round_dir = store.project_dir / f"round_{result.round_number:03d}"
    files = iter_delivery_files(round_dir)
    warnings = collect_delivery_warnings(result, files=files)
    return DeliveryPreflightReport(
        project_id=result.project_id,
        round_number=result.round_number,
        target_episode_range=result.episode_context.target_episode_range,
        quality_status=result.quality_report.status,
        ready=not warnings,
        warnings=warnings,
        files=[
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
    allow_issues: bool = False,
) -> Path:
    result = read_delivery_round(store, round_number)
    round_dir = store.project_dir / f"round_{result.round_number:03d}"
    files = iter_delivery_files(round_dir)
    preflight = build_delivery_preflight_report(store, round_number=result.round_number)
    warnings = preflight.warnings
    if warnings and not allow_issues:
        raise DeliveryValidationError(warnings)
    manifest = build_delivery_manifest(
        result,
        round_dir=round_dir,
        files=files,
        warnings=warnings,
    )
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
