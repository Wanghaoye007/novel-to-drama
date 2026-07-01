from __future__ import annotations

from novel_drama_engine import prompts
from novel_drama_engine.llm import JsonLLM
from novel_drama_engine.models import (
    EpisodeContext,
    NextRoundContext,
    QualityReport,
    QualityStatus,
    ScriptBatch,
    SourceAnalysis,
    StoryBible,
)
from novel_drama_engine.script_quality import episode_quality_warnings


class SourceParser:
    def __init__(self, llm: JsonLLM) -> None:
        self.llm = llm

    def run(self, source_text: str) -> SourceAnalysis:
        return self.llm.complete(
            system=prompts.SOURCE_PARSER_SYSTEM,
            user=prompts.source_parser_user(source_text),
            response_model=SourceAnalysis,
        )


class EpisodeContextResolver:
    def __init__(self, llm: JsonLLM) -> None:
        self.llm = llm

    def run(
        self,
        source_text: str,
        previous_context: NextRoundContext | None,
        source_analysis: SourceAnalysis,
        round_number: int = 1,
        target_episode_count: int | None = None,
    ) -> EpisodeContext:
        return self.llm.complete(
            system=prompts.EPISODE_CONTEXT_SYSTEM,
            user=prompts.episode_context_user(
                source_text,
                previous_context,
                source_analysis,
                round_number,
                target_episode_count,
            ),
            response_model=EpisodeContext,
        )


class InternalBibleBuilder:
    def __init__(self, llm: JsonLLM) -> None:
        self.llm = llm

    def run(
        self,
        source_text: str,
        source_analysis: SourceAnalysis,
        episode_context: EpisodeContext,
    ) -> StoryBible:
        return self.llm.complete(
            system=prompts.BIBLE_SYSTEM,
            user=prompts.bible_user(source_text, source_analysis, episode_context),
            response_model=StoryBible,
        )


class ScriptBatchGenerator:
    def __init__(self, llm: JsonLLM) -> None:
        self.llm = llm

    def run(
        self,
        source_text: str,
        source_analysis: SourceAnalysis,
        episode_context: EpisodeContext,
        story_bible: StoryBible,
        previous_context: NextRoundContext | None,
        rewrite_instruction: str,
        round_number: int = 1,
        target_episode_count: int | None = None,
    ) -> ScriptBatch:
        return self.llm.complete(
            system=prompts.SCRIPT_SYSTEM,
            user=prompts.script_user(
                source_text,
                source_analysis,
                episode_context,
                story_bible,
                previous_context,
                rewrite_instruction,
                round_number,
                target_episode_count,
            ),
            response_model=ScriptBatch,
        )


class ContinuityBoomChecker:
    def __init__(self, llm: JsonLLM) -> None:
        self.llm = llm

    def run(
        self,
        source_analysis: SourceAnalysis,
        episode_context: EpisodeContext,
        story_bible: StoryBible,
        script_batch: ScriptBatch,
        previous_context: NextRoundContext | None,
    ) -> QualityReport:
        report = self.llm.complete(
            system=prompts.QUALITY_SYSTEM,
            user=prompts.quality_user(
                source_analysis,
                episode_context,
                story_bible,
                script_batch,
                previous_context,
            ),
            response_model=QualityReport,
        )
        warnings = [
            warning
            for episode in script_batch.episodes
            for warning in episode_quality_warnings(episode)
        ]
        if not warnings:
            return report

        blocking_issues = [*report.blocking_issues, *warnings]
        rewrite_instruction = "；".join(
            [
                "按参考短剧密度重写：每集 800-1700 字，2-5 场，8 条以上镜头动作，16 条以上对白/OS/VO，开头 8 个 beat 爆冲突，结尾留强钩子",
                *warnings[:6],
                report.rewrite_instruction,
            ]
        ).strip("；")
        status = (
            QualityStatus.NEEDS_REWRITE
            if report.status == QualityStatus.USABLE
            else report.status
        )
        return report.model_copy(
            update={
                "status": status,
                "blocking_issues": blocking_issues,
                "rewrite_instruction": rewrite_instruction,
            },
        )


class StateWriter:
    def __init__(self, llm: JsonLLM) -> None:
        self.llm = llm

    def run(
        self,
        source_analysis: SourceAnalysis,
        episode_context: EpisodeContext,
        story_bible: StoryBible,
        script_batch: ScriptBatch,
        quality_report: QualityReport,
        previous_context: NextRoundContext | None,
    ) -> NextRoundContext:
        return self.llm.complete(
            system=prompts.STATE_SYSTEM,
            user=prompts.state_user(
                source_analysis,
                episode_context,
                story_bible,
                script_batch,
                quality_report,
                previous_context,
            ),
            response_model=NextRoundContext,
        )
