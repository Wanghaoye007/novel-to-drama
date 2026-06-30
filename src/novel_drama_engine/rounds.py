from __future__ import annotations

from novel_drama_engine import prompts
from novel_drama_engine.llm import JsonLLM
from novel_drama_engine.models import (
    EpisodeContext,
    LocalizedScriptBatch,
    MarketingAssets,
    NextRoundContext,
    QualityReport,
    RoundResult,
    ScriptBatch,
    SourceAnalysis,
    StoryBible,
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
    ) -> EpisodeContext:
        return self.llm.complete(
            system=prompts.EPISODE_CONTEXT_SYSTEM,
            user=prompts.episode_context_user(
                source_text,
                previous_context,
                source_analysis,
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
        return self.llm.complete(
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


class ScriptLocalizer:
    def __init__(self, llm: JsonLLM) -> None:
        self.llm = llm

    def run(
        self,
        round_result: RoundResult,
        locale: str,
        platform: str,
        guidance: str = "",
    ) -> LocalizedScriptBatch:
        return self.llm.complete(
            system=prompts.LOCALIZATION_SYSTEM,
            user=prompts.localization_user(round_result, locale, platform, guidance),
            response_model=LocalizedScriptBatch,
        )


class MarketingAssetGenerator:
    def __init__(self, llm: JsonLLM) -> None:
        self.llm = llm

    def run(
        self,
        round_result: RoundResult,
        localized_script: LocalizedScriptBatch | None,
        locale: str,
        platform: str,
        guidance: str = "",
    ) -> MarketingAssets:
        return self.llm.complete(
            system=prompts.MARKETING_SYSTEM,
            user=prompts.marketing_user(
                round_result,
                localized_script,
                locale,
                platform,
                guidance,
            ),
            response_model=MarketingAssets,
        )
