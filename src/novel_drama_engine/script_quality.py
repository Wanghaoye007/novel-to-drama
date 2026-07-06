from __future__ import annotations

from dataclasses import dataclass
import os
import re
from typing import Literal

from novel_drama_engine.models import (
    CrossEpisodeSimilarityIssue,
    CurrentEpisodeRepairPacket,
    EpisodeNoveltyProfile,
    EpisodeScript,
    QualityReport,
    QualityStatus,
    SceneLine,
    ScriptBatch,
    ScriptNoveltyReport,
)
from novel_drama_engine.renderer import render_episode

MIN_EPISODE_CHARS = 800
MAX_EPISODE_CHARS = 1700
MIN_SCENES = 2
MAX_SCENES = 5
MIN_TOTAL_SCENE_LINES = 28
MIN_ACTION_LINES = 10
MIN_VOICED_LINES = 18
MIN_SHOT_LANGUAGE_LINES = 8
MIN_STRONG_LINES = 2
MAX_VOICED_LINE_CHARS = 34
SUGGESTED_VOICED_LINE_CHARS = 22
NOVELTY_BLOCKING_SCORE = 0.72
NOVELTY_ADVISORY_SCORE = 0.62
NOVELTY_SCENE_SKELETON_BLOCKING_SCORE = 0.82
NOVELTY_ACTION_BLOCKING_SCORE = 0.76
NOVELTY_DIALOGUE_BLOCKING_SCORE = 0.78
NOVELTY_CLIFFHANGER_BLOCKING_SCORE = 0.78
SCENE_HEADING_RE = re.compile(r"^\d+-\d+\s+(日|夜)-+[内外]-+.+")
ABNORMAL_REPEATED_PHRASE_RE = re.compile(r"([\u4e00-\u9fff]{2,6})\1{2,}")
ABNORMAL_REPEATED_CHAR_RE = re.compile(r"([\u4e00-\u9fff])\1{3,}")
EPISODE_MARKER_RE = re.compile(r"(?:EP\s*\d+|第\s*\d+\s*集|\d+-\d+)", re.IGNORECASE)
SHOT_PREFIX_CLEAN_RE = re.compile(
    r"△?\s*(?:EP\d{2,}\s+)?(?:全景|中景|中近景|近景|特写|俯拍|仰拍|长焦)?"
    r"(?:推近|推移|拉远|拉紧|横移|跟拍|摇向|甩向|反打|切到|扫过|快剪|拉焦|环绕|上移|下移|定格|定镜|慢镜头)?"
)
CHINESE_TOKEN_RE = re.compile(r"[\u4e00-\u9fffA-Za-z0-9]+")
ACTION_OPENING_BANNED_RE = re.compile(
    r"^△\s*(女主|男主|他|她|门外|突然|众人|大家|甲|乙|丙|丁|温铮|温舟|林晚|林雪|武植|金莲)"
)

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

SHOT_SIZE_TOKENS = (
    "全景",
    "中景",
    "中近景",
    "近景",
    "特写",
    "俯拍",
    "仰拍",
    "长焦",
)

MOVEMENT_TOKENS = (
    "推近",
    "推移",
    "拉远",
    "拉紧",
    "横移",
    "跟拍",
    "摇向",
    "甩向",
    "反打",
    "切到",
    "扫过",
    "快剪",
    "拉焦",
    "环绕",
    "缓慢推向",
    "上移",
    "下移",
    "定格",
    "定镜",
    "慢镜头",
)

FRAMING_TOKENS = (
    "前景",
    "画面",
    "侧脸",
    "下半身",
    "额头",
    "指节",
    "反光",
    "占",
    "左上",
    "右上",
    "门外",
    "门内",
)

SHOT_LINK_TOKENS = (
    "切到",
    "切回",
    "反打",
    "接",
    "视线",
    "声音先入",
    "音效",
    "BGM",
    "道具",
    "前景",
    "J-cut",
)

EXPOSED_ANALYSIS_TOKENS = (
    "3秒 Hook",
    "三秒 Hook",
    "Hook",
    "hook",
    "Hook：",
    "Hook:",
    "hook：",
    "hook:",
    "主情绪",
    "消费理由",
    "main_emotion",
    "watch_reason",
    "hook_3s",
    "观看理由",
    "看点分析",
    "观众要看",
    "观众想看",
    "本集看点",
    "本集钩子",
)

ABSTRACT_ACTION_TOKENS = (
    "众人震惊",
    "众人哗然",
    "气氛凝固",
    "场面混乱",
    "开始争吵",
    "很害怕",
    "很紧张",
    "很震惊",
    "很生气",
    "若有所思",
    "眼神复杂",
    "陷入沉思",
    "空气安静",
    "意识到",
    "决定反击",
    "情绪爆发",
)

EXPLANATORY_SUMMARY_TOKENS = (
    "这说明",
    "这就是",
    "这才是",
    "道理",
    "价值观",
    "价值",
    "意义",
    "人生",
    "命运",
    "尊严",
    "真正的",
    "我终于明白",
    "我们应该",
    "你要明白",
    "因为",
    "所以",
)

EXPLANATORY_CLIFFHANGER_TOKENS = (
    "悬念",
    "留下",
    "关于",
    "关系",
    "感到",
    "准备",
    "面对",
    "气氛",
    "达到顶点",
    "似乎",
    "决定",
    "背叛",
    "真实身份",
    "未解",
    "引出",
    "继续",
    "后续",
)

SONG_WORLD_TOKENS = (
    "武植",
    "武大郎",
    "大郎",
    "金莲",
    "潘金莲",
    "西门庆",
    "大宋",
    "清河",
    "武家",
)

URBAN_IDENTITY_TEMPLATE_TOKENS = (
    "真假千金",
    "真千金",
    "假千金",
    "豪门",
    "宴会厅",
    "生日宴",
    "林家",
    "大小姐",
    "顾承",
    "顾少",
    "总裁",
    "亲子鉴定",
    "鉴定编号",
    "董事长",
    "继承权",
)

ENDING_HOOK_PROP_TOKENS = (
    "特写",
    "道具",
    "手机",
    "药碗",
    "木盒",
    "钥匙",
    "玉佩",
    "录音",
    "屏幕",
    "门",
    "剪刀",
    "血",
    "信",
    "鉴定",
    "帘子",
    "刀",
    "碗",
    "锅",
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
    "游戏才刚刚开始",
    "这只是开始",
    "废物",
    "狗",
    "一起死",
)

HOOK_DIALOGUE_POLISH_WARNING_TOKENS = (
    "too short",
    "voiced lines",
    "verbose voiced lines",
    "shot-to-shot linkage",
    "OS at",
    "cliffhanger is not performed",
    "cliffhanger is too soft",
    "cliffhanger field",
    "explanatory/value-summary",
)

EpisodeRepairMode = Literal[
    "format_patch",
    "ending_hook_patch",
    "creative_episode_repair",
    "full_episode_rewrite",
]

FORMAT_ONLY_WARNING_TOKENS = (
    "action lines violating",
    "abstract action lines",
    "exposes hook/watch_reason",
    "explanatory/value-summary",
    "invalid scene heading",
    "genre template mismatch",
    "abnormal repeated",
)

ENDING_ONLY_WARNING_TOKENS = (
    "cliffhanger",
    "OS at",
    "shot-to-shot linkage",
    "verbose voiced lines",
)

CREATIVE_REPAIR_TOKENS = (
    "ooc",
    "source",
    "fidelity",
    "原文",
    "人设",
    "动机",
    "主动方",
    "因果",
    "证据来源",
    "关键决定",
    "情绪递进",
    "改编一致性",
    "跨集新鲜度",
    "重复",
)


def strict_shooting_quality_enabled() -> bool:
    raw = os.environ.get("NOVEL_DRAMA_STRICT_SHOOTING_QUALITY", "0")
    return raw.strip().lower() in {"1", "true", "yes", "on", "strict", "shooting"}


@dataclass(frozen=True)
class EpisodeQualityMetrics:
    chars: int
    scenes: int
    total_scene_lines: int
    action_lines: int
    voiced_lines: int
    os_lines: int
    camera_lines: int
    shot_language_lines: int
    linked_shot_lines: int
    formatted_action_lines: int
    strong_lines: int
    long_voiced_lines: int
    opening_conflict_lines: int
    invalid_scene_headings: int
    invalid_action_format_lines: int
    exposed_analysis_lines: int
    abstract_action_lines: int
    explanatory_voiced_lines: int
    abnormal_repetition_lines: int


def _line_text(line: SceneLine) -> str:
    if line.speaker:
        return f"{line.speaker} {line.emotion or ''} {line.text}"
    return line.text


def has_camera_language(text: str) -> bool:
    return any(token in text for token in CAMERA_TOKENS)


def has_strong_language(text: str) -> bool:
    return any(token in text for token in STRONG_TOKENS)


def has_executable_shot_language(text: str) -> bool:
    has_shot_size = any(token in text for token in SHOT_SIZE_TOKENS)
    has_motion_or_framing = any(token in text for token in MOVEMENT_TOKENS) or any(
        token in text for token in FRAMING_TOKENS
    )
    return has_shot_size and (has_motion_or_framing or len(text) >= 18)


def has_shot_linkage(text: str) -> bool:
    return any(token in text for token in SHOT_LINK_TOKENS)


def has_action_line_template(text: str) -> bool:
    stripped = text.strip()
    if not stripped.startswith("△"):
        return False
    body = stripped[1:].lstrip()
    body = re.sub(r"^EP\d{2,}\s+", "", body)
    if ACTION_OPENING_BANNED_RE.match("△" + body):
        return False
    starts_with_shot_size = any(body.startswith(token) for token in SHOT_SIZE_TOKENS)
    has_motion = any(token in body for token in MOVEMENT_TOKENS)
    return starts_with_shot_size and has_motion


def has_exposed_analysis(text: str) -> bool:
    return any(token in text for token in EXPOSED_ANALYSIS_TOKENS)


def has_abstract_action(text: str) -> bool:
    return any(token in text for token in ABSTRACT_ACTION_TOKENS)


def has_explanatory_or_value_summary(text: str) -> bool:
    if len(text) <= SUGGESTED_VOICED_LINE_CHARS:
        return False
    return any(token in text for token in EXPLANATORY_SUMMARY_TOKENS)


def has_explanatory_cliffhanger(text: str) -> bool:
    if len(text.strip()) <= SUGGESTED_VOICED_LINE_CHARS and has_strong_language(text):
        return False
    return any(token in text for token in EXPLANATORY_CLIFFHANGER_TOKENS)


def has_cliffhanger_force(text: str) -> bool:
    return (
        has_strong_language(text)
        or has_executable_shot_language(text)
        or any(token in text for token in ENDING_HOOK_PROP_TOKENS)
    )


def has_template_mismatch(text: str) -> bool:
    return any(token in text for token in SONG_WORLD_TOKENS) and any(
        token in text for token in URBAN_IDENTITY_TEMPLATE_TOKENS
    )


def has_abnormal_repetition(text: str) -> bool:
    normalized = re.sub(r"\s+", "", text)
    return bool(
        ABNORMAL_REPEATED_PHRASE_RE.search(normalized)
        or ABNORMAL_REPEATED_CHAR_RE.search(normalized)
    )


def has_shooting_scene_heading(heading: str) -> bool:
    return bool(SCENE_HEADING_RE.match(heading.strip()))


def _episode_visible_text(episode: EpisodeScript) -> str:
    parts: list[str] = [episode.title]
    for scene in episode.scenes:
        parts.append(scene.heading)
        parts.extend(scene.characters)
        parts.extend(_line_text(line) for line in scene.lines)
    return "\n".join(parts)


def has_performed_ending_hook(episode: EpisodeScript) -> bool:
    if not episode.scenes or not episode.scenes[-1].lines:
        return False

    last_two = episode.scenes[-1].lines[-2:]
    if len(last_two) < 2:
        return False
    if any(has_exposed_analysis(_line_text(line)) for line in last_two):
        return False

    has_action_or_prop = any(
        line.kind == "action"
        and (
            has_executable_shot_language(line.text)
            or any(token in line.text for token in ENDING_HOOK_PROP_TOKENS)
        )
        for line in last_two
    )
    has_hook_dialogue = any(
        line.kind in {"dialogue", "os", "vo"} and has_strong_language(_line_text(line))
        for line in last_two
    )
    return has_action_or_prop or has_hook_dialogue


def final_scene_tail_text(episode: EpisodeScript, line_count: int = 4) -> str:
    if not episode.scenes:
        return ""
    lines = episode.scenes[-1].lines[-line_count:]
    return "\n".join(_line_text(line) for line in lines)


def cliffhanger_field_is_performed(episode: EpisodeScript) -> bool:
    cliffhanger = episode.cliffhanger.strip()
    if not cliffhanger:
        return False
    tail_text = final_scene_tail_text(episode)
    if not tail_text:
        return False
    return cliffhanger in tail_text or tail_text in cliffhanger


def episode_quality_metrics(episode: EpisodeScript) -> EpisodeQualityMetrics:
    lines = [line for scene in episode.scenes for line in scene.lines]
    action_lines = [line for line in lines if line.kind == "action"]
    voiced_lines = [line for line in lines if line.kind in {"dialogue", "os", "vo"}]
    os_lines = [line for line in lines if line.kind == "os"]
    camera_lines = [line for line in action_lines if has_camera_language(line.text)]
    shot_language_lines = [
        line for line in action_lines if has_executable_shot_language(line.text)
    ]
    linked_shot_lines = [line for line in action_lines if has_shot_linkage(line.text)]
    formatted_action_lines = [
        line for line in action_lines if has_action_line_template(line.text)
    ]
    strong_lines = [line for line in voiced_lines if has_strong_language(_line_text(line))]
    long_voiced_lines = [
        line for line in voiced_lines if len(line.text) > MAX_VOICED_LINE_CHARS
    ]
    opening_lines = lines[:8]
    opening_conflict_lines = [
        line for line in opening_lines if has_strong_language(_line_text(line))
    ]
    invalid_scene_headings = [
        scene.heading
        for scene in episode.scenes
        if not has_shooting_scene_heading(scene.heading)
    ]
    exposed_analysis_lines = [
        line for line in lines if has_exposed_analysis(_line_text(line))
    ]
    abstract_action_lines = [
        line for line in action_lines if has_abstract_action(line.text)
    ]
    explanatory_voiced_lines = [
        line for line in voiced_lines if has_explanatory_or_value_summary(line.text)
    ]
    abnormal_repetition_lines = [
        line for line in lines if has_abnormal_repetition(_line_text(line))
    ]

    return EpisodeQualityMetrics(
        chars=len(render_episode(episode)),
        scenes=len(episode.scenes),
        total_scene_lines=len(lines),
        action_lines=len(action_lines),
        voiced_lines=len(voiced_lines),
        os_lines=len(os_lines),
        camera_lines=len(camera_lines),
        shot_language_lines=len(shot_language_lines),
        linked_shot_lines=len(linked_shot_lines),
        formatted_action_lines=len(formatted_action_lines),
        strong_lines=len(strong_lines),
        long_voiced_lines=len(long_voiced_lines),
        opening_conflict_lines=len(opening_conflict_lines),
        invalid_scene_headings=len(invalid_scene_headings),
        invalid_action_format_lines=len(action_lines) - len(formatted_action_lines),
        exposed_analysis_lines=len(exposed_analysis_lines),
        abstract_action_lines=len(abstract_action_lines),
        explanatory_voiced_lines=len(explanatory_voiced_lines),
        abnormal_repetition_lines=len(abnormal_repetition_lines),
    )


def episode_quality_warnings(
    episode: EpisodeScript,
    *,
    strict_shooting: bool | None = None,
) -> list[str]:
    if strict_shooting is None:
        strict_shooting = strict_shooting_quality_enabled()
    metrics = episode_quality_metrics(episode)
    prefix = f"EP{episode.episode:02d}"
    warnings: list[str] = []
    underfilled_episode = metrics.chars < MIN_EPISODE_CHARS or metrics.scenes < MIN_SCENES

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
    if strict_shooting and metrics.total_scene_lines < MIN_TOTAL_SCENE_LINES:
        warnings.append(
            f"{prefix} has {metrics.total_scene_lines} visible scene lines, expected >= {MIN_TOTAL_SCENE_LINES}"
        )
    if metrics.invalid_scene_headings:
        invalid_headings = [
            scene.heading
            for scene in episode.scenes
            if not has_shooting_scene_heading(scene.heading)
        ][:3]
        warnings.append(
            f"{prefix} has non-shooting scene headings: {', '.join(invalid_headings)}; expected like 1-1 夜-内-具体地点"
        )
    if (strict_shooting or underfilled_episode) and metrics.action_lines < MIN_ACTION_LINES:
        warnings.append(
            f"{prefix} has {metrics.action_lines} action lines, expected >= {MIN_ACTION_LINES}"
        )
    if (strict_shooting or underfilled_episode) and metrics.voiced_lines < MIN_VOICED_LINES:
        warnings.append(
            f"{prefix} has {metrics.voiced_lines} voiced lines, expected >= {MIN_VOICED_LINES}"
        )
    if strict_shooting and metrics.camera_lines < MIN_ACTION_LINES:
        warnings.append(
            f"{prefix} has weak camera direction density: {metrics.camera_lines}"
        )
    if strict_shooting and metrics.shot_language_lines < MIN_SHOT_LANGUAGE_LINES:
        warnings.append(
            f"{prefix} lacks executable shot language: {metrics.shot_language_lines}, expected >= {MIN_SHOT_LANGUAGE_LINES}"
        )
    if (strict_shooting or underfilled_episode) and metrics.linked_shot_lines < 3:
        warnings.append(
            f"{prefix} lacks shot-to-shot linkage: {metrics.linked_shot_lines}, expected >= 3"
        )
    if strict_shooting and metrics.invalid_action_format_lines:
        warnings.append(
            f"{prefix} has {metrics.invalid_action_format_lines} action lines violating △景别+运镜 opening format"
        )
    if metrics.strong_lines < MIN_STRONG_LINES:
        warnings.append(
            f"{prefix} lacks high-pressure dialogue: {metrics.strong_lines} strong lines"
        )
    if metrics.long_voiced_lines:
        warnings.append(
            f"{prefix} has {metrics.long_voiced_lines} verbose voiced lines, expected <= {MAX_VOICED_LINE_CHARS} chars each"
        )
    if metrics.opening_conflict_lines < 1:
        warnings.append(f"{prefix} opening does not explode in the first 8 beats")
    if metrics.exposed_analysis_lines:
        warnings.append(
            f"{prefix} exposes hook/watch_reason analysis in user-visible script lines"
        )
    if metrics.abstract_action_lines:
        warnings.append(
            f"{prefix} has abstract action lines instead of executable shots: {metrics.abstract_action_lines}"
        )
    if metrics.explanatory_voiced_lines:
        warnings.append(
            f"{prefix} has explanatory/value-summary voiced lines: {metrics.explanatory_voiced_lines}"
        )
    if metrics.abnormal_repetition_lines:
        warnings.append(
            f"{prefix} has abnormal repeated words/phrases in visible lines: {metrics.abnormal_repetition_lines}"
        )
    if has_template_mismatch(_episode_visible_text(episode)):
        warnings.append(f"{prefix} has genre template mismatch in user-visible script lines")
    if not has_performed_ending_hook(episode):
        warnings.append(
            f"{prefix} cliffhanger is not performed in the final scene last 2 lines"
        )

    for scene in episode.scenes:
        for index, line in enumerate(scene.lines[:-1]):
            if line.kind == "os" and scene.lines[index + 1].kind != "action":
                warnings.append(f"{prefix} OS at {scene.heading} is not followed by action")

    if not episode.cliffhanger.strip() or not has_cliffhanger_force(episode.cliffhanger):
        warnings.append(f"{prefix} cliffhanger is too soft")
    if has_explanatory_cliffhanger(episode.cliffhanger):
        warnings.append(
            f"{prefix} cliffhanger field is explanatory; use the performed final hook line/action"
        )
    if not cliffhanger_field_is_performed(episode):
        warnings.append(
            f"{prefix} cliffhanger field is not present in the final scene tail"
        )

    return warnings


def episode_repair_mode(
    episode: EpisodeScript,
    base_instruction: str = "",
) -> EpisodeRepairMode:
    metrics = episode_quality_metrics(episode)
    warnings = episode_quality_warnings(episode, strict_shooting=True)
    warning_text = "\n".join([*warnings, base_instruction]).lower()
    structural_collapse = (
        metrics.chars < 500
        or metrics.scenes < 2
        or metrics.total_scene_lines < 12
        or metrics.action_lines < 4
        or metrics.voiced_lines < 6
    )
    if structural_collapse:
        return "full_episode_rewrite"

    if any(token in warning_text for token in CREATIVE_REPAIR_TOKENS):
        return "creative_episode_repair"

    if warnings and all(
        any(token in warning for token in FORMAT_ONLY_WARNING_TOKENS)
        for warning in warnings
    ):
        return "format_patch"

    if warnings and all(
        any(token in warning for token in ENDING_ONLY_WARNING_TOKENS)
        for warning in warnings
    ):
        return "ending_hook_patch"

    if any(token in base_instruction for token in ("结尾", "钩子", "断点", "cliffhanger")):
        return "ending_hook_patch"
    if any(token in base_instruction for token in ("格式", "action", "镜头格式", "场景标题")):
        return "format_patch"
    return "creative_episode_repair"


def build_current_episode_repair_packet(
    episode: EpisodeScript,
    base_instruction: str = "",
) -> CurrentEpisodeRepairPacket:
    mode = episode_repair_mode(episode, base_instruction)
    warnings = episode_quality_warnings(episode, strict_shooting=True)
    mode_scope = {
        "format_patch": (
            "只修不合格 action 行、场景标题或外露分析字段；其余场景、对白、人物关系、"
            "事件因果、原文资产和结尾钩子照抄当前集旧稿。"
        ),
        "ending_hook_patch": (
            "只修最后一场最后 8-12 行和必要短对白；前文场景、人物动机、证据来源、"
            "主动方和已演出的原文资产照抄当前集旧稿。"
        ),
        "creative_episode_repair": (
            "只修被质检点名的 OOC、原文偏离、情绪递进、冲突因果或跨集承接问题；"
            "已合格场次和 C1 名场面尽量照抄当前集旧稿。"
        ),
        "full_episode_rewrite": (
            "当前集结构崩坏或严重缺量，允许整集重写；仍必须以当前集已出现的人物、"
            "事件意图、原文锚点和上下集边界为基准。"
        ),
    }
    scene_headings = [scene.heading for scene in episode.scenes]
    characters = sorted({character for scene in episode.scenes for character in scene.characters})
    protected_elements = [
        f"title: {episode.title}",
        "scene_headings: " + " / ".join(scene_headings),
        "characters: " + "、".join(characters),
        f"hook_3s: {episode.hook_3s}",
        f"cliffhanger: {episode.cliffhanger}",
    ]
    if episode.state_update:
        protected_elements.append(
            "state_update_keys: " + "、".join(str(key) for key in episode.state_update)
        )
    editable_targets = warnings or [base_instruction.strip() or "未点名具体本地缺口"]
    return CurrentEpisodeRepairPacket(
        episode=episode.episode,
        repair_mode=mode,
        baseline_policy=(
            "当前集旧稿是唯一文本基准。修复只能在 baseline_episode_text 的基础上做最小必要改动；"
            "不得用 episode_plan、source packet 或全局质检意见覆盖当前集已成立的正片内容。"
        ),
        baseline_episode_text=render_episode(episode),
        allowed_change_scope=mode_scope[mode],
        editable_targets=editable_targets,
        protected_elements=protected_elements,
        continuity_requirements=[
            "保留当前集已演出的事实、人物关系、主动方、关键决定时机和证据来源。",
            "如果改动最后钩子导致 handoff 变化，只能向后一集追加承接修复，不能回头洗前文。",
            "不得跨集挪用其他 episode_source_packet 的事件、道具或真相揭示。",
        ],
        forbidden_changes=[
            "不得新增无原文依据的新剧情、新道具、新证据或新狠话",
            "不得把预谋改成冲动、把被动承受改成主动索取、把克制人物改成歇斯底里",
            "不得为了补格式或镜头密度增加水对白、空镜、泛场景或新支线",
        ],
    )


def episode_repair_instruction(
    episode: EpisodeScript,
    base_instruction: str = "",
) -> str:
    metrics = episode_quality_metrics(episode)
    warnings = episode_quality_warnings(episode, strict_shooting=True)
    mode = episode_repair_mode(episode, base_instruction)
    missing_chars = max(0, MIN_EPISODE_CHARS - metrics.chars)
    missing_actions = max(0, MIN_ACTION_LINES - metrics.action_lines)
    missing_voiced = max(0, MIN_VOICED_LINES - metrics.voiced_lines)
    missing_shots = max(0, MIN_SHOT_LANGUAGE_LINES - metrics.shot_language_lines)
    missing_links = max(0, 3 - metrics.linked_shot_lines)

    quality_snapshot = (
        "当前本地质检："
        f"{metrics.chars} 字、{metrics.scenes} 场、"
        f"{metrics.action_lines} 条 action、{metrics.voiced_lines} 条对白/OS/VO、"
        f"{metrics.shot_language_lines} 条可执行镜头、"
        f"{metrics.linked_shot_lines} 条镜头衔接。"
    )
    full_rewrite_parts = [
        "修复级别：结构崩坏整集重写。",
        f"第 {episode.episode} 集结构崩坏或严重缺量，允许整集重写；不要摘要复述 existing_episode。",
        quality_snapshot,
        (
            "本次重写硬目标：900-1500 字、优先 3 场、至少 10 条 action、"
            "至少 18 条 dialogue/os/vo、至少 28 条用户可见 scene line、"
            "至少 8 条 action 同时含景别+运镜、"
            "至少 3 条 action 含切到/切回/反打/声音先入/音效/BGM/道具特写/前景。"
        ),
        (
            "action 行硬格式：每条 action.text 必须以“△景别+运镜”开头，例如"
            "“△中近景推近女主侧脸，手机屏幕占前景，BGM骤停，切到温铮发白的指节”。"
            "禁止以“△女主/△温铮/△他/△她/△门外/△突然”直接开头。"
        ),
        (
            "必须补足缺口："
            f"至少增加 {missing_chars} 字、{missing_actions} 条 action、"
            f"{missing_voiced} 条对白/OS/VO、{missing_shots} 条可执行镜头、"
            f"{missing_links} 条镜头衔接。"
        ),
        (
            "结构要求：第一场前 8 个 beat 直接爆冲突；中段必须有一次假打脸或期待落空；"
            "最后一场倒数第 2 行必须是 action，且包含景别、运镜、道具/动作和衔接词；"
            "最后一行必须是强对白/强 OS/强 VO 或动作未完成的道具特写。"
        ),
        (
            "镜头写法禁止抽象：不要写“眼神复杂、气氛凝固、若有所思、转身离开”作为钩子；"
            "要写清镜头怎么拍、道具在哪里、角色手/脸/视线如何变化、声音如何切入下一拍。"
        ),
    ]

    focused_parts_by_mode: dict[EpisodeRepairMode, list[str]] = {
        "format_patch": [
            "修复级别：格式局部修复。",
            f"第 {episode.episode} 集只修不合格 action 行、场景标题或外露分析字段；不要整集重写。",
            quality_snapshot,
            (
                "允许改动范围：只改被本地质检点名的行，以及为保持语义连贯必须同步的极少量相邻行。"
                "标题、场景顺序、人物关系、事件因果、原文资产、结尾钩子和已合格对白必须保留。"
            ),
            (
                "格式目标：action 行以“△景别+运镜”开头，补齐构图/道具/表情/声音/切镜衔接；"
                "不要新增无原文依据的新道具、新证据、新狠话。"
            ),
        ],
        "ending_hook_patch": [
            "修复级别：结尾钩子局部修复。",
            f"第 {episode.episode} 集只修最后一场最后 8-12 行和必要短对白；不要整集重写。",
            quality_snapshot,
            f"当前尾部：{final_scene_tail_text(episode, line_count=8)!r}",
            (
                "允许改动范围：保留前文场景、人物动机、证据来源、主动方和已演出的原文资产；"
                "只把结尾停在身份将揭未揭、证据将爆未爆、威胁将落未落或强问题未回答的位置。"
            ),
            (
                "cliffhanger 字段必须直接填写最后 4 行里已经演出来的钩子台词或动作；"
                "禁止写说明句，禁止用转身离开、明天再说、黑屏、普通背影收束。"
            ),
        ],
        "creative_episode_repair": [
            "修复级别：单集创作修复。",
            f"第 {episode.episode} 集回到 source packet、Story Bible 和 existing_episode 做定向修复；不要整集洗稿。",
            quality_snapshot,
            (
                "允许改动范围：只修被点名的 OOC、原文偏离、情绪递进、冲突因果或跨集承接问题。"
                "已合格场次、已保留的 C1 名场面、人物关系和结尾边界必须尽量照抄。"
            ),
            (
                "如果原文本身已有强冲突和爆款属性，只做视听化增强和短台词压缩；"
                "不得为了更爽新增改变主动方、动机、关键决定时机或证据来源的剧情。"
            ),
        ],
        "full_episode_rewrite": full_rewrite_parts,
    }
    parts = focused_parts_by_mode[mode]
    if warnings:
        parts.append("本集本地阻断项：\n- " + "\n- ".join(warnings))
    if base_instruction.strip():
        parts.append("全局修复背景（仅供参考，必须优先执行本集修复级别）：\n" + base_instruction.strip())
    return "\n".join(part for part in parts if part)


def episode_needs_hook_dialogue_polish(episode: EpisodeScript) -> bool:
    warnings = episode_quality_warnings(episode)
    return any(
        any(token in warning for token in HOOK_DIALOGUE_POLISH_WARNING_TOKENS)
        for warning in warnings
    )


def hook_dialogue_polish_instruction(
    episode: EpisodeScript,
    base_instruction: str = "",
) -> str:
    metrics = episode_quality_metrics(episode)
    warnings = episode_quality_warnings(episode, strict_shooting=True)
    missing_chars = max(0, MIN_EPISODE_CHARS - metrics.chars)
    missing_voiced = max(0, MIN_VOICED_LINES - metrics.voiced_lines)
    missing_links = max(0, 3 - metrics.linked_shot_lines)

    parts = [
        (
            f"第 {episode.episode} 集进入结尾钩子/对白密度二次编译。"
            "这是 focused pass，不要整集重写，不要改掉已经合格的场次、人物关系和镜头动作。"
        ),
        (
            "只允许做三类改动："
            "1. 在最后一场或倒数第二场补短对白/OS/VO，使对白密度达标；"
            "2. 修复 OS 后缺少动作承接的问题；"
            "3. 重写最后一场最后 8-12 行，让结尾停在未回答的问题、身份将揭、证据将爆、威胁将落下或动作未完成。"
        ),
        (
            "当前本地质检："
            f"{metrics.chars} 字、{metrics.voiced_lines} 条对白/OS/VO、"
            f"{metrics.linked_shot_lines} 条镜头衔接、cliffhanger={episode.cliffhanger!r}。"
            f"最后尾部={final_scene_tail_text(episode)!r}。"
        ),
        (
            "本次 focused 目标："
            f"至少补 {missing_chars} 字、{missing_voiced} 条短对白/OS/VO、"
            f"{missing_links} 条镜头衔接；最后两行必须形成追更断点。"
        ),
        (
            "结尾禁止：转身离开、我需要时间、明天再说、画面冻结、普通背影、情绪总结、"
            "把秘密说完、把冲突解决完、让角色退场收束。"
        ),
        (
            "结尾必须：倒数第 2 行是 action，且以“△景别+运镜”开头，包含道具/动作和切到/切回/反打/"
            "声音先入/音效/BGM/道具特写/前景之一；最后 1 行是强对白/强 OS/强 VO，"
            "或一个动作未完成的道具特写。"
        ),
        (
            "cliffhanger 字段硬规则：必须直接填写最后 4 行里已经演出来的钩子台词或动作，"
            "例如“这东西，为什么在你手里？”；禁止写“留下悬念/关于真实身份的悬念/气氛紧张”等说明句。"
        ),
        (
            "推荐最后一句模板："
            "“你敢再说一遍？”、“她不是你能碰的人。”、“这东西，为什么在你手里？”、"
            "“你到底是谁？”、“别信她，她会害死你。”"
        ),
        (
            "输出仍必须是完整 EpisodeScript JSON，但除最后 8-12 行和必要短对白补足外，其余内容照抄 existing_episode。"
        ),
    ]
    if warnings:
        parts.append("本集剩余阻断项：\n- " + "\n- ".join(warnings))
    if base_instruction.strip():
        parts.append("全局修复背景（仅供参考，不得覆盖 focused 目标）：\n" + base_instruction.strip())
    return "\n".join(part for part in parts if part)


def _parse_target_episode_range(target_episode_range: str) -> tuple[int, int] | None:
    match = re.fullmatch(r"EP(\d{2,})-EP(\d{2,})", target_episode_range.strip())
    if not match:
        return None
    start_episode = int(match.group(1))
    end_episode = int(match.group(2))
    if end_episode < start_episode:
        return None
    return start_episode, end_episode


def _normalize_for_similarity(text: str) -> str:
    cleaned = SHOT_PREFIX_CLEAN_RE.sub("", text)
    cleaned = EPISODE_MARKER_RE.sub("", cleaned)
    cleaned = re.sub(r"\b\d+\b", "", cleaned)
    cleaned = re.sub(r"\s+", "", cleaned)
    return "".join(CHINESE_TOKEN_RE.findall(cleaned))


def _char_ngrams(text: str, n: int = 3) -> set[str]:
    normalized = _normalize_for_similarity(text)
    if len(normalized) <= n:
        return {normalized} if normalized else set()
    return {normalized[index : index + n] for index in range(len(normalized) - n + 1)}


def _jaccard_similarity(left: str, right: str, *, n: int = 3) -> float:
    left_tokens = _char_ngrams(left, n)
    right_tokens = _char_ngrams(right, n)
    if not left_tokens and not right_tokens:
        return 1.0
    if not left_tokens or not right_tokens:
        return 0.0
    return len(left_tokens & right_tokens) / len(left_tokens | right_tokens)


def _line_length_bucket(text: str) -> str:
    length = len(_normalize_for_similarity(text))
    if length <= 8:
        return "S"
    if length <= 18:
        return "M"
    if length <= 32:
        return "L"
    return "XL"


def _episode_action_text(episode: EpisodeScript) -> str:
    return "\n".join(
        line.text
        for scene in episode.scenes
        for line in scene.lines
        if line.kind == "action"
    )


def _episode_dialogue_pattern(episode: EpisodeScript) -> str:
    parts: list[str] = []
    for scene in episode.scenes:
        for line in scene.lines:
            if line.kind not in {"dialogue", "os", "vo"}:
                continue
            speaker = line.speaker or ""
            emotion = line.emotion or ""
            parts.append(
                f"{line.kind}:{speaker}:{emotion}:{_line_length_bucket(line.text)}:"
                f"{_normalize_for_similarity(line.text)[:12]}"
            )
    return "|".join(parts)


def _episode_scene_skeleton(episode: EpisodeScript) -> str:
    parts: list[str] = []
    for scene in episode.scenes:
        heading = EPISODE_MARKER_RE.sub("", scene.heading)
        heading = re.sub(r"\s+", "", heading)
        characters = ",".join(sorted(scene.characters))
        line_kinds = "".join(line.kind[0] for line in scene.lines)
        parts.append(f"{heading}:{characters}:{line_kinds}")
    return "|".join(parts)


def _episode_profile(episode: EpisodeScript) -> EpisodeNoveltyProfile:
    return EpisodeNoveltyProfile(
        episode=episode.episode,
        title=episode.title,
        scene_skeleton=_episode_scene_skeleton(episode),
        action_signature=_normalize_for_similarity(_episode_action_text(episode))[:240],
        dialogue_signature=_episode_dialogue_pattern(episode)[:240],
        cliffhanger_signature=_normalize_for_similarity(episode.cliffhanger),
    )


def _issue_text(issue: CrossEpisodeSimilarityIssue) -> str:
    left, right = issue.episodes
    label = {
        "overall": "整体剧情骨架",
        "scene_skeleton": "场景骨架",
        "action_chain": "动作/镜头链",
        "dialogue_pattern": "对白句式",
        "cliffhanger": "结尾钩子",
    }[issue.kind]
    return (
        f"EP{left:02d}/EP{right:02d} {label}重复度过高 "
        f"({issue.score:.2f})"
    )


def _similarity_issue(
    *,
    left: EpisodeScript,
    right: EpisodeScript,
    kind: Literal[
        "overall",
        "scene_skeleton",
        "action_chain",
        "dialogue_pattern",
        "cliffhanger",
    ],
    score: float,
    threshold: float,
    evidence: list[str],
    suggestion: str,
) -> CrossEpisodeSimilarityIssue | None:
    if score < NOVELTY_ADVISORY_SCORE:
        return None
    severity = "blocking" if score >= threshold else "advisory"
    return CrossEpisodeSimilarityIssue(
        episodes=(left.episode, right.episode),
        kind=kind,
        score=round(score, 3),
        severity=severity,
        evidence=evidence,
        suggestion=suggestion,
    )


def build_script_novelty_report(script_batch: ScriptBatch) -> ScriptNoveltyReport:
    episodes = sorted(script_batch.episodes, key=lambda item: item.episode)
    profiles = [_episode_profile(episode) for episode in episodes]
    issues: list[CrossEpisodeSimilarityIssue] = []

    for left_index, left in enumerate(episodes):
        for right in episodes[left_index + 1 :]:
            overall_score = _jaccard_similarity(render_episode(left), render_episode(right))
            scene_score = _jaccard_similarity(
                _episode_scene_skeleton(left),
                _episode_scene_skeleton(right),
                n=2,
            )
            action_score = _jaccard_similarity(
                _episode_action_text(left),
                _episode_action_text(right),
            )
            dialogue_score = _jaccard_similarity(
                _episode_dialogue_pattern(left),
                _episode_dialogue_pattern(right),
                n=2,
            )
            cliffhanger_score = _jaccard_similarity(left.cliffhanger, right.cliffhanger)
            maybe_issues = [
                _similarity_issue(
                    left=left,
                    right=right,
                    kind="overall",
                    score=overall_score,
                    threshold=NOVELTY_BLOCKING_SCORE,
                    evidence=[
                        f"EP{left.episode:02d}: {left.title}",
                        f"EP{right.episode:02d}: {right.title}",
                    ],
                    suggestion=(
                        "重写其中一集的核心事件推进：更换冲突场域、施压方、信息增量和结尾问题，"
                        "避免只替换标题/一句台词。"
                    ),
                ),
                _similarity_issue(
                    left=left,
                    right=right,
                    kind="scene_skeleton",
                    score=scene_score,
                    threshold=NOVELTY_SCENE_SKELETON_BLOCKING_SCORE,
                    evidence=[
                        _episode_scene_skeleton(left)[:140],
                        _episode_scene_skeleton(right)[:140],
                    ],
                    suggestion="调整场景顺序、地点、入场人物和每场戏的戏剧功能。",
                ),
                _similarity_issue(
                    left=left,
                    right=right,
                    kind="action_chain",
                    score=action_score,
                    threshold=NOVELTY_ACTION_BLOCKING_SCORE,
                    evidence=[
                        _episode_action_text(left).split("\n")[0][:120],
                        _episode_action_text(right).split("\n")[0][:120],
                    ],
                    suggestion="重写动作链和关键视觉道具，不要复用同一套镜头模板。",
                ),
                _similarity_issue(
                    left=left,
                    right=right,
                    kind="dialogue_pattern",
                    score=dialogue_score,
                    threshold=NOVELTY_DIALOGUE_BLOCKING_SCORE,
                    evidence=[
                        _episode_dialogue_pattern(left)[:140],
                        _episode_dialogue_pattern(right)[:140],
                    ],
                    suggestion="改变施压/反击对白结构，让角色本集诉求和信息增量发生变化。",
                ),
                _similarity_issue(
                    left=left,
                    right=right,
                    kind="cliffhanger",
                    score=cliffhanger_score,
                    threshold=NOVELTY_CLIFFHANGER_BLOCKING_SCORE,
                    evidence=[left.cliffhanger, right.cliffhanger],
                    suggestion="结尾钩子要换成新的未回答问题，避免同类证据/同类威胁连续重复。",
                ),
            ]
            issues.extend(issue for issue in maybe_issues if issue is not None)

    blocking_issues = [_issue_text(issue) for issue in issues if issue.severity == "blocking"]
    advisory_warnings = [_issue_text(issue) for issue in issues if issue.severity == "advisory"]
    if blocking_issues:
        score = max(0, 10 - len(blocking_issues) * 2 - len(advisory_warnings))
    elif advisory_warnings:
        score = max(6, 10 - len(advisory_warnings))
    else:
        score = 10

    rewrite_instruction = ""
    if blocking_issues or advisory_warnings:
        repair_targets = sorted(
            {
                episode
                for issue in issues
                for episode in issue.episodes
                if issue.severity == "blocking"
            }
        )
        target_text = (
            "、".join(f"EP{episode:02d}" for episode in repair_targets)
            if repair_targets
            else "相似度最高的集"
        )
        issue_lines = blocking_issues[:8] or advisory_warnings[:8]
        rewrite_instruction = (
            "跨集新鲜度不足，必须按集重写而不是局部替换台词。优先处理 "
            f"{target_text}。\n"
            "修复规则：每集必须有不同的冲突场域、施压动作、信息增量、视觉道具和结尾未回答问题；"
            "禁止复用同一套场景三段式、同一组人物进出场和同一句式反击。\n"
            "检测到的问题：\n- "
            + "\n- ".join(issue_lines)
        )

    return ScriptNoveltyReport(
        overall_score=score,
        episode_profiles=profiles,
        similarity_issues=issues,
        blocking_issues=blocking_issues,
        advisory_warnings=advisory_warnings,
        rewrite_instruction=rewrite_instruction,
    )


def merge_script_novelty_into_quality_report(
    quality_report: QualityReport,
    novelty_report: ScriptNoveltyReport,
) -> QualityReport:
    if not novelty_report.blocking_issues:
        return quality_report
    return quality_report.model_copy(
        update={
            "status": QualityStatus.NEEDS_REWRITE
            if quality_report.status == QualityStatus.USABLE
            else quality_report.status,
            "blocking_issues": [
                *quality_report.blocking_issues,
                *[
                    f"script_novelty: {issue}"
                    for issue in novelty_report.blocking_issues
                ],
            ],
            "rewrite_instruction": "\n\n".join(
                part
                for part in [
                    quality_report.rewrite_instruction,
                    novelty_report.rewrite_instruction,
                ]
                if part.strip()
            ),
        }
    )


def render_script_novelty_report(report: ScriptNoveltyReport) -> str:
    lines = [
        "# Script Novelty Report",
        "",
        f"- Overall score: {report.overall_score}/10",
        f"- Blocking issues: {len(report.blocking_issues)}",
        f"- Advisory warnings: {len(report.advisory_warnings)}",
        "",
        "## Episode Profiles",
        "",
    ]
    for profile in report.episode_profiles:
        lines.append(
            f"- EP{profile.episode:02d} {profile.title}: "
            f"{profile.scene_skeleton[:120]}"
        )
    if report.similarity_issues:
        lines.extend(
            [
                "",
                "## Similarity Issues",
                "",
                "| Episodes | Kind | Score | Severity | Suggestion |",
                "|---|---|---:|---|---|",
            ]
        )
        for issue in report.similarity_issues:
            lines.append(
                "| "
                + " | ".join(
                    [
                        f"EP{issue.episodes[0]:02d}/EP{issue.episodes[1]:02d}",
                        issue.kind,
                        f"{issue.score:.2f}",
                        issue.severity,
                        issue.suggestion.replace("|", "/"),
                    ]
                )
                + " |"
            )
    if report.rewrite_instruction:
        lines.extend(["", "## Rewrite Instruction", "", report.rewrite_instruction])
    lines.append("")
    return "\n".join(lines)


def script_batch_quality_warnings(
    script_batch: ScriptBatch,
    target_episode_range: str,
) -> list[str]:
    parsed_range = _parse_target_episode_range(target_episode_range)
    if parsed_range is None:
        return [
            f"target_episode_range is malformed: {target_episode_range}; expected EP01-EP05"
        ]

    start_episode, end_episode = parsed_range
    expected_episodes = list(range(start_episode, end_episode + 1))
    actual_episodes = [episode.episode for episode in script_batch.episodes]
    warnings: list[str] = []

    if actual_episodes != expected_episodes:
        expected_label = ",".join(f"EP{episode:02d}" for episode in expected_episodes)
        actual_label = ",".join(f"EP{episode:02d}" for episode in actual_episodes)
        warnings.append(
            f"script episodes mismatch target range {target_episode_range}: expected {expected_label}, got {actual_label}"
        )

    if len(actual_episodes) != len(set(actual_episodes)):
        warnings.append("script episodes contain duplicate episode numbers")

    return warnings
