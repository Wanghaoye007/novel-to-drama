from __future__ import annotations

from novel_drama_engine import prompts
from novel_drama_engine.llm import JsonLLM
from novel_drama_engine.models import (
    EpisodeScript,
    EpisodeContext,
    EpisodePlan,
    NextRoundContext,
    QualityReport,
    QualityStatus,
    ScriptBatch,
    SourceAnalysis,
    StoryBible,
)
from novel_drama_engine.script_quality import (
    episode_quality_warnings,
    script_batch_quality_warnings,
)


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


class EpisodeBeatPlanner:
    def __init__(self, llm: JsonLLM) -> None:
        self.llm = llm

    def run(
        self,
        source_text: str,
        source_analysis: SourceAnalysis,
        episode_context: EpisodeContext,
        story_bible: StoryBible,
        previous_context: NextRoundContext | None,
    ) -> EpisodePlan:
        return self.llm.complete(
            system=prompts.EPISODE_PLAN_SYSTEM,
            user=prompts.episode_plan_user(
                source_text,
                source_analysis,
                episode_context,
                story_bible,
                previous_context,
            ),
            response_model=EpisodePlan,
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
        episode_plan: EpisodePlan | None = None,
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
                episode_plan,
            ),
            response_model=ScriptBatch,
        )

    def run_episode(
        self,
        source_text: str,
        source_analysis: SourceAnalysis,
        episode_context: EpisodeContext,
        story_bible: StoryBible,
        previous_context: NextRoundContext | None,
        existing_episode: EpisodeScript | None,
        episode_number: int,
        rewrite_instruction: str,
        episode_plan: EpisodePlan | None = None,
    ) -> EpisodeScript:
        episode = self.llm.complete(
            system=prompts.SCRIPT_SYSTEM,
            user=prompts.script_episode_user(
                source_text,
                source_analysis,
                episode_context,
                story_bible,
                previous_context,
                existing_episode,
                episode_number,
                rewrite_instruction,
                episode_plan,
            ),
            response_model=EpisodeScript,
        )
        if episode.episode == episode_number:
            return episode
        return episode.model_copy(update={"episode": episode_number})


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
        warnings = script_batch_quality_warnings(
            script_batch,
            episode_context.target_episode_range,
        ) + [
            warning
            for episode in script_batch.episodes
            for warning in episode_quality_warnings(episode)
        ]
        if not warnings:
            return report

        blocking_issues = [*report.blocking_issues, *warnings]
        rewrite_instruction = "；".join(
            [
                "按参考短剧密度重写：每集 800-1700 字，2-5 场，8 条以上镜头动作，16 条以上对白/OS/VO，开头 8 个 beat 爆冲突，结尾留强钩子；scene.heading 必须是“集数-场次 日/夜-内/外-具体地点”，例如 1-1 夜-内-武家卧室；不要把 hook/主情绪/watch_reason 当成用户可见说明；每条 action 必须显式包含一个景别词和一个运镜词，例如“△中近景推近武植侧脸，油灯占前景，切到金莲发白的指节”；台词/OS 单句不超过 30 个汉字，超长必须拆行",
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
        episode_plan: EpisodePlan | None = None,
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
                episode_plan,
            ),
            response_model=NextRoundContext,
        )
