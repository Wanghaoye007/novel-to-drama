from __future__ import annotations

from dataclasses import dataclass

from novel_drama_engine.llm import JsonLLM
from novel_drama_engine.models import NextRoundContext, QualityStatus, RoundResult
from novel_drama_engine.rounds import (
    ContinuityBoomChecker,
    EpisodeContextResolver,
    InternalBibleBuilder,
    ScriptBatchGenerator,
    SourceParser,
    StateWriter,
)
from novel_drama_engine.storage import ProjectStore


class EmptySourceError(ValueError):
    pass


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
    ) -> RoundResult:
        if not source_text.strip():
            raise EmptySourceError("source_text is empty")

        source_analysis = SourceParser(self.llm).run(source_text)
        self.store.write_round_artifact(round_number, "source_analysis", source_analysis)

        episode_context = EpisodeContextResolver(self.llm).run(
            source_text,
            previous_context,
            source_analysis,
            round_number,
            target_episode_count,
        )
        self.store.write_round_artifact(round_number, "episode_context", episode_context)

        story_bible = InternalBibleBuilder(self.llm).run(
            source_text,
            source_analysis,
            episode_context,
        )
        self.store.write_round_artifact(round_number, "story_bible", story_bible)

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
        )

        result = RoundResult(
            project_id=project_id,
            round_number=round_number,
            source_analysis=source_analysis,
            episode_context=episode_context,
            story_bible=story_bible,
            script_batch=script_batch,
            quality_report=quality_report,
            next_round_context=next_round_context,
        )
        self.store.write_round_result(result)
        self.store.write_next_round_context(result)
        return result
