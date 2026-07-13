from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
from threading import Event, Lock, Thread
from time import monotonic
from typing import Callable, TypeVar

from pydantic import BaseModel

from novel_drama_engine.adaptation_quality import (
    build_adaptation_quality_report,
    build_methodology_quality_report,
    merge_adaptation_quality_into_report,
    merge_methodology_quality_into_report,
)
from novel_drama_engine.drama_quality import (
    build_drama_quality_report,
    merge_drama_quality_into_report,
    render_drama_quality_report,
)
from novel_drama_engine.llm import JsonLLM
from novel_drama_engine.lean_flow import (
    build_episode_cut_table,
    build_production_spec,
    build_source_annotation,
)
from novel_drama_engine.models import (
    EpisodeCutTable,
    EpisodeContext,
    EpisodePlan,
    EpisodeScript,
    EpisodeSourcePackets,
    LLMCallMetric,
    LLMUsageMetrics,
    GenerationVariant,
    MethodologyContext,
    MethodologyStage,
    NextRoundContext,
    PipelineStageMetric,
    ProductionSpec,
    QualityReport,
    QualityStatus,
    RoundResult,
    RuntimeReport,
    ScriptBatch,
    SourceAnnotation,
    SourceFactLedger,
    SeriesStructurePlan,
    SourceAnalysis,
    SourceStrengthProfile,
    StoryBible,
    ViralAssetReport,
)
from novel_drama_engine.quality_text import (
    filter_quality_text_for_episode,
    merge_rewrite_instructions,
)
from novel_drama_engine.quality_policy import (
    apply_quality_policy,
    decide_quality,
    partition_quality_issues,
)
from novel_drama_engine.methodology import (
    load_methodology_cards,
    retrieve_methodology_context,
)
from novel_drama_engine.rounds import (
    ContinuityBoomChecker,
    EpisodeBeatPlanner,
    EpisodeContextResolver,
    InternalBibleBuilder,
    ScriptBatchGenerator,
    SeriesStructurePlanner,
    SourceParser,
    StateWriter,
    ViralAssetExtractor,
)
from novel_drama_engine.renderer import (
    render_creative_round,
    render_round_summary,
    render_shooting_round,
)
from novel_drama_engine.script_quality import (
    build_current_episode_repair_packet,
    episode_repair_diff,
    episode_repair_scope_regression_reasons,
    build_script_novelty_report,
    episode_quality_warnings,
    episode_revision_regression_reasons,
    episode_repair_instruction,
    merge_script_novelty_into_quality_report,
    render_script_novelty_report,
)
from novel_drama_engine.source_packets import (
    bind_episode_plan_to_facts,
    build_episode_source_packets,
    build_source_packet_confidence_report,
    ensure_source_packet_confidence,
    handoff_from_episode,
    normalize_story_bible_against_source_packets,
    packet_for_episode,
    render_source_packet_confidence_report,
    sanitize_episode_plan_against_source_packets,
    story_bible_source_packet_conflicts,
)
from novel_drama_engine.source_facts import build_source_fact_ledger
from novel_drama_engine.source_evidence import (
    build_source_evidence_report,
    merge_source_evidence_into_quality_report,
    render_source_evidence_report,
)
from novel_drama_engine.source_strength import classify_source_strength
from novel_drama_engine.storage import ProjectStore
from novel_drama_engine.trace_analysis import (
    analyze_round_trace_artifacts,
    render_prompt_trace_analysis,
)

EPISODES_PER_ROUND = 5
RUN_MANIFEST_SCHEMA_VERSION = "run_manifest.v2.traceable_quality_experiment"
CACHE_FINGERPRINT_FILES = (
    "prompts.py",
    "models.py",
    "script_quality.py",
    "quality_policy.py",
    "adaptation_quality.py",
    "source_packets.py",
    "lean_flow.py",
    "source_evidence.py",
    "source_facts.py",
)
CACHE_RELEVANT_ENV = (
    "OPENAI_BASE_URL",
    "OPENAI_MODEL",
    "NOVEL_DRAMA_LLM_PROVIDER",
    "NOVEL_DRAMA_GENERATION_VARIANT",
    "NOVEL_DRAMA_REPAIR_BUDGET",
    "NOVEL_DRAMA_SCRIPT_EPISODE_FIRST",
    "NOVEL_DRAMA_STRICT_SHOOTING_QUALITY",
    "NOVEL_DRAMA_SOURCE_STRENGTH_COST_CONTROL",
    "NOVEL_DRAMA_REUSE_PRIOR_ROUND_ARTIFACTS",
)
T = TypeVar("T", bound=BaseModel)


class EmptySourceError(ValueError):
    pass


class RepairBudgetError(ValueError):
    pass


class EpisodesPerRoundError(ValueError):
    pass


class RepairBudget:
    NONE = "none"
    EPISODE = "episode"


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _read_file_sha256(path: Path) -> str | None:
    if not path.exists():
        return None
    return hashlib.sha256(path.read_bytes()).hexdigest()


def pipeline_code_fingerprint() -> dict[str, str | None]:
    base_dir = Path(__file__).parent
    return {
        name: _read_file_sha256(base_dir / name)
        for name in CACHE_FINGERPRINT_FILES
    }


def experiment_mode_enabled() -> bool:
    raw = os.environ.get("NOVEL_DRAMA_EXPERIMENT_MODE", "0")
    return raw.strip().lower() in {"1", "true", "yes", "on", "experiment"}


def reuse_prior_round_artifacts_enabled() -> bool:
    raw = os.environ.get("NOVEL_DRAMA_REUSE_PRIOR_ROUND_ARTIFACTS", "1")
    return raw.strip().lower() not in {"0", "false", "no", "off"}


def raw_output_trace_enabled() -> bool:
    raw = os.environ.get("NOVEL_DRAMA_TRACE_RAW_OUTPUTS", "1")
    return raw.strip().lower() not in {"0", "false", "no", "off"}


def _json_fingerprint(payload: dict[str, object]) -> str:
    return _sha256_text(
        json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str)
    )


def normalize_repair_budget(value: str | None) -> str:
    raw = value or os.environ.get("NOVEL_DRAMA_REPAIR_BUDGET", RepairBudget.EPISODE)
    normalized = raw.strip().lower().replace("-", "_")
    aliases = {
        "0": RepairBudget.NONE,
        "off": RepairBudget.NONE,
        "none": RepairBudget.NONE,
        "skip": RepairBudget.NONE,
        "1": RepairBudget.EPISODE,
        "batch": RepairBudget.EPISODE,
        "rewrite": RepairBudget.EPISODE,
        "whole": RepairBudget.EPISODE,
        "2": RepairBudget.EPISODE,
        "episode": RepairBudget.EPISODE,
        "episode_repair": RepairBudget.EPISODE,
        "strict": RepairBudget.EPISODE,
        "full": RepairBudget.EPISODE,
    }
    if normalized not in aliases:
        allowed = ", ".join(sorted(set(aliases)))
        raise RepairBudgetError(f"unknown repair budget: {value}. Allowed: {allowed}")
    return aliases[normalized]


def normalize_episodes_per_round(value: int | str | None = None) -> int:
    raw = value
    if raw is None:
        raw = os.environ.get("NOVEL_DRAMA_EPISODES_PER_ROUND", EPISODES_PER_ROUND)
    try:
        normalized = int(raw)
    except (TypeError, ValueError) as exc:
        raise EpisodesPerRoundError(
            f"episodes per round must be between 1 and {EPISODES_PER_ROUND}: {raw}"
        ) from exc
    if normalized < 1 or normalized > EPISODES_PER_ROUND:
        raise EpisodesPerRoundError(
            f"episodes per round must be between 1 and {EPISODES_PER_ROUND}: {raw}"
        )
    return normalized


def elapsed_ms(start: float) -> int:
    return max(0, round((monotonic() - start) * 1000))


class InstrumentedJsonLLM:
    def __init__(
        self,
        llm: JsonLLM,
        *,
        on_update: Callable[[], None] | None = None,
        on_prompt: Callable[[dict[str, object]], None] | None = None,
        on_raw: Callable[[dict[str, object]], None] | None = None,
        heartbeat_seconds: float | None = None,
    ) -> None:
        self.llm = llm
        self.current_stage = "unknown"
        self.calls: list[LLMCallMetric] = []
        self.on_update = on_update
        self.on_prompt = on_prompt
        self.on_raw = on_raw
        self.heartbeat_seconds = (
            heartbeat_seconds
            if heartbeat_seconds is not None
            else float(os.environ.get("NOVEL_DRAMA_RUNTIME_HEARTBEAT_SECONDS", "5"))
        )
        self._lock = Lock()

    def _write_update(self) -> None:
        if self.on_update is None:
            return
        self.on_update()

    def _replace_call(self, index: int, metric: LLMCallMetric) -> None:
        with self._lock:
            self.calls[index] = metric
        self._write_update()

    def snapshot_calls(self) -> list[LLMCallMetric]:
        with self._lock:
            return list(self.calls)

    def _write_prompt_trace(
        self,
        *,
        call_index: int,
        system: str,
        user: str,
        response_model: type[BaseModel],
    ) -> None:
        if self.on_prompt is None:
            return
        self.on_prompt(
            {
                "call_index": call_index,
                "stage": self.current_stage,
                "response_model": response_model.__name__,
                "system_prompt_sha256": hashlib.sha256(
                    system.encode("utf-8")
                ).hexdigest(),
                "user_prompt_sha256": hashlib.sha256(user.encode("utf-8")).hexdigest(),
                "system_prompt_chars": len(system),
                "user_prompt_chars": len(user),
                "system_prompt": system,
                "user_prompt": user,
            }
        )

    def _write_raw_trace(
        self,
        *,
        call_index: int,
        response_model: type[BaseModel],
        status: str,
        error: str | None = None,
    ) -> None:
        if self.on_raw is None:
            return
        raw_response = getattr(self.llm, "last_raw_response", None)
        self.on_raw(
            {
                "call_index": call_index,
                "stage": self.current_stage,
                "response_model": response_model.__name__,
                "status": status,
                "error": error,
                "raw_response_sha256": _sha256_text(
                    json.dumps(raw_response, ensure_ascii=False, default=str)
                )
                if raw_response is not None
                else None,
                "raw_response": raw_response,
            }
        )

    def complete(self, *, system: str, user: str, response_model: type[T]) -> T:
        start = monotonic()
        with self._lock:
            call_index = len(self.calls)
            self.calls.append(
                LLMCallMetric(
                    stage=self.current_stage,
                    response_model=response_model.__name__,
                    duration_ms=0,
                    status="running",
                )
            )
        self._write_prompt_trace(
            call_index=call_index,
            system=system,
            user=user,
            response_model=response_model,
        )
        self._write_update()

        stop_heartbeat = Event()

        def heartbeat() -> None:
            while not stop_heartbeat.wait(max(0.1, self.heartbeat_seconds)):
                self._replace_call(
                    call_index,
                    LLMCallMetric(
                        stage=self.current_stage,
                        response_model=response_model.__name__,
                        duration_ms=elapsed_ms(start),
                        status="running",
                    ),
                )

        heartbeat_thread = Thread(target=heartbeat, daemon=True)
        heartbeat_thread.start()
        try:
            result = self.llm.complete(
                system=system,
                user=user,
                response_model=response_model,
            )
        except Exception as exc:
            stop_heartbeat.set()
            heartbeat_thread.join(timeout=0.2)
            self._write_raw_trace(
                call_index=call_index,
                response_model=response_model,
                status="failed",
                error=str(exc),
            )
            self._replace_call(
                call_index,
                LLMCallMetric(
                    stage=self.current_stage,
                    response_model=response_model.__name__,
                    duration_ms=elapsed_ms(start),
                    status="failed",
                    error=str(exc),
                )
            )
            raise

        stop_heartbeat.set()
        heartbeat_thread.join(timeout=0.2)
        self._write_raw_trace(
            call_index=call_index,
            response_model=response_model,
            status="succeeded",
        )
        usage = getattr(self.llm, "last_usage", None)
        if usage is not None and not isinstance(usage, LLMUsageMetrics):
            usage = LLMUsageMetrics.model_validate(usage)
        self._replace_call(
            call_index,
            LLMCallMetric(
                stage=self.current_stage,
                response_model=response_model.__name__,
                duration_ms=elapsed_ms(start),
                status="succeeded",
                usage=usage,
            )
        )
        return result


def episode_range_label(start_episode: int, end_episode: int) -> str:
    return f"EP{start_episode:02d}-EP{end_episode:02d}"


def episode_window(
    *,
    round_number: int,
    previous_context: NextRoundContext | None,
    target_episode_count: int | None,
    episodes_per_round: int = EPISODES_PER_ROUND,
) -> tuple[int, int]:
    start_episode = (
        previous_context.current_episode + 1
        if previous_context is not None
        else (round_number - 1) * episodes_per_round + 1
    )
    planned_end = start_episode + episodes_per_round - 1
    if target_episode_count is not None and target_episode_count >= start_episode:
        planned_end = min(planned_end, target_episode_count)
    return start_episode, planned_end


def normalize_episode_context_range(
    episode_context: EpisodeContext,
    *,
    round_number: int,
    previous_context: NextRoundContext | None,
    target_episode_count: int | None,
    episodes_per_round: int = EPISODES_PER_ROUND,
) -> EpisodeContext:
    start_episode, end_episode = episode_window(
        round_number=round_number,
        previous_context=previous_context,
        target_episode_count=target_episode_count,
        episodes_per_round=episodes_per_round,
    )
    target_range = episode_range_label(start_episode, end_episode)
    if episode_context.target_episode_range == target_range:
        return episode_context

    return episode_context.model_copy(
        update={
            "target_episode_range": target_range,
            "adaptation_actions": [
                *episode_context.adaptation_actions,
                f"系统已将本轮集数范围规范为 {target_range}，不得输出未编号或重复集数。",
            ],
        },
    )


def expected_episode_numbers(
    *,
    round_number: int,
    previous_context: NextRoundContext | None,
    target_episode_count: int | None,
    episodes_per_round: int = EPISODES_PER_ROUND,
) -> list[int]:
    start_episode, end_episode = episode_window(
        round_number=round_number,
        previous_context=previous_context,
        target_episode_count=target_episode_count,
        episodes_per_round=episodes_per_round,
    )
    return list(range(start_episode, end_episode + 1))


def variant_uses_episode_plan(generation_variant: GenerationVariant) -> bool:
    return generation_variant in {
        GenerationVariant.DRAMA_ENGINE_FIRST,
        GenerationVariant.SOP_FULL_STACK,
    }


def variant_uses_sop_stack(generation_variant: GenerationVariant) -> bool:
    return generation_variant == GenerationVariant.SOP_FULL_STACK


def use_episode_first_script_generation(model: str | None = None) -> bool:
    raw = os.environ.get("NOVEL_DRAMA_SCRIPT_EPISODE_FIRST", "")
    if raw.strip():
        return raw.strip().lower() in {
            "1",
            "true",
            "yes",
            "on",
            "episode",
            "episode_first",
        }
    selected_model = model or os.environ.get("OPENAI_MODEL", "")
    return selected_model.startswith("bytedance-seed/")


def prompt_trace_enabled() -> bool:
    raw = os.environ.get("NOVEL_DRAMA_TRACE_PROMPTS", "1")
    return raw.strip().lower() not in {"0", "false", "no", "off"}


def source_strength_cost_control_enabled() -> bool:
    raw = os.environ.get("NOVEL_DRAMA_SOURCE_STRENGTH_COST_CONTROL", "1")
    return raw.strip().lower() not in {"0", "false", "no", "off"}


def strong_source_light_adaptation(
    source_strength_profile: SourceStrengthProfile,
    generation_variant: GenerationVariant,
) -> bool:
    return (
        source_strength_cost_control_enabled()
        and generation_variant
        in {
            GenerationVariant.DRAMA_ENGINE_FIRST,
            GenerationVariant.SOP_FULL_STACK,
        }
        and source_strength_profile.overall_level.value == "strong"
        and source_strength_profile.recommended_intensity.value == "light"
    )


def resume_artifacts_enabled() -> bool:
    raw = os.environ.get("NOVEL_DRAMA_RESUME_ARTIFACTS", "1")
    return raw.strip().lower() not in {"0", "false", "no", "off"}


def build_run_manifest(
    *,
    project_id: str,
    round_number: int,
    source_text: str,
    target_episode_count: int | None,
    episodes_per_round: int,
    generation_variant: GenerationVariant,
    repair_budget: str,
    llm: JsonLLM,
    methodology_cards_path: Path | str | None,
) -> dict[str, object]:
    llm_model = getattr(llm, "_model", None) or os.environ.get("OPENAI_MODEL")
    fingerprint_payload: dict[str, object] = {
        "schema_version": RUN_MANIFEST_SCHEMA_VERSION,
        "project_id": project_id,
        "round_number": round_number,
        "source_sha256": _sha256_text(source_text),
        "source_chars": len(source_text),
        "target_episode_count": target_episode_count,
        "episodes_per_round": episodes_per_round,
        "generation_variant": generation_variant.value,
        "repair_budget": repair_budget,
        "llm_class": llm.__class__.__name__,
        "llm_model": llm_model,
        "llm_provider": os.environ.get("NOVEL_DRAMA_LLM_PROVIDER"),
        "openai_base_url": os.environ.get("OPENAI_BASE_URL"),
        "env": {name: os.environ.get(name) for name in CACHE_RELEVANT_ENV},
        "code": pipeline_code_fingerprint(),
        "methodology_cards_path": str(methodology_cards_path)
        if methodology_cards_path
        else None,
    }
    return {
        **fingerprint_payload,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "experiment_mode": experiment_mode_enabled(),
        "resume_requested": resume_artifacts_enabled(),
        "trace_prompts": prompt_trace_enabled() or experiment_mode_enabled(),
        "trace_raw_outputs": raw_output_trace_enabled(),
        "cache_fingerprint": _json_fingerprint(fingerprint_payload),
    }


def source_evidence_targets_for_episode(
    quality_report: QualityReport,
    episode_number: int,
) -> list[str]:
    prefix = f"EP{episode_number:02d}"
    # The structured blocking issues are the repair boundary. The synthesized
    # rewrite instruction is intentionally excluded: it may contain advice for
    # other episodes or a whole-round explanation.
    text = "\n".join(quality_report.blocking_issues)
    matches = re.findall(
        rf"{re.escape(prefix)}\s*缺少原文资产[：:][^；;\n]+",
        text,
    )
    return list(dict.fromkeys(match.strip() for match in matches))


def quality_instruction_for_episode(
    quality_report: QualityReport,
    episode_number: int,
    *,
    include_unscoped: bool = False,
) -> str:
    scoped_issues = filter_quality_text_for_episode(
        "\n".join(quality_report.blocking_issues),
        episode_number,
        include_unscoped=include_unscoped,
    )
    scoped_instruction = filter_quality_text_for_episode(
        quality_report.rewrite_instruction,
        episode_number,
        include_unscoped=include_unscoped,
    )
    return merge_rewrite_instructions(
        [scoped_issues, scoped_instruction],
        blocking=bool(scoped_issues or scoped_instruction),
    )


def provisional_next_round_context(
    script_batch: ScriptBatch,
    previous_context: NextRoundContext | None = None,
) -> NextRoundContext:
    episodes = sorted(script_batch.episodes, key=lambda item: item.episode)
    current_episode = episodes[-1].episode if episodes else 0
    open_hooks = [episodes[-1].cliffhanger] if episodes else []
    prop_states: list[str] = []
    relationship_changes: list[str] = []
    foreshadowing_ledger: list[str] = []
    character_knowledge: dict[str, list[str]] = {}

    for episode in episodes:
        for key, value in episode.state_update.items():
            text = f"EP{episode.episode:02d} {key}: {value}"
            normalized_key = str(key).lower()
            if "relationship" in normalized_key or "关系" in str(key):
                relationship_changes.append(text)
            elif "foreshadow" in normalized_key or "伏笔" in str(key):
                foreshadowing_ledger.append(text)
            elif "character" in normalized_key or "knowledge" in normalized_key:
                character_knowledge.setdefault("system", []).append(text)
            else:
                prop_states.append(text)

    return NextRoundContext(
        summary=(
            f"临时质检上下文：已生成到 EP{current_episode:02d}。"
            if current_episode
            else "临时质检上下文：暂无已生成集。"
        ),
        current_episode=current_episode,
        open_hooks=open_hooks,
        forbidden_reveals=(
            previous_context.forbidden_reveals if previous_context else []
        ),
        character_knowledge=character_knowledge,
        relationship_changes=relationship_changes,
        prop_states=prop_states,
        foreshadowing_ledger=foreshadowing_ledger,
    )


@dataclass
class RoundPipeline:
    llm: JsonLLM
    store: ProjectStore

    def run(
        self,
        *,
        project_id: str,
        round_number: int,
        source_text: str,
        previous_context: NextRoundContext | None = None,
        target_episode_count: int | None = None,
        episodes_per_round: int | str | None = None,
        generation_variant: GenerationVariant | str = GenerationVariant.DRAMA_ENGINE_FIRST,
        repair_budget: str | None = None,
        methodology_cards_path: Path | str | None = None,
    ) -> RoundResult:
        if not source_text.strip():
            raise EmptySourceError("source_text is empty")
        generation_variant = GenerationVariant(generation_variant)
        resolved_episodes_per_round = normalize_episodes_per_round(episodes_per_round)
        resolved_repair_budget = normalize_repair_budget(repair_budget)
        effective_repair_budget = resolved_repair_budget
        stages: list[PipelineStageMetric] = []
        pipeline_start = monotonic()
        tracked_llm: InstrumentedJsonLLM
        runtime_methodology_cards: list[str] = []
        light_source_cost_control = False
        expected_manifest = build_run_manifest(
            project_id=project_id,
            round_number=round_number,
            source_text=source_text,
            target_episode_count=target_episode_count,
            episodes_per_round=resolved_episodes_per_round,
            generation_variant=generation_variant,
            repair_budget=resolved_repair_budget,
            llm=self.llm,
            methodology_cards_path=methodology_cards_path,
        )

        def load_persisted_episode_baselines() -> dict[int, EpisodeScript]:
            round_dir = self.store.project_dir / f"round_{round_number:03d}"
            manifest_path = round_dir / "run_manifest.json"
            if not manifest_path.exists():
                return {}
            try:
                previous_manifest = json.loads(
                    manifest_path.read_text(encoding="utf-8")
                )
            except (json.JSONDecodeError, OSError):
                return {}
            if (
                previous_manifest.get("project_id") != project_id
                or previous_manifest.get("source_sha256")
                != expected_manifest.get("source_sha256")
            ):
                return {}

            baselines: dict[int, EpisodeScript] = {}
            for path in sorted(round_dir.glob("episode_[0-9][0-9][0-9].json")):
                try:
                    episode = EpisodeScript.model_validate_json(
                        path.read_text(encoding="utf-8")
                    )
                except (OSError, ValueError):
                    continue
                baselines[episode.episode] = episode
            return baselines

        persisted_episode_baselines = load_persisted_episode_baselines()
        should_trace_prompts = prompt_trace_enabled() or experiment_mode_enabled()
        prompt_trace_entries: list[dict[str, object]] = []
        raw_trace_entries: list[dict[str, object]] = []

        def write_run_manifest(cache_status: str, reason: str | None = None) -> None:
            self.store.write_text_artifact(
                round_number,
                "run_manifest.json",
                json.dumps(
                    {
                        **expected_manifest,
                        "cache_status": cache_status,
                        "cache_status_reason": reason,
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
            )

        def cached_manifest_status() -> tuple[bool, str]:
            path = self.store.project_dir / f"round_{round_number:03d}" / "run_manifest.json"
            if experiment_mode_enabled():
                return False, "experiment mode disables artifact resume"
            if not resume_artifacts_enabled():
                return False, "NOVEL_DRAMA_RESUME_ARTIFACTS disabled"
            if not path.exists():
                return False, "run_manifest.json missing"
            try:
                raw_manifest = json.loads(path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                return False, "run_manifest.json is invalid JSON"
            if raw_manifest.get("cache_fingerprint") != expected_manifest["cache_fingerprint"]:
                return False, "run_manifest cache fingerprint mismatch"
            return True, "run_manifest cache fingerprint matched"

        def runtime_report() -> RuntimeReport:
            return RuntimeReport(
                generation_variant=generation_variant,
                repair_budget=effective_repair_budget,
                llm_model=getattr(self.llm, "_model", None) or os.environ.get("OPENAI_MODEL"),
                total_duration_ms=elapsed_ms(pipeline_start),
                stages=stages,
                llm_calls=tracked_llm.snapshot_calls(),
                methodology_cards=runtime_methodology_cards,
            )

        def write_runtime_report() -> RuntimeReport:
            report = runtime_report()
            self.store.write_round_artifact(round_number, "runtime_report", report)
            return report

        def write_prompt_trace(entry: dict[str, object]) -> None:
            prompt_trace_entries.append(entry)
            self.store.write_text_artifact(
                round_number,
                "prompt_trace.json",
                json.dumps(prompt_trace_entries, ensure_ascii=False, indent=2),
            )

        def write_raw_trace(entry: dict[str, object]) -> None:
            raw_trace_entries.append(entry)
            self.store.write_text_artifact(
                round_number,
                "raw_llm_output.jsonl",
                "\n".join(
                    json.dumps(item, ensure_ascii=False, default=str)
                    for item in raw_trace_entries
                )
                + "\n",
            )

        def write_trace_analysis() -> None:
            report = analyze_round_trace_artifacts(
                self.store.project_dir / f"round_{round_number:03d}",
                round_number=round_number,
            )
            self.store.write_text_artifact(
                round_number,
                "prompt_trace_analysis.json",
                report.model_dump_json(indent=2),
            )
            self.store.write_text_artifact(
                round_number,
                "prompt_trace_analysis.md",
                render_prompt_trace_analysis(report),
            )

        tracked_llm = InstrumentedJsonLLM(
            self.llm,
            on_update=write_runtime_report,
            on_prompt=write_prompt_trace if should_trace_prompts else None,
            on_raw=write_raw_trace if raw_output_trace_enabled() else None,
        )
        should_resume_artifacts, resume_reason = cached_manifest_status()
        should_reuse_prior_round_artifacts = (
            reuse_prior_round_artifacts_enabled() and not experiment_mode_enabled()
        )
        write_run_manifest(
            "resume_enabled" if should_resume_artifacts else "resume_disabled",
            resume_reason,
        )
        if should_resume_artifacts:
            cached_result = self.store.read_round_artifact(
                round_number,
                "round_result",
                RoundResult,
            )
            if cached_result is not None:
                write_run_manifest("round_result_cache_hit", resume_reason)
                write_trace_analysis()
                return cached_result

        def repair_instruction_for_episode(
            episode_number: int,
            existing_episode,
            base_instruction: str,
        ) -> str:
            if existing_episode is None:
                return base_instruction
            return episode_repair_instruction(
                existing_episode,
                base_instruction,
                allow_full_rewrite=False,
            )

        def write_episode_artifact(episode: EpisodeScript) -> None:
            self.store.write_round_artifact(
                round_number,
                f"episode_{episode.episode:03d}",
                episode,
            )

        def run_stage(name: str, fn: Callable[[], T]) -> T:
            tracked_llm.current_stage = name
            stage_start = monotonic()
            try:
                result = fn()
            except Exception as exc:
                stages.append(
                    PipelineStageMetric(
                        name=name,
                        duration_ms=elapsed_ms(stage_start),
                        status="failed",
                        error=str(exc),
                    )
                )
                write_runtime_report()
                raise
            stages.append(
                PipelineStageMetric(
                    name=name,
                    duration_ms=elapsed_ms(stage_start),
                    status="succeeded",
                )
            )
            write_runtime_report()
            return result

        def read_cached_artifact(name: str, model_type: type[T]) -> T | None:
            if not should_resume_artifacts:
                return None
            return self.store.read_round_artifact(round_number, name, model_type)

        def read_prior_round_artifact(name: str, model_type: type[T]) -> T | None:
            if not should_reuse_prior_round_artifacts:
                return None
            prior_round_numbers = [
                candidate
                for candidate in self.store.existing_round_numbers()
                if candidate < round_number
            ]
            for prior_round_number in reversed(prior_round_numbers):
                if not prior_run_manifest_compatible(prior_round_number):
                    continue
                artifact = self.store.read_round_artifact(
                    prior_round_number,
                    name,
                    model_type,
                )
                if artifact is not None:
                    return artifact
            return None

        def prior_run_manifest_compatible(prior_round_number: int) -> bool:
            path = self.store.project_dir / f"round_{prior_round_number:03d}" / "run_manifest.json"
            if not path.exists():
                return False
            try:
                prior_manifest = json.loads(path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                return False

            # Prior-round artifacts such as Story Bible represent story facts, not
            # an exact replay cache. Code fingerprints, provider env, repair
            # budgets, and generation variants are allowed to change without
            # invalidating reusable source-grounded planning assets.
            comparable_keys = (
                "schema_version",
                "project_id",
                "source_sha256",
                "source_chars",
                "target_episode_count",
            )
            return all(
                prior_manifest.get(key) == expected_manifest.get(key)
                for key in comparable_keys
            )

        def record_cached_stage(name: str) -> None:
            stages.append(
                PipelineStageMetric(
                    name=name,
                    duration_ms=0,
                    status="cached",
                )
            )
            write_runtime_report()

        def record_skipped_stage(name: str, reason: str | None = None) -> None:
            stages.append(
                PipelineStageMetric(
                    name=name,
                    duration_ms=0,
                    status="skipped",
                    error=reason,
                )
            )
            write_runtime_report()

        def cached_stage(
            name: str,
            artifact_name: str,
            model_type: type[T],
            fn: Callable[[], T],
        ) -> T:
            cached = read_cached_artifact(artifact_name, model_type)
            if cached is not None:
                record_cached_stage(name)
                return cached
            result = run_stage(name, fn)
            self.store.write_round_artifact(round_number, artifact_name, result)
            return result

        source_analysis = cached_stage(
            "source_analysis",
            "source_analysis",
            SourceAnalysis,
            lambda: SourceParser(tracked_llm).run(source_text),
        )

        viral_asset_report = None
        if variant_uses_sop_stack(generation_variant):
            viral_asset_report = cached_stage(
                "viral_asset_report",
                "viral_asset_report",
                ViralAssetReport,
                lambda: ViralAssetExtractor(tracked_llm).run(
                    source_text,
                    source_analysis,
                    target_episode_count,
                ),
            )

        source_strength_profile = cached_stage(
            "source_strength_profile",
            "source_strength_profile",
            SourceStrengthProfile,
            lambda: classify_source_strength(source_analysis, viral_asset_report),
        )
        light_source_cost_control = strong_source_light_adaptation(
            source_strength_profile,
            generation_variant,
        )
        self.store.write_text_artifact(
            round_number,
            "cost_control_decision.json",
            json.dumps(
                {
                    "enabled": source_strength_cost_control_enabled(),
                    "mode": "strong_source_light_adaptation"
                    if light_source_cost_control
                    else "standard",
                    "source_strength_level": source_strength_profile.overall_level.value,
                    "adaptation_intensity": source_strength_profile.recommended_intensity.value,
                    "requested_repair_budget": resolved_repair_budget,
                    "effective_repair_budget": effective_repair_budget,
                    "reason": (
                        "强原文本身具备钩子/冲突/名场面，禁止默认大改和无目标返工。"
                        if light_source_cost_control
                        else "按标准修复预算执行。"
                    ),
                },
                ensure_ascii=False,
                indent=2,
            ),
        )
        methodology_cards = load_methodology_cards(
            Path(methodology_cards_path) if methodology_cards_path else None
        )
        methodology_channel = viral_asset_report.channel if viral_asset_report else "mixed"
        methodology_genres = viral_asset_report.genre_tags if viral_asset_report else ["unknown"]

        def methodology_context_for(stage: MethodologyStage) -> MethodologyContext:
            return retrieve_methodology_context(
                methodology_cards,
                stage=stage,
                channel=methodology_channel,
                genre_tags=methodology_genres,
                source_strength_profile=source_strength_profile,
            )

        cached_episode_context = read_cached_artifact("episode_context", EpisodeContext)
        if cached_episode_context is not None:
            record_cached_stage("episode_context")
            episode_context = cached_episode_context
        else:
            episode_context = run_stage(
                "episode_context",
                lambda: EpisodeContextResolver(tracked_llm).run(
                    source_text,
                    previous_context,
                    source_analysis,
                    round_number,
                    target_episode_count,
                    resolved_episodes_per_round,
                    viral_asset_report=viral_asset_report,
                    methodology_context=methodology_context_for(
                        MethodologyStage.EPISODE_CONTEXT,
                    ),
                ),
            )
            episode_context = run_stage(
                "normalize_episode_context",
                lambda: normalize_episode_context_range(
                    episode_context,
                    round_number=round_number,
                    previous_context=previous_context,
                    target_episode_count=target_episode_count,
                    episodes_per_round=resolved_episodes_per_round,
                ),
            )
            self.store.write_round_artifact(round_number, "episode_context", episode_context)

        cached_story_bible = read_cached_artifact("story_bible", StoryBible)
        if cached_story_bible is not None:
            record_cached_stage("story_bible")
            story_bible = cached_story_bible
        else:
            prior_story_bible = read_prior_round_artifact("story_bible", StoryBible)
            if prior_story_bible is not None:
                record_cached_stage("story_bible")
                story_bible = prior_story_bible
                self.store.write_round_artifact(round_number, "story_bible", story_bible)
            else:
                story_bible = run_stage(
                    "story_bible",
                    lambda: InternalBibleBuilder(tracked_llm).run(
                        source_text,
                        source_analysis,
                        episode_context,
                        viral_asset_report=viral_asset_report,
                        methodology_context=methodology_context_for(
                            MethodologyStage.STORY_BIBLE,
                        ),
                    ),
                )
                self.store.write_round_artifact(round_number, "story_bible", story_bible)

        series_structure_plan = None
        if viral_asset_report is not None:
            cached_series_structure_plan = read_cached_artifact(
                "series_structure_plan",
                SeriesStructurePlan,
            )
            if cached_series_structure_plan is not None:
                record_cached_stage("series_structure_plan")
                series_structure_plan = cached_series_structure_plan
            else:
                series_structure_plan = run_stage(
                    "series_structure_plan",
                    lambda: SeriesStructurePlanner(tracked_llm).run(
                        source_text,
                        source_analysis,
                        episode_context,
                        story_bible,
                        viral_asset_report,
                        previous_context,
                        target_episode_count,
                        methodology_context=methodology_context_for(
                            MethodologyStage.SERIES_STRUCTURE,
                        ),
                    ),
                )
                series_structure_plan = run_stage(
                    "normalize_series_structure_plan",
                    lambda: series_structure_plan.model_copy(
                        update={
                            "target_episode_count": target_episode_count,
                            "target_episode_range": episode_context.target_episode_range,
                        },
                    ),
                )
                self.store.write_round_artifact(
                    round_number,
                    "series_structure_plan",
                    series_structure_plan,
                )

        episode_source_packets = cached_stage(
            "episode_source_packets",
            "episode_source_packets",
            EpisodeSourcePackets,
            lambda: build_episode_source_packets(
                source_text=source_text,
                episode_context=episode_context,
                series_structure_plan=series_structure_plan,
                target_episode_count=target_episode_count,
            ),
        )
        source_fact_ledger = cached_stage(
            "source_fact_ledger",
            "source_fact_ledger",
            SourceFactLedger,
            lambda: build_source_fact_ledger(source_text, episode_source_packets),
        )
        source_packet_confidence_report = run_stage(
            "source_packet_confidence",
            lambda: build_source_packet_confidence_report(
                episode_source_packets,
                source_text=source_text,
                target_episode_count=target_episode_count,
            ),
        )
        self.store.write_round_artifact(
            round_number,
            "source_packet_confidence_report",
            source_packet_confidence_report,
        )
        self.store.write_text_artifact(
            round_number,
            "source_packet_confidence_report.md",
            render_source_packet_confidence_report(source_packet_confidence_report),
        )
        run_stage(
            "ensure_source_packet_confidence",
            lambda: ensure_source_packet_confidence(source_packet_confidence_report),
        )
        source_bible_conflicts = run_stage(
            "source_bible_conflicts",
            lambda: story_bible_source_packet_conflicts(
                story_bible,
                episode_source_packets,
            ),
        )
        if source_bible_conflicts:
            self.store.write_text_artifact(
                round_number,
                "source_bible_conflicts.md",
                "\n".join(
                    [
                        "# Source/Bible Contract Conflicts",
                        "",
                        "以下 Story Bible forbidden_changes 与当前集 source packet 必留资产冲突，"
                        "本轮按原文 source packet 优先处理，并从 Bible 禁止项中移除：",
                        "",
                        *[f"- {rule}" for rule in source_bible_conflicts],
                    ]
                ),
            )
            story_bible = run_stage(
                "normalize_story_bible_against_source_packets",
                lambda: normalize_story_bible_against_source_packets(
                    story_bible,
                    episode_source_packets,
                ),
            )
            self.store.write_round_artifact(round_number, "story_bible", story_bible)

        production_spec = cached_stage(
            "production_spec",
            "production_spec",
            ProductionSpec,
            build_production_spec,
        )
        source_annotation = cached_stage(
            "source_annotation",
            "source_annotation",
            SourceAnnotation,
            lambda: build_source_annotation(
                source_text=source_text,
                source_analysis=source_analysis,
                episode_context=episode_context,
                story_bible=story_bible,
                episode_source_packets=episode_source_packets,
            ),
        )
        episode_cut_table = cached_stage(
            "episode_cut_table",
            "episode_cut_table",
            EpisodeCutTable,
            lambda: build_episode_cut_table(
                episode_context=episode_context,
                episode_source_packets=episode_source_packets,
            ),
        )

        episode_plan = None
        if variant_uses_episode_plan(generation_variant):
            cached_episode_plan = read_cached_artifact("episode_plan", EpisodePlan)
            if cached_episode_plan is not None:
                record_cached_stage("episode_plan")
                episode_plan = cached_episode_plan
            else:
                episode_plan = run_stage(
                    "episode_plan",
                    lambda: EpisodeBeatPlanner(tracked_llm).run(
                        source_text,
                        source_analysis,
                        episode_context,
                        story_bible,
                        previous_context,
                        viral_asset_report=viral_asset_report,
                        series_structure_plan=series_structure_plan,
                        methodology_context=methodology_context_for(
                            MethodologyStage.EPISODE_PLAN,
                        ),
                    ),
                )
                episode_plan = run_stage(
                    "normalize_episode_plan",
                    lambda: episode_plan.model_copy(
                        update={
                            "variant": generation_variant,
                            "target_episode_range": episode_context.target_episode_range,
                        },
                    ),
                )
                self.store.write_round_artifact(round_number, "episode_plan", episode_plan)

        methodology_context = cached_stage(
            "methodology_context",
            "methodology_context",
            MethodologyContext,
            lambda: methodology_context_for(MethodologyStage.SCRIPT_GENERATION),
        )
        runtime_methodology_cards = [card.name for card in methodology_context.cards]
        script_methodology_context: MethodologyContext | None = None
        write_runtime_report()

        if episode_plan is not None:
            episode_plan = run_stage(
                "sanitize_episode_plan",
                lambda: sanitize_episode_plan_against_source_packets(
                    episode_plan,
                    episode_source_packets,
                ),
            )
            self.store.write_round_artifact(
                round_number,
                "episode_plan_sanitized",
                episode_plan,
            )
            episode_plan = run_stage(
                "bind_episode_plan_to_facts",
                lambda: bind_episode_plan_to_facts(
                    episode_plan,
                    episode_source_packets,
                    source_fact_ledger,
                ),
            )
            self.store.write_round_artifact(
                round_number,
                "episode_plan_fact_bound",
                episode_plan,
            )

        def source_evidence_score(episode: EpisodeScript) -> int:
            packet = packet_for_episode(
                episode_source_packets,
                episode.episode,
            )
            if packet is None:
                return 0
            report = build_source_evidence_report(
                ScriptBatch(episodes=[episode]),
                episode_source_packets=EpisodeSourcePackets(packets=[packet]),
            )
            return report.coverage_score

        def revision_regression_reasons(
            current_episode: EpisodeScript,
            candidate_episode: EpisodeScript,
        ) -> list[str]:
            source_gain = max(
                0,
                source_evidence_score(candidate_episode)
                - source_evidence_score(current_episode),
            )
            return episode_revision_regression_reasons(
                current_episode,
                candidate_episode,
                source_evidence_gain=source_gain,
            )

        script_generator = ScriptBatchGenerator(
            tracked_llm,
            episode_writer=(
                None if persisted_episode_baselines else write_episode_artifact
            ),
        )

        def generate_script_batch() -> ScriptBatch:
            candidate_batch = (
                script_generator.run_episode_batch(
                    source_text,
                    source_analysis,
                    episode_context,
                    story_bible,
                    previous_context,
                    "",
                    episode_plan=episode_plan,
                    viral_asset_report=viral_asset_report,
                    series_structure_plan=series_structure_plan,
                    methodology_context=script_methodology_context,
                    episode_source_packets=episode_source_packets,
                    source_fact_ledger=source_fact_ledger,
                    production_spec=production_spec,
                    source_annotation=source_annotation,
                    episode_cut_table=episode_cut_table,
                )
                if use_episode_first_script_generation(
                    getattr(self.llm, "_model", None)
                )
                else script_generator.run(
                    source_text,
                    source_analysis,
                    episode_context,
                    story_bible,
                    previous_context,
                    "",
                    round_number,
                    target_episode_count,
                    episode_plan=episode_plan,
                    viral_asset_report=viral_asset_report,
                    series_structure_plan=series_structure_plan,
                    methodology_context=script_methodology_context,
                    episode_source_packets=episode_source_packets,
                    source_fact_ledger=source_fact_ledger,
                    production_spec=production_spec,
                    source_annotation=source_annotation,
                    episode_cut_table=episode_cut_table,
                )
            )
            if not persisted_episode_baselines:
                return candidate_batch

            selected_episodes: list[EpisodeScript] = []
            rejection_lines: list[str] = []
            for candidate_episode in candidate_batch.episodes:
                baseline = persisted_episode_baselines.get(candidate_episode.episode)
                regression_reasons = (
                    revision_regression_reasons(
                        baseline,
                        candidate_episode,
                    )
                    if baseline is not None
                    else []
                )
                selected_episode = baseline if regression_reasons else candidate_episode
                if regression_reasons:
                    rejection_lines.append(
                        f"script_batch EP{candidate_episode.episode:02d}: "
                        + "; ".join(regression_reasons)
                    )
                write_episode_artifact(selected_episode)
                selected_episodes.append(selected_episode)
            if rejection_lines:
                self.store.write_text_artifact(
                    round_number,
                    "script_batch_generation_rejections.md",
                    "\n".join(rejection_lines),
                )
            return candidate_batch.model_copy(update={"episodes": selected_episodes})

        script_batch = cached_stage(
            "script_batch",
            "script_batch",
            ScriptBatch,
            generate_script_batch,
        )
        quality_methodology_context = methodology_context_for(MethodologyStage.QUALITY_GATE)

        checker = ContinuityBoomChecker(tracked_llm)
        quality_report = run_stage(
            "quality_report",
            lambda: checker.run(
                source_analysis,
                episode_context,
                story_bible,
                script_batch,
                previous_context,
                viral_asset_report=viral_asset_report,
                series_structure_plan=series_structure_plan,
                episode_plan=episode_plan,
                methodology_context=quality_methodology_context,
            ),
        )

        def apply_local_quality_gates(
            current_script_batch: ScriptBatch,
            current_quality_report: QualityReport,
            artifact_prefix: str,
        ) -> QualityReport:
            provisional_context = provisional_next_round_context(
                current_script_batch,
                previous_context,
            )
            local_adaptation_quality = run_stage(
                f"{artifact_prefix}_adaptation_quality",
                lambda: build_adaptation_quality_report(
                    source_text=source_text,
                    source_analysis=source_analysis,
                    episode_context=episode_context,
                    story_bible=story_bible,
                    script_batch=current_script_batch,
                    next_round_context=provisional_context,
                    previous_context=previous_context,
                    viral_asset_report=viral_asset_report,
                    episode_plan=episode_plan,
                    series_structure_plan=series_structure_plan,
                    episode_source_packets=episode_source_packets,
                ),
            )
            self.store.write_round_artifact(
                round_number,
                f"{artifact_prefix}_adaptation_quality",
                local_adaptation_quality,
            )
            local_methodology_quality = run_stage(
                f"{artifact_prefix}_methodology_quality",
                lambda: build_methodology_quality_report(
                    source_analysis=source_analysis,
                    script_batch=current_script_batch,
                    source_strength_profile=source_strength_profile,
                    methodology_context=quality_methodology_context,
                    viral_asset_report=viral_asset_report,
                ),
            )
            self.store.write_round_artifact(
                round_number,
                f"{artifact_prefix}_methodology_quality",
                local_methodology_quality,
            )
            local_novelty_report = run_stage(
                f"{artifact_prefix}_script_novelty",
                lambda: build_script_novelty_report(current_script_batch),
            )
            self.store.write_round_artifact(
                round_number,
                f"{artifact_prefix}_script_novelty_report",
                local_novelty_report,
            )
            self.store.write_text_artifact(
                round_number,
                f"{artifact_prefix}_script_novelty_report.md",
                render_script_novelty_report(local_novelty_report),
            )
            local_source_evidence_report = run_stage(
                f"{artifact_prefix}_source_evidence",
                lambda: build_source_evidence_report(
                    current_script_batch,
                    episode_source_packets=episode_source_packets,
                    episode_context=episode_context,
                ),
            )
            self.store.write_round_artifact(
                round_number,
                f"{artifact_prefix}_source_evidence_report",
                local_source_evidence_report,
            )
            self.store.write_text_artifact(
                round_number,
                f"{artifact_prefix}_source_evidence_report.md",
                render_source_evidence_report(local_source_evidence_report),
            )
            local_drama_quality_report = run_stage(
                f"{artifact_prefix}_drama_quality",
                lambda: build_drama_quality_report(
                    script_batch=current_script_batch,
                    quality_report=current_quality_report,
                    adaptation_quality_report=local_adaptation_quality,
                ),
            )
            self.store.write_round_artifact(
                round_number,
                f"{artifact_prefix}_drama_quality_report",
                local_drama_quality_report,
            )
            self.store.write_text_artifact(
                round_number,
                f"{artifact_prefix}_drama_quality_report.md",
                render_drama_quality_report(local_drama_quality_report),
            )
            gated_report = run_stage(
                f"{artifact_prefix}_merge_adaptation_quality",
                lambda: merge_adaptation_quality_into_report(
                    current_quality_report,
                    local_adaptation_quality,
                ),
            )
            gated_report = run_stage(
                f"{artifact_prefix}_merge_methodology_quality",
                lambda: merge_methodology_quality_into_report(
                    gated_report,
                    local_methodology_quality,
                ),
            )
            gated_report = run_stage(
                f"{artifact_prefix}_merge_script_novelty",
                lambda: merge_script_novelty_into_quality_report(
                    gated_report,
                    local_novelty_report,
                ),
            )
            gated_report = run_stage(
                f"{artifact_prefix}_merge_source_evidence",
                lambda: merge_source_evidence_into_quality_report(
                    gated_report,
                    local_source_evidence_report,
                ),
            )
            gated_report = run_stage(
                f"{artifact_prefix}_merge_drama_quality",
                lambda: merge_drama_quality_into_report(
                    gated_report,
                    local_drama_quality_report,
                ),
            )
            return run_stage(
                f"{artifact_prefix}_apply_quality_policy",
                lambda: apply_quality_policy(gated_report),
            )

        def persist_quality_decision(
            current_quality_report: QualityReport,
            artifact_prefix: str,
        ):
            valid_episode_numbers = expected_episode_numbers(
                round_number=round_number,
                previous_context=previous_context,
                target_episode_count=target_episode_count,
                episodes_per_round=resolved_episodes_per_round,
            )
            decision = decide_quality(
                [
                    *current_quality_report.blocking_issues,
                    *current_quality_report.advisory_warnings,
                ],
                valid_episode_numbers=valid_episode_numbers,
            )
            self.store.write_round_artifact(
                round_number,
                f"{artifact_prefix}_quality_decision",
                decision,
            )
            if artifact_prefix == "final":
                self.store.write_round_artifact(
                    round_number,
                    "quality_decision",
                    decision,
                )
            return decision

        def finalize_terminal_quality(
            current_quality_report: QualityReport,
            artifact_prefix: str,
        ) -> QualityReport:
            normalized = run_stage(
                f"{artifact_prefix}_apply_quality_policy",
                lambda: apply_quality_policy(current_quality_report),
            )
            if normalized.status != QualityStatus.NEEDS_REWRITE:
                return normalized
            return run_stage(
                f"{artifact_prefix}_mark_human_review",
                lambda: normalized.model_copy(
                    update={"status": QualityStatus.NEEDS_HUMAN_REVIEW}
                ),
            )

        quality_report = apply_local_quality_gates(
            script_batch,
            quality_report,
            "pre_repair",
        )
        pre_repair_quality_decision = persist_quality_decision(
            quality_report,
            "pre_repair",
        )

        def run_episode_repair_cycle(
            current_script_batch: ScriptBatch,
            current_quality_report: QualityReport,
            current_quality_decision,
        ) -> tuple[ScriptBatch, QualityReport]:
            self.store.write_round_artifact(
                round_number,
                "quality_report_before_episode_repair",
                current_quality_report,
            )
            current_episodes = {
                episode.episode: episode for episode in current_script_batch.episodes
            }
            current_episode_repair_packet_records: list[dict[str, object]] = []
            repair_patch_records: list[dict[str, object]] = []
            episode_revision_rejections: list[str] = []
            episode_repair_diffs: list[dict[str, object]] = []
            repair_script_generator = ScriptBatchGenerator(tracked_llm)

            def record_episode_repair_diff(
                current_episode: EpisodeScript,
                candidate_episode: EpisodeScript,
                *,
                accepted: bool,
                reasons: list[str],
            ) -> None:
                episode_repair_diffs.append(
                    {
                        **episode_repair_diff(current_episode, candidate_episode),
                        "accepted": accepted,
                        "rejection_reasons": reasons,
                    }
                )
                self.store.write_text_artifact(
                    round_number,
                    "repair_diff.json",
                    json.dumps(
                        episode_repair_diffs,
                        ensure_ascii=False,
                        indent=2,
                    ),
                )

            def revision_or_current(
                stage_name: str,
                current_episode: EpisodeScript | None,
                candidate_episode: EpisodeScript,
                repair_packet=None,
            ) -> EpisodeScript:
                if current_episode is None:
                    write_episode_artifact(candidate_episode)
                    return candidate_episode
                regression_reasons = [
                    *revision_regression_reasons(
                        current_episode,
                        candidate_episode,
                    ),
                    *episode_repair_scope_regression_reasons(
                        current_episode,
                        candidate_episode,
                        repair_packet,
                    ),
                ]
                if regression_reasons:
                    record_episode_repair_diff(
                        current_episode,
                        candidate_episode,
                        accepted=False,
                        reasons=regression_reasons,
                    )
                    episode_revision_rejections.append(
                        f"{stage_name} EP{current_episode.episode:02d}: "
                        + "; ".join(regression_reasons)
                    )
                    self.store.write_text_artifact(
                        round_number,
                        "episode_revision_rejections.md",
                        "\n".join(episode_revision_rejections),
                    )
                    return current_episode
                record_episode_repair_diff(
                    current_episode,
                    candidate_episode,
                    accepted=True,
                    reasons=[],
                )
                write_episode_artifact(candidate_episode)
                return candidate_episode

            def record_current_episode_repair_packet(packet) -> None:
                current_episode_repair_packet_records.append(
                    packet.model_dump(mode="json")
                )
                repair_patch_records.append(
                    {
                        "episode": packet.episode,
                        "repair_mode": packet.repair_mode,
                        "patches": [
                            repair_patch.model_dump(mode="json")
                            for repair_patch in packet.repair_patches
                        ],
                    }
                )
                self.store.write_text_artifact(
                    round_number,
                    "current_episode_repair_packets.json",
                    json.dumps(
                        current_episode_repair_packet_records,
                        ensure_ascii=False,
                        indent=2,
                    ),
                )
                self.store.write_text_artifact(
                    round_number,
                    "repair_patches.json",
                    json.dumps(
                        repair_patch_records,
                        ensure_ascii=False,
                        indent=2,
                    ),
                )

            episode_numbers = expected_episode_numbers(
                round_number=round_number,
                previous_context=previous_context,
                target_episode_count=target_episode_count,
                episodes_per_round=resolved_episodes_per_round,
            )
            cached_repaired_batch = read_cached_artifact(
                "script_batch_episode_repair",
                ScriptBatch,
            )
            if cached_repaired_batch is not None:
                record_cached_stage("episode_repair")
                repaired_batch = cached_repaired_batch
            else:
                local_repair_targets = {
                    episode.episode
                    for episode in current_script_batch.episodes
                    if episode.episode in episode_numbers
                    and partition_quality_issues(
                        episode_quality_warnings(episode)
                    ).hard_issues
                }
                report_repair_targets = set(current_quality_decision.repair_targets)
                if (
                    not report_repair_targets
                    and len(episode_numbers) == 1
                    and current_quality_report.blocking_issues
                ):
                    # A global hard finding is still precisely localizable when
                    # this round contains exactly one episode.
                    report_repair_targets = set(episode_numbers)
                missing_episode_targets = {
                    episode_number
                    for episode_number in episode_numbers
                    if episode_number not in current_episodes
                }
                repair_targets = (
                    local_repair_targets
                    | report_repair_targets
                    | missing_episode_targets
                )

                self.store.write_text_artifact(
                    round_number,
                    "episode_repair_targets.md",
                    "\n".join(
                        [
                            f"EP{episode_number:02d}"
                            for episode_number in sorted(repair_targets)
                        ]
                        or [
                            "none",
                            "全局质检未点名具体集数，本轮未触发逐集重写。",
                        ]
                    ),
                )
                if repair_targets:
                    def handoff_changed(
                        before: EpisodeScript | None,
                        after: EpisodeScript,
                    ) -> bool:
                        before_handoff = handoff_from_episode(before)
                        after_handoff = handoff_from_episode(after)
                        if before_handoff is None or after_handoff is None:
                            return before_handoff != after_handoff
                        return (
                            before_handoff.previous_cliffhanger
                            != after_handoff.previous_cliffhanger
                            or before_handoff.previous_final_lines
                            != after_handoff.previous_final_lines
                            or before_handoff.previous_state_update
                            != after_handoff.previous_state_update
                        )

                    def repair_episode_sequence() -> list[EpisodeScript]:
                        dynamic_repair_targets = set(repair_targets)
                        handoff_boundary_targets: set[int] = set()
                        repaired: list[EpisodeScript] = []
                        for episode_number in episode_numbers:
                            previous_episode = repaired[-1] if repaired else None
                            if episode_number in dynamic_repair_targets:
                                existing_episode = current_episodes.get(episode_number)
                                if episode_number in handoff_boundary_targets:
                                    episode_repair_context = (
                                        "跨集承接更新：上一集结尾已发生变更。"
                                        "只修本集第一场前 8-12 行和必要相邻行，使其承接"
                                        " previous_episode_handoff；后续场次、人物动机、事件顺序、"
                                        "本集结尾与既有原文资产必须保持不变。"
                                    )
                                else:
                                    episode_repair_context = quality_instruction_for_episode(
                                        current_quality_report,
                                        episode_number,
                                        include_unscoped=len(episode_numbers) == 1,
                                    )
                                current_repair_packet = (
                                    build_current_episode_repair_packet(
                                        existing_episode,
                                        episode_repair_context,
                                        allow_full_rewrite=False,
                                        source_evidence_targets=(
                                            source_evidence_targets_for_episode(
                                                current_quality_report,
                                                episode_number,
                                            )
                                        ),
                                    )
                                    if existing_episode is not None
                                    else None
                                )
                                if current_repair_packet is not None:
                                    record_current_episode_repair_packet(
                                        current_repair_packet,
                                    )
                                candidate_episode = repair_script_generator.run_episode(
                                    source_text,
                                    source_analysis,
                                    episode_context,
                                    story_bible,
                                    previous_context,
                                    existing_episode,
                                    episode_number,
                                    repair_instruction_for_episode(
                                        episode_number,
                                        existing_episode,
                                        episode_repair_context,
                                    ),
                                    episode_plan=episode_plan,
                                    viral_asset_report=viral_asset_report,
                                    series_structure_plan=series_structure_plan,
                                    methodology_context=script_methodology_context,
                                    episode_source_packet=packet_for_episode(
                                        episode_source_packets,
                                        episode_number,
                                    ),
                                    source_fact_ledger=source_fact_ledger,
                                    previous_episode_handoff=handoff_from_episode(
                                        previous_episode,
                                    ),
                                    current_episode_repair_packet=current_repair_packet,
                                    production_spec=production_spec,
                                    source_annotation=source_annotation,
                                    episode_cut_table=episode_cut_table,
                                )
                                episode = revision_or_current(
                                    "episode_repair",
                                    existing_episode,
                                    candidate_episode,
                                    current_repair_packet,
                                )
                                if (
                                    not partition_quality_issues(
                                        episode_quality_warnings(episode)
                                    ).hard_issues
                                    and handoff_changed(
                                        current_episodes.get(episode_number),
                                        episode,
                                    )
                                    and episode_number + 1 in episode_numbers
                                ):
                                    next_episode_number = episode_number + 1
                                    if next_episode_number not in dynamic_repair_targets:
                                        dynamic_repair_targets.add(next_episode_number)
                                        handoff_boundary_targets.add(next_episode_number)
                            else:
                                episode = current_episodes[episode_number]
                            repaired.append(episode)
                        return repaired

                    repaired_episodes = run_stage(
                        "episode_repair",
                        repair_episode_sequence,
                    )
                    repaired_batch = run_stage(
                        "apply_episode_repair",
                        lambda: current_script_batch.model_copy(
                            update={"episodes": repaired_episodes},
                        ),
                    )
                else:
                    record_skipped_stage(
                        "episode_repair",
                        "No precisely located hard repair target; keep the draft and require human review.",
                    )
                    repaired_batch = current_script_batch
                    return repaired_batch, current_quality_report.model_copy(
                        update={"status": QualityStatus.NEEDS_HUMAN_REVIEW}
                    )
                self.store.write_round_artifact(
                    round_number,
                    "script_batch_episode_repair",
                    repaired_batch,
                )

            repaired_quality = run_stage(
                "quality_report_after_episode_repair",
                lambda: checker.run(
                    source_analysis,
                    episode_context,
                    story_bible,
                    repaired_batch,
                    previous_context,
                    viral_asset_report=viral_asset_report,
                    series_structure_plan=series_structure_plan,
                    episode_plan=episode_plan,
                    methodology_context=quality_methodology_context,
                ),
            )
            repaired_quality = apply_local_quality_gates(
                repaired_batch,
                repaired_quality,
                "post_episode_repair",
            )
            persist_quality_decision(repaired_quality, "post_episode_repair")
            if repaired_quality.status == QualityStatus.NEEDS_REWRITE:
                repaired_quality = run_stage(
                    "mark_human_review_after_episode_repair",
                    lambda: repaired_quality.model_copy(
                        update={"status": QualityStatus.NEEDS_HUMAN_REVIEW},
                    ),
                )
            return repaired_batch, repaired_quality

        if (
            quality_report.status == QualityStatus.NEEDS_REWRITE
            and effective_repair_budget != RepairBudget.NONE
        ):
            self.store.write_round_artifact(
                round_number,
                "quality_report_before_rewrite",
                quality_report,
            )
            script_batch, quality_report = run_episode_repair_cycle(
                script_batch,
                quality_report,
                pre_repair_quality_decision,
            )
        elif quality_report.status == QualityStatus.NEEDS_REWRITE:
            quality_report = run_stage(
                "mark_human_review_without_repair",
                lambda: quality_report.model_copy(
                    update={"status": QualityStatus.NEEDS_HUMAN_REVIEW},
                ),
            )

        self.store.write_round_artifact(round_number, "quality_report", quality_report)

        # Final gates audit a deterministic candidate. An LLM-written state is not
        # canonical until the script itself has passed every content gate.
        next_round_context = provisional_next_round_context(
            script_batch,
            previous_context,
        )

        adaptation_quality_report = run_stage(
            "adaptation_quality_report",
            lambda: build_adaptation_quality_report(
                source_text=source_text,
                source_analysis=source_analysis,
                episode_context=episode_context,
                story_bible=story_bible,
                script_batch=script_batch,
                next_round_context=next_round_context,
                previous_context=previous_context,
                viral_asset_report=viral_asset_report,
                episode_plan=episode_plan,
                series_structure_plan=series_structure_plan,
                episode_source_packets=episode_source_packets,
            ),
        )
        self.store.write_round_artifact(
            round_number,
            "adaptation_quality_report",
            adaptation_quality_report,
        )
        methodology_quality_report = run_stage(
            "methodology_quality_report",
            lambda: build_methodology_quality_report(
                source_analysis=source_analysis,
                script_batch=script_batch,
                source_strength_profile=source_strength_profile,
                methodology_context=quality_methodology_context,
                viral_asset_report=viral_asset_report,
            ),
        )
        self.store.write_round_artifact(
            round_number,
            "methodology_quality_report",
            methodology_quality_report,
        )
        story_state_ledger = adaptation_quality_report.story_state_ledger
        self.store.write_round_artifact(
            round_number,
            "story_state_ledger",
            story_state_ledger,
        )
        quality_report = run_stage(
            "merge_adaptation_quality",
            lambda: merge_adaptation_quality_into_report(
                quality_report,
                adaptation_quality_report,
            ),
        )
        quality_report = run_stage(
            "merge_methodology_quality",
            lambda: merge_methodology_quality_into_report(
                quality_report,
                methodology_quality_report,
            ),
        )
        drama_quality_report = run_stage(
            "drama_quality_report",
            lambda: build_drama_quality_report(
                script_batch=script_batch,
                quality_report=quality_report,
                adaptation_quality_report=adaptation_quality_report,
            ),
        )
        self.store.write_round_artifact(
            round_number,
            "drama_quality_report",
            drama_quality_report,
        )
        self.store.write_text_artifact(
            round_number,
            "drama_quality_report.md",
            render_drama_quality_report(drama_quality_report),
        )
        quality_report = run_stage(
            "merge_drama_quality",
            lambda: merge_drama_quality_into_report(
                quality_report,
                drama_quality_report,
            ),
        )
        script_novelty_report = run_stage(
            "script_novelty_report",
            lambda: build_script_novelty_report(script_batch),
        )
        self.store.write_round_artifact(
            round_number,
            "script_novelty_report",
            script_novelty_report,
        )
        self.store.write_text_artifact(
            round_number,
            "script_novelty_report.md",
            render_script_novelty_report(script_novelty_report),
        )
        quality_report = run_stage(
            "merge_final_script_novelty",
            lambda: merge_script_novelty_into_quality_report(
                quality_report,
                script_novelty_report,
            ),
        )
        source_evidence_report = run_stage(
            "source_evidence_report",
            lambda: build_source_evidence_report(
                script_batch,
                episode_source_packets=episode_source_packets,
                episode_context=episode_context,
            ),
        )
        self.store.write_round_artifact(
            round_number,
            "source_evidence_report",
            source_evidence_report,
        )
        self.store.write_text_artifact(
            round_number,
            "source_evidence_report.md",
            render_source_evidence_report(source_evidence_report),
        )
        quality_report = run_stage(
            "merge_source_evidence",
            lambda: merge_source_evidence_into_quality_report(
                quality_report,
                source_evidence_report,
            ),
        )
        quality_report = finalize_terminal_quality(
            quality_report,
            "final",
        )
        persist_quality_decision(quality_report, "final")

        if quality_report.status == QualityStatus.USABLE:
            next_round_context = run_stage(
                "next_round_context",
                lambda: StateWriter(tracked_llm).run(
                    source_analysis,
                    episode_context,
                    story_bible,
                    script_batch,
                    quality_report,
                    previous_context,
                    episode_plan=episode_plan,
                    viral_asset_report=viral_asset_report,
                    series_structure_plan=series_structure_plan,
                ),
            )
            adaptation_quality_report = run_stage(
                "state_commit_adaptation_quality",
                lambda: build_adaptation_quality_report(
                    source_text=source_text,
                    source_analysis=source_analysis,
                    episode_context=episode_context,
                    story_bible=story_bible,
                    script_batch=script_batch,
                    next_round_context=next_round_context,
                    previous_context=previous_context,
                    viral_asset_report=viral_asset_report,
                    episode_plan=episode_plan,
                    series_structure_plan=series_structure_plan,
                    episode_source_packets=episode_source_packets,
                ),
            )
            story_state_ledger = adaptation_quality_report.story_state_ledger
            self.store.write_round_artifact(
                round_number,
                "adaptation_quality_report",
                adaptation_quality_report,
            )
            self.store.write_round_artifact(
                round_number,
                "story_state_ledger",
                story_state_ledger,
            )
            quality_report = run_stage(
                "merge_state_commit_quality",
                lambda: merge_adaptation_quality_into_report(
                    quality_report,
                    adaptation_quality_report,
                ),
            )
            quality_report = finalize_terminal_quality(
                quality_report,
                "state_commit",
            )
            persist_quality_decision(quality_report, "final")
        self.store.write_round_artifact(round_number, "quality_report", quality_report)

        final_runtime_report = write_runtime_report()
        result = RoundResult(
            project_id=project_id,
            round_number=round_number,
            source_analysis=source_analysis,
            episode_context=episode_context,
            viral_asset_report=viral_asset_report,
            source_strength_profile=source_strength_profile,
            methodology_context=methodology_context,
            story_bible=story_bible,
            production_spec=production_spec,
            source_annotation=source_annotation,
            episode_cut_table=episode_cut_table,
            series_structure_plan=series_structure_plan,
            episode_plan=episode_plan,
            episode_source_packets=episode_source_packets,
            source_fact_ledger=source_fact_ledger,
            source_packet_confidence_report=source_packet_confidence_report,
            script_batch=script_batch,
            quality_report=quality_report,
            next_round_context=next_round_context,
            adaptation_quality_report=adaptation_quality_report,
            methodology_quality_report=methodology_quality_report,
            drama_quality_report=drama_quality_report,
            script_novelty_report=script_novelty_report,
            source_evidence_report=source_evidence_report,
            story_state_ledger=story_state_ledger,
            runtime_report=final_runtime_report,
        )
        self.store.write_text_artifact(
            round_number,
            "creative_script.md",
            render_creative_round(script_batch),
        )
        self.store.write_text_artifact(
            round_number,
            "shooting_script.md",
            render_shooting_round(script_batch),
        )
        self.store.write_text_artifact(
            round_number,
            "rendered_scripts.md",
            render_round_summary(script_batch, quality_report),
        )
        self.store.write_round_result(result)
        if quality_report.status == QualityStatus.USABLE:
            self.store.write_next_round_context(result)
        write_runtime_report()
        write_run_manifest("completed", "fresh run completed")
        write_trace_analysis()
        return result
