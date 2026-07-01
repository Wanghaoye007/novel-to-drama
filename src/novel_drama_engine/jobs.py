from __future__ import annotations

import uuid
from datetime import UTC, datetime
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any, Literal

from pydantic import BaseModel, Field

JobStatus = Literal["queued", "running", "succeeded", "failed"]
TERMINAL_JOB_STATUSES = {"succeeded", "failed"}


class JobRecord(BaseModel):
    job_id: str
    kind: str
    status: JobStatus
    created_at: str
    updated_at: str
    request: dict[str, Any]
    attempt: int = Field(default=1, ge=1)
    parent_job_id: str | None = None
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

    def create(
        self,
        *,
        kind: str,
        request: dict[str, Any],
        attempt: int = 1,
        parent_job_id: str | None = None,
    ) -> JobRecord:
        now = utc_now()
        record = JobRecord(
            job_id=uuid.uuid4().hex,
            kind=kind,
            status="queued",
            created_at=now,
            updated_at=now,
            request=request,
            attempt=attempt,
            parent_job_id=parent_job_id,
        )
        self.write(record)
        return record

    def create_retry(self, source: JobRecord) -> JobRecord:
        return self.create(
            kind=source.kind,
            request=source.request,
            attempt=source.attempt + 1,
            parent_job_id=source.job_id,
        )

    def read(self, job_id: str) -> JobRecord:
        path = self.job_path(job_id)
        if not path.is_file():
            raise FileNotFoundError("Job not found")
        return JobRecord.model_validate_json(path.read_text(encoding="utf-8"))

    def list(self) -> list[JobRecord]:
        if not self.jobs_dir.is_dir():
            return []
        records = []
        for path in sorted(self.jobs_dir.glob("*.json")):
            records.append(
                JobRecord.model_validate_json(path.read_text(encoding="utf-8"))
            )
        return sorted(records, key=lambda record: record.created_at, reverse=True)

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


def jobs_payload(store: JobStore) -> dict[str, Any]:
    jobs = [job_payload(store, record) for record in store.list()]
    return {
        "jobs_dir": str(store.jobs_dir),
        "job_count": len(jobs),
        "jobs": jobs,
    }


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
