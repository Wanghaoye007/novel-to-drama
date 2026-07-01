from __future__ import annotations

import json
import re
from pathlib import Path

from novel_drama_engine.llm import JsonLLM
from novel_drama_engine.models import (
    LocalizationIssue,
    LocalizationPackage,
    LocalizationProfile,
    LocalizationRewrite,
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


def collect_localization_issues(
    episodes: list[LocalizedEpisodePackage],
    profile: LocalizationProfile,
) -> list[LocalizationIssue]:
    issues: list[LocalizationIssue] = []
    for episode in episodes:
        issue_candidates = {
            f"EP{episode.episode:02d}.title": episode.title,
            f"EP{episode.episode:02d}.hook_3s": episode.hook_3s,
            f"EP{episode.episode:02d}.watch_reason": episode.watch_reason,
            f"EP{episode.episode:02d}.cliffhanger": episode.cliffhanger,
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
            scene_location = f"EP{episode.episode:02d}.scene_{scene_index:02d}"
            for line_index, line_text in enumerate(scene.adapted_lines, start=1):
                issues.extend(
                    scan_forbidden_terms(
                        text=line_text,
                        location=f"{scene_location}.line_{line_index:02d}",
                        forbidden_terms=profile.forbidden_terms,
                    )
                )
    return issues


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

    for episode in result.script_batch.episodes:
        title = localize_title(episode.title, profile)
        hook_3s = apply_replacements(episode.hook_3s, profile.replacements)
        main_emotion = apply_replacements(episode.main_emotion, profile.replacements)
        watch_reason = apply_replacements(episode.watch_reason, profile.replacements)
        cliffhanger = apply_replacements(episode.cliffhanger, profile.replacements)
        scenes: list[LocalizedScene] = []

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
        issues=collect_localization_issues(episodes, profile),
    )


LOCALIZATION_REWRITE_SYSTEM = (
    "You are a short-drama localization editor. Rewrite the provided localized "
    "package for the target locale and platform while preserving episode numbers, "
    "scene order, hooks, cliffhangers, and production intent."
)


def localization_rewrite_user(package: LocalizationPackage) -> str:
    return "\n\n".join(
        [
            "Rewrite the localization package episodes for the target profile.",
            "Do not add new scenes. Keep each scene's core action and conflict.",
            "Make lines natural for the target language and platform.",
            "Avoid forbidden terms from the profile.",
            package.model_dump_json(indent=2),
        ]
    )


def rewrite_localization_package_with_llm(
    package: LocalizationPackage,
    llm: JsonLLM,
) -> LocalizationPackage:
    rewrite = llm.complete(
        system=LOCALIZATION_REWRITE_SYSTEM,
        user=localization_rewrite_user(package),
        response_model=LocalizationRewrite,
    )
    return LocalizationPackage(
        project_id=package.project_id,
        round_number=package.round_number,
        target_episode_range=package.target_episode_range,
        profile=package.profile,
        episodes=rewrite.episodes,
        issues=collect_localization_issues(rewrite.episodes, package.profile),
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
