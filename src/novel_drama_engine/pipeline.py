from __future__ import annotations

from dataclasses import dataclass

from novel_drama_engine.llm import JsonLLM
from novel_drama_engine.models import (
    EpisodeContext,
    GenerationVariant,
    NextRoundContext,
    QualityStatus,
    RoundResult,
)
from novel_drama_engine.rounds import (
    ContinuityBoomChecker,
    EpisodeBeatPlanner,
    EpisodeContextResolver,
    InternalBibleBuilder,
    ScriptBatchGenerator,
    SourceParser,
    StateWriter,
)
from novel_drama_engine.storage import ProjectStore

EPISODES_PER_ROUND = 5


class EmptySourceError(ValueError):
    pass


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
) -> EpisodeContext:
    start_episode, end_episode = episode_window(
        round_number=round_number,
        previous_context=previous_context,
        target_episode_count=target_episode_count,
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
) -> list[int]:
    start_episode, end_episode = episode_window(
        round_number=round_number,
        previous_context=previous_context,
        target_episode_count=target_episode_count,
    )
    return list(range(start_episode, end_episode + 1))


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
        generation_variant: GenerationVariant | str = GenerationVariant.CURRENT_DENSITY,
    ) -> RoundResult:
        if not source_text.strip():
            raise EmptySourceError("source_text is empty")
        generation_variant = GenerationVariant(generation_variant)

        source_analysis = SourceParser(self.llm).run(source_text)
        self.store.write_round_artifact(round_number, "source_analysis", source_analysis)

        episode_context = EpisodeContextResolver(self.llm).run(
            source_text,
            previous_context,
            source_analysis,
            round_number,
            target_episode_count,
        )
        episode_context = normalize_episode_context_range(
            episode_context,
            round_number=round_number,
            previous_context=previous_context,
            target_episode_count=target_episode_count,
        )
        self.store.write_round_artifact(round_number, "episode_context", episode_context)

        story_bible = InternalBibleBuilder(self.llm).run(
            source_text,
            source_analysis,
            episode_context,
        )
        self.store.write_round_artifact(round_number, "story_bible", story_bible)

        episode_plan = None
        if generation_variant == GenerationVariant.DRAMA_ENGINE_FIRST:
            episode_plan = EpisodeBeatPlanner(self.llm).run(
                source_text,
                source_analysis,
                episode_context,
                story_bible,
                previous_context,
            )
            episode_plan = episode_plan.model_copy(
                update={
                    "variant": GenerationVariant.DRAMA_ENGINE_FIRST,
                    "target_episode_range": episode_context.target_episode_range,
                },
            )
            self.store.write_round_artifact(round_number, "episode_plan", episode_plan)

        script_generator = ScriptBatchGenerator(self.llm)
        script_batch = script_generator.run(
            source_text,
            source_analysis,
            episode_context,
            story_bible,
            previous_context,
            "",
            round_number,
            target_episode_count,
            episode_plan=episode_plan,
        )
        self.store.write_round_artifact(round_number, "script_batch", script_batch)

        checker = ContinuityBoomChecker(self.llm)
        quality_report = checker.run(
            source_analysis,
            episode_context,
            story_bible,
            script_batch,
            previous_context,
        )

        if quality_report.status == QualityStatus.NEEDS_REWRITE:
            self.store.write_round_artifact(
                round_number,
                "quality_report_before_rewrite",
                quality_report,
            )
            script_batch = script_generator.run(
                source_text,
                source_analysis,
                episode_context,
                story_bible,
                previous_context,
                quality_report.rewrite_instruction,
                round_number,
                target_episode_count,
                episode_plan=episode_plan,
            )
            self.store.write_round_artifact(round_number, "script_batch_rewrite", script_batch)
            quality_report = checker.run(
                source_analysis,
                episode_context,
                story_bible,
                script_batch,
                previous_context,
            )
            if quality_report.status == QualityStatus.NEEDS_REWRITE:
                self.store.write_round_artifact(
                    round_number,
                    "quality_report_before_episode_repair",
                    quality_report,
                )
                current_episodes = {
                    episode.episode: episode for episode in script_batch.episodes
                }
                repaired_episodes = [
                    script_generator.run_episode(
                        source_text,
                        source_analysis,
                        episode_context,
                        story_bible,
                        previous_context,
                        current_episodes.get(episode_number),
                        episode_number,
                        quality_report.rewrite_instruction,
                        episode_plan=episode_plan,
                    )
                    for episode_number in expected_episode_numbers(
                        round_number=round_number,
                        previous_context=previous_context,
                        target_episode_count=target_episode_count,
                    )
                ]
                script_batch = script_batch.model_copy(
                    update={"episodes": repaired_episodes},
                )
                self.store.write_round_artifact(
                    round_number,
                    "script_batch_episode_repair",
                    script_batch,
                )
                quality_report = checker.run(
                    source_analysis,
                    episode_context,
                    story_bible,
                    script_batch,
                    previous_context,
                )
                if quality_report.status == QualityStatus.NEEDS_REWRITE:
                    quality_report = quality_report.model_copy(
                        update={"status": QualityStatus.NEEDS_HUMAN_REVIEW},
                    )

        self.store.write_round_artifact(round_number, "quality_report", quality_report)

        next_round_context = StateWriter(self.llm).run(
            source_analysis,
            episode_context,
            story_bible,
            script_batch,
            quality_report,
            previous_context,
            episode_plan=episode_plan,
        )

        result = RoundResult(
            project_id=project_id,
            round_number=round_number,
            source_analysis=source_analysis,
            episode_context=episode_context,
            story_bible=story_bible,
            episode_plan=episode_plan,
            script_batch=script_batch,
            quality_report=quality_report,
            next_round_context=next_round_context,
        )
        self.store.write_round_result(result)
        self.store.write_next_round_context(result)
        return result
