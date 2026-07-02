from __future__ import annotations

from enum import StrEnum
from pathlib import Path
from typing import Any, Literal

import re

from pydantic import BaseModel, Field, field_validator, model_validator


class StoryStage(StrEnum):
    OPENING_PRESSURE = "opening_pressure"
    IDENTITY_HOOK = "identity_hook"
    FIRST_COUNTERATTACK = "first_counterattack"
    MISUNDERSTANDING_ESCALATION = "misunderstanding_escalation"
    MIDPOINT_REVERSAL = "midpoint_reversal"
    TRUTH_NEAR_REVEAL = "truth_near_reveal"
    PUBLIC_REVEAL = "public_reveal"
    FINAL_RECKONING = "final_reckoning"


class QualityStatus(StrEnum):
    USABLE = "usable"
    NEEDS_REWRITE = "needs_rewrite"
    CONTEXT_CONFLICT = "context_conflict"
    NEEDS_HUMAN_REVIEW = "needs_human_review"


class BatchItemStatus(StrEnum):
    COMPLETED = "completed"
    FAILED = "failed"


class GenerationVariant(StrEnum):
    CURRENT_DENSITY = "current_density"
    DRAMA_ENGINE_FIRST = "drama_engine_first"
    SOP_FULL_STACK = "sop_full_stack"


class SourceAnalysis(BaseModel):
    characters: list[str]
    events: list[str]
    conflicts: list[str]
    visual_moments: list[str]
    low_value_passages: list[str]
    candidate_hooks: list[str]


class EpisodeSourceMapping(BaseModel):
    source: str
    target_episode: str | int | None = None
    retained_assets: list[str] | str | None = None
    adaptation_reason: str | None = None
    information_increment: str | None = None
    adaptation_action: str | None = None


class EpisodeContext(BaseModel):
    target_episode_range: str
    story_stage: StoryStage
    source_to_episode_mapping: list[EpisodeSourceMapping]
    must_carry_context: list[str]
    forbidden_reveals: list[str]
    adaptation_actions: list[str]
    confidence: float = Field(ge=0.0, le=1.0)

    @field_validator("source_to_episode_mapping", mode="before")
    @classmethod
    def normalize_source_mapping(cls, value: object) -> object:
        if not isinstance(value, list):
            return value
        normalized: list[object] = []
        for item in value:
            if isinstance(item, str):
                normalized.append({"source": item})
            else:
                normalized.append(item)
        return normalized


class StoryBible(BaseModel):
    genre: str
    mainline: str
    characters: list[str]
    relationships: list[str]
    speech_styles: dict[str, str]
    immutable_facts: list[str]
    forbidden_changes: list[str]


class ViralAssetReport(BaseModel):
    channel: str
    genre_tags: list[str]
    core_setting: str
    core_dilemma: str
    protagonist_goal: str
    main_conflict: str
    signature_scenes: list[str] = Field(min_length=3)
    small_highlights: list[str] = Field(min_length=5)
    golden_lines: list[str]
    emotion_curve: list[str] = Field(min_length=3)
    adaptation_risks: list[str]
    risk_treatments: list[str]
    low_value_removal_rules: list[str]


class CharacterProfile(BaseModel):
    name: str
    base_identity: str
    memory_tag: str
    contrast: str
    core_desire: str
    obsession: str
    drama_function: str
    speech_style: str
    sample_lines: list[str] = Field(min_length=1)


class ConflictStack(BaseModel):
    surface_event_conflict: str
    emotional_conflict: str
    deep_value_conflict: str


class SeriesEpisodeOutline(BaseModel):
    episode: int = Field(ge=1)
    core_event: str
    emotion_node: str
    information_increment: str
    ending_hook_type: str
    ending_hook: str
    source_anchor: str
    climax_role: str = "未标注"


class SeriesStructurePlan(BaseModel):
    target_episode_count: int | None = Field(default=None, ge=1)
    target_episode_range: str
    structure_rationale: str
    opening_contract: list[str] = Field(min_length=3)
    small_climax_cadence: str
    big_climax_cadence: str
    character_profiles: list[CharacterProfile]
    conflict_stack: ConflictStack
    global_emotion_curve: list[str] = Field(min_length=3)
    episode_outlines: list[SeriesEpisodeOutline] = Field(min_length=1)
    adaptation_rules: list[str]
    forbidden_slowdowns: list[str]


class EpisodeDramaPlan(BaseModel):
    episode: int = Field(ge=1)
    title: str
    drama_engine: str
    protagonist_misbelief: str
    truth_gap: str
    physical_action_chain: list[str] = Field(min_length=3)
    scene_dynamics: list[str] = Field(min_length=2)
    emotional_turns: list[str] = Field(min_length=2)
    audience_information_gap: str
    three_pull_beats: list[str] = Field(min_length=3)
    false_payoff: str
    planted_key: str
    strongest_line: str
    cliffhanger_design: str
    source_assets_to_keep: list[str]
    forbidden_shortcuts: list[str]


class EpisodePlan(BaseModel):
    variant: GenerationVariant
    target_episode_range: str
    adaptation_strategy: str
    episodes: list[EpisodeDramaPlan] = Field(min_length=1, max_length=5)


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


def _episode_action_prefix(body: str) -> tuple[str, str]:
    match = re.match(r"^(EP\d{2,}\s+)(.+)$", body)
    if not match:
        return "", body
    return match.group(1), match.group(2)


def _normalize_action_text(text: str) -> str:
    stripped = text.strip()
    if not stripped:
        return stripped
    if not stripped.startswith("△"):
        stripped = f"△中近景推近，{stripped}"

    body = stripped[1:].lstrip()
    ep_prefix, body = _episode_action_prefix(body)

    for shot_size in SHOT_SIZE_OPENERS:
        if not body.startswith(shot_size):
            continue
        rest = body[len(shot_size) :]
        if rest.startswith(("，", ",")):
            return f"△{ep_prefix}{shot_size}定镜{rest}"
        if not rest or not any(rest.startswith(motion) for motion in SHOT_MOTION_OPENERS):
            return f"△{ep_prefix}{shot_size}定镜{rest}"
        return f"△{ep_prefix}{body}"

    for opener in SHOT_LINK_OPENERS:
        if body.startswith(opener):
            return f"△{ep_prefix}中近景{body}"

    return f"△{ep_prefix}中近景推近，{body}"


def _speaker_aliases(speaker: str | None) -> list[str]:
    if not speaker:
        return []
    aliases = [speaker.strip()]
    parts = [part for part in re.split(r"\s+", speaker.strip()) if part]
    if parts:
        aliases.append(parts[0])
    return sorted(set(aliases), key=len, reverse=True)


def _strip_voiced_prefix(
    text: str,
    *,
    speaker: str | None,
    kind: str,
    emotion: str | None,
) -> tuple[str, str | None]:
    stripped = text.strip()
    next_emotion = emotion
    kind_marker = "OS|VO" if kind == "dialogue" else kind.upper()

    for alias in _speaker_aliases(speaker):
        pattern = re.compile(
            rf"^\s*{re.escape(alias)}\s*(?:{kind_marker})?\s*"
            rf"(?:[（(](?P<emotion>[^）)]{{1,24}})[）)])?\s*[：:]\s*(?P<body>.+)$",
            re.IGNORECASE,
        )
        match = pattern.match(stripped)
        if match:
            captured_emotion = (match.group("emotion") or "").strip()
            if captured_emotion and not next_emotion:
                next_emotion = captured_emotion
            return match.group("body").strip(), next_emotion

    return stripped, next_emotion


def _strip_parenthetical_speaker_marker(
    text: str,
    *,
    speaker: str | None,
    kind: str,
    emotion: str | None,
) -> tuple[str, str | None]:
    stripped = text.strip()
    next_emotion = emotion
    marker_pattern = "|".join(re.escape(alias) for alias in _speaker_aliases(speaker))
    if marker_pattern:
        stripped = re.sub(
            rf"^\s*[（(]\s*(?:{marker_pattern})\s*(?:{kind.upper()})?\s*[）)]\s*",
            "",
            stripped,
            flags=re.IGNORECASE,
        ).strip()

    match = re.match(r"^\s*[（(](?P<emotion>[^）)]{1,12})[）)]\s*(?P<body>.+)$", stripped)
    if match and not next_emotion:
        next_emotion = match.group("emotion").strip()
        stripped = match.group("body").strip()

    return stripped, next_emotion


def _normalize_voiced_text(
    text: str,
    *,
    speaker: str | None,
    kind: str,
    emotion: str | None,
) -> tuple[str, str | None]:
    stripped, next_emotion = _strip_voiced_prefix(
        text,
        speaker=speaker,
        kind=kind,
        emotion=emotion,
    )
    stripped, next_emotion = _strip_parenthetical_speaker_marker(
        stripped,
        speaker=speaker,
        kind=kind,
        emotion=next_emotion,
    )
    return stripped, next_emotion


CLIFFHANGER_EXPLANATORY_TOKENS = (
    "悬念",
    "留下",
    "关于",
    "关系",
    "气氛",
    "达到顶点",
    "后续",
    "继续",
)
CLIFFHANGER_STRONG_TOKENS = (
    "！",
    "？",
    "滚",
    "死",
    "杀",
    "跪",
    "闭嘴",
    "放手",
    "不配",
    "凭什么",
    "游戏才刚刚开始",
    "这只是开始",
)
CLIFFHANGER_PROP_TOKENS = (
    "手机",
    "屏幕",
    "录音",
    "消息",
    "钥匙",
    "鉴定",
    "心脏",
    "血",
    "门",
    "刀",
)


class SceneLine(BaseModel):
    kind: Literal["action", "dialogue", "os", "vo", "transition"] = Field(
        description=(
            "action 是可拍摄镜头指令，必须写景别、运镜、构图、道具、表情、声音或衔接；"
            "dialogue/os/vo 是短台词，不能承载分析说明。"
        ),
    )
    text: str = Field(
        description=(
            "用户可见正片文本。action 以 △ 开头；对白/OS/VO 单句尽量短，"
            "不得出现 Hook、主情绪、消费理由、观众要看、本集看点等分析字段。"
        ),
    )
    speaker: str | None = Field(default=None, description="对白/OS/VO 的角色名；action 可为空。")
    emotion: str | None = Field(default=None, description="短情绪提示，例如 冷、怒、压低声音。")

    @model_validator(mode="after")
    def normalize_user_visible_text(self) -> "SceneLine":
        if self.kind == "action":
            self.text = _normalize_action_text(self.text)
        elif self.kind in {"dialogue", "os", "vo"}:
            self.text, self.emotion = _normalize_voiced_text(
                self.text,
                speaker=self.speaker,
                kind=self.kind,
                emotion=self.emotion,
            )
        return self


class Scene(BaseModel):
    heading: str = Field(
        description="拍摄场次头，格式为 集数-场次 日/夜-内/外-具体地点，例如 1-1 夜-内-温家走廊。",
    )
    characters: list[str] = Field(description="本场实际出镜或发声角色。")
    lines: list[SceneLine] = Field(
        description="正片分镜和台词。单场不要只站桩对话，要交替出现 action 与短对白。",
    )


def _scene_line_hook_text(line: SceneLine) -> str:
    return line.text.strip()


def _tail_scene_lines(scenes: list[Scene], line_count: int = 4) -> list[SceneLine]:
    if not scenes:
        return []
    return [line for line in scenes[-1].lines[-line_count:] if line.text.strip()]


def _cliffhanger_needs_sync(cliffhanger: str, tail_lines: list[SceneLine]) -> bool:
    stripped = cliffhanger.strip()
    if not stripped:
        return True
    tail_text = "\n".join(_scene_line_hook_text(line) for line in tail_lines)
    if not tail_text:
        return False
    is_performed = stripped in tail_text or tail_text in stripped
    if not is_performed:
        return True
    return any(token in stripped for token in CLIFFHANGER_EXPLANATORY_TOKENS)


def _best_performed_cliffhanger(tail_lines: list[SceneLine]) -> str | None:
    voiced = [line for line in tail_lines if line.kind in {"dialogue", "os", "vo"}]
    for line in reversed(voiced):
        text = _scene_line_hook_text(line)
        if any(token in text for token in CLIFFHANGER_STRONG_TOKENS):
            return text
    for line in reversed(tail_lines):
        text = _scene_line_hook_text(line)
        if line.kind == "action" and any(token in text for token in CLIFFHANGER_PROP_TOKENS):
            return text
    if voiced:
        return _scene_line_hook_text(voiced[-1])
    for line in reversed(tail_lines):
        if line.kind == "action":
            return _scene_line_hook_text(line)
    return None


def _raw_scene_line_text(line: object) -> str:
    if isinstance(line, SceneLine):
        return line.text.strip()
    if isinstance(line, dict):
        text = line.get("text")
        if isinstance(text, str):
            return text.strip()
    return ""


def _raw_scene_line_kind(line: object) -> str:
    if isinstance(line, SceneLine):
        return line.kind
    if isinstance(line, dict):
        kind = line.get("kind")
        if isinstance(kind, str):
            return kind
    return ""


def _raw_scene_lines(scenes: object, line_count: int = 4) -> list[object]:
    if not isinstance(scenes, list) or not scenes:
        return []
    last_scene = scenes[-1]
    if isinstance(last_scene, Scene):
        lines: object = last_scene.lines
    elif isinstance(last_scene, dict):
        lines = last_scene.get("lines")
    else:
        return []
    if not isinstance(lines, list):
        return []
    return [line for line in lines[-line_count:] if _raw_scene_line_text(line)]


def _best_raw_performed_cliffhanger(scenes: object) -> str | None:
    tail_lines = _raw_scene_lines(scenes)
    voiced = [
        line
        for line in tail_lines
        if _raw_scene_line_kind(line) in {"dialogue", "os", "vo"}
    ]
    for line in reversed(voiced):
        text = _raw_scene_line_text(line)
        if any(token in text for token in CLIFFHANGER_STRONG_TOKENS):
            return text
    for line in reversed(tail_lines):
        text = _raw_scene_line_text(line)
        if _raw_scene_line_kind(line) == "action" and any(
            token in text for token in CLIFFHANGER_PROP_TOKENS
        ):
            return text
    if voiced:
        return _raw_scene_line_text(voiced[-1])
    for line in reversed(tail_lines):
        if _raw_scene_line_kind(line) == "action":
            return _raw_scene_line_text(line)
    return None


class EpisodeScript(BaseModel):
    episode: int = Field(ge=1)
    title: str = Field(description="本集标题，只写冲突事件，不写分析。")
    hook_3s: str = Field(
        description="系统内部字段：前三秒钩子设计。必须在第一场第一组动作/台词里被演出来。",
    )
    main_emotion: str = Field(description="系统内部字段：本集主情绪，不得作为 scene line 输出。")
    watch_reason: str = Field(
        description="系统内部字段：观看理由，不得作为 scene line 输出，不得写成用户可见消费理由。",
    )
    scenes: list[Scene] = Field(
        description=(
            "完整正片脚本，不是摘要。目标 2-5 场，优先 3 场；"
            "整集至少 8 条 action 和 16 条 dialogue/os/vo。"
        ),
    )
    cliffhanger: str = Field(
        description=(
            "系统内部字段：必须直接填写最后一场最后几行里已经演出来的钩子台词或动作。"
            "禁止写成“留下悬念/关于身份的悬念/气氛紧张”等说明句。"
        ),
    )
    state_update: dict[str, Any] = Field(description="本集已经演出的事实、关系、道具和伏笔状态。")

    @model_validator(mode="before")
    @classmethod
    def fill_missing_cliffhanger_from_final_scene(cls, data: object) -> object:
        if not isinstance(data, dict):
            return data
        cliffhanger = data.get("cliffhanger")
        if isinstance(cliffhanger, str) and cliffhanger.strip():
            return data
        performed = _best_raw_performed_cliffhanger(data.get("scenes"))
        if not performed:
            return data
        return {**data, "cliffhanger": performed}

    @model_validator(mode="after")
    def sync_cliffhanger_with_final_scene(self) -> "EpisodeScript":
        tail_lines = _tail_scene_lines(self.scenes)
        if _cliffhanger_needs_sync(self.cliffhanger, tail_lines):
            performed = _best_performed_cliffhanger(tail_lines)
            if performed:
                self.cliffhanger = performed
        return self


class ScriptBatch(BaseModel):
    episodes: list[EpisodeScript] = Field(min_length=1, max_length=5)


class QualityScores(BaseModel):
    hook: int = Field(ge=0, le=10)
    conflict: int = Field(ge=0, le=10)
    cliffhanger: int = Field(ge=0, le=10)
    continuity: int = Field(ge=0, le=10)
    video_feasibility: int = Field(ge=0, le=10)


class QualityReport(BaseModel):
    status: QualityStatus
    scores: QualityScores
    blocking_issues: list[str]
    rewrite_instruction: str


class LLMUsageMetrics(BaseModel):
    prompt_tokens: int | None = Field(default=None, ge=0)
    completion_tokens: int | None = Field(default=None, ge=0)
    total_tokens: int | None = Field(default=None, ge=0)


class LLMCallMetric(BaseModel):
    stage: str
    response_model: str
    duration_ms: int = Field(ge=0)
    status: str
    usage: LLMUsageMetrics | None = None
    error: str | None = None


class PipelineStageMetric(BaseModel):
    name: str
    duration_ms: int = Field(ge=0)
    status: str
    error: str | None = None


class RuntimeReport(BaseModel):
    generation_variant: GenerationVariant
    repair_budget: str
    total_duration_ms: int = Field(ge=0)
    stages: list[PipelineStageMetric] = Field(default_factory=list)
    llm_calls: list[LLMCallMetric] = Field(default_factory=list)

    @property
    def total_llm_calls(self) -> int:
        return len(self.llm_calls)

    @property
    def total_tokens(self) -> int | None:
        values = [
            call.usage.total_tokens
            for call in self.llm_calls
            if call.usage and call.usage.total_tokens is not None
        ]
        if not values:
            return None
        return sum(values)


class NextRoundContext(BaseModel):
    summary: str
    current_episode: int = Field(ge=0)
    open_hooks: list[str]
    forbidden_reveals: list[str]
    character_knowledge: dict[str, list[str]]
    relationship_changes: list[str]
    prop_states: list[str]
    foreshadowing_ledger: list[str]


class SourceFidelityCheck(BaseModel):
    category: Literal[
        "C0_immutable_fact",
        "C1_must_keep_scene",
        "C2_visual_asset",
        "C4_forbidden_addition",
        "hook_preservation",
        "character_integrity",
        "source_mapping",
    ]
    anchor: str
    status: Literal["passed", "advisory", "blocking"]
    episode: int | None = None
    evidence: list[str] = Field(default_factory=list)
    warning: str | None = None


class SourceFidelityReport(BaseModel):
    score: int = Field(ge=0, le=100)
    preserved_original_hook: bool
    checks: list[SourceFidelityCheck] = Field(default_factory=list)
    blocking_warnings: list[str] = Field(default_factory=list)
    advisory_warnings: list[str] = Field(default_factory=list)


class ContinuityLinkReport(BaseModel):
    previous_episode: int
    next_episode: int
    previous_cliffhanger: str
    next_opening: str
    status: Literal["passed", "advisory", "blocking"]
    warnings: list[str] = Field(default_factory=list)


class ContinuityAuditReport(BaseModel):
    score: int = Field(ge=0, le=100)
    links: list[ContinuityLinkReport] = Field(default_factory=list)
    blocking_warnings: list[str] = Field(default_factory=list)
    advisory_warnings: list[str] = Field(default_factory=list)


class StoryStateEntry(BaseModel):
    episode: int | None = None
    kind: Literal[
        "open_hook",
        "forbidden_reveal",
        "character_knowledge",
        "relationship_change",
        "prop_state",
        "foreshadowing",
        "episode_state",
    ]
    key: str
    value: str
    status: Literal["open", "active", "closed", "forbidden"] = "active"
    source: str | None = None


class StoryStateLedger(BaseModel):
    current_episode: int = Field(ge=0)
    entries: list[StoryStateEntry] = Field(default_factory=list)
    open_hooks: list[str] = Field(default_factory=list)
    forbidden_reveals: list[str] = Field(default_factory=list)
    character_knowledge: dict[str, list[str]] = Field(default_factory=dict)
    relationship_changes: list[str] = Field(default_factory=list)
    prop_states: list[str] = Field(default_factory=list)
    foreshadowing_ledger: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class AdaptationQualityReport(BaseModel):
    source_fidelity: SourceFidelityReport
    continuity: ContinuityAuditReport
    story_state_ledger: StoryStateLedger
    blocking_warnings: list[str] = Field(default_factory=list)
    advisory_warnings: list[str] = Field(default_factory=list)
    rewrite_instruction: str = ""


class RoundResult(BaseModel):
    project_id: str
    round_number: int = Field(ge=1)
    source_analysis: SourceAnalysis
    episode_context: EpisodeContext
    viral_asset_report: ViralAssetReport | None = None
    story_bible: StoryBible
    series_structure_plan: SeriesStructurePlan | None = None
    episode_plan: EpisodePlan | None = None
    script_batch: ScriptBatch
    quality_report: QualityReport
    next_round_context: NextRoundContext
    adaptation_quality_report: AdaptationQualityReport | None = None
    story_state_ledger: StoryStateLedger | None = None
    runtime_report: RuntimeReport | None = None


class BatchManifestItem(BaseModel):
    project_id: str
    input: Path
    context: Path | None = None
    round_number: int | None = Field(default=None, ge=1)


class BatchManifest(BaseModel):
    projects: list[BatchManifestItem] = Field(min_length=1)


class BatchItemResult(BaseModel):
    project_id: str
    status: BatchItemStatus
    project_dir: str
    round_number: int | None = None
    target_episode_range: str | None = None
    quality_status: QualityStatus | None = None
    error: str | None = None


class BatchRunReport(BaseModel):
    items: list[BatchItemResult]

    @property
    def completed_count(self) -> int:
        return sum(1 for item in self.items if item.status == BatchItemStatus.COMPLETED)

    @property
    def failed_count(self) -> int:
        return sum(1 for item in self.items if item.status == BatchItemStatus.FAILED)


class QualitySample(BaseModel):
    sample_id: str
    label: str
    source_text: str


class QualitySampleManifest(BaseModel):
    samples: list[QualitySample] = Field(min_length=1)


class QualitySampleRoundReport(BaseModel):
    round_number: int = Field(ge=1)
    generation_variant: GenerationVariant | None = None
    target_episode_range: str | None = None
    quality_status: QualityStatus | None = None
    hook_score: int | None = None
    conflict_score: int | None = None
    cliffhanger_score: int | None = None
    continuity_score: int | None = None
    video_feasibility_score: int | None = None
    source_fidelity_score: int | None = None
    continuity_audit_score: int | None = None
    source_fidelity_warnings: list[str] = Field(default_factory=list)
    continuity_warnings: list[str] = Field(default_factory=list)
    ledger_warnings: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)

    @property
    def passed(self) -> bool:
        return not self.warnings


class QualitySampleResult(BaseModel):
    sample_id: str
    label: str
    variant: GenerationVariant = GenerationVariant.CURRENT_DENSITY
    project_dir: str
    rounds: list[QualitySampleRoundReport]

    @property
    def passed(self) -> bool:
        return all(round_report.passed for round_report in self.rounds)


class QualitySampleEvaluationReport(BaseModel):
    samples: list[QualitySampleResult]
    variants: list[GenerationVariant] = Field(default_factory=list)

    @property
    def passed_count(self) -> int:
        return sum(1 for sample in self.samples if sample.passed)

    @property
    def failed_count(self) -> int:
        return len(self.samples) - self.passed_count


class VideoShotBrief(BaseModel):
    shot_id: str
    scene_heading: str
    duration_seconds: int = Field(ge=1)
    aspect_ratio: str
    characters: list[str]
    visual_prompt: str
    dialogue_beats: list[str]
    camera_notes: str
    audio_notes: str
    asset_requirements: list[str]


class VideoEpisodeBrief(BaseModel):
    episode: int = Field(ge=1)
    title: str
    aspect_ratio: str
    target_duration_seconds: int = Field(ge=1)
    hook_3s: str
    main_emotion: str
    cliffhanger: str
    shots: list[VideoShotBrief]


class VideoBrief(BaseModel):
    project_id: str
    round_number: int = Field(ge=1)
    target_episode_range: str
    profile: str
    episodes: list[VideoEpisodeBrief]


class LocalizationProfile(BaseModel):
    profile_id: str
    locale: str
    platform: str
    target_language: str
    aspect_ratio: str = "9:16"
    target_duration_seconds: int = Field(default=90, ge=1)
    tone: str = "high-conflict vertical short drama"
    title_prefix: str | None = None
    replacements: dict[str, str] = Field(default_factory=dict)
    forbidden_terms: list[str] = Field(default_factory=list)
    compliance_notes: list[str] = Field(default_factory=list)
    production_notes: list[str] = Field(default_factory=list)


class LocalizedScene(BaseModel):
    heading: str
    characters: list[str]
    adapted_lines: list[str]


class LocalizedEpisodePackage(BaseModel):
    episode: int = Field(ge=1)
    title: str
    hook_3s: str
    main_emotion: str
    watch_reason: str
    cliffhanger: str
    scenes: list[LocalizedScene]


class LocalizationIssue(BaseModel):
    term: str
    location: str
    text: str


class LocalizationPackage(BaseModel):
    project_id: str
    round_number: int = Field(ge=1)
    target_episode_range: str
    profile: LocalizationProfile
    episodes: list[LocalizedEpisodePackage]
    issues: list[LocalizationIssue]


class LocalizationRewrite(BaseModel):
    episodes: list[LocalizedEpisodePackage]


class DeliveryFile(BaseModel):
    path: str
    bytes: int = Field(ge=0)


class DeliveryManifest(BaseModel):
    project_id: str
    round_number: int = Field(ge=1)
    target_episode_range: str
    quality_status: QualityStatus
    warnings: list[str] = Field(default_factory=list)
    included_files: list[DeliveryFile]


class DeliveryPreflightReport(BaseModel):
    project_id: str
    round_number: int = Field(ge=1)
    target_episode_range: str
    quality_status: QualityStatus
    ready: bool
    warnings: list[str] = Field(default_factory=list)
    files: list[DeliveryFile]
