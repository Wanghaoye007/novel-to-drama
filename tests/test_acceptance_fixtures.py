import pytest

from novel_drama_engine.demo import demo_round_outputs
from novel_drama_engine.llm import StaticJsonLLM
from novel_drama_engine.pipeline import RoundPipeline
from novel_drama_engine.storage import ProjectStore


@pytest.mark.parametrize(
    "source_text",
    [
        "林晚在豪门宴会上被未婚夫当众赶走，假千金站在旁边假意求情。",
        "亲子鉴定报告被林雪藏进包里，林晚发现报告编号被换过。",
        "顾承误会林晚害了林雪，三年后才发现自己签下的是假证词。",
        "赘婿叶辰被岳父一家羞辱，下一秒黑卡被银行经理亲自送到门口。",
        "沈青重生回成亲当夜，发现毒酒已经端到自己面前。",
    ],
)
def test_five_genre_fixtures_complete_one_round(tmp_path, source_text, happy_round_outputs):
    result = RoundPipeline(
        llm=StaticJsonLLM(demo_round_outputs(include_episode_plan=True)),
        store=ProjectStore(tmp_path),
    ).run(project_id="acceptance", round_number=1, source_text=source_text)

    assert result.episode_plan is not None
    assert result.episode_context.target_episode_range.startswith("EP")
    assert result.script_batch.episodes[0].hook_3s
    assert result.script_batch.episodes[0].cliffhanger
    assert result.next_round_context.current_episode >= 1
