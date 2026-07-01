from __future__ import annotations

from pathlib import Path

from novel_drama_engine.models import (
    RoundResult,
    Scene,
    VideoBrief,
    VideoEpisodeBrief,
    VideoShotBrief,
)
from novel_drama_engine.renderer import render_line
from novel_drama_engine.storage import ProjectStore

DEFAULT_PROFILE = "vertical_short_drama"
DEFAULT_ASPECT_RATIO = "9:16"
DEFAULT_CAMERA_NOTES = (
    "竖屏构图；人物中近景优先；情绪反应给特写；冲突动作使用快速切换。"
)
DEFAULT_AUDIO_NOTES = "保留对白清晰度；冲突点加短促音效；结尾钩子前留半拍停顿。"


def as_sentence(text: str) -> str:
    stripped = text.strip()
    if not stripped:
        return ""
    if stripped[-1] in "。！？.!?":
        return stripped
    return f"{stripped}。"


def scene_action_text(scene: Scene) -> str:
    actions = [
        line.text
        for line in scene.lines
        if line.kind in {"action", "transition"}
    ]
    if actions:
        return " ".join(actions)
    return " ".join(line.text for line in scene.lines[:2])


def scene_dialogue_beats(scene: Scene) -> list[str]:
    beats = [
        render_line(line)
        for line in scene.lines
        if line.kind in {"dialogue", "os", "vo"}
    ]
    if beats:
        return beats
    return [line.text for line in scene.lines[:2]]


def shot_duration(target_duration_seconds: int, scene_count: int) -> int:
    return max(6, target_duration_seconds // max(scene_count, 1))


def build_visual_prompt(
    *,
    scene: Scene,
    aspect_ratio: str,
    hook_3s: str,
    main_emotion: str,
    cliffhanger: str,
    is_first_scene: bool,
    is_last_scene: bool,
) -> str:
    parts = [
        as_sentence(f"竖屏短剧，{aspect_ratio}，{scene.heading}"),
        as_sentence(f"人物：{'、'.join(scene.characters)}"),
        as_sentence(f"主情绪：{main_emotion}"),
        as_sentence(f"画面动作：{scene_action_text(scene)}"),
    ]
    if is_first_scene:
        parts.append(as_sentence(f"前3秒必须打出钩子：{hook_3s}"))
    if is_last_scene:
        parts.append(as_sentence(f"结尾停在钩子：{cliffhanger}"))
    return "".join(parts)


def build_asset_requirements(result: RoundResult, scene: Scene) -> list[str]:
    requirements = [f"场景：{scene.heading}"]
    requirements.extend(f"角色：{character}" for character in scene.characters)
    requirements.extend(f"道具状态：{prop}" for prop in result.next_round_context.prop_states)
    return requirements


def episode_scenes(episode_number: int, scenes: list[Scene]) -> list[Scene]:
    if scenes:
        return scenes
    return [
        Scene(
            heading=f"EP{episode_number:02d} generated scene",
            characters=[],
            lines=[],
        )
    ]


def build_video_brief(
    result: RoundResult,
    *,
    duration_seconds: int | None = None,
    target_duration_seconds: int | None = None,
    aspect_ratio: str = DEFAULT_ASPECT_RATIO,
    profile: str = DEFAULT_PROFILE,
) -> VideoBrief:
    resolved_duration = (
        target_duration_seconds
        if target_duration_seconds is not None
        else duration_seconds
        if duration_seconds is not None
        else 90
    )
    episode_briefs: list[VideoEpisodeBrief] = []
    for episode in result.script_batch.episodes:
        scenes = episode_scenes(episode.episode, episode.scenes)
        duration = shot_duration(resolved_duration, len(scenes))
        shots: list[VideoShotBrief] = []
        for index, scene in enumerate(scenes, start=1):
            shots.append(
                VideoShotBrief(
                    shot_id=f"EP{episode.episode:02d}-S{index:02d}",
                    scene_heading=scene.heading,
                    duration_seconds=duration,
                    aspect_ratio=aspect_ratio,
                    characters=scene.characters,
                    visual_prompt=build_visual_prompt(
                        scene=scene,
                        aspect_ratio=aspect_ratio,
                        hook_3s=episode.hook_3s,
                        main_emotion=episode.main_emotion,
                        cliffhanger=episode.cliffhanger,
                        is_first_scene=index == 1,
                        is_last_scene=index == len(scenes),
                    ),
                    dialogue_beats=scene_dialogue_beats(scene),
                    camera_notes=DEFAULT_CAMERA_NOTES,
                    audio_notes=DEFAULT_AUDIO_NOTES,
                    asset_requirements=build_asset_requirements(result, scene),
                )
            )
        episode_briefs.append(
            VideoEpisodeBrief(
                episode=episode.episode,
                title=episode.title,
                aspect_ratio=aspect_ratio,
                target_duration_seconds=resolved_duration,
                hook_3s=episode.hook_3s,
                main_emotion=episode.main_emotion,
                cliffhanger=episode.cliffhanger,
                shots=shots,
            )
        )

    return VideoBrief(
        project_id=result.project_id,
        round_number=result.round_number,
        target_episode_range=result.episode_context.target_episode_range,
        profile=profile,
        episodes=episode_briefs,
    )


def render_video_brief_markdown(brief: VideoBrief) -> str:
    parts = [
        f"# Video Brief Round {brief.round_number}",
        "",
        f"Project: {brief.project_id}",
        f"Episode range: {brief.target_episode_range}",
        f"Profile: {brief.profile}",
        "",
    ]
    for episode in brief.episodes:
        parts.extend(
            [
                f"## EP{episode.episode:02d} {episode.title}",
                "",
                f"Aspect ratio: {episode.aspect_ratio}",
                f"Target duration: {episode.target_duration_seconds}s",
                f"3s hook: {episode.hook_3s}",
                f"Main emotion: {episode.main_emotion}",
                f"Cliffhanger: {episode.cliffhanger}",
                "",
            ]
        )
        for shot in episode.shots:
            parts.extend(
                [
                    f"### {shot.shot_id} {shot.scene_heading}",
                    "",
                    f"Duration: {shot.duration_seconds}s",
                    f"Characters: {'、'.join(shot.characters)}",
                    f"Visual prompt: {shot.visual_prompt}",
                    f"Camera: {shot.camera_notes}",
                    f"Audio: {shot.audio_notes}",
                    "Dialogue beats:",
                    *[f"- {beat}" for beat in shot.dialogue_beats],
                    "Asset requirements:",
                    *[f"- {requirement}" for requirement in shot.asset_requirements],
                    "",
                ]
            )
    return "\n".join(parts).strip()


def render_video_brief(brief: VideoBrief) -> str:
    return render_video_brief_markdown(brief)


def export_project_video_brief(
    *,
    store: ProjectStore,
    round_number: int,
    duration_seconds: int = 75,
    aspect_ratio: str = "9:16",
    profile: str = DEFAULT_PROFILE,
) -> tuple[VideoBrief, Path, Path]:
    round_result = store.read_round_result(round_number)
    brief = build_video_brief(
        round_result,
        duration_seconds=duration_seconds,
        aspect_ratio=aspect_ratio,
        profile=profile,
    )
    json_path = store.write_round_artifact(round_number, "video_brief", brief)
    markdown_path = store.write_text_artifact(
        round_number,
        "video_brief.md",
        render_video_brief_markdown(brief),
    )
    return brief, json_path, markdown_path
