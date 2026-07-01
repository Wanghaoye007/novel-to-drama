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


def test_api_run_mock_project_writes_round_artifacts(tmp_path):
    project_dir = tmp_path / "project"

    response = TestClient(app).post(
        "/projects/run-mock",
        json={
            "project_dir": str(project_dir),
            "project_id": "api-demo",
            "source_text": "林晚被赶出生日宴。",
        },
    )
    payload = response.json()

    assert response.status_code == 200
    assert payload["round_number"] == 1
    assert payload["quality_status"] == "usable"
    assert payload["project_status"]["round_count"] == 1
    assert (project_dir / "round_001" / "round_result.json").exists()
    assert (project_dir / "round_001" / "rendered_scripts.md").exists()


def test_api_run_mock_project_auto_continues_rounds(tmp_path):
    project_dir = tmp_path / "project"
    client = TestClient(app)
    request = {
        "project_dir": str(project_dir),
        "project_id": "api-demo",
        "source_text": "林晚被赶出生日宴。",
    }

    first = client.post("/projects/run-mock", json=request)
    second = client.post("/projects/run-mock", json=request)

    assert first.status_code == 200
    assert second.status_code == 200
    assert second.json()["round_number"] == 2
    assert (project_dir / "round_002" / "round_result.json").exists()


def test_api_run_mock_project_rejects_blank_source(tmp_path):
    response = TestClient(app).post(
        "/projects/run-mock",
        json={
            "project_dir": str(tmp_path / "project"),
            "project_id": "api-demo",
            "source_text": "   ",
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "source_text is empty"
