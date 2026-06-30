from __future__ import annotations

from novel_drama_engine.models import (
    EpisodeScript,
    LocalizedScriptBatch,
    QualityReport,
    SceneLine,
    ScriptBatch,
)


def render_line(line: SceneLine) -> str:
    if line.kind == "action":
        return line.text
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


def render_episode(script: EpisodeScript) -> str:
    parts = [
        f"第{script.episode}集 {script.title}",
        "",
        f"3秒 Hook：{script.hook_3s}",
        f"主情绪：{script.main_emotion}",
        f"消费理由：{script.watch_reason}",
        "",
    ]
    for scene in script.scenes:
        parts.append(scene.heading)
        parts.append(f"人物：{'、'.join(scene.characters)}")
        parts.append("")
        parts.extend(render_line(line) for line in scene.lines)
        parts.append("")
    parts.append(f"结尾钩子：{script.cliffhanger}")
    return "\n".join(parts).strip()


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


def render_localized_line(line: SceneLine) -> str:
    if line.kind == "action":
        return line.text
    if line.kind == "dialogue":
        emotion = f" ({line.emotion})" if line.emotion else ""
        speaker = line.speaker or "Character"
        return f"{speaker}{emotion}: {line.text}"
    if line.kind == "os":
        speaker = line.speaker or "Character"
        return f"{speaker} OS: {line.text}"
    if line.kind == "vo":
        speaker = line.speaker or "VO"
        return f"{speaker} VO: {line.text}"
    return line.text


def render_localized_episode(script: EpisodeScript) -> str:
    parts = [
        f"Episode {script.episode}: {script.title}",
        "",
        f"3s Hook: {script.hook_3s}",
        f"Core Emotion: {script.main_emotion}",
        f"Watch Reason: {script.watch_reason}",
        "",
    ]
    for scene in script.scenes:
        parts.append(scene.heading)
        parts.append(f"Characters: {', '.join(scene.characters)}")
        parts.append("")
        parts.extend(render_localized_line(line) for line in scene.lines)
        parts.append("")
    parts.append(f"Cliffhanger: {script.cliffhanger}")
    return "\n".join(parts).strip()


def render_localization_result(localized: LocalizedScriptBatch) -> str:
    sections = [
        f"Locale: {localized.locale}",
        f"Platform: {localized.platform}",
        f"Title Strategy: {localized.title_strategy}",
        "",
        "Adaptation Notes:",
        *[f"- {note}" for note in localized.adaptation_notes],
        "",
        "Cultural Notes:",
        *[f"- {note}" for note in localized.cultural_notes],
        "",
        "Compliance Notes:",
        *[f"- {note}" for note in localized.compliance_notes],
        "",
        "Preserved Hooks:",
        *[f"- {hook}" for hook in localized.preserved_hooks],
        "",
        *[render_localized_episode(episode) for episode in localized.episodes],
    ]
    return "\n".join(sections).strip()
