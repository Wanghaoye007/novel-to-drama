from __future__ import annotations

import json
import re
from pathlib import Path

from novel_drama_engine.models import (
    LocalizationIssue,
    LocalizationPackage,
    LocalizationProfile,
    LocalizedEpisodePackage,
    LocalizedScene,
    RoundResult,
)
from novel_drama_engine.renderer import render_line


def read_localization_profile(path: Path) -> LocalizationProfile:
    raw = json.loads(path.read_text(encoding="utf-8"))
    return LocalizationProfile.model_validate(raw)


def apply_replacements(text: str, replacements: dict[str, str]) -> str:
    adapted = text
    for source, target in replacements.items():
        adapted = adapted.replace(source, target)
    adapted = re.sub(r"([\u4e00-\u9fff])([A-Za-z0-9])", r"\1 \2", adapted)
    adapted = re.sub(r"([A-Za-z0-9])([\u4e00-\u9fff])", r"\1 \2", adapted)
    adapted = re.sub(r"\s+([，。！？、：；])", r"\1", adapted)
    return adapted


def scan_forbidden_terms(
    *,
    text: str,
    location: str,
    forbidden_terms: list[str],
) -> list[LocalizationIssue]:
    return [
        LocalizationIssue(term=term, location=location, text=text)
        for term in forbidden_terms
        if term and term in text
    ]


def localize_title(title: str, profile: LocalizationProfile) -> str:
    adapted = apply_replacements(title, profile.replacements)
    if profile.title_prefix:
        return f"{profile.title_prefix} {adapted}"
    return adapted


def build_localization_package(
    result: RoundResult,
    profile: LocalizationProfile,
) -> LocalizationPackage:
    episodes: list[LocalizedEpisodePackage] = []
    issues: list[LocalizationIssue] = []

    for episode in result.script_batch.episodes:
        title = localize_title(episode.title, profile)
        hook_3s = apply_replacements(episode.hook_3s, profile.replacements)
        main_emotion = apply_replacements(episode.main_emotion, profile.replacements)
        watch_reason = apply_replacements(episode.watch_reason, profile.replacements)
        cliffhanger = apply_replacements(episode.cliffhanger, profile.replacements)
        scenes: list[LocalizedScene] = []

        issue_candidates = {
            f"EP{episode.episode:02d}.title": title,
            f"EP{episode.episode:02d}.hook_3s": hook_3s,
            f"EP{episode.episode:02d}.watch_reason": watch_reason,
            f"EP{episode.episode:02d}.cliffhanger": cliffhanger,
        }
        for location, text in issue_candidates.items():
            issues.extend(
                scan_forbidden_terms(
                    text=text,
                    location=location,
                    forbidden_terms=profile.forbidden_terms,
                )
            )

        for scene_index, scene in enumerate(episode.scenes, start=1):
            heading = apply_replacements(scene.heading, profile.replacements)
            characters = [
                apply_replacements(character, profile.replacements)
                for character in scene.characters
            ]
            adapted_lines = [
                apply_replacements(render_line(line), profile.replacements)
                for line in scene.lines
            ]
            scene_location = f"EP{episode.episode:02d}.scene_{scene_index:02d}"
            for line_index, line_text in enumerate(adapted_lines, start=1):
                issues.extend(
                    scan_forbidden_terms(
                        text=line_text,
                        location=f"{scene_location}.line_{line_index:02d}",
                        forbidden_terms=profile.forbidden_terms,
                    )
                )
            scenes.append(
                LocalizedScene(
                    heading=heading,
                    characters=characters,
                    adapted_lines=adapted_lines,
                )
            )

        episodes.append(
            LocalizedEpisodePackage(
                episode=episode.episode,
                title=title,
                hook_3s=hook_3s,
                main_emotion=main_emotion,
                watch_reason=watch_reason,
                cliffhanger=cliffhanger,
                scenes=scenes,
            )
        )

    return LocalizationPackage(
        project_id=result.project_id,
        round_number=result.round_number,
        target_episode_range=result.episode_context.target_episode_range,
        profile=profile,
        episodes=episodes,
        issues=issues,
    )


def render_localization_package_markdown(package: LocalizationPackage) -> str:
    profile = package.profile
    parts = [
        f"# Localization Package Round {package.round_number}",
        "",
        f"Project: {package.project_id}",
        f"Episode range: {package.target_episode_range}",
        f"Profile: {profile.profile_id}",
        f"Locale: {profile.locale}",
        f"Platform: {profile.platform}",
        f"Target language: {profile.target_language}",
        f"Aspect ratio: {profile.aspect_ratio}",
        f"Target duration: {profile.target_duration_seconds}s",
        f"Tone: {profile.tone}",
        "",
    ]
    if profile.compliance_notes:
        parts.extend(["## Compliance Notes", ""])
        parts.extend(f"- {note}" for note in profile.compliance_notes)
        parts.append("")
    if profile.production_notes:
        parts.extend(["## Production Notes", ""])
        parts.extend(f"- {note}" for note in profile.production_notes)
        parts.append("")

    parts.extend(["## Episodes", ""])
    for episode in package.episodes:
        parts.extend(
            [
                f"### EP{episode.episode:02d} {episode.title}",
                "",
                f"3s hook: {episode.hook_3s}",
                f"Main emotion: {episode.main_emotion}",
                f"Watch reason: {episode.watch_reason}",
                f"Cliffhanger: {episode.cliffhanger}",
                "",
            ]
        )
        for scene in episode.scenes:
            parts.extend(
                [
                    f"#### {scene.heading}",
                    "",
                    f"Characters: {'、'.join(scene.characters)}",
                    "",
                    *[f"- {line}" for line in scene.adapted_lines],
                    "",
                ]
            )

    if package.issues:
        parts.extend(["## Review Issues", ""])
        parts.extend(
            f"- {issue.term} at {issue.location}: {issue.text}"
            for issue in package.issues
        )
    else:
        parts.extend(["## Review Issues", "", "No forbidden terms found."])

    return "\n".join(parts).strip()
