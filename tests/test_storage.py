from novel_drama_engine.models import RoundResult, SourceAnalysis
from novel_drama_engine.storage import ProjectStore


def build_round_result(round_number, outputs):
    return RoundResult(
        project_id="demo",
        round_number=round_number,
        source_analysis=outputs[0],
        episode_context=outputs[1],
        story_bible=outputs[2],
        script_batch=outputs[3],
        quality_report=outputs[4],
        next_round_context=outputs[5],
    )


def test_store_writes_round_artifact(tmp_path):
    store = ProjectStore(tmp_path)
    analysis = SourceAnalysis(
        characters=["林晚"],
        events=["宴会被羞辱"],
        conflicts=["身份冲突"],
        visual_moments=["邀请函被撕碎"],
        low_value_passages=[],
        candidate_hooks=["把她拖出去！"],
    )

    path = store.write_round_artifact(1, "source_analysis", analysis)

    assert path == tmp_path / "round_001" / "source_analysis.json"
    assert '"林晚"' in path.read_text(encoding="utf-8")


def test_store_reads_context_json(tmp_path):
    context_path = tmp_path / "context.json"
    context_path.write_text(
        '{"summary":"EP01结束","current_episode":1,"open_hooks":[],"forbidden_reveals":[],"character_knowledge":{},"relationship_changes":[],"prop_states":[],"foreshadowing_ledger":[]}',
        encoding="utf-8",
    )

    context = ProjectStore(tmp_path).read_next_round_context(context_path)

    assert context.summary == "EP01结束"
    assert context.current_episode == 1


def test_store_finds_existing_rounds_and_latest_context(tmp_path):
    (tmp_path / "round_002").mkdir()
    (tmp_path / "round_010").mkdir()
    (tmp_path / "round_draft").mkdir()
    (tmp_path / "round_002" / "next_round_context.json").write_text(
        '{"summary":"EP02结束","current_episode":2,"open_hooks":[],"forbidden_reveals":[],"character_knowledge":{},"relationship_changes":[],"prop_states":[],"foreshadowing_ledger":[]}',
        encoding="utf-8",
    )
    store = ProjectStore(tmp_path)

    assert store.existing_round_numbers() == [2, 10]
    assert store.latest_round_number() == 10
    assert store.latest_next_round_context_path() == tmp_path / "round_002" / "next_round_context.json"


def test_store_reads_round_results_in_order(tmp_path, happy_round_outputs):
    store = ProjectStore(tmp_path)
    store.write_round_result(build_round_result(2, happy_round_outputs))
    store.write_round_result(build_round_result(1, happy_round_outputs))
    (tmp_path / "round_003").mkdir()

    results = store.read_round_results()

    assert [result.round_number for result in results] == [1, 2]
    assert results[0].episode_context.target_episode_range == "EP01-EP01"
