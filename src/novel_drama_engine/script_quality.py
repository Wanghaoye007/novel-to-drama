from __future__ import annotations

from dataclasses import dataclass

from novel_drama_engine.models import EpisodeScript, SceneLine
from novel_drama_engine.renderer import render_episode

MIN_EPISODE_CHARS = 800
MAX_EPISODE_CHARS = 1700
MIN_SCENES = 2
MAX_SCENES = 5
MIN_ACTION_LINES = 8
MIN_VOICED_LINES = 16
MIN_STRONG_LINES = 2

CAMERA_TOKENS = (
    "△",
    "特写",
    "镜头",
    "定格",
    "快剪",
    "切",
    "黑屏",
    "上移",
    "下半身",
    "手指",
    "眼神",
)

STRONG_TOKENS = (
    "！",
    "？",
    "滚",
    "死",
    "毒",
    "杀",
    "跪",
    "闭嘴",
    "放手",
    "马上",
    "立刻",
    "不配",
    "凭什么",
    "废物",
    "狗",
    "一起死",
)


@dataclass(frozen=True)
class EpisodeQualityMetrics:
    chars: int
    scenes: int
    action_lines: int
    voiced_lines: int
    os_lines: int
    camera_lines: int
    strong_lines: int
    opening_conflict_lines: int


def _line_text(line: SceneLine) -> str:
    if line.speaker:
        return f"{line.speaker} {line.emotion or ''} {line.text}"
    return line.text


def has_camera_language(text: str) -> bool:
    return any(token in text for token in CAMERA_TOKENS)


def has_strong_language(text: str) -> bool:
    return any(token in text for token in STRONG_TOKENS)


def episode_quality_metrics(episode: EpisodeScript) -> EpisodeQualityMetrics:
    lines = [line for scene in episode.scenes for line in scene.lines]
    action_lines = [line for line in lines if line.kind == "action"]
    voiced_lines = [line for line in lines if line.kind in {"dialogue", "os", "vo"}]
    os_lines = [line for line in lines if line.kind == "os"]
    camera_lines = [line for line in action_lines if has_camera_language(line.text)]
    strong_lines = [line for line in voiced_lines if has_strong_language(_line_text(line))]
    opening_lines = lines[:8]
    opening_conflict_lines = [
        line for line in opening_lines if has_strong_language(_line_text(line))
    ]

    return EpisodeQualityMetrics(
        chars=len(render_episode(episode)),
        scenes=len(episode.scenes),
        action_lines=len(action_lines),
        voiced_lines=len(voiced_lines),
        os_lines=len(os_lines),
        camera_lines=len(camera_lines),
        strong_lines=len(strong_lines),
        opening_conflict_lines=len(opening_conflict_lines),
    )


def episode_quality_warnings(episode: EpisodeScript) -> list[str]:
    metrics = episode_quality_metrics(episode)
    prefix = f"EP{episode.episode:02d}"
    warnings: list[str] = []

    if metrics.chars < MIN_EPISODE_CHARS:
        warnings.append(
            f"{prefix} too short: {metrics.chars} chars, expected >= {MIN_EPISODE_CHARS}"
        )
    if metrics.chars > MAX_EPISODE_CHARS:
        warnings.append(
            f"{prefix} too long: {metrics.chars} chars, expected <= {MAX_EPISODE_CHARS}"
        )
    if metrics.scenes < MIN_SCENES:
        warnings.append(f"{prefix} has {metrics.scenes} scenes, expected >= {MIN_SCENES}")
    if metrics.scenes > MAX_SCENES:
        warnings.append(f"{prefix} has {metrics.scenes} scenes, expected <= {MAX_SCENES}")
    if metrics.action_lines < MIN_ACTION_LINES:
        warnings.append(
            f"{prefix} has {metrics.action_lines} action lines, expected >= {MIN_ACTION_LINES}"
        )
    if metrics.voiced_lines < MIN_VOICED_LINES:
        warnings.append(
            f"{prefix} has {metrics.voiced_lines} voiced lines, expected >= {MIN_VOICED_LINES}"
        )
    if metrics.camera_lines < MIN_ACTION_LINES:
        warnings.append(
            f"{prefix} has weak camera direction density: {metrics.camera_lines}"
        )
    if metrics.strong_lines < MIN_STRONG_LINES:
        warnings.append(
            f"{prefix} lacks high-pressure dialogue: {metrics.strong_lines} strong lines"
        )
    if metrics.opening_conflict_lines < 1:
        warnings.append(f"{prefix} opening does not explode in the first 8 beats")

    for scene in episode.scenes:
        for index, line in enumerate(scene.lines[:-1]):
            if line.kind == "os" and scene.lines[index + 1].kind != "action":
                warnings.append(f"{prefix} OS at {scene.heading} is not followed by action")

    if not episode.cliffhanger.strip() or not has_strong_language(episode.cliffhanger):
        warnings.append(f"{prefix} cliffhanger is too soft")

    return warnings
