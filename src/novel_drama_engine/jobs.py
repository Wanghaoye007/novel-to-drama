from __future__ import annotations

import uuid
from datetime import UTC, datetime
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any, Literal

from pydantic import BaseModel

JobStatus = Literal["queued", "running", "succeeded", "failed"]


class JobRecord(BaseModel):
    job_id: str
    kind: str
    status: JobStatus
    created_at: str
    updated_at: str
    request: dict[str, Any]
    result: dict[str, Any] | None = None
    error: str | None = None


class JobStore:
    def __init__(self, jobs_dir: str | Path) -> None:
        self.jobs_dir = Path(jobs_dir).expanduser().resolve()

    def job_path(self, job_id: str) -> Path:
        raw_job_id = Path(job_id)
        if raw_job_id.name != job_id or job_id in {"", ".", ".."}:
            raise ValueError("job_id must be a filename")
        return self.jobs_dir / f"{job_id}.json"

    def create(self, *, kind: str, request: dict[str, Any]) -> JobRecord:
        now = utc_now()
        record = JobRecord(
            job_id=uuid.uuid4().hex,
            kind=kind,
            status="queued",
            created_at=now,
            updated_at=now,
            request=request,
        )
        self.write(record)
        return record

    def read(self, job_id: str) -> JobRecord:
        path = self.job_path(job_id)
        if not path.is_file():
            raise FileNotFoundError("Job not found")
        return JobRecord.model_validate_json(path.read_text(encoding="utf-8"))

    def update(
        self,
        job_id: str,
        *,
        status: JobStatus,
        result: dict[str, Any] | None = None,
        error: str | None = None,
    ) -> JobRecord:
        record = self.read(job_id)
        record.status = status
        record.updated_at = utc_now()
        if result is not None:
            record.result = result
        if error is not None:
            record.error = error
        self.write(record)
        return record

    def write(self, record: JobRecord) -> Path:
        path = self.job_path(record.job_id)
        write_text_atomic(path, record.model_dump_json(indent=2))
        return path


def job_payload(store: JobStore, record: JobRecord) -> dict[str, Any]:
    payload = record.model_dump(mode="json")
    payload["jobs_dir"] = str(store.jobs_dir)
    payload["job_path"] = str(store.job_path(record.job_id))
    return payload


def utc_now() -> str:
    return datetime.now(UTC).isoformat()


def write_text_atomic(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = None
    try:
        with NamedTemporaryFile(
            "w",
            delete=False,
            dir=path.parent,
            encoding="utf-8",
            prefix=f".{path.name}.",
            suffix=".tmp",
        ) as temp_file:
            temp_file.write(text)
            temp_path = Path(temp_file.name)
        temp_path.replace(path)
    finally:
        if temp_path is not None and temp_path.exists():
            temp_path.unlink()
