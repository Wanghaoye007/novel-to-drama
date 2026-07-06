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
from novel_drama_engine.models import (
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
    QualityReport,
    QualityStatus,
    RoundResult,
    RuntimeReport,
    ScriptBatch,
    SeriesStructurePlan,
    SourceAnalysis,
    SourceStrengthProfile,
    StoryBible,
    ViralAssetReport,
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
    build_script_novelty_report,
    episode_needs_hook_dialogue_polish,
    episode_quality_warnings,
    episode_repair_instruction,
    hook_dialogue_polish_instruction,
    merge_script_novelty_into_quality_report,
    render_script_novelty_report,
)
from novel_drama_engine.source_packets import (
    build_episode_source_packets,
    handoff_from_episode,
    packet_for_episode,
)
from novel_drama_engine.source_evidence import (
    build_source_evidence_report,
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
    "adaptation_quality.py",
    "source_packets.py",
    "source_evidence.py",
)
CACHE_RELEVANT_ENV = (
    "OPENAI_BASE_URL",
    "OPENAI_MODEL",
    "NOVEL_DRAMA_LLM_PROVIDER",
    "NOVEL_DRAMA_GENERATION_VARIANT",
    "NOVEL_DRAMA_REPAIR_BUDGET",
    "NOVEL_DRAMA_EPISODE_REPAIR_FALLBACK",
    "NOVEL_DRAMA_SCRIPT_EPISODE_FIRST",
    "NOVEL_DRAMA_SCRIPT_PROMPT_MODE",
    "NOVEL_DRAMA_STRICT_SHOOTING_QUALITY",
    "NOVEL_DRAMA_SOURCE_STRENGTH_COST_CONTROL",
    "NOVEL_DRAMA_BLOCKING_OPTIONAL_POLISH",
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
    REWRITE = "rewrite"
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
        "1": RepairBudget.REWRITE,
        "batch": RepairBudget.REWRITE,
        "rewrite": RepairBudget.REWRITE,
        "whole": RepairBudget.REWRITE,
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


def use_episode_first_script_generation() -> bool:
    raw = os.environ.get("NOVEL_DRAMA_SCRIPT_EPISODE_FIRST", "")
    return raw.strip().lower() in {"1", "true", "yes", "on", "episode", "episode_first"}


def prompt_trace_enabled() -> bool:
    raw = os.environ.get("NOVEL_DRAMA_TRACE_PROMPTS", "0")
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def blocking_optional_polish_enabled() -> bool:
    raw = os.environ.get("NOVEL_DRAMA_BLOCKING_OPTIONAL_POLISH", "0")
    return raw.strip().lower() in {"1", "true", "yes", "on", "blocking", "strict"}


def source_strength_cost_control_enabled() -> bool:
    raw = os.environ.get("NOVEL_DRAMA_SOURCE_STRENGTH_COST_CONTROL", "1")
    return raw.strip().lower() not in {"0", "false", "no", "off"}


def strong_source_light_adaptation(
    source_strength_profile: SourceStrengthProfile,
    generation_variant: GenerationVariant,
) -> bool:
    return (
        source_strength_cost_control_enabled()
        and generation_variant == GenerationVariant.SOP_FULL_STACK
        and source_strength_profile.overall_level.value == "strong"
        and source_strength_profile.recommended_intensity.value == "light"
    )


def fallback_episode_repair_targets(episode_numbers: list[int]) -> set[int]:
    raw = os.environ.get("NOVEL_DRAMA_EPISODE_REPAIR_FALLBACK", "none")
    normalized = raw.strip().lower().replace("-", "_")
    if normalized in {"all", "full", "every", "全部"}:
        return set(episode_numbers)
    if normalized in {"none", "skip", "off", "0"}:
        return set()
    if not episode_numbers:
        return set()
    return {episode_numbers[0]}


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


EPISODE_RANGE_PATTERNS = (
    re.compile(
        r"\bEP\s*0*(\d{1,3})\s*(?:-|~|–|—|至|到)\s*(?:EP\s*)?0*(\d{1,3})\b",
        re.IGNORECASE,
    ),
    re.compile(r"第\s*0*(\d{1,3})\s*(?:-|~|–|—|至|到)\s*0*(\d{1,3})\s*集"),
)

EPISODE_REF_PATTERNS = (
    re.compile(r"\bEP\s*0*(\d{1,3})\b", re.IGNORECASE),
    re.compile(r"第\s*0*(\d{1,3})\s*集"),
)


def episode_numbers_mentioned_in_quality(
    quality_report: QualityReport,
    valid_episode_numbers: list[int],
) -> set[int]:
    valid = set(valid_episode_numbers)
    text = "\n".join(
        [*quality_report.blocking_issues, quality_report.rewrite_instruction]
    )
    mentioned: set[int] = set()
    for pattern in EPISODE_RANGE_PATTERNS:
        for start_text, end_text in pattern.findall(text):
            start, end = int(start_text), int(end_text)
            if end < start:
                start, end = end, start
            mentioned.update(
                number for number in range(start, end + 1) if number in valid
            )
    for pattern in EPISODE_REF_PATTERNS:
        mentioned.update(
            number
            for number in (int(match) for match in pattern.findall(text))
            if number in valid
        )
    return mentioned


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
        generation_variant: GenerationVariant | str = GenerationVariant.CURRENT_DENSITY,
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
            resume_artifacts_enabled() and not experiment_mode_enabled()
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
            return episode_repair_instruction(existing_episode, base_instruction)

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
        if light_source_cost_control and resolved_repair_budget == RepairBudget.REWRITE:
            effective_repair_budget = RepairBudget.EPISODE
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
                    "allow_repair_fallback": not light_source_cost_control,
                    "allow_optional_polish": (
                        blocking_optional_polish_enabled()
                        and not light_source_cost_control
                    ),
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
        write_runtime_report()

        episode_source_packets = cached_stage(
            "episode_source_packets",
            "episode_source_packets",
            EpisodeSourcePackets,
            lambda: build_episode_source_packets(
                source_text=source_text,
                episode_context=episode_context,
                episode_plan=episode_plan,
                series_structure_plan=series_structure_plan,
                target_episode_count=target_episode_count,
            ),
        )

        script_generator = ScriptBatchGenerator(
            tracked_llm,
            episode_writer=write_episode_artifact,
        )
        script_batch = cached_stage(
            "script_batch",
            "script_batch",
            ScriptBatch,
            lambda: (
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
                    methodology_context=methodology_context,
                    episode_source_packets=episode_source_packets,
                )
                if use_episode_first_script_generation()
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
                    methodology_context=methodology_context,
                    episode_source_packets=episode_source_packets,
                )
            ),
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
            return gated_report

        quality_report = apply_local_quality_gates(
            script_batch,
            quality_report,
            "pre_repair",
        )

        def run_episode_repair_cycle(
            current_script_batch: ScriptBatch,
            current_quality_report: QualityReport,
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

            def record_current_episode_repair_packet(packet) -> None:
                current_episode_repair_packet_records.append(
                    packet.model_dump(mode="json")
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
                    and episode_quality_warnings(episode)
                }
                report_repair_targets = episode_numbers_mentioned_in_quality(
                    current_quality_report,
                    episode_numbers,
                )
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
                if not repair_targets and not light_source_cost_control:
                    repair_targets = fallback_episode_repair_targets(episode_numbers)

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
                        repaired: list[EpisodeScript] = []
                        for episode_number in episode_numbers:
                            previous_episode = repaired[-1] if repaired else None
                            if episode_number in dynamic_repair_targets:
                                existing_episode = current_episodes.get(episode_number)
                                current_repair_packet = (
                                    build_current_episode_repair_packet(
                                        existing_episode,
                                        current_quality_report.rewrite_instruction,
                                    )
                                    if existing_episode is not None
                                    else None
                                )
                                if current_repair_packet is not None:
                                    record_current_episode_repair_packet(
                                        current_repair_packet,
                                    )
                                episode = script_generator.run_episode(
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
                                        current_quality_report.rewrite_instruction,
                                    ),
                                    episode_plan=episode_plan,
                                    viral_asset_report=viral_asset_report,
                                    series_structure_plan=series_structure_plan,
                                    methodology_context=methodology_context,
                                    episode_source_packet=packet_for_episode(
                                        episode_source_packets,
                                        episode_number,
                                    ),
                                    previous_episode_handoff=handoff_from_episode(
                                        previous_episode,
                                    ),
                                    current_episode_repair_packet=current_repair_packet,
                                )
                                if (
                                    not episode_quality_warnings(episode)
                                    and handoff_changed(
                                        current_episodes.get(episode_number),
                                        episode,
                                    )
                                    and episode_number + 1 in episode_numbers
                                ):
                                    dynamic_repair_targets.add(episode_number + 1)
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
                        "Strong-source cost control blocked fallback repair."
                        if light_source_cost_control
                        else "No local, reported, missing, or fallback episode targets.",
                    )
                    repaired_batch = current_script_batch
                    return repaired_batch, current_quality_report
                self.store.write_round_artifact(
                    round_number,
                    "script_batch_episode_repair",
                    repaired_batch,
                )

            episodes_after_repair = {
                episode.episode: episode for episode in repaired_batch.episodes
            }
            episodes_needing_polish = {
                episode_number
                for episode_number, episode in episodes_after_repair.items()
                if episode_quality_warnings(episode)
            }
            if episodes_needing_polish:
                cached_polished_batch = read_cached_artifact(
                    "script_batch_episode_polish",
                    ScriptBatch,
                )
                if cached_polished_batch is not None:
                    record_cached_stage("episode_quality_polish")
                    repaired_batch = cached_polished_batch
                else:
                    polish_instructions = [
                        f"EP{episode_number:02d}: "
                        + repair_instruction_for_episode(
                            episode_number,
                            episodes_after_repair[episode_number],
                            current_quality_report.rewrite_instruction,
                        )
                        for episode_number in sorted(episodes_needing_polish)
                    ]
                    self.store.write_text_artifact(
                        round_number,
                        "episode_polish_instructions.md",
                        "\n\n---\n\n".join(polish_instructions),
                    )
                    if (
                        not blocking_optional_polish_enabled()
                        or light_source_cost_control
                    ):
                        record_skipped_stage(
                            "episode_quality_polish",
                            "Strong-source cost control keeps local polish as "
                            "review-only."
                            if light_source_cost_control
                            else "Set NOVEL_DRAMA_BLOCKING_OPTIONAL_POLISH=1 "
                            "to run this pass inline.",
                        )
                    else:
                        episode_polish_failures: list[str] = []

                        def polish_episode_or_keep(
                            episode_number: int,
                        ) -> EpisodeScript:
                            if episode_number not in episodes_needing_polish:
                                return episodes_after_repair[episode_number]
                            existing_episode = episodes_after_repair.get(episode_number)
                            current_repair_packet = (
                                build_current_episode_repair_packet(
                                    existing_episode,
                                    current_quality_report.rewrite_instruction,
                                )
                                if existing_episode is not None
                                else None
                            )
                            if current_repair_packet is not None:
                                record_current_episode_repair_packet(current_repair_packet)
                            try:
                                return script_generator.run_episode(
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
                                        current_quality_report.rewrite_instruction,
                                    ),
                                    episode_plan=episode_plan,
                                    viral_asset_report=viral_asset_report,
                                    series_structure_plan=series_structure_plan,
                                    methodology_context=methodology_context,
                                    episode_source_packet=packet_for_episode(
                                        episode_source_packets,
                                        episode_number,
                                    ),
                                    previous_episode_handoff=handoff_from_episode(
                                        episodes_after_repair.get(episode_number - 1),
                                    ),
                                    current_episode_repair_packet=current_repair_packet,
                                )
                            except Exception as exc:
                                episode_polish_failures.append(
                                    f"EP{episode_number:02d}: {exc}"
                                )
                                return episodes_after_repair[episode_number]

                        polished_episodes = run_stage(
                            "episode_quality_polish",
                            lambda: [
                                polish_episode_or_keep(episode_number)
                                for episode_number in episode_numbers
                            ],
                        )
                        if episode_polish_failures:
                            self.store.write_text_artifact(
                                round_number,
                                "episode_quality_polish_failures.md",
                                "\n".join(episode_polish_failures),
                            )
                        repaired_batch = run_stage(
                            "apply_episode_quality_polish",
                            lambda: repaired_batch.model_copy(
                                update={"episodes": polished_episodes},
                            ),
                        )
                        self.store.write_round_artifact(
                            round_number,
                            "script_batch_episode_polish",
                            repaired_batch,
                        )

            episodes_after_quality_polish = {
                episode.episode: episode for episode in repaired_batch.episodes
            }
            episodes_needing_hook_dialogue = {
                episode_number
                for episode_number, episode in episodes_after_quality_polish.items()
                if episode_needs_hook_dialogue_polish(episode)
            }
            if episodes_needing_hook_dialogue:
                cached_hook_dialogue_batch = read_cached_artifact(
                    "script_batch_hook_dialogue_polish",
                    ScriptBatch,
                )
                if cached_hook_dialogue_batch is not None:
                    record_cached_stage("hook_dialogue_polish")
                    repaired_batch = cached_hook_dialogue_batch
                else:
                    hook_dialogue_instructions = [
                        f"EP{episode_number:02d}: "
                        + hook_dialogue_polish_instruction(
                            episodes_after_quality_polish[episode_number],
                            current_quality_report.rewrite_instruction,
                        )
                        for episode_number in sorted(episodes_needing_hook_dialogue)
                    ]
                    self.store.write_text_artifact(
                        round_number,
                        "hook_dialogue_polish_instructions.md",
                        "\n\n---\n\n".join(hook_dialogue_instructions),
                    )
                    if (
                        not blocking_optional_polish_enabled()
                        or light_source_cost_control
                    ):
                        record_skipped_stage(
                            "hook_dialogue_polish",
                            "Strong-source cost control keeps hook/dialogue polish "
                            "as review-only."
                            if light_source_cost_control
                            else "Set NOVEL_DRAMA_BLOCKING_OPTIONAL_POLISH=1 "
                            "to run this pass inline.",
                        )
                    else:
                        hook_dialogue_failures: list[str] = []

                        def hook_dialogue_episode_or_keep(
                            episode_number: int,
                        ) -> EpisodeScript:
                            if episode_number not in episodes_needing_hook_dialogue:
                                return episodes_after_quality_polish[episode_number]
                            current_repair_packet = build_current_episode_repair_packet(
                                episodes_after_quality_polish[episode_number],
                                current_quality_report.rewrite_instruction,
                            )
                            record_current_episode_repair_packet(current_repair_packet)
                            try:
                                return script_generator.run_episode_hook_dialogue_polish(
                                    source_text,
                                    source_analysis,
                                    episode_context,
                                    story_bible,
                                    previous_context,
                                    episodes_after_quality_polish[episode_number],
                                    episode_number,
                                    hook_dialogue_polish_instruction(
                                        episodes_after_quality_polish[episode_number],
                                        current_quality_report.rewrite_instruction,
                                    ),
                                    episode_plan=episode_plan,
                                    viral_asset_report=viral_asset_report,
                                    series_structure_plan=series_structure_plan,
                                    methodology_context=methodology_context,
                                    episode_source_packet=packet_for_episode(
                                        episode_source_packets,
                                        episode_number,
                                    ),
                                    previous_episode_handoff=handoff_from_episode(
                                        episodes_after_quality_polish.get(
                                            episode_number - 1,
                                        ),
                                    ),
                                    current_episode_repair_packet=(
                                        current_repair_packet
                                    ),
                                )
                            except Exception as exc:
                                hook_dialogue_failures.append(
                                    f"EP{episode_number:02d}: {exc}"
                                )
                                return episodes_after_quality_polish[episode_number]

                        hook_dialogue_episodes = run_stage(
                            "hook_dialogue_polish",
                            lambda: [
                                hook_dialogue_episode_or_keep(episode_number)
                                for episode_number in episode_numbers
                            ],
                        )
                        if hook_dialogue_failures:
                            self.store.write_text_artifact(
                                round_number,
                                "hook_dialogue_polish_failures.md",
                                "\n".join(hook_dialogue_failures),
                            )
                        repaired_batch = run_stage(
                            "apply_hook_dialogue_polish",
                            lambda: repaired_batch.model_copy(
                                update={"episodes": hook_dialogue_episodes},
                            ),
                        )
                        self.store.write_round_artifact(
                            round_number,
                            "script_batch_hook_dialogue_polish",
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
            if (
                effective_repair_budget == RepairBudget.EPISODE
            ):
                script_batch, quality_report = run_episode_repair_cycle(
                    script_batch,
                    quality_report,
                )
            else:
                script_batch = cached_stage(
                    "script_batch_rewrite",
                    "script_batch_rewrite",
                    ScriptBatch,
                    lambda: script_generator.run(
                        source_text,
                        source_analysis,
                        episode_context,
                        story_bible,
                        previous_context,
                        quality_report.rewrite_instruction,
                        round_number,
                        target_episode_count,
                        episode_plan=episode_plan,
                        viral_asset_report=viral_asset_report,
                        series_structure_plan=series_structure_plan,
                        methodology_context=methodology_context,
                        episode_source_packets=episode_source_packets,
                    ),
                )
                quality_report = run_stage(
                    "quality_report_after_rewrite",
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
                quality_report = apply_local_quality_gates(
                    script_batch,
                    quality_report,
                    "post_rewrite",
                )
                if (
                    quality_report.status == QualityStatus.NEEDS_REWRITE
                    and effective_repair_budget == RepairBudget.EPISODE
                ):
                    script_batch, quality_report = run_episode_repair_cycle(
                        script_batch,
                        quality_report,
                    )
                elif quality_report.status == QualityStatus.NEEDS_REWRITE:
                    quality_report = run_stage(
                        "mark_human_review_after_rewrite_budget",
                        lambda: quality_report.model_copy(
                            update={"status": QualityStatus.NEEDS_HUMAN_REVIEW},
                        ),
                    )
        elif quality_report.status == QualityStatus.NEEDS_REWRITE:
            quality_report = run_stage(
                "mark_human_review_without_repair",
                lambda: quality_report.model_copy(
                    update={"status": QualityStatus.NEEDS_HUMAN_REVIEW},
                ),
            )

        self.store.write_round_artifact(round_number, "quality_report", quality_report)

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
            series_structure_plan=series_structure_plan,
            episode_plan=episode_plan,
            episode_source_packets=episode_source_packets,
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
        self.store.write_next_round_context(result)
        write_runtime_report()
        write_run_manifest("completed", "fresh run completed")
        write_trace_analysis()
        return result
