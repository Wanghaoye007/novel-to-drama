from __future__ import annotations

import re
from collections.abc import Callable

from novel_drama_engine import prompts
from novel_drama_engine.llm import JsonLLM
from novel_drama_engine.models import (
    EpisodeScript,
    EpisodeSourcePackets,
    EpisodeContext,
    EpisodePlan,
    MethodologyContext,
    NextRoundContext,
    QualityReport,
    QualityStatus,
    ScriptBatch,
    SourceAnalysis,
    StoryBible,
    SeriesStructurePlan,
    ViralAssetReport,
)
from novel_drama_engine.source_packets import handoff_from_episode, packet_for_episode
from novel_drama_engine.script_quality import (
    episode_quality_warnings,
    script_batch_quality_warnings,
)


def expected_episode_numbers_from_context(
    episode_context: EpisodeContext,
) -> list[int]:
    match = re.fullmatch(
        r"EP(\d+)(?:-EP(\d+))?",
        episode_context.target_episode_range.strip(),
    )
    if not match:
        return []
    start = int(match.group(1))
    end = int(match.group(2) or match.group(1))
    if end < start:
        return []
    return list(range(start, end + 1))


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
        episodes_per_round: int = 5,
        viral_asset_report: ViralAssetReport | None = None,
        methodology_context: MethodologyContext | None = None,
    ) -> EpisodeContext:
        return self.llm.complete(
            system=prompts.EPISODE_CONTEXT_SYSTEM,
            user=prompts.episode_context_user(
                source_text,
                previous_context,
                source_analysis,
                round_number,
                target_episode_count,
                episodes_per_round,
                viral_asset_report=viral_asset_report,
                methodology_context=methodology_context,
            ),
            response_model=EpisodeContext,
        )


class ViralAssetExtractor:
    def __init__(self, llm: JsonLLM) -> None:
        self.llm = llm

    def run(
        self,
        source_text: str,
        source_analysis: SourceAnalysis,
        target_episode_count: int | None = None,
    ) -> ViralAssetReport:
        return self.llm.complete(
            system=prompts.VIRAL_ASSET_SYSTEM,
            user=prompts.viral_asset_user(
                source_text,
                source_analysis,
                target_episode_count,
            ),
            response_model=ViralAssetReport,
        )


class InternalBibleBuilder:
    def __init__(self, llm: JsonLLM) -> None:
        self.llm = llm

    def run(
        self,
        source_text: str,
        source_analysis: SourceAnalysis,
        episode_context: EpisodeContext,
        viral_asset_report: ViralAssetReport | None = None,
        methodology_context: MethodologyContext | None = None,
    ) -> StoryBible:
        return self.llm.complete(
            system=prompts.BIBLE_SYSTEM,
            user=prompts.bible_user(
                source_text,
                source_analysis,
                episode_context,
                viral_asset_report=viral_asset_report,
                methodology_context=methodology_context,
            ),
            response_model=StoryBible,
        )


class SeriesStructurePlanner:
    def __init__(self, llm: JsonLLM) -> None:
        self.llm = llm

    def run(
        self,
        source_text: str,
        source_analysis: SourceAnalysis,
        episode_context: EpisodeContext,
        story_bible: StoryBible,
        viral_asset_report: ViralAssetReport,
        previous_context: NextRoundContext | None,
        target_episode_count: int | None = None,
        methodology_context: MethodologyContext | None = None,
    ) -> SeriesStructurePlan:
        return self.llm.complete(
            system=prompts.SERIES_STRUCTURE_SYSTEM,
            user=prompts.series_structure_user(
                source_text,
                source_analysis,
                episode_context,
                story_bible,
                viral_asset_report,
                previous_context,
                target_episode_count,
                methodology_context=methodology_context,
            ),
            response_model=SeriesStructurePlan,
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
        viral_asset_report: ViralAssetReport | None = None,
        series_structure_plan: SeriesStructurePlan | None = None,
        methodology_context: MethodologyContext | None = None,
    ) -> EpisodePlan:
        return self.llm.complete(
            system=prompts.EPISODE_PLAN_SYSTEM,
            user=prompts.episode_plan_user(
                source_text,
                source_analysis,
                episode_context,
                story_bible,
                previous_context,
                viral_asset_report=viral_asset_report,
                series_structure_plan=series_structure_plan,
                methodology_context=methodology_context,
            ),
            response_model=EpisodePlan,
        )


class ScriptBatchGenerator:
    def __init__(
        self,
        llm: JsonLLM,
        episode_writer: Callable[[EpisodeScript], None] | None = None,
    ) -> None:
        self.llm = llm
        self.episode_writer = episode_writer

    def _emit_episode(self, episode: EpisodeScript) -> EpisodeScript:
        if self.episode_writer is not None:
            self.episode_writer(episode)
        return episode

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
        viral_asset_report: ViralAssetReport | None = None,
        series_structure_plan: SeriesStructurePlan | None = None,
        methodology_context: MethodologyContext | None = None,
        episode_source_packets: EpisodeSourcePackets | None = None,
    ) -> ScriptBatch:
        batch = self.llm.complete(
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
                viral_asset_report=viral_asset_report,
                series_structure_plan=series_structure_plan,
                methodology_context=methodology_context,
                episode_source_packets=episode_source_packets,
            ),
            response_model=ScriptBatch,
        )
        filled_batch = self._fill_missing_episodes(
            batch,
            source_text,
            source_analysis,
            episode_context,
            story_bible,
            previous_context,
            rewrite_instruction,
            episode_plan,
            viral_asset_report,
            series_structure_plan,
            methodology_context,
            episode_source_packets,
        )
        for episode in filled_batch.episodes:
            self._emit_episode(episode)
        return filled_batch

    def run_episode_batch(
        self,
        source_text: str,
        source_analysis: SourceAnalysis,
        episode_context: EpisodeContext,
        story_bible: StoryBible,
        previous_context: NextRoundContext | None,
        rewrite_instruction: str,
        episode_plan: EpisodePlan | None = None,
        viral_asset_report: ViralAssetReport | None = None,
        series_structure_plan: SeriesStructurePlan | None = None,
        methodology_context: MethodologyContext | None = None,
        episode_source_packets: EpisodeSourcePackets | None = None,
    ) -> ScriptBatch:
        expected_numbers = expected_episode_numbers_from_context(episode_context)
        if not expected_numbers:
            return self.run(
                source_text,
                source_analysis,
                episode_context,
                story_bible,
                previous_context,
                rewrite_instruction,
                episode_plan=episode_plan,
                viral_asset_report=viral_asset_report,
                series_structure_plan=series_structure_plan,
                methodology_context=methodology_context,
                episode_source_packets=episode_source_packets,
            )

        episode_first_instruction = "；".join(
            part
            for part in [
                rewrite_instruction,
                (
                    "逐集优先生成模式：本次只生成当前 episode 的完整可拍摄正片，"
                    "不要压缩成提纲，不要引用其他集正文，不要等待整批汇总。"
                ),
            ]
            if part
        )
        episodes: list[EpisodeScript] = []
        previous_episode: EpisodeScript | None = None
        for episode_number in expected_numbers:
            episode = self.run_episode(
                source_text,
                source_analysis,
                episode_context,
                story_bible,
                previous_context,
                None,
                episode_number,
                episode_first_instruction,
                episode_plan=episode_plan,
                viral_asset_report=viral_asset_report,
                series_structure_plan=series_structure_plan,
                methodology_context=methodology_context,
                episode_source_packet=packet_for_episode(
                    episode_source_packets,
                    episode_number,
                ),
                previous_episode_handoff=handoff_from_episode(previous_episode),
            )
            episodes.append(episode)
            previous_episode = episode
        return ScriptBatch(episodes=episodes)

    def _fill_missing_episodes(
        self,
        batch: ScriptBatch,
        source_text: str,
        source_analysis: SourceAnalysis,
        episode_context: EpisodeContext,
        story_bible: StoryBible,
        previous_context: NextRoundContext | None,
        rewrite_instruction: str,
        episode_plan: EpisodePlan | None = None,
        viral_asset_report: ViralAssetReport | None = None,
        series_structure_plan: SeriesStructurePlan | None = None,
        methodology_context: MethodologyContext | None = None,
        episode_source_packets: EpisodeSourcePackets | None = None,
    ) -> ScriptBatch:
        expected_numbers = expected_episode_numbers_from_context(episode_context)
        if not expected_numbers:
            return batch

        episodes_by_number = {
            episode.episode: episode
            for episode in batch.episodes
            if episode.episode in expected_numbers
        }
        missing_numbers = [
            episode_number
            for episode_number in expected_numbers
            if episode_number not in episodes_by_number
        ]
        if not missing_numbers and len(episodes_by_number) == len(batch.episodes):
            return batch

        fill_instruction = "；".join(
            part
            for part in [
                rewrite_instruction,
                (
                    "整批输出缺集，系统正在逐集补齐。必须完整生成本集正片，"
                    "不能摘要、不能复述其他集、不能把多个 EP 合并。"
                ),
            ]
            if part
        )
        for episode_number in missing_numbers:
            episodes_by_number[episode_number] = self.run_episode(
                source_text,
                source_analysis,
                episode_context,
                story_bible,
                previous_context,
                None,
                episode_number,
                fill_instruction,
                episode_plan=episode_plan,
                viral_asset_report=viral_asset_report,
                series_structure_plan=series_structure_plan,
                methodology_context=methodology_context,
                episode_source_packet=packet_for_episode(
                    episode_source_packets,
                    episode_number,
                ),
                previous_episode_handoff=handoff_from_episode(
                    episodes_by_number.get(episode_number - 1),
                ),
            )

        return ScriptBatch(
            episodes=[
                episodes_by_number[episode_number]
                for episode_number in expected_numbers
                if episode_number in episodes_by_number
            ]
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
        viral_asset_report: ViralAssetReport | None = None,
        series_structure_plan: SeriesStructurePlan | None = None,
        methodology_context: MethodologyContext | None = None,
        episode_source_packet: object | None = None,
        previous_episode_handoff: object | None = None,
        current_episode_repair_packet: object | None = None,
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
                viral_asset_report=viral_asset_report,
                series_structure_plan=series_structure_plan,
                methodology_context=methodology_context,
                episode_source_packet=episode_source_packet,
                previous_episode_handoff=previous_episode_handoff,
                current_episode_repair_packet=current_episode_repair_packet,
            ),
            response_model=EpisodeScript,
        )
        if episode.episode != episode_number:
            episode = episode.model_copy(update={"episode": episode_number})
        return self._emit_episode(episode)

    def run_episode_hook_dialogue_polish(
        self,
        source_text: str,
        source_analysis: SourceAnalysis,
        episode_context: EpisodeContext,
        story_bible: StoryBible,
        previous_context: NextRoundContext | None,
        existing_episode: EpisodeScript,
        episode_number: int,
        polish_instruction: str,
        episode_plan: EpisodePlan | None = None,
        viral_asset_report: ViralAssetReport | None = None,
        series_structure_plan: SeriesStructurePlan | None = None,
        methodology_context: MethodologyContext | None = None,
        episode_source_packet: object | None = None,
        previous_episode_handoff: object | None = None,
        current_episode_repair_packet: object | None = None,
    ) -> EpisodeScript:
        episode = self.llm.complete(
            system=prompts.SCRIPT_SYSTEM,
            user=prompts.hook_dialogue_polish_user(
                source_text,
                source_analysis,
                episode_context,
                story_bible,
                previous_context,
                existing_episode,
                episode_number,
                polish_instruction,
                episode_plan,
                viral_asset_report=viral_asset_report,
                series_structure_plan=series_structure_plan,
                methodology_context=methodology_context,
                episode_source_packet=episode_source_packet,
                previous_episode_handoff=previous_episode_handoff,
                current_episode_repair_packet=current_episode_repair_packet,
            ),
            response_model=EpisodeScript,
        )
        if episode.episode != episode_number:
            episode = episode.model_copy(update={"episode": episode_number})
        return self._emit_episode(episode)


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
        viral_asset_report: ViralAssetReport | None = None,
        series_structure_plan: SeriesStructurePlan | None = None,
        episode_plan: EpisodePlan | None = None,
        methodology_context: MethodologyContext | None = None,
    ) -> QualityReport:
        report = self.llm.complete(
            system=prompts.QUALITY_SYSTEM,
            user=prompts.quality_user(
                source_analysis,
                episode_context,
                story_bible,
                script_batch,
                previous_context,
                viral_asset_report=viral_asset_report,
                series_structure_plan=series_structure_plan,
                episode_plan=episode_plan,
                methodology_context=methodology_context,
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
                "按双层质检修复：先保证创作稿成立（人物动机不偏、冲突自然、情绪递进、对白像人话、原文 C0/C1 不丢、结尾钩子已被演出来），再补执行稿需要的动作、道具、声音和镜头衔接；scene.heading 必须是“集数-场次 日/夜-内/外-具体地点”，例如 1-1 夜-内-武家卧室；不要把 hook/主情绪/watch_reason/消费理由/观众要看 当成用户可见说明；禁止“众人震惊、气氛凝固、他很害怕”这类抽象动作；台词/OS 单句尽量短，超长必须拆行",
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
        viral_asset_report: ViralAssetReport | None = None,
        series_structure_plan: SeriesStructurePlan | None = None,
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
                viral_asset_report=viral_asset_report,
                series_structure_plan=series_structure_plan,
            ),
            response_model=NextRoundContext,
        )
