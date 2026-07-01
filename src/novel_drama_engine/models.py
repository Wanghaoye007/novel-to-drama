from __future__ import annotations

from enum import StrEnum
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator


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


class Scene(BaseModel):
    heading: str = Field(
        description="拍摄场次头，格式为 集数-场次 日/夜-内/外-具体地点，例如 1-1 夜-内-温家走廊。",
    )
    characters: list[str] = Field(description="本场实际出镜或发声角色。")
    lines: list[SceneLine] = Field(
        description="正片分镜和台词。单场不要只站桩对话，要交替出现 action 与短对白。",
    )


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
    target_episode_range: str | None = None
    quality_status: QualityStatus | None = None
    hook_score: int | None = None
    conflict_score: int | None = None
    cliffhanger_score: int | None = None
    continuity_score: int | None = None
    video_feasibility_score: int | None = None
    warnings: list[str] = Field(default_factory=list)

    @property
    def passed(self) -> bool:
        return not self.warnings


class QualitySampleResult(BaseModel):
    sample_id: str
    label: str
    project_dir: str
    rounds: list[QualitySampleRoundReport]

    @property
    def passed(self) -> bool:
        return all(round_report.passed for round_report in self.rounds)


class QualitySampleEvaluationReport(BaseModel):
    samples: list[QualitySampleResult]

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
