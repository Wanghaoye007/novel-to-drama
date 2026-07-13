from __future__ import annotations

import re

from novel_drama_engine.models import EpisodeScript, QualityReport, SceneLine, ScriptBatch


SHOT_PREFIX_RE = re.compile(
    r"^△?\s*(?:EP\d{2,}\s+)?"
    r"(?:全景|中景|中近景|近景|特写|俯拍|仰拍|长焦)?"
    r"(?:推近|推移|拉远|拉紧|横移|跟拍|摇向|甩向|切到|扫过|快剪|拉焦|环绕|上移|下移|定格|定镜|慢镜头)?"
    r"[，,：:\s]*"
)

SHOT_SIZE_OPENERS = ("全景", "中景", "中近景", "近景", "特写", "俯拍", "仰拍", "长焦")
SHOT_MOTION_OPENERS = (
    "推近",
    "推移",
    "拉远",
    "拉紧",
    "横移",
    "跟拍",
    "摇向",
    "甩向",
    "切到",
    "扫过",
    "快剪",
    "拉焦",
    "环绕",
    "上移",
    "下移",
    "定格",
    "定镜",
    "慢镜头",
)
SHOT_LINK_OPENERS = ("反打", "切到", "切回", "快剪", "拉焦", "摇向", "扫过")


def normalize_shooting_action(text: str) -> str:
    stripped = text.strip()
    if not stripped:
        return stripped
    body = stripped[1:].lstrip() if stripped.startswith("△") else stripped
    prefix_match = re.match(r"^(EP\d{2,}\s+)(.+)$", body)
    episode_prefix = prefix_match.group(1) if prefix_match else ""
    body = prefix_match.group(2) if prefix_match else body

    for shot_size in SHOT_SIZE_OPENERS:
        if not body.startswith(shot_size):
            continue
        rest = body[len(shot_size) :]
        if rest.startswith(("，", ",")):
            return f"△{episode_prefix}{shot_size}定镜{rest}"
        if not rest or not any(rest.startswith(motion) for motion in SHOT_MOTION_OPENERS):
            return f"△{episode_prefix}{shot_size}定镜{rest}"
        return f"△{episode_prefix}{body}"

    for opener in SHOT_LINK_OPENERS:
        if body.startswith(opener):
            return f"△{episode_prefix}中近景{body}"

    return f"△{episode_prefix}中近景推近，{body}"


def strip_shooting_markup(text: str) -> str:
    stripped = text.strip()
    if not stripped:
        return stripped
    cleaned = SHOT_PREFIX_RE.sub("", stripped, count=1).strip()
    return cleaned or stripped.lstrip("△").strip()


def render_line(line: SceneLine) -> str:
    if line.kind == "action":
        return normalize_shooting_action(line.text)
    if line.kind == "dialogue":
        emotion = f"（{line.emotion}）" if line.emotion else ""
        speaker = line.speaker or "角色"
        return f"{speaker}{emotion}：{line.text}"
    if line.kind == "os":
        speaker = line.speaker or "角色"
        return f"{speaker}OS：{line.text}"
    if line.kind == "vo":
        speaker = line.speaker or "画外"
        return f"{speaker}VO：{line.text}"
    return line.text


def render_creative_line(line: SceneLine) -> str:
    if line.kind == "action":
        return f"▲ {strip_shooting_markup(line.text)}"
    return render_line(line)


def render_episode(script: EpisodeScript) -> str:
    return render_shooting_episode(script)


def render_shooting_episode(script: EpisodeScript) -> str:
    parts = [
        f"第{script.episode}集 {script.title}",
        "",
    ]
    for scene in script.scenes:
        parts.append(scene.heading)
        parts.append(f"人物：{'、'.join(scene.characters)}")
        parts.append("")
        parts.extend(render_line(line) for line in scene.lines)
        parts.append("")
    return "\n".join(parts).strip()


def render_creative_episode(script: EpisodeScript) -> str:
    parts = [
        f"# EPISODE {script.episode}",
        "",
        f"第{script.episode}集 {script.title}",
        "",
    ]
    for scene in script.scenes:
        parts.append(scene.heading)
        parts.append(f"人物：{'、'.join(scene.characters)}")
        parts.append("")
        parts.extend(render_creative_line(line) for line in scene.lines)
        parts.append("")
    return "\n".join(parts).strip()


def render_shooting_round(script_batch: ScriptBatch) -> str:
    return "\n\n".join(render_shooting_episode(episode) for episode in script_batch.episodes)


def render_creative_round(script_batch: ScriptBatch) -> str:
    return "\n\n".join(render_creative_episode(episode) for episode in script_batch.episodes)


def render_round_summary(script_batch: ScriptBatch, quality_report: QualityReport) -> str:
    scores = quality_report.scores
    return "\n".join(
        [
            f"质量结论：{quality_report.status.value}",
            f"Hook: {scores.hook}",
            f"Conflict: {scores.conflict}",
            f"Cliffhanger: {scores.cliffhanger}",
            f"Continuity: {scores.continuity}",
            f"Video Feasibility: {scores.video_feasibility}",
            "",
            *[render_episode(episode) for episode in script_batch.episodes],
        ]
    )
