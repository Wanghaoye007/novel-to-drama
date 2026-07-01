from concurrent.futures import ThreadPoolExecutor, as_completed

from fastapi.testclient import TestClient

import novel_drama_engine.api as api
from novel_drama_engine.api import app
from novel_drama_engine.demo import demo_localization_output, demo_marketing_assets
from novel_drama_engine.llm import LLMResponseError, StaticJsonLLM
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


def test_api_project_status_by_id_supports_nested_project_ids(tmp_path, happy_round_outputs):
    project_root = tmp_path / "projects"
    project_dir = project_root / "genre" / "haomen" / "book"
    ProjectStore(project_dir).write_round_result(build_round_result(1, happy_round_outputs))

    response = TestClient(app).get(
        "/projects/genre/haomen/book/status",
        params={"project_root": str(project_root)},
    )
    payload = response.json()

    assert response.status_code == 200
    assert payload["project_dir"] == str(project_dir)
    assert payload["round_count"] == 1


def test_api_project_status_by_id_rejects_project_root_escape(tmp_path):
    response = TestClient(app).get(
        "/projects/%2E%2E/outside/status",
        params={"project_root": str(tmp_path / "projects")},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "project_id must stay inside project_root"


def test_api_projects_lists_workspace_projects(tmp_path, happy_round_outputs):
    project_root = tmp_path / "projects"
    haomen_dir = project_root / "haomen"
    nested_dir = project_root / "genre" / "xianxia" / "book"
    ProjectStore(haomen_dir).write_round_result(build_round_result(1, happy_round_outputs))
    ProjectStore(nested_dir).write_round_result(build_round_result(2, happy_round_outputs))
    (project_root / "notes").mkdir()

    response = TestClient(app).get(
        "/projects",
        params={"project_root": str(project_root)},
    )
    payload = response.json()

    assert response.status_code == 200
    assert payload["project_root"] == str(project_root)
    assert payload["project_count"] == 2
    assert payload["total_round_count"] == 2
    assert [project["project_id"] for project in payload["projects"]] == [
        "genre/xianxia/book",
        "haomen",
    ]
    assert payload["projects"][0]["latest_round"]["round_number"] == 2
    assert payload["projects"][1]["latest_round"]["round_number"] == 1


def test_api_projects_lists_missing_workspace_as_empty(tmp_path):
    response = TestClient(app).get(
        "/projects",
        params={"project_root": str(tmp_path / "missing")},
    )
    payload = response.json()

    assert response.status_code == 200
    assert payload["project_count"] == 0
    assert payload["projects"] == []


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


def test_api_run_project_uses_configured_llm_and_model(
    tmp_path,
    happy_round_outputs,
    monkeypatch,
):
    project_dir = tmp_path / "project"
    captured = {}

    def fake_build_api_llm(model=None):
        captured["model"] = model
        return StaticJsonLLM(happy_round_outputs)

    monkeypatch.setattr(api, "build_api_llm", fake_build_api_llm)

    response = TestClient(app).post(
        "/projects/run",
        json={
            "project_dir": str(project_dir),
            "project_id": "api-demo",
            "source_text": "林晚被赶出生日宴。",
            "model": "gpt-test",
        },
    )
    payload = response.json()

    assert response.status_code == 200
    assert captured["model"] == "gpt-test"
    assert payload["round_number"] == 1
    assert payload["quality_status"] == "usable"
    assert (project_dir / "round_001" / "round_result.json").exists()


def test_api_run_project_reports_llm_errors(tmp_path, monkeypatch):
    def fake_build_api_llm(model=None):
        raise LLMResponseError("model exploded")

    monkeypatch.setattr(api, "build_api_llm", fake_build_api_llm)

    response = TestClient(app).post(
        "/projects/run",
        json={
            "project_dir": str(tmp_path / "project"),
            "project_id": "api-demo",
            "source_text": "林晚被赶出生日宴。",
        },
    )

    assert response.status_code == 502
    assert response.json()["detail"] == "model exploded"


def test_api_run_full_mock_project_writes_requested_deliverables(tmp_path):
    project_dir = tmp_path / "project"

    response = TestClient(app).post(
        "/projects/run-full-mock",
        json={
            "project_dir": str(project_dir),
            "project_id": "api-demo",
            "source_text": "林晚被赶出生日宴。",
            "locale": "en-US",
            "platform": "TikTok/Reels",
            "deliverables": ["localization", "ad_assets"],
        },
    )
    payload = response.json()

    assert response.status_code == 200
    assert payload["round_number"] == 1
    assert payload["deliverables"]["localization"]["locale"] == "en-US"
    assert payload["deliverables"]["ad_assets"]["platform"] == "TikTok/Reels"
    assert (project_dir / "round_001" / "round_result.json").exists()
    assert (project_dir / "round_001" / "localization_en-US_TikTok-Reels.json").exists()
    assert (project_dir / "round_001" / "marketing_assets_en-US_TikTok-Reels.md").exists()
    assert payload["project_status"]["rounds"][0]["localizations"] == ["en-US_TikTok-Reels"]
    assert payload["project_status"]["rounds"][0]["marketing_assets"] == [
        "en-US_TikTok-Reels"
    ]


def test_api_run_full_mock_project_rejects_unknown_deliverable(tmp_path):
    response = TestClient(app).post(
        "/projects/run-full-mock",
        json={
            "project_dir": str(tmp_path / "project"),
            "project_id": "api-demo",
            "source_text": "林晚被赶出生日宴。",
            "deliverables": ["thumbnail"],
        },
    )

    assert response.status_code == 422


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


def test_api_live_deliverable_endpoints_use_configured_llm_and_model(
    tmp_path,
    happy_round_outputs,
    monkeypatch,
):
    project_dir = tmp_path / "project"
    store = ProjectStore(project_dir)
    store.write_round_result(build_round_result(1, happy_round_outputs))
    captured_models = []
    outputs = [
        demo_localization_output("en-US", "TikTok/Reels"),
        demo_marketing_assets("en-US", "TikTok/Reels"),
    ]

    def fake_build_api_llm(model=None):
        captured_models.append(model)
        return StaticJsonLLM([outputs.pop(0)])

    monkeypatch.setattr(api, "build_api_llm", fake_build_api_llm)
    client = TestClient(app)

    localize_response = client.post(
        "/projects/localize",
        json={
            "project_dir": str(project_dir),
            "locale": "en-US",
            "platform": "TikTok/Reels",
            "model": "gpt-test",
        },
    )
    ad_assets_response = client.post(
        "/projects/ad-assets",
        json={
            "project_dir": str(project_dir),
            "locale": "en-US",
            "platform": "TikTok/Reels",
            "model": "gpt-test",
        },
    )

    assert localize_response.status_code == 200
    assert ad_assets_response.status_code == 200
    assert captured_models == ["gpt-test", "gpt-test"]
    assert (project_dir / "round_001" / "localization_en-US_TikTok-Reels.json").exists()
    assert (project_dir / "round_001" / "marketing_assets_en-US_TikTok-Reels.md").exists()


def test_api_live_deliverable_endpoints_report_llm_errors(
    tmp_path,
    happy_round_outputs,
    monkeypatch,
):
    project_dir = tmp_path / "project"
    ProjectStore(project_dir).write_round_result(build_round_result(1, happy_round_outputs))

    def fake_build_api_llm(model=None):
        raise LLMResponseError("deliverable model exploded")

    monkeypatch.setattr(api, "build_api_llm", fake_build_api_llm)

    response = TestClient(app).post(
        "/projects/localize",
        json={
            "project_dir": str(project_dir),
            "locale": "en-US",
            "platform": "TikTok/Reels",
        },
    )

    assert response.status_code == 502
    assert response.json()["detail"] == "deliverable model exploded"


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
