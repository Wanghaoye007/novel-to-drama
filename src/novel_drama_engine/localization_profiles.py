from __future__ import annotations

from pathlib import Path
from typing import Any

from novel_drama_engine.localization import read_localization_profile
from novel_drama_engine.models import LocalizationProfile


def list_localization_profiles(profiles_dir: Path | str) -> list[LocalizationProfile]:
    root = Path(profiles_dir)
    if not root.is_dir():
        raise FileNotFoundError(f"Localization profiles directory not found: {root}")

    profiles = [
        read_localization_profile(path)
        for path in sorted(root.glob("*.json"))
        if path.is_file()
    ]
    seen: set[str] = set()
    duplicates: set[str] = set()
    for profile in profiles:
        if profile.profile_id in seen:
            duplicates.add(profile.profile_id)
        seen.add(profile.profile_id)
    if duplicates:
        raise ValueError(
            "Duplicate localization profile_id: " + ", ".join(sorted(duplicates))
        )
    return sorted(profiles, key=lambda profile: profile.profile_id)


def get_localization_profile(
    profiles_dir: Path | str,
    profile_id: str,
) -> LocalizationProfile:
    for profile in list_localization_profiles(profiles_dir):
        if profile.profile_id == profile_id:
            return profile
    raise FileNotFoundError(f"Localization profile not found: {profile_id}")


def profile_summary(profile: LocalizationProfile) -> dict[str, Any]:
    return {
        "profile_id": profile.profile_id,
        "locale": profile.locale,
        "platform": profile.platform,
        "target_language": profile.target_language,
        "aspect_ratio": profile.aspect_ratio,
        "target_duration_seconds": profile.target_duration_seconds,
        "tone": profile.tone,
        "compliance_note_count": len(profile.compliance_notes),
        "production_note_count": len(profile.production_notes),
    }


def localization_profiles_payload(profiles_dir: Path | str) -> dict[str, Any]:
    profiles = list_localization_profiles(profiles_dir)
    return {
        "profiles_dir": str(Path(profiles_dir)),
        "profile_count": len(profiles),
        "profiles": [profile_summary(profile) for profile in profiles],
    }


def localization_profile_payload(
    profiles_dir: Path | str,
    profile_id: str,
) -> dict[str, Any]:
    profile = get_localization_profile(profiles_dir, profile_id)
    return {
        "profiles_dir": str(Path(profiles_dir)),
        "profile": profile.model_dump(mode="json"),
    }


def resolve_localization_profile(
    *,
    profile_path: Path | None,
    profile_id: str | None,
    profiles_dir: Path | str,
) -> LocalizationProfile:
    if bool(profile_path) == bool(profile_id):
        raise ValueError("Pass exactly one of --profile or --profile-id")
    if profile_path:
        return read_localization_profile(profile_path)
    if profile_id is None:
        raise ValueError("profile_id is required")
    return get_localization_profile(profiles_dir, profile_id)
