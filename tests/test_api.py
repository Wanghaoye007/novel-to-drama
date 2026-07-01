from fastapi.testclient import TestClient

from novel_drama_engine.api import app
from novel_drama_engine.models import RoundResult
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


def test_api_health():
    response = TestClient(app).get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_api_project_status_reads_project_dir(tmp_path, happy_round_outputs):
    project_dir = tmp_path / "project"
    store = ProjectStore(project_dir)
    store.write_round_result(build_round_result(1, happy_round_outputs))
    store.write_next_round_context(build_round_result(1, happy_round_outputs))

    response = TestClient(app).get(
        "/projects/status",
        params={"project_dir": str(project_dir)},
    )
    payload = response.json()

    assert response.status_code == 200
    assert payload["round_count"] == 1
    assert payload["rounds"][0]["target_episode_range"] == "EP01-EP01"
    assert payload["latest_context"].endswith("next_round_context.json")


def test_api_project_status_by_id_reads_project_root(tmp_path, happy_round_outputs):
    project_root = tmp_path / "projects"
    project_dir = project_root / "demo"
    ProjectStore(project_dir).write_round_result(build_round_result(1, happy_round_outputs))

    response = TestClient(app).get(
        "/projects/demo/status",
        params={"project_root": str(project_root)},
    )
    payload = response.json()

    assert response.status_code == 200
    assert payload["project_dir"] == str(project_dir)
    assert payload["round_count"] == 1


def test_api_project_status_handles_empty_project(tmp_path):
    response = TestClient(app).get(
        "/projects/status",
        params={"project_dir": str(tmp_path / "missing")},
    )
    payload = response.json()

    assert response.status_code == 200
    assert payload["round_count"] == 0
    assert payload["rounds"] == []
