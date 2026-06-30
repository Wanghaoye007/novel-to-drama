from novel_drama_engine.models import SourceAnalysis
from novel_drama_engine.storage import ProjectStore


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
