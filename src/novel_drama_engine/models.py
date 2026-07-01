from __future__ import annotations

from enum import StrEnum
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field


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


class SourceAnalysis(BaseModel):
    characters: list[str]
    events: list[str]
    conflicts: list[str]
    visual_moments: list[str]
    low_value_passages: list[str]
    candidate_hooks: list[str]


class EpisodeContext(BaseModel):
    target_episode_range: str
    story_stage: StoryStage
    source_to_episode_mapping: list[str]
    must_carry_context: list[str]
    forbidden_reveals: list[str]
    adaptation_actions: list[str]
    confidence: float = Field(ge=0.0, le=1.0)


class StoryBible(BaseModel):
    genre: str
    mainline: str
    characters: list[str]
    relationships: list[str]
    speech_styles: dict[str, str]
    immutable_facts: list[str]
    forbidden_changes: list[str]


class SceneLine(BaseModel):
    kind: Literal["action", "dialogue", "os", "vo", "transition"]
    text: str
    speaker: str | None = None
    emotion: str | None = None


class Scene(BaseModel):
    heading: str
    characters: list[str]
    lines: list[SceneLine]


class EpisodeScript(BaseModel):
    episode: int = Field(ge=1)
    title: str
    hook_3s: str
    main_emotion: str
    watch_reason: str
    scenes: list[Scene]
    cliffhanger: str
    state_update: dict[str, Any]


class ScriptBatch(BaseModel):
    episodes: list[EpisodeScript] = Field(min_length=1, max_length=3)


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
    story_bible: StoryBible
    script_batch: ScriptBatch
    quality_report: QualityReport
    next_round_context: NextRoundContext


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
    included_files: list[DeliveryFile]
