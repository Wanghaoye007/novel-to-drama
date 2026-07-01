import json

import pytest

from novel_drama_engine.platform_access import (
    PlatformAccessStore,
    PlatformKeyUnauthorizedError,
    PlatformQuotaExceededError,
    platform_key_payload,
)


def test_platform_access_store_creates_hashed_key(tmp_path):
    store = PlatformAccessStore(tmp_path / "api_keys.json")

    record, api_key = store.create_key(
        name="beta",
        scopes=["project:read", "delivery:export"],
        monthly_quota=2,
    )
    raw = json.loads((tmp_path / "api_keys.json").read_text(encoding="utf-8"))
    payload = platform_key_payload(record)

    assert api_key.startswith(f"ndk_{record.key_id}_")
    assert raw["keys"][0]["key_hash"] != api_key
    assert raw["keys"][0]["key_prefix"] == api_key[:18]
    assert payload["status"] == "active"
    assert payload["usage_this_month"] == 0
    assert "key_hash" not in payload


def test_platform_access_store_checks_scope_and_consumes_quota(tmp_path):
    store = PlatformAccessStore(tmp_path / "api_keys.json")
    _, api_key = store.create_key(
        name="beta",
        scopes=["project:read"],
        monthly_quota=2,
    )

    first = store.check_key(
        api_key,
        scope="project:read",
        units=1,
        consume=True,
    )
    second = store.check_key(
        api_key,
        scope="project:read",
        units=1,
        consume=True,
    )

    assert platform_key_payload(first)["usage_this_month"] == 1
    assert platform_key_payload(second)["usage_this_month"] == 2
    with pytest.raises(PlatformQuotaExceededError):
        store.check_key(api_key, scope="project:read", units=1, consume=True)
    with pytest.raises(PlatformKeyUnauthorizedError):
        store.check_key(api_key, scope="delivery:export")


def test_platform_access_store_revokes_key(tmp_path):
    store = PlatformAccessStore(tmp_path / "api_keys.json")
    record, api_key = store.create_key(name="beta", scopes=["*"])

    revoked = store.revoke_key(record.key_id)

    assert revoked.revoked_at
    with pytest.raises(PlatformKeyUnauthorizedError):
        store.check_key(api_key)
