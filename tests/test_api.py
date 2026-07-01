from concurrent.futures import ThreadPoolExecutor, as_completed

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


def test_api_mock_deliverable_endpoints_write_assets(tmp_path):
    project_dir = tmp_path / "project"
    client = TestClient(app)
    run_response = client.post(
        "/projects/run-mock",
        json={
            "project_dir": str(project_dir),
            "project_id": "api-demo",
            "source_text": "林晚被赶出生日宴。",
        },
    )

    localize_response = client.post(
        "/projects/localize-mock",
        json={
            "project_dir": str(project_dir),
            "locale": "en-US",
            "platform": "TikTok/Reels",
        },
    )
    ad_assets_response = client.post(
        "/projects/ad-assets-mock",
        json={
            "project_dir": str(project_dir),
            "locale": "en-US",
            "platform": "TikTok/Reels",
        },
    )
    status_response = client.get(
        "/projects/status",
        params={"project_dir": str(project_dir)},
    )
    status_payload = status_response.json()

    assert run_response.status_code == 200
    assert localize_response.status_code == 200
    assert ad_assets_response.status_code == 200
    assert localize_response.json()["round_number"] == 1
    assert ad_assets_response.json()["round_number"] == 1
    assert (project_dir / "round_001" / "localization_en-US_TikTok-Reels.json").exists()
    assert (project_dir / "round_001" / "marketing_assets_en-US_TikTok-Reels.md").exists()
    assert status_payload["rounds"][0]["localizations"] == ["en-US_TikTok-Reels"]
    assert status_payload["rounds"][0]["marketing_assets"] == ["en-US_TikTok-Reels"]


def test_api_mock_deliverable_endpoints_handle_same_project_concurrency(tmp_path):
    project_dir = tmp_path / "project"
    run_response = TestClient(app).post(
        "/projects/run-mock",
        json={
            "project_dir": str(project_dir),
            "project_id": "api-demo",
            "source_text": "林晚被赶出生日宴。",
        },
    )
    assert run_response.status_code == 200

    def post_deliverable(endpoint: str):
        return TestClient(app).post(
            endpoint,
            json={
                "project_dir": str(project_dir),
                "locale": "en-US",
                "platform": "TikTok/Reels",
            },
        )

    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [
            executor.submit(post_deliverable, "/projects/localize-mock"),
            executor.submit(post_deliverable, "/projects/ad-assets-mock"),
        ]
        responses = [future.result() for future in as_completed(futures)]

    assert [response.status_code for response in responses] == [200, 200]
    status_response = TestClient(app).get(
        "/projects/status",
        params={"project_dir": str(project_dir)},
    )
    status_payload = status_response.json()

    assert status_response.status_code == 200
    assert (project_dir / "round_001" / "localization_en-US_TikTok-Reels.json").exists()
    assert (project_dir / "round_001" / "marketing_assets_en-US_TikTok-Reels.json").exists()
    assert status_payload["rounds"][0]["localizations"] == ["en-US_TikTok-Reels"]
    assert status_payload["rounds"][0]["marketing_assets"] == ["en-US_TikTok-Reels"]


def test_api_mock_deliverable_endpoints_report_empty_project(tmp_path):
    response = TestClient(app).post(
        "/projects/localize-mock",
        json={"project_dir": str(tmp_path / "project")},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "No completed rounds found"
