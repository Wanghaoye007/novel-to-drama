from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass
from inspect import signature
from pathlib import Path

from novel_drama_engine.llm import JsonLLM
from novel_drama_engine.models import (
    BatchItemResult,
    BatchItemStatus,
    BatchManifest,
    BatchRunReport,
)
from novel_drama_engine.pipeline import RoundPipeline
from novel_drama_engine.renderer import render_round_summary
from novel_drama_engine.storage import ProjectStore


def resolve_manifest_path(path: Path, manifest_dir: Path) -> Path:
    if path.is_absolute():
        return path
    return manifest_dir / path


def read_batch_manifest(path: Path) -> BatchManifest:
    raw = json.loads(path.read_text(encoding="utf-8"))
    return BatchManifest.model_validate(raw)


@dataclass
class BatchRunner:
    projects_dir: Path
    llm_factory: Callable[..., JsonLLM]
    continue_on_error: bool = True

    def make_llm(
        self,
        *,
        round_number: int,
        previous_context,
        manifest_item,
        source_text: str,
        store: ProjectStore,
    ) -> JsonLLM:
        parameters = signature(self.llm_factory).parameters
        accepts_context = (
            any(param.kind == param.VAR_POSITIONAL for param in parameters.values())
            or len(parameters) >= 5
        )
        if accepts_context:
            return self.llm_factory(
                round_number,
                previous_context,
                manifest_item,
                source_text,
                store,
            )
        return self.llm_factory()

    def run(self, manifest_path: Path) -> BatchRunReport:
        manifest = read_batch_manifest(manifest_path)
        manifest_dir = manifest_path.parent
        items: list[BatchItemResult] = []

        for manifest_item in manifest.projects:
            project_dir = self.projects_dir / manifest_item.project_id
            store = ProjectStore(project_dir)
            try:
                source_path = resolve_manifest_path(manifest_item.input, manifest_dir)
                context_path = (
                    resolve_manifest_path(manifest_item.context, manifest_dir)
                    if manifest_item.context
                    else None
                )
                round_number, resolved_context_path = store.resolve_run_state(
                    context_path=context_path,
                    round_number=manifest_item.round_number,
                )
                previous_context = (
                    store.read_next_round_context(resolved_context_path)
                    if resolved_context_path
                    else None
                )
                source_text = source_path.read_text(encoding="utf-8")
                result = RoundPipeline(
                    llm=self.make_llm(
                        round_number=round_number,
                        previous_context=previous_context,
                        manifest_item=manifest_item,
                        source_text=source_text,
                        store=store,
                    ),
                    store=store,
                ).run(
                    project_id=manifest_item.project_id,
                    round_number=round_number,
                    source_text=source_text,
                    previous_context=previous_context,
                    target_episode_count=manifest_item.target_episode_count,
                    episodes_per_round=manifest_item.episodes_per_round,
                )
                rendered = render_round_summary(result.script_batch, result.quality_report)
                store.write_text_artifact(round_number, "rendered_scripts.md", rendered)
                items.append(
                    BatchItemResult(
                        project_id=manifest_item.project_id,
                        status=BatchItemStatus.COMPLETED,
                        project_dir=str(project_dir),
                        round_number=round_number,
                        target_episode_range=result.episode_context.target_episode_range,
                        quality_status=result.quality_report.status,
                    )
                )
            except Exception as exc:
                items.append(
                    BatchItemResult(
                        project_id=manifest_item.project_id,
                        status=BatchItemStatus.FAILED,
                        project_dir=str(project_dir),
                        error=str(exc),
                    )
                )
                if not self.continue_on_error:
                    break

        report = BatchRunReport(items=items)
        ProjectStore(self.projects_dir).write_batch_report(report)
        return report
