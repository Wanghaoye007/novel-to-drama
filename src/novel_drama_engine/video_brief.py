from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, Field

from novel_drama_engine.models import EpisodeScript, RoundResult, Scene, SceneLine
from novel_drama_engine.storage import ProjectStore


class VideoShotBrief(BaseModel):
    shot: int = Field(ge=1)
    source_scene: str
    characters: list[str]
    visual_prompt: str
    camera_notes: str
    audio_notes: str
    dialogue_beats: list[str]
    duration_seconds: int = Field(ge=1)


class VideoEpisodeBrief(BaseModel):
    episode: int = Field(ge=1)
    title: str
    aspect_ratio: str
    target_duration_seconds: int = Field(ge=1)
    hook: str
    cliffhanger: str
    shots: list[VideoShotBrief] = Field(min_length=1)
    asset_requirements: list[str]


class VideoBrief(BaseModel):
    project_id: str
    round_number: int = Field(ge=1)
    target_episode_range: str
    episodes: list[VideoEpisodeBrief] = Field(min_length=1)


def line_beat(line: SceneLine) -> str:
    if line.speaker:
        return f"{line.speaker}: {line.text}"
    return line.text


def scene_action_summary(scene: Scene) -> str:
    actions = [line.text for line in scene.lines if line.kind == "action"]
    if actions:
        return " ".join(actions[:2])
    return scene.heading


def build_shot_brief(
    *,
    episode: EpisodeScript,
    scene: Scene,
    shot: int,
    duration_seconds: int,
) -> VideoShotBrief:
    dialogue_beats = [
        line_beat(line)
        for line in scene.lines
        if line.kind in {"dialogue", "os", "vo"}
    ]
    visual_focus = scene_action_summary(scene)
    characters = scene.characters
    return VideoShotBrief(
        shot=shot,
        source_scene=scene.heading,
        characters=characters,
        visual_prompt=(
            f"{episode.title}; {scene.heading}; characters: {', '.join(characters)}; "
            f"emotion: {episode.main_emotion}; visual focus: {visual_focus}"
        ),
        camera_notes="Vertical close-up first, then medium reaction shot; keep faces readable.",
        audio_notes=f"Start with the hook line energy: {episode.hook_3s}",
        dialogue_beats=dialogue_beats[:6],
        duration_seconds=duration_seconds,
    )


def build_episode_brief(
    *,
    episode: EpisodeScript,
    aspect_ratio: str,
    duration_seconds: int,
    visual_moments: list[str],
) -> VideoEpisodeBrief:
    scenes = episode.scenes or [
        Scene(
            heading=f"EP{episode.episode:02d} generated scene",
            characters=[],
            lines=[],
        )
    ]
    scene_count = max(1, len(scenes))
    shot_duration = max(1, duration_seconds // scene_count)
    shots = [
        build_shot_brief(
            episode=episode,
            scene=scene,
            shot=index,
            duration_seconds=shot_duration,
        )
        for index, scene in enumerate(scenes, start=1)
    ]
    episode_characters = sorted(
        {character for scene in scenes for character in scene.characters}
    )
    return VideoEpisodeBrief(
        episode=episode.episode,
        title=episode.title,
        aspect_ratio=aspect_ratio,
        target_duration_seconds=duration_seconds,
        hook=episode.hook_3s,
        cliffhanger=episode.cliffhanger,
        shots=shots,
        asset_requirements=[
            *[f"Character look: {character}" for character in episode_characters],
            *[f"Scene asset: {scene.heading}" for scene in scenes],
            *[f"Key visual: {moment}" for moment in visual_moments[:3]],
        ],
    )


def build_video_brief(
    round_result: RoundResult,
    *,
    duration_seconds: int = 75,
    aspect_ratio: str = "9:16",
) -> VideoBrief:
    episodes = [
        build_episode_brief(
            episode=episode,
            aspect_ratio=aspect_ratio,
            duration_seconds=duration_seconds,
            visual_moments=round_result.source_analysis.visual_moments,
        )
        for episode in round_result.script_batch.episodes
    ]
    return VideoBrief(
        project_id=round_result.project_id,
        round_number=round_result.round_number,
        target_episode_range=round_result.episode_context.target_episode_range,
        episodes=episodes,
    )


def render_video_brief(brief: VideoBrief) -> str:
    parts = [
        "# Video Production Brief",
        "",
        f"Project: {brief.project_id}",
        f"Round: {brief.round_number}",
        f"Episode Range: {brief.target_episode_range}",
    ]
    for episode in brief.episodes:
        parts.extend(
            [
                "",
                f"## EP{episode.episode:02d} {episode.title}",
                "",
                f"Aspect Ratio: {episode.aspect_ratio}",
                f"Target Duration: {episode.target_duration_seconds}s",
                f"Hook: {episode.hook}",
                f"Cliffhanger: {episode.cliffhanger}",
                "",
                "Asset Requirements:",
                *[f"- {requirement}" for requirement in episode.asset_requirements],
            ]
        )
        for shot in episode.shots:
            parts.extend(
                [
                    "",
                    f"### Shot {shot.shot}: {shot.source_scene}",
                    "",
                    f"Duration: {shot.duration_seconds}s",
                    f"Characters: {', '.join(shot.characters)}",
                    f"Visual Prompt: {shot.visual_prompt}",
                    f"Camera: {shot.camera_notes}",
                    f"Audio: {shot.audio_notes}",
                    "Dialogue Beats:",
                    *[f"- {beat}" for beat in shot.dialogue_beats],
                ]
            )
    return "\n".join(parts).strip()


def export_project_video_brief(
    *,
    store: ProjectStore,
    round_number: int,
    duration_seconds: int = 75,
    aspect_ratio: str = "9:16",
) -> tuple[VideoBrief, Path, Path]:
    round_result = store.read_round_result(round_number)
    brief = build_video_brief(
        round_result,
        duration_seconds=duration_seconds,
        aspect_ratio=aspect_ratio,
    )
    json_path = store.write_round_artifact(round_number, "video_brief", brief)
    markdown_path = store.write_text_artifact(
        round_number,
        "video_brief.md",
        render_video_brief(brief),
    )
    return brief, json_path, markdown_path
