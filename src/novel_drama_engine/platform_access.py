from __future__ import annotations

import hashlib
import json
import secrets
import uuid
from datetime import UTC, datetime
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any

from pydantic import BaseModel, Field


class PlatformAccessError(RuntimeError):
    pass


class PlatformKeyNotFoundError(PlatformAccessError):
    pass


class PlatformKeyUnauthorizedError(PlatformAccessError):
    pass


class PlatformQuotaExceededError(PlatformAccessError):
    pass


class PlatformApiKeyRecord(BaseModel):
    key_id: str
    name: str
    key_prefix: str
    key_hash: str
    scopes: list[str] = Field(default_factory=list)
    monthly_quota: int | None = Field(default=None, ge=1)
    usage: dict[str, int] = Field(default_factory=dict)
    created_at: str
    last_used_at: str | None = None
    revoked_at: str | None = None


class PlatformAccessRegistry(BaseModel):
    keys: list[PlatformApiKeyRecord] = Field(default_factory=list)


def utc_now() -> str:
    return datetime.now(UTC).isoformat()


def current_month() -> str:
    return datetime.now(UTC).strftime("%Y-%m")


def hash_api_key(api_key: str) -> str:
    return hashlib.sha256(api_key.encode("utf-8")).hexdigest()


def make_api_key(key_id: str) -> str:
    return f"ndk_{key_id}_{secrets.token_urlsafe(24)}"


def parse_key_id(api_key: str) -> str:
    parts = api_key.split("_", 2)
    if len(parts) != 3 or parts[0] != "ndk" or not parts[1]:
        raise PlatformKeyUnauthorizedError("Invalid API key format")
    return parts[1]


def normalize_scopes(scopes: str | list[str] | tuple[str, ...] | None) -> list[str]:
    if scopes is None:
        values = ["project:read"]
    elif isinstance(scopes, str):
        values = scopes.split(",")
    else:
        values = list(scopes)
    normalized = sorted({value.strip() for value in values if value.strip()})
    if not normalized:
        raise ValueError("At least one scope is required")
    return normalized


def platform_key_payload(record: PlatformApiKeyRecord) -> dict[str, Any]:
    month = current_month()
    return {
        "key_id": record.key_id,
        "name": record.name,
        "key_prefix": record.key_prefix,
        "scopes": record.scopes,
        "monthly_quota": record.monthly_quota,
        "usage_month": month,
        "usage_this_month": record.usage.get(month, 0),
        "created_at": record.created_at,
        "last_used_at": record.last_used_at,
        "revoked_at": record.revoked_at,
        "status": "revoked" if record.revoked_at else "active",
    }


def platform_keys_payload(
    store_path: Path | str,
    records: list[PlatformApiKeyRecord],
) -> dict[str, Any]:
    return {
        "store_path": str(Path(store_path)),
        "key_count": len(records),
        "keys": [platform_key_payload(record) for record in records],
    }


class PlatformAccessStore:
    def __init__(self, store_path: Path | str = ".drama_platform/api_keys.json") -> None:
        self.store_path = Path(store_path)

    def read_registry(self) -> PlatformAccessRegistry:
        if not self.store_path.is_file():
            return PlatformAccessRegistry()
        raw = json.loads(self.store_path.read_text(encoding="utf-8"))
        return PlatformAccessRegistry.model_validate(raw)

    def write_registry(self, registry: PlatformAccessRegistry) -> None:
        write_text_atomic(self.store_path, registry.model_dump_json(indent=2))

    def list_keys(self) -> list[PlatformApiKeyRecord]:
        return sorted(
            self.read_registry().keys,
            key=lambda record: record.created_at,
            reverse=True,
        )

    def create_key(
        self,
        *,
        name: str,
        scopes: str | list[str] | tuple[str, ...] | None = None,
        monthly_quota: int | None = None,
    ) -> tuple[PlatformApiKeyRecord, str]:
        if not name.strip():
            raise ValueError("API key name is required")
        key_id = uuid.uuid4().hex[:12]
        api_key = make_api_key(key_id)
        record = PlatformApiKeyRecord(
            key_id=key_id,
            name=name,
            key_prefix=api_key[:18],
            key_hash=hash_api_key(api_key),
            scopes=normalize_scopes(scopes),
            monthly_quota=monthly_quota,
            created_at=utc_now(),
        )
        registry = self.read_registry()
        registry.keys.append(record)
        self.write_registry(registry)
        return record, api_key

    def find_key(self, key_id: str) -> PlatformApiKeyRecord:
        for record in self.read_registry().keys:
            if record.key_id == key_id:
                return record
        raise PlatformKeyNotFoundError(f"API key not found: {key_id}")

    def revoke_key(self, key_id: str) -> PlatformApiKeyRecord:
        registry = self.read_registry()
        for index, record in enumerate(registry.keys):
            if record.key_id != key_id:
                continue
            if record.revoked_at is None:
                record.revoked_at = utc_now()
            registry.keys[index] = record
            self.write_registry(registry)
            return record
        raise PlatformKeyNotFoundError(f"API key not found: {key_id}")

    def check_key(
        self,
        api_key: str,
        *,
        scope: str | None = None,
        units: int = 1,
        consume: bool = False,
    ) -> PlatformApiKeyRecord:
        if units < 0:
            raise ValueError("units must be greater than or equal to 0")
        key_id = parse_key_id(api_key)
        registry = self.read_registry()
        for index, record in enumerate(registry.keys):
            if record.key_id != key_id:
                continue
            if not secrets.compare_digest(record.key_hash, hash_api_key(api_key)):
                raise PlatformKeyUnauthorizedError("Invalid API key")
            if record.revoked_at:
                raise PlatformKeyUnauthorizedError("API key is revoked")
            if scope and "*" not in record.scopes and scope not in record.scopes:
                raise PlatformKeyUnauthorizedError(f"Missing required scope: {scope}")
            month = current_month()
            used = record.usage.get(month, 0)
            if record.monthly_quota is not None and used + units > record.monthly_quota:
                raise PlatformQuotaExceededError("Monthly quota exceeded")
            if consume and units:
                record.usage[month] = used + units
                record.last_used_at = utc_now()
                registry.keys[index] = record
                self.write_registry(registry)
            return record
        raise PlatformKeyUnauthorizedError("Invalid API key")


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
