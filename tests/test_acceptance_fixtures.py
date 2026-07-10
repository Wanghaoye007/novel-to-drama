from pathlib import Path

import pytest

from novel_drama_engine.demo import demo_source_grounded_round_outputs
from novel_drama_engine.evaluation import read_quality_sample_manifest
from novel_drama_engine.llm import StaticJsonLLM
from novel_drama_engine.pipeline import RoundPipeline
from novel_drama_engine.storage import ProjectStore


SAMPLES = read_quality_sample_manifest(Path("examples/quality_samples.json")).samples


@pytest.mark.parametrize("sample", SAMPLES, ids=lambda sample: sample.sample_id)
def test_five_genre_fixtures_complete_one_grounded_round(tmp_path, sample):
    result = RoundPipeline(
        llm=StaticJsonLLM(
            demo_source_grounded_round_outputs(source_text=sample.source_text)
        ),
        store=ProjectStore(tmp_path),
    ).run(
        project_id="acceptance",
        round_number=1,
        source_text=sample.source_text,
        target_episode_count=sample.target_episode_count,
        episodes_per_round=sample.episodes_per_round,
    )

    assert result.episode_plan is not None
    assert result.episode_context.target_episode_range == "EP01-EP01"
    assert result.source_packet_confidence_report is not None
    assert result.source_packet_confidence_report.status != "blocking"
    assert result.adaptation_quality_report is not None
    assert result.adaptation_quality_report.source_fidelity.score >= 50
    assert result.script_batch.episodes[0].hook_3s
    assert result.script_batch.episodes[0].cliffhanger
