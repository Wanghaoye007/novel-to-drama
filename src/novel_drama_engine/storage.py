from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel

from novel_drama_engine.models import NextRoundContext, RoundResult


class ProjectStore:
    def __init__(self, project_dir: Path | str) -> None:
        self.project_dir = Path(project_dir)

    def round_dir(self, round_number: int) -> Path:
        path = self.project_dir / f"round_{round_number:03d}"
        path.mkdir(parents=True, exist_ok=True)
        return path

    def write_round_artifact(self, round_number: int, name: str, model: BaseModel) -> Path:
        path = self.round_dir(round_number) / f"{name}.json"
        path.write_text(model.model_dump_json(indent=2), encoding="utf-8")
        return path

    def write_text_artifact(self, round_number: int, name: str, text: str) -> Path:
        path = self.round_dir(round_number) / name
        path.write_text(text, encoding="utf-8")
        return path

    def write_round_result(self, result: RoundResult) -> Path:
        return self.write_round_artifact(result.round_number, "round_result", result)

    def write_next_round_context(self, result: RoundResult) -> Path:
        path = self.round_dir(result.round_number) / "next_round_context.json"
        path.write_text(result.next_round_context.model_dump_json(indent=2), encoding="utf-8")
        return path

    def read_next_round_context(self, path: Path | str) -> NextRoundContext:
        raw = json.loads(Path(path).read_text(encoding="utf-8"))
        return NextRoundContext.model_validate(raw)
