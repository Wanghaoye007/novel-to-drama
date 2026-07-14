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


class SourceStrengthLevel(StrEnum):
    STRONG = "strong"
    MEDIUM = "medium"
    WEAK = "weak"


class AdaptationIntensity(StrEnum):
    LIGHT = "light"
    MEDIUM = "medium"
    HEAVY = "heavy"


class MethodologyStatus(StrEnum):
    DRAFT = "draft"
    ACTIVE = "active"
    ARCHIVED = "archived"
    REJECTED = "rejected"


class MethodologyStage(StrEnum):
    SOURCE_ANALYSIS = "source_analysis"
    VIRAL_ASSET = "viral_asset"
    EPISODE_CONTEXT = "episode_context"
    STORY_BIBLE = "story_bible"
    SERIES_STRUCTURE = "series_structure"
    EPISODE_PLAN = "episode_plan"
    SCRIPT_GENERATION = "script_generation"
    QUALITY_GATE = "quality_gate"


class MethodologySource(BaseModel):
    id: str
    title: str
    source_type: str
    raw_text: str
    origin_path: str | None = None
    status: MethodologyStatus = MethodologyStatus.DRAFT
    created_at: str | None = None
    updated_at: str | None = None


class MethodologyCard(BaseModel):
    id: str
    source_id: str
    name: str
    category: str
    applies_to_channel: list[str] = Field(default_factory=list)
    applies_to_genre: list[str] = Field(default_factory=list)
    applies_to_stage: list[MethodologyStage] = Field(default_factory=list)
    trigger: str
    generation_rule: str
    quality_rule: str
    positive_examples: list[str] = Field(default_factory=list)
    negative_examples: list[str] = Field(default_factory=list)
    status: MethodologyStatus = MethodologyStatus.DRAFT
    version: int = Field(default=1, ge=1)


class SourceStrengthProfile(BaseModel):
    conflict_strength: int = Field(ge=0, le=10)
    hook_strength: int = Field(ge=0, le=10)
    character_tag_strength: int = Field(ge=0, le=10)
    emotion_asset_strength: int = Field(ge=0, le=10)
    signature_scene_strength: int = Field(ge=0, le=10)
    visualization_readiness: int = Field(ge=0, le=10)
    overall_level: SourceStrengthLevel
    recommended_intensity: AdaptationIntensity
    reasons: list[str] = Field(default_factory=list)


class MethodologyContext(BaseModel):
    source_strength_level: SourceStrengthLevel
    adaptation_intensity: AdaptationIntensity
    cards: list[MethodologyCard] = Field(default_factory=list)


class MethodologyQualityIssue(BaseModel):
    card_id: str
    card_name: str
    severity: Literal["advisory", "blocking"]
    episode: int | None = None
    message: str
    evidence: list[str] = Field(default_factory=list)


class MethodologyQualityReport(BaseModel):
    issues: list[MethodologyQualityIssue] = Field(default_factory=list)
    rewrite_instruction: str = ""


class SourceAnalysis(BaseModel):
    characters: list[str]
    events: list[str]
    conflicts: list[str]
    visual_moments: list[str]
    low_value_passages: list[str]
    candidate_hooks: list[str]


class SourceSpan(BaseModel):
    span_id: str
    # Legacy artifacts associated one synthetic span with an episode. Canonical
    # spans are source-level evidence and intentionally have no episode owner.
    episode: int | None = Field(default=None, ge=1)
    start: int = Field(ge=0)
    end: int = Field(ge=0)
    text: str


class SourceFact(BaseModel):
    fact_id: str
    # Kept readable for prior artifacts; canonical facts are mapped to episodes
    # by SourceFactLedger.episode_fact_ids instead.
    episode: int | None = Field(default=None, ge=1)
    content: str
    source_span_ids: list[str] = Field(min_length=1)
    fact_type: Literal[
        "character",
        "relationship",
        "event",
        "timeline",
        "location",
        "item",
        "knowledge",
        "secret",
    ]
    confidence: float = Field(ge=0.0, le=1.0)
    status: Literal["source_confirmed", "inferred", "adapted"]
    origin: Literal[
        "direct_extraction",
        "source_packet",
        "story_bible",
        "episode_plan",
    ] = "direct_extraction"
    verification_status: Literal[
        "unverified",
        "lexically_supported",
        "semantically_verified",
    ] = "semantically_verified"
    # A direct source sentence may express more than one constraint, for
    # example an item plus a character knowledge boundary.
    fact_types: list[
        Literal[
            "character",
            "relationship",
            "event",
            "timeline",
            "location",
            "item",
            "knowledge",
            "secret",
        ]
    ] = Field(default_factory=list)
    adaptation_reason: str | None = None

    @model_validator(mode="after")
    def protect_source_confirmed_origin(self) -> "SourceFact":
        """Only immutable full-source extraction may be source-confirmed."""
        if self.origin != "direct_extraction" and self.status == "source_confirmed":
            self.status = "inferred"
            self.verification_status = "unverified"
        return self


class SourceFactCandidate(BaseModel):
    candidate_id: str
    episode: int = Field(ge=1)
    content: str
    source_span_ids: list[str] = Field(default_factory=list)
    origin: Literal[
        "direct_extraction",
        "source_packet",
        "story_bible",
        "episode_plan",
    ]
    verification_status: Literal[
        "unverified",
        "lexically_supported",
        "semantically_verified",
    ] = "unverified"
    status: Literal["inferred", "source_confirmed"] = "inferred"
    confidence: float = Field(default=0.6, ge=0.0, le=1.0)
    category: str | None = None

    @model_validator(mode="after")
    def keep_upstream_claims_inferred(self) -> "SourceFactCandidate":
        """Packets, Bible, and plans are interpretations, never source proof."""
        if self.origin in {"source_packet", "story_bible", "episode_plan"}:
            self.status = "inferred"
            self.verification_status = "unverified"
        return self


class SourceFactLedger(BaseModel):
    source_hash: str
    spans: list[SourceSpan] = Field(default_factory=list)
    facts: list[SourceFact] = Field(default_factory=list)
    candidates: list[SourceFactCandidate] = Field(default_factory=list)
    episode_fact_ids: dict[int, list[str]] = Field(default_factory=dict)


class RepairPatch(BaseModel):
    # New repair contract. The model may choose replacement text only; target
    # location and baseline hash are system-owned and verified at application.
    patch_id: str = ""
    episode: int | None = Field(default=None, ge=1)
    scene_id: str | None = None
    target_type: Literal[
        "dialogue",
        "action",
        "scene_heading",
    ] | None = None
    target_ids: list[str] = Field(default_factory=list)
    operation: Literal["replace"]
    expected_before_hash: str = ""
    replacement: str | None = None
    issue_code: str = ""
    required_fact_ids: list[str] = Field(default_factory=list)
    forbidden_fact_ids: list[str] = Field(default_factory=list)
    preserve_beat_ids: list[str] = Field(default_factory=list)
    preserve_state_after: list[str] = Field(default_factory=list)
    # Compatibility fields for historical repair-packet artifacts. They are
    # never used to authorize a new automatic patch.
    target: str | None = None
    issue: str | None = None
    constraint: str | None = None


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


class ProductionSpec(BaseModel):
    primary_output: Literal["creative_script", "shooting_script"] = "creative_script"
    script_priorities: list[str] = Field(default_factory=list)
    format_rules: list[str] = Field(default_factory=list)
    vo_os_rules: list[str] = Field(default_factory=list)
    dialogue_rules: list[str] = Field(default_factory=list)
    shooting_rules: list[str] = Field(default_factory=list)
    delivery_rules: list[str] = Field(default_factory=list)


class SourceAnnotationEpisode(BaseModel):
    episode: int = Field(ge=1)
    source_anchor: str
    source_excerpt: str
    core_conflict: str
    must_keep_events: list[str] = Field(default_factory=list)
    must_keep_assets: list[str] = Field(default_factory=list)
    must_keep_lines: list[str] = Field(default_factory=list)
    psychological_beats: list[str] = Field(default_factory=list)
    visual_assets: list[str] = Field(default_factory=list)
    removable_passages: list[str] = Field(default_factory=list)
    forbidden_changes: list[str] = Field(default_factory=list)
    active_party: str | None = None
    key_decision_timing: str | None = None


class SourceAnnotation(BaseModel):
    north_star: str
    global_must_keep: list[str] = Field(default_factory=list)
    global_forbidden_changes: list[str] = Field(default_factory=list)
    removable_passages: list[str] = Field(default_factory=list)
    episodes: list[SourceAnnotationEpisode] = Field(default_factory=list)


class EpisodeCut(BaseModel):
    episode: int = Field(ge=1)
    source_anchor: str
    core_conflict: str
    duration_target: str = "60-90s"
    title_seed: str
    ending_hook_seed: str


class EpisodeCutTable(BaseModel):
    target_episode_range: str
    cuts: list[EpisodeCut] = Field(default_factory=list)


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


class EpisodeBeat(BaseModel):
    beat_id: str
    event: str
    source_span_ids: list[str] = Field(min_length=1)
    required_fact_ids: list[str] = Field(min_length=1)
    forbidden_changes: list[str] = Field(default_factory=list)
    allowed_adaptation: str = "允许压缩旁白，改成可拍动作与短对白。"
    state_before: list[str] = Field(default_factory=list)
    state_after: list[str] = Field(default_factory=list)


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
    beats: list[EpisodeBeat] = Field(default_factory=list)


class EpisodePlan(BaseModel):
    variant: GenerationVariant
    target_episode_range: str
    adaptation_strategy: str
    episodes: list[EpisodeDramaPlan] = Field(min_length=1, max_length=5)

    @model_validator(mode="before")
    @classmethod
    def wrap_provider_episode_items(cls, data: object) -> object:
        if isinstance(data, list):
            episode_items = data
            normalized: dict[str, Any] = {"episodes": episode_items}
        elif isinstance(data, dict) and "episodes" not in data and "episode" in data:
            episode_items = [data]
            normalized = {"episodes": episode_items}
        elif isinstance(data, dict) and isinstance(data.get("episodes"), list):
            episode_items = data["episodes"]
            normalized = dict(data)
        else:
            return data

        episode_numbers = [
            item.get("episode")
            for item in episode_items
            if isinstance(item, dict) and isinstance(item.get("episode"), int)
        ]
        if not episode_numbers:
            return data
        start = min(episode_numbers)
        end = max(episode_numbers)
        valid_variants = {variant.value for variant in GenerationVariant}
        if normalized.get("variant") not in valid_variants:
            normalized["variant"] = GenerationVariant.DRAMA_ENGINE_FIRST.value
        normalized.setdefault("target_episode_range", f"EP{start:02d}-EP{end:02d}")
        normalized.setdefault(
            "adaptation_strategy",
            (
                "兼容修复：provider 返回了 EpisodeDramaPlan item，"
                "系统按任务参数补齐 EpisodePlan 控制字段。"
            ),
        )
        return normalized


class EpisodeSourcePacket(BaseModel):
    episode: int = Field(ge=1)
    source_anchor: str
    source_excerpt: str
    source_start: int | None = Field(default=None, ge=0)
    source_end: int | None = Field(default=None, ge=0)
    source_hash: str | None = None
    # Canonical evidence references. Legacy source_excerpt/start/end remain
    # available for old artifacts but do not identify evidence in new rounds.
    source_span_ids: list[str] = Field(default_factory=list)
    c0_facts: list[str] = Field(default_factory=list)
    c1_must_keep_assets: list[str] = Field(default_factory=list)
    source_evidence_assets: list[str] | None = None
    c2_visual_assets: list[str] = Field(default_factory=list)
    c3_compress_assets: list[str] = Field(default_factory=list)
    c4_forbidden_additions: list[str] = Field(default_factory=list)
    golden_lines: list[str] = Field(default_factory=list)
    active_party: str | None = None
    key_decision_timing: str | None = None
    handoff_requirement: str | None = None
    source_selection_method: Literal[
        "heading",
        "chapter_partition",
        "asset_window",
        "proportional_fallback",
        "manual",
        "unknown",
    ] = "unknown"
    source_confidence: Literal["high", "medium", "low"] = "medium"
    source_confidence_warnings: list[str] = Field(default_factory=list)


class EpisodeSourcePackets(BaseModel):
    packets: list[EpisodeSourcePacket] = Field(min_length=1, max_length=5)


class SourcePacketConfidenceItem(BaseModel):
    episode: int = Field(ge=1)
    source_anchor: str
    selection_method: str
    source_confidence: Literal["high", "medium", "low"]
    evidence_asset_count: int = Field(ge=0)
    status: Literal["passed", "advisory", "blocking"]
    warnings: list[str] = Field(default_factory=list)


class SourcePacketConfidenceReport(BaseModel):
    score: int = Field(ge=0, le=100)
    status: Literal["passed", "advisory", "blocking"]
    items: list[SourcePacketConfidenceItem] = Field(default_factory=list)
    blocking_warnings: list[str] = Field(default_factory=list)
    advisory_warnings: list[str] = Field(default_factory=list)
    rewrite_instruction: str = ""


class EpisodeHandoff(BaseModel):
    previous_episode: int = Field(ge=1)
    previous_title: str
    previous_cliffhanger: str
    previous_final_lines: list[str] = Field(default_factory=list)
    previous_state_update: dict[str, Any] = Field(default_factory=dict)


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


SCENE_LINE_TEXT_ALIASES = (
    "dialogue",
    "line",
    "content",
    "description",
    "shot",
    "action",
    "voiceover",
    "voice_over",
    "narration",
    "inner_voice",
    "subtitle",
    "visual",
    "camera",
)


def _coerce_scene_line_text(data: dict[str, Any]) -> str:
    text = data.get("text")
    if isinstance(text, str) and text.strip():
        return text
    for key in SCENE_LINE_TEXT_ALIASES:
        value = data.get(key)
        if isinstance(value, str) and value.strip():
            return value
    kind = data.get("kind")
    if kind == "action":
        return "人物停住动作，现场声音压低。"
    if kind == "transition":
        return "切到下一场。"
    return "……"


class SceneLine(BaseModel):
    line_id: str | None = Field(
        default=None,
        description="系统稳定行 ID；初稿由系统按场次与行序生成，修复时不得由模型任意改写。",
    )
    kind: Literal["action", "dialogue", "os", "vo", "transition"] = Field(
        description=(
            "action 是创作稿中的可见动作、表情、道具、空间关系或声音变化；"
            "不要为满足执行稿格式强行添加景别和运镜；"
            "dialogue/os/vo 是短台词，不能承载分析说明。"
        ),
    )
    text: str = Field(
        description=(
            "用户可见正片文本。action 保留模型原始创作文本；对白/OS/VO 单句尽量短，"
            "不得出现 Hook、主情绪、消费理由、观众要看、本集看点等分析字段。"
        ),
    )
    speaker: str | None = Field(default=None, description="对白/OS/VO 的角色名；action 可为空。")
    emotion: str | None = Field(default=None, description="短情绪提示，例如 冷、怒、压低声音。")

    @model_validator(mode="before")
    @classmethod
    def normalize_provider_line_shape(cls, data: object) -> object:
        if not isinstance(data, dict):
            return data
        return {**data, "text": _coerce_scene_line_text(data)}

    @model_validator(mode="after")
    def normalize_user_visible_text(self) -> "SceneLine":
        if self.kind in {"dialogue", "os", "vo"}:
            self.text, self.emotion = _normalize_voiced_text(
                self.text,
                speaker=self.speaker,
                kind=self.kind,
                emotion=self.emotion,
            )
        return self


class Scene(BaseModel):
    scene_id: str | None = Field(
        default=None,
        description="系统稳定场次 ID；初稿由系统生成，修复 Patch 只能引用既有 ID。",
    )
    heading: str = Field(
        description="拍摄场次头，格式为 集数-场次 日/夜-内/外-具体地点，例如 1-1 夜-内-温家走廊。",
    )
    characters: list[str] = Field(description="本场实际出镜或发声角色。")
    lines: list[SceneLine] = Field(
        description="创作稿动作和台词。单场不要只站桩对话，要交替出现 action 与短对白。",
    )

    @model_validator(mode="after")
    def normalize_offstage_voice_and_sentence_beats(self) -> "Scene":
        normalized: list[SceneLine] = []
        for line in self.lines:
            kind = line.kind
            if kind == "os" and line.speaker and line.speaker not in self.characters:
                kind = "vo"
            sentence_parts = [
                part.strip()
                for part in re.findall(r"[^。！？!?]+[。！？!?]?", line.text)
                if part.strip()
            ]
            should_split = (
                kind == "vo"
                and len(line.text) > 22
                and len(sentence_parts) > 1
            )
            if should_split:
                normalized.extend(
                    line.model_copy(update={"kind": kind, "text": part})
                    for part in sentence_parts
                )
            else:
                normalized.append(line.model_copy(update={"kind": kind}))
        self.lines = normalized
        return self


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
    if tail_lines:
        return _scene_line_hook_text(tail_lines[-1])
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
    if tail_lines:
        return _raw_scene_line_text(tail_lines[-1])
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
            "完整创作稿，不是摘要。围绕本集原文资产写出完整冲突、情绪递进和结尾断点；"
            "动作必须可见、台词必须服务人物与剧情，不按执行稿镜头数量凑行。"
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

    @model_validator(mode="after")
    def assign_missing_stable_node_ids(self) -> "EpisodeScript":
        """Make node IDs system-owned before the draft is persisted.

        Provider-supplied IDs are never trusted: a RepairPatch can only point to
        a deterministic position in the baseline that the system persisted.
        """
        for scene_index, scene in enumerate(self.scenes, start=1):
            expected_scene_id = f"EP{self.episode:02d}-S{scene_index:02d}"
            scene.scene_id = expected_scene_id
            for line_index, line in enumerate(scene.lines, start=1):
                expected_line_id = f"{scene.scene_id}-L{line_index:02d}"
                line.line_id = expected_line_id
        return self


class ScriptBatch(BaseModel):
    episodes: list[EpisodeScript] = Field(min_length=1, max_length=5)

    @model_validator(mode="before")
    @classmethod
    def wrap_provider_episode_array(cls, data: object) -> object:
        if isinstance(data, list):
            return {"episodes": data}
        if isinstance(data, dict) and "episodes" not in data:
            for alias in ("EpisodeScript", "episode_scripts", "scripts"):
                candidate = data.get(alias)
                if isinstance(candidate, list):
                    return {**data, "episodes": candidate}
                if isinstance(candidate, dict):
                    return {**data, "episodes": [candidate]}
        return data


class RepairPatchBatch(BaseModel):
    episode: int = Field(ge=1)
    patches: list[RepairPatch] = Field(default_factory=list)


class QualityScores(BaseModel):
    hook: int = Field(ge=0, le=10)
    conflict: int = Field(ge=0, le=10)
    cliffhanger: int = Field(ge=0, le=10)
    continuity: int = Field(ge=0, le=10)
    video_feasibility: int = Field(ge=0, le=10)

    @model_validator(mode="before")
    @classmethod
    def normalize_provider_score_scale(cls, data: object) -> object:
        if not isinstance(data, dict):
            return data
        keys = ("hook", "conflict", "cliffhanger", "continuity", "video_feasibility")
        values = [data.get(key) for key in keys]
        if not all(isinstance(value, (int, float)) and not isinstance(value, bool) for value in values):
            return data
        if not all(0 <= float(value) <= 10 for value in values):
            return data
        scale = 10 if all(float(value) <= 1 for value in values) else 1
        normalized = {**data}
        for key, value in zip(keys, values, strict=True):
            normalized[key] = round(float(value) * scale)
        return normalized


class QualityIssue(BaseModel):
    """A typed quality finding with enough scope for a safe repair decision."""

    code: Literal[
        "UNSUPPORTED_SOURCE_FACT",
        "MISSING_REQUIRED_FACT",
        "KNOWLEDGE_CONFLICT",
        "TIMELINE_CONFLICT",
        "CAUSALITY_CONFLICT",
        "CONTINUITY_CONFLICT",
        "STRUCTURE_INVALID",
        "HOOK_WEAK",
        "DIALOGUE_DENSITY_LOW",
        "EMOTION_WEAK",
    ]
    severity: Literal["hard", "advisory"]
    episode: int | None = Field(default=None, ge=1)
    scene_id: str | None = None
    target_ids: list[str] = Field(default_factory=list)
    evidence: list[str] = Field(default_factory=list)
    message: str

    @field_validator("target_ids", "evidence", mode="before")
    @classmethod
    def normalize_nonempty_strings(cls, value: object) -> object:
        if not isinstance(value, list):
            return value
        return [
            re.sub(r"\s+", " ", item).strip()
            for item in value
            if isinstance(item, str) and item.strip()
        ]

    @field_validator("message", mode="before")
    @classmethod
    def normalize_message(cls, value: object) -> object:
        if not isinstance(value, str):
            return value
        return re.sub(r"\s+", " ", value).strip()


class QualityIssueDisposition(BaseModel):
    issue: QualityIssue
    disposition: Literal[
        "missing_scope_metadata",
        "global_structure_failure",
        "out_of_range_episode",
    ]
    reason: str


class QualityReport(BaseModel):
    status: QualityStatus
    scores: QualityScores
    blocking_issues: list[str]
    advisory_warnings: list[str] = Field(default_factory=list)
    rewrite_instruction: str
    issues: list[QualityIssue] = Field(default_factory=list)

    @model_validator(mode="before")
    @classmethod
    def fill_nonessential_provider_fields(cls, data: object) -> object:
        if not isinstance(data, dict):
            return data
        raw_status = data.get("status")
        status = raw_status.value if isinstance(raw_status, QualityStatus) else str(raw_status or "")
        default_score = {
            QualityStatus.USABLE.value: 8,
            QualityStatus.NEEDS_REWRITE.value: 4,
            QualityStatus.CONTEXT_CONFLICT.value: 2,
            QualityStatus.NEEDS_HUMAN_REVIEW.value: 5,
        }.get(status, 4)
        score_keys = ("hook", "conflict", "cliffhanger", "continuity", "video_feasibility")
        raw_scores = data.get("scores")
        if isinstance(raw_scores, QualityScores):
            scores = raw_scores.model_dump()
        else:
            scores = dict(raw_scores) if isinstance(raw_scores, dict) else {}
        for key in score_keys:
            scores.setdefault(key, default_score)

        rewrite_instruction = data.get("rewrite_instruction")
        if not isinstance(rewrite_instruction, str):
            rewrite_instruction = ""
        blocking_issues = data.get("blocking_issues")
        if not isinstance(blocking_issues, list):
            blocking_issues = (
                [rewrite_instruction]
                if status != QualityStatus.USABLE.value and rewrite_instruction.strip()
                else []
            )
        return {
            **data,
            "scores": scores,
            "blocking_issues": blocking_issues,
            "rewrite_instruction": rewrite_instruction,
        }

    @field_validator("blocking_issues", mode="before")
    @classmethod
    def compact_blocking_issue_whitespace(cls, value: object) -> object:
        if not isinstance(value, list):
            return value
        return [re.sub(r"\s+", " ", item).strip() if isinstance(item, str) else item for item in value]

    @field_validator("rewrite_instruction", mode="before")
    @classmethod
    def compact_rewrite_instruction_whitespace(cls, value: object) -> object:
        if not isinstance(value, str):
            return value
        return re.sub(r"\s+", " ", value).strip()


class QualityDecision(BaseModel):
    issues: list[QualityIssue] = Field(default_factory=list)
    hard_issues: list[str] = Field(default_factory=list)
    advisory_issues: list[str] = Field(default_factory=list)
    repair_targets: list[int] = Field(default_factory=list)
    unscoped_hard_issues: list[str] = Field(default_factory=list)
    unscoped_hard_dispositions: list[QualityIssueDisposition] = Field(
        default_factory=list
    )


class DramaQualityDimension(BaseModel):
    name: Literal[
        "character_integrity",
        "conflict_causality",
        "emotional_progression",
        "dialogue_naturalness",
        "source_asset_preservation",
        "hook_and_cliffhanger",
    ]
    score: int = Field(ge=0, le=10)
    status: Literal["passed", "advisory", "blocking"]
    evidence: list[str] = Field(default_factory=list)
    suggestion: str = ""


class DramaQualityComparison(BaseModel):
    baseline_overall_score: int = Field(ge=0, le=10)
    pipeline_overall_score: int = Field(ge=0, le=10)
    delta: int
    verdict: Literal[
        "pipeline_clearly_better",
        "pipeline_slightly_better",
        "tie",
        "baseline_better",
    ]
    reason: str


class DramaQualityReport(BaseModel):
    overall_score: int = Field(ge=0, le=10)
    dimensions: list[DramaQualityDimension] = Field(default_factory=list)
    blocking_issues: list[str] = Field(default_factory=list)
    advisory_warnings: list[str] = Field(default_factory=list)
    rewrite_instruction: str = ""
    baseline_comparison: DramaQualityComparison | None = None


class EpisodeNoveltyProfile(BaseModel):
    episode: int = Field(ge=1)
    title: str
    scene_skeleton: str
    action_signature: str
    dialogue_signature: str
    cliffhanger_signature: str


class CrossEpisodeSimilarityIssue(BaseModel):
    episodes: tuple[int, int]
    kind: Literal[
        "overall",
        "scene_skeleton",
        "action_chain",
        "dialogue_pattern",
        "cliffhanger",
    ]
    score: float = Field(ge=0.0, le=1.0)
    severity: Literal["blocking", "advisory"]
    evidence: list[str] = Field(default_factory=list)
    suggestion: str = ""


class ScriptNoveltyReport(BaseModel):
    overall_score: int = Field(ge=0, le=10)
    episode_profiles: list[EpisodeNoveltyProfile] = Field(default_factory=list)
    similarity_issues: list[CrossEpisodeSimilarityIssue] = Field(default_factory=list)
    blocking_issues: list[str] = Field(default_factory=list)
    advisory_warnings: list[str] = Field(default_factory=list)
    rewrite_instruction: str = ""


class SourceEvidenceSpan(BaseModel):
    asset: str
    source_anchor: str
    source_excerpt: str
    source_line: str | None = None
    source_line_index: int | None = Field(default=None, ge=1)
    script_line: str | None = None
    script_line_index: int | None = Field(default=None, ge=1)
    adaptation_reason: str
    status: Literal["matched", "missing", "source_missing", "script_missing"]


class SourceEvidenceItem(BaseModel):
    episode: int = Field(ge=1)
    source_anchor: str
    adaptation_reason: str
    retained_assets: list[str] = Field(default_factory=list)
    script_evidence: list[str] = Field(default_factory=list)
    evidence_spans: list[SourceEvidenceSpan] = Field(default_factory=list)
    status: Literal["matched", "partial", "missing", "source_unverified"]


class SourceEvidenceReport(BaseModel):
    coverage_score: int = Field(ge=0, le=100)
    items: list[SourceEvidenceItem] = Field(default_factory=list)
    missing_items: list[str] = Field(default_factory=list)
    rewrite_instruction: str = ""


class CurrentEpisodeRepairPacket(BaseModel):
    episode: int = Field(ge=1)
    quality_issue: QualityIssue | None = None
    repair_mode: Literal[
        "format_patch",
        "ending_hook_patch",
        "handoff_patch",
        "creative_episode_repair",
        "full_episode_rewrite",
    ]
    baseline_policy: str
    baseline_episode_text: str
    allowed_change_scope: str
    repair_patches: list[RepairPatch] = Field(default_factory=list)
    editable_targets: list[str] = Field(default_factory=list)
    source_evidence_targets: list[str] = Field(default_factory=list)
    protected_elements: list[str] = Field(default_factory=list)
    continuity_requirements: list[str] = Field(default_factory=list)
    forbidden_changes: list[str] = Field(default_factory=list)


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
    llm_model: str | None = None
    total_duration_ms: int = Field(ge=0)
    stages: list[PipelineStageMetric] = Field(default_factory=list)
    llm_calls: list[LLMCallMetric] = Field(default_factory=list)
    methodology_cards: list[str] = Field(default_factory=list)

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
        "opening_tension_preservation",
        "intent_drift",
        "agency_ramp",
        "support_role_boundary",
        "opponent_agency",
        "character_integrity",
        "source_mapping",
        "source_mapping_required",
        "source_mapping_context",
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
        "story_event",
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
    blocking_warnings: list[str] = Field(default_factory=list)
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
    source_strength_profile: SourceStrengthProfile | None = None
    methodology_context: MethodologyContext | None = None
    story_bible: StoryBible
    production_spec: ProductionSpec | None = None
    source_annotation: SourceAnnotation | None = None
    episode_cut_table: EpisodeCutTable | None = None
    series_structure_plan: SeriesStructurePlan | None = None
    episode_plan: EpisodePlan | None = None
    episode_source_packets: EpisodeSourcePackets | None = None
    source_fact_ledger: SourceFactLedger | None = None
    source_packet_confidence_report: SourcePacketConfidenceReport | None = None
    script_batch: ScriptBatch
    quality_report: QualityReport
    next_round_context: NextRoundContext
    adaptation_quality_report: AdaptationQualityReport | None = None
    methodology_quality_report: MethodologyQualityReport | None = None
    drama_quality_report: DramaQualityReport | None = None
    script_novelty_report: ScriptNoveltyReport | None = None
    source_evidence_report: SourceEvidenceReport | None = None
    story_state_ledger: StoryStateLedger | None = None
    runtime_report: RuntimeReport | None = None


class BatchManifestItem(BaseModel):
    project_id: str
    input: Path
    context: Path | None = None
    round_number: int | None = Field(default=None, ge=1)
    target_episode_count: int | None = Field(default=None, ge=1)
    episodes_per_round: int = Field(default=5, ge=1, le=5)


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
    target_episode_count: int | None = Field(default=None, ge=1)
    episodes_per_round: int = Field(default=5, ge=1, le=5)


class QualitySampleManifest(BaseModel):
    samples: list[QualitySample] = Field(min_length=1)


QUALITY_SAMPLE_BLOCKING_WARNING_TOKENS = (
    "LLM_PROVIDER_LIMIT",
    "LLM_PROVIDER_AUTH",
    "quality status is",
    "no episodes generated",
    "missing 3s hook",
    "missing cliffhanger",
    "has no scenes",
    "too short",
    "source_fidelity:",
    "未追踪",
    "原文偏离",
    "OOC",
    "全知全能",
    "主动权",
    "证据链",
    "does not hand off",
    "missing from next",
    "forbidden reveal",
    "weak lexical overlap",
    "opening linkage",
)


def quality_sample_warning_is_blocking(warning: str) -> bool:
    normalized_warning = warning.lower()
    return any(
        token.lower() in normalized_warning
        for token in QUALITY_SAMPLE_BLOCKING_WARNING_TOKENS
    )


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
    baseline_overall_score: int | None = None
    pipeline_overall_score: int | None = None
    baseline_delta: int | None = None
    baseline_verdict: Literal[
        "pipeline_clearly_better",
        "pipeline_slightly_better",
        "tie",
        "baseline_better",
    ] | None = None
    baseline_reason: str | None = None
    source_fidelity_warnings: list[str] = Field(default_factory=list)
    continuity_warnings: list[str] = Field(default_factory=list)
    ledger_warnings: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)

    @property
    def passed(self) -> bool:
        structured_warnings = [
            *self.source_fidelity_warnings,
            *self.continuity_warnings,
            *self.ledger_warnings,
        ]
        return not (
            self.warnings
            or (
                self.source_fidelity_score is not None
                and self.source_fidelity_score < 50
            )
            or any(quality_sample_warning_is_blocking(warning) for warning in structured_warnings)
        )


class QualitySampleResult(BaseModel):
    sample_id: str
    label: str
    variant: GenerationVariant = GenerationVariant.DRAMA_ENGINE_FIRST
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
