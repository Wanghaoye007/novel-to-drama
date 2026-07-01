from concurrent.futures import ThreadPoolExecutor, as_completed
import json
import time

from fastapi.testclient import TestClient

import novel_drama_engine.api as api
from novel_drama_engine.api import app
from novel_drama_engine.demo import demo_localization_output, demo_marketing_assets
from novel_drama_engine.jobs import JobStore
from novel_drama_engine.llm import LLMResponseError, StaticJsonLLM
from novel_drama_engine.models import RoundResult
from novel_drama_engine.platform_access import PlatformAccessStore
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


def test_api_localization_profiles_list_defaults():
    response = TestClient(app).get("/localization-profiles")
    payload = response.json()

    assert response.status_code == 200
    assert payload["profile_count"] >= 4
    assert {profile["profile_id"] for profile in payload["profiles"]} >= {
        "us_tiktok",
        "us_reela",
        "jp_reela",
        "sea_tiktok",
    }


def test_api_localization_profiles_read_one_profile():
    response = TestClient(app).get("/localization-profiles/jp_reela")
    payload = response.json()

    assert response.status_code == 200
    assert payload["profile"]["profile_id"] == "jp_reela"
    assert payload["profile"]["locale"] == "ja-JP"
    assert payload["profile"]["platform"] == "Reela"


def test_api_localization_profiles_report_missing_profile():
    response = TestClient(app).get("/localization-profiles/missing")

    assert response.status_code == 404


def test_api_platform_auth_check_validates_and_consumes_key(tmp_path):
    store_path = tmp_path / "api_keys.json"
    _, api_key = PlatformAccessStore(store_path).create_key(
        name="beta",
        scopes=["project:read"],
        monthly_quota=1,
    )
    client = TestClient(app)

    missing = client.post(
        "/platform/auth/check",
        params={"store_path": str(store_path), "scope": "project:read"},
    )
    first = client.post(
        "/platform/auth/check",
        params={
            "store_path": str(store_path),
            "scope": "project:read",
            "consume": "true",
        },
        headers={"X-API-Key": api_key},
    )
    exceeded = client.post(
        "/platform/auth/check",
        params={
            "store_path": str(store_path),
            "scope": "project:read",
            "consume": "true",
        },
        headers={"X-API-Key": api_key},
    )
    wrong_scope = client.post(
        "/platform/auth/check",
        params={"store_path": str(store_path), "scope": "delivery:export"},
        headers={"X-API-Key": api_key},
    )

    assert missing.status_code == 401
    assert first.status_code == 200
    assert first.json()["key"]["usage_this_month"] == 1
    assert exceeded.status_code == 429
    assert wrong_scope.status_code == 403


def test_api_quality_samples_mock_runs_manifest(tmp_path):
    response = TestClient(app).post(
        "/quality-samples/run-mock",
        json={
            "manifest_path": "examples/quality_samples.json",
            "projects_dir": str(tmp_path / "quality"),
        },
    )
    payload = response.json()

    assert response.status_code == 200
    assert payload["schema_version"] == "quality_sample_report.v1"
    assert payload["sample_count"] == 5
    assert payload["round_count"] == 10
    assert payload["passed"] is True
    assert (
        tmp_path
        / "quality"
        / "haomen_identity_swap"
        / "round_002"
        / "round_result.json"
    ).exists()


def test_api_quality_samples_mock_reports_missing_manifest(tmp_path):
    response = TestClient(app).post(
        "/quality-samples/run-mock",
        json={
            "manifest_path": str(tmp_path / "missing.json"),
            "projects_dir": str(tmp_path / "quality"),
        },
    )

    assert response.status_code == 404


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
    assert payload["schema_version"] == "project_status.v1"
    assert payload["round_count"] == 1
    assert payload["rounds"][0]["target_episode_range"] == "EP01-EP01"
    assert payload["rounds"][0]["artifact_counts"]["round_result"] == 1
    assert payload["rounds"][0]["delivery"]["ready"] is False
    assert "missing required artifact: rendered_scripts.md" in payload["rounds"][0]["delivery"]["warnings"]
    assert payload["latest_round"]["round_number"] == 1
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


def test_api_project_status_by_id_can_include_related_jobs(tmp_path, happy_round_outputs):
    project_root = tmp_path / "projects"
    project_dir = project_root / "haomen"
    ProjectStore(project_dir).write_round_result(build_round_result(1, happy_round_outputs))
    jobs_dir = tmp_path / "jobs"
    job = JobStore(jobs_dir).create(
        kind="batch-run-mock",
        request={
            "project_root": str(project_root),
            "jobs": [
                {
                    "project_id": "haomen",
                    "source_text": "林晚被赶出生日宴。",
                }
            ],
        },
    )

    response = TestClient(app).get(
        "/projects/haomen/status",
        params={"project_root": str(project_root), "jobs_dir": str(jobs_dir)},
    )
    payload = response.json()

    assert response.status_code == 200
    assert payload["jobs"]["job_count"] == 1
    assert payload["jobs"]["status_counts"] == {"queued": 1}
    assert payload["jobs"]["jobs"][0]["job_id"] == job.job_id


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
    assert payload["schema_version"] == "workspace_status.v1"
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


def test_api_batch_run_mock_writes_multiple_projects(tmp_path):
    project_root = tmp_path / "projects"

    response = TestClient(app).post(
        "/projects/batch-run-mock",
        json={
            "project_root": str(project_root),
            "jobs": [
                {
                    "project_id": "haomen",
                    "source_text": "林晚被赶出生日宴。",
                    "locale": "en-US",
                    "platform": "TikTok/Reels",
                    "deliverables": ["localization", "ad_assets", "video_brief"],
                    "duration_seconds": 60,
                },
                {
                    "project_id": "genre/xianxia/book",
                    "source_text": "师姐当众退婚。",
                },
            ],
        },
    )
    payload = response.json()

    assert response.status_code == 200
    assert payload["status"] == "ok"
    assert payload["successes"] == 2
    assert payload["failures"] == 0
    report_path = project_root / "batch_report.json"
    report_payload = json.loads(report_path.read_text(encoding="utf-8"))
    assert payload["report_path"] == str(report_path)
    assert report_payload["successes"] == 2
    assert [result["project_id"] for result in payload["results"]] == [
        "haomen",
        "genre/xianxia/book",
    ]
    assert payload["workspace_status"]["project_count"] == 2
    assert (project_root / "haomen" / "round_001" / "round_result.json").exists()
    assert (
        project_root / "haomen" / "round_001" / "localization_en-US_TikTok-Reels.json"
    ).exists()
    assert (
        project_root
        / "haomen"
        / "round_001"
        / "marketing_assets_en-US_TikTok-Reels.json"
    ).exists()
    assert (project_root / "haomen" / "round_001" / "video_brief.json").exists()
    assert (project_root / "genre" / "xianxia" / "book" / "round_001").exists()


def poll_api_job(client, job_id, jobs_dir):
    for _ in range(100):
        response = client.get(
            f"/jobs/{job_id}",
            params={"jobs_dir": str(jobs_dir)},
        )
        assert response.status_code == 200
        payload = response.json()
        if payload["status"] in {"succeeded", "failed", "canceled"}:
            return payload
        time.sleep(0.02)
    raise AssertionError("job did not complete")


class DeferredExecutor:
    def __init__(self):
        self.calls = []

    def submit(self, fn, *args, **kwargs):
        self.calls.append((fn, args, kwargs))
        return None


def test_api_batch_run_mock_job_completes_and_persists_status(tmp_path):
    project_root = tmp_path / "projects"
    jobs_dir = tmp_path / "jobs"
    client = TestClient(app)

    response = client.post(
        "/jobs/batch-run-mock",
        json={
            "jobs_dir": str(jobs_dir),
            "project_root": str(project_root),
            "jobs": [
                {
                    "project_id": "haomen",
                    "source_text": "林晚被赶出生日宴。",
                    "locale": "en-US",
                    "platform": "TikTok/Reels",
                    "deliverables": ["video_brief"],
                    "duration_seconds": 60,
                }
            ],
        },
    )
    payload = response.json()

    assert response.status_code == 200
    assert payload["kind"] == "batch-run-mock"
    assert payload["status"] in {"queued", "running"}
    job_id = payload["job_id"]
    assert payload["jobs_dir"] == str(jobs_dir.resolve())
    assert (jobs_dir / f"{job_id}.json").exists()

    job_payload = poll_api_job(client, job_id, jobs_dir)

    assert job_payload["status"] == "succeeded"
    assert job_payload["result"]["status"] == "ok"
    assert job_payload["result"]["successes"] == 1
    assert job_payload["result"]["results"][0]["deliverables"]["video_brief"][
        "episode_count"
    ] == 1
    assert job_payload["result"]["report_path"] == str(
        project_root / "batch_report.json"
    )
    assert (project_root / "batch_report.json").exists()
    assert (project_root / "haomen" / "round_001" / "video_brief.json").exists()

    list_response = client.get(
        "/jobs",
        params={"jobs_dir": str(jobs_dir)},
    )
    list_payload = list_response.json()

    assert list_response.status_code == 200
    assert list_payload["job_count"] == 1
    assert list_payload["jobs"][0]["job_id"] == job_id
    assert list_payload["jobs"][0]["status"] == "succeeded"


def test_api_batch_run_mock_job_retry_creates_new_attempt(tmp_path):
    project_root = tmp_path / "projects"
    jobs_dir = tmp_path / "jobs"
    client = TestClient(app)

    response = client.post(
        "/jobs/batch-run-mock",
        json={
            "jobs_dir": str(jobs_dir),
            "project_root": str(project_root),
            "jobs": [
                {
                    "project_id": "haomen",
                    "source_text": "林晚被赶出生日宴。",
                    "deliverables": ["video_brief"],
                }
            ],
        },
    )
    first_job = poll_api_job(client, response.json()["job_id"], jobs_dir)

    retry_response = client.post(
        f"/jobs/{first_job['job_id']}/retry",
        params={"jobs_dir": str(jobs_dir)},
    )
    retry_payload = retry_response.json()

    assert retry_response.status_code == 200
    assert retry_payload["kind"] == "batch-run-mock"
    assert retry_payload["attempt"] == 2
    assert retry_payload["parent_job_id"] == first_job["job_id"]

    second_job = poll_api_job(client, retry_payload["job_id"], jobs_dir)
    list_response = client.get("/jobs", params={"jobs_dir": str(jobs_dir)})
    list_payload = list_response.json()

    assert second_job["status"] == "succeeded"
    assert second_job["parent_job_id"] == first_job["job_id"]
    assert second_job["attempt"] == 2
    assert list_payload["job_count"] == 2
    assert list_payload["jobs"][0]["job_id"] == second_job["job_id"]
    assert (project_root / "haomen" / "round_001" / "video_brief.json").exists()
    assert (project_root / "haomen" / "round_002" / "video_brief.json").exists()


def test_api_batch_run_mock_job_cancel_prevents_queued_execution(
    tmp_path,
    monkeypatch,
):
    project_root = tmp_path / "projects"
    jobs_dir = tmp_path / "jobs"
    executor = DeferredExecutor()
    monkeypatch.setattr(api, "_JOB_EXECUTOR", executor)
    client = TestClient(app)

    response = client.post(
        "/jobs/batch-run-mock",
        json={
            "jobs_dir": str(jobs_dir),
            "project_root": str(project_root),
            "jobs": [
                {
                    "project_id": "haomen",
                    "source_text": "林晚被赶出生日宴。",
                    "deliverables": ["video_brief"],
                }
            ],
        },
    )
    payload = response.json()

    assert response.status_code == 200
    assert payload["status"] == "queued"
    assert len(executor.calls) == 1

    cancel_response = client.post(
        f"/jobs/{payload['job_id']}/cancel",
        params={"jobs_dir": str(jobs_dir)},
    )
    cancel_payload = cancel_response.json()

    assert cancel_response.status_code == 200
    assert cancel_payload["status"] == "canceled"
    assert cancel_payload["cancel_requested"] is True
    assert cancel_payload["cancel_requested_at"]

    fn, args, kwargs = executor.calls[0]
    fn(*args, **kwargs)
    final_payload = client.get(
        f"/jobs/{payload['job_id']}",
        params={"jobs_dir": str(jobs_dir)},
    ).json()

    assert final_payload["status"] == "canceled"
    assert not (project_root / "haomen" / "round_001").exists()


def test_api_batch_run_mock_job_cancel_rejects_completed_job(tmp_path):
    project_root = tmp_path / "projects"
    jobs_dir = tmp_path / "jobs"
    client = TestClient(app)

    response = client.post(
        "/jobs/batch-run-mock",
        json={
            "jobs_dir": str(jobs_dir),
            "project_root": str(project_root),
            "jobs": [
                {
                    "project_id": "haomen",
                    "source_text": "林晚被赶出生日宴。",
                }
            ],
        },
    )
    completed = poll_api_job(client, response.json()["job_id"], jobs_dir)

    cancel_response = client.post(
        f"/jobs/{completed['job_id']}/cancel",
        params={"jobs_dir": str(jobs_dir)},
    )

    assert completed["status"] == "succeeded"
    assert cancel_response.status_code == 409
    assert (
        cancel_response.json()["detail"]
        == "Only queued or running jobs can be canceled"
    )


def test_api_jobs_list_filters_by_status_and_kind(tmp_path):
    jobs_dir = tmp_path / "jobs"
    store = JobStore(jobs_dir)
    request = {
        "project_root": str(tmp_path / "projects"),
        "jobs": [{"project_id": "haomen", "source_text": "林晚被赶出生日宴。"}],
    }
    queued = store.create(kind="batch-run-mock", request=request)
    failed = store.create(kind="batch-run", request=request)
    canceled = store.create(kind="batch-run-mock", request=request)
    store.update(failed.job_id, status="failed", error="model exploded")
    store.update(canceled.job_id, status="canceled")
    client = TestClient(app)

    failed_response = client.get(
        "/jobs",
        params={"jobs_dir": str(jobs_dir), "status": "failed"},
    )
    mock_response = client.get(
        "/jobs",
        params={"jobs_dir": str(jobs_dir), "kind": "batch-run-mock"},
    )

    assert failed_response.status_code == 200
    assert failed_response.json()["job_count"] == 1
    assert failed_response.json()["total_job_count"] == 3
    assert failed_response.json()["filters"] == {"status": "failed", "kind": None}
    assert failed_response.json()["jobs"][0]["job_id"] == failed.job_id
    assert failed_response.json()["status_counts"] == {
        "canceled": 1,
        "failed": 1,
        "queued": 1,
    }
    assert mock_response.status_code == 200
    assert mock_response.json()["job_count"] == 2
    assert {job["job_id"] for job in mock_response.json()["jobs"]} == {
        queued.job_id,
        canceled.job_id,
    }
    assert mock_response.json()["kind_counts"] == {
        "batch-run": 1,
        "batch-run-mock": 2,
    }


def test_api_batch_run_live_job_uses_configured_llm_and_model(
    tmp_path,
    happy_round_outputs,
    monkeypatch,
):
    project_root = tmp_path / "projects"
    jobs_dir = tmp_path / "jobs"
    captured = {}

    def fake_build_api_llm(model=None):
        captured["model"] = model
        return StaticJsonLLM(
            [
                *happy_round_outputs,
                demo_localization_output("en-US", "TikTok/Reels"),
                demo_marketing_assets("en-US", "TikTok/Reels"),
            ]
        )

    monkeypatch.setattr(api, "build_api_llm", fake_build_api_llm)
    client = TestClient(app)

    response = client.post(
        "/jobs/batch-run",
        json={
            "jobs_dir": str(jobs_dir),
            "project_root": str(project_root),
            "model": "gpt-test",
            "jobs": [
                {
                    "project_id": "haomen",
                    "source_text": "林晚被赶出生日宴。",
                    "locale": "en-US",
                    "platform": "TikTok/Reels",
                    "deliverables": ["localization", "ad_assets"],
                }
            ],
        },
    )
    payload = response.json()

    assert response.status_code == 200
    assert payload["kind"] == "batch-run"
    job_payload = poll_api_job(client, payload["job_id"], jobs_dir)

    assert captured["model"] == "gpt-test"
    assert job_payload["status"] == "succeeded"
    assert job_payload["result"]["successes"] == 1
    assert sorted(job_payload["result"]["results"][0]["deliverables"]) == [
        "ad_assets",
        "localization",
    ]
    assert (
        project_root / "haomen" / "round_001" / "localization_en-US_TikTok-Reels.json"
    ).exists()
    assert (
        project_root
        / "haomen"
        / "round_001"
        / "marketing_assets_en-US_TikTok-Reels.json"
    ).exists()


def test_api_job_status_reports_missing_job(tmp_path):
    response = TestClient(app).get(
        "/jobs/missing",
        params={"jobs_dir": str(tmp_path / "jobs")},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Job not found"


def test_api_batch_run_mock_continues_after_job_failure(tmp_path):
    project_root = tmp_path / "projects"

    response = TestClient(app).post(
        "/projects/batch-run-mock",
        json={
            "project_root": str(project_root),
            "jobs": [
                {
                    "project_id": "bad",
                    "source_text": "   ",
                },
                {
                    "project_id": "good",
                    "source_text": "林晚被赶出生日宴。",
                },
            ],
        },
    )
    payload = response.json()

    assert response.status_code == 200
    assert payload["status"] == "partial"
    assert payload["successes"] == 1
    assert payload["failures"] == 1
    assert [result["status"] for result in payload["results"]] == ["failed", "ok"]
    assert payload["results"][0]["error"] == "source_text is empty"
    assert (project_root / "good" / "round_001" / "round_result.json").exists()


def test_api_batch_run_uses_configured_llm_and_model(
    tmp_path,
    happy_round_outputs,
    monkeypatch,
):
    project_root = tmp_path / "projects"
    captured = {}

    def fake_build_api_llm(model=None):
        captured["model"] = model
        return StaticJsonLLM(
            [
                *happy_round_outputs,
                demo_localization_output("en-US", "TikTok/Reels"),
                demo_marketing_assets("en-US", "TikTok/Reels"),
            ]
        )

    monkeypatch.setattr(api, "build_api_llm", fake_build_api_llm)

    response = TestClient(app).post(
        "/projects/batch-run",
        json={
            "project_root": str(project_root),
            "model": "gpt-test",
            "jobs": [
                {
                    "project_id": "haomen",
                    "source_text": "林晚被赶出生日宴。",
                    "locale": "en-US",
                    "platform": "TikTok/Reels",
                    "deliverables": ["localization", "ad_assets"],
                }
            ],
        },
    )
    payload = response.json()

    assert response.status_code == 200
    assert captured["model"] == "gpt-test"
    assert payload["status"] == "ok"
    assert payload["successes"] == 1
    assert (project_root / "haomen" / "round_001" / "round_result.json").exists()
    assert (project_root / "haomen" / "round_001" / "marketing_assets_en-US_TikTok-Reels.json").exists()


def test_api_project_status_handles_empty_project(tmp_path):
    response = TestClient(app).get(
        "/projects/status",
        params={"project_dir": str(tmp_path / "missing")},
    )
    payload = response.json()

    assert response.status_code == 200
    assert payload["round_count"] == 0
    assert payload["rounds"] == []


def test_api_project_artifacts_list_and_read_content(tmp_path, happy_round_outputs):
    project_dir = tmp_path / "project"
    store = ProjectStore(project_dir)
    store.write_round_result(build_round_result(1, happy_round_outputs))
    store.write_text_artifact(1, "rendered_scripts.md", "短剧脚本")
    client = TestClient(app)

    list_response = client.get(
        "/projects/artifacts",
        params={"project_dir": str(project_dir), "round_number": 1},
    )
    list_payload = list_response.json()
    read_response = client.get(
        "/projects/artifact",
        params={
            "project_dir": str(project_dir),
            "round_number": 1,
            "name": "rendered_scripts.md",
        },
    )
    read_payload = read_response.json()

    assert list_response.status_code == 200
    assert [artifact["name"] for artifact in list_payload["artifacts"]] == [
        "rendered_scripts.md",
        "round_result.json",
    ]
    assert read_response.status_code == 200
    assert read_payload["content_type"] == "text/markdown"
    assert read_payload["content"] == "短剧脚本"


def test_api_project_round_artifacts_by_id_reads_nested_project(
    tmp_path,
    happy_round_outputs,
):
    project_root = tmp_path / "projects"
    project_dir = project_root / "genre" / "haomen" / "book"
    store = ProjectStore(project_dir)
    store.write_round_result(build_round_result(1, happy_round_outputs))
    store.write_text_artifact(1, "rendered_scripts.md", "短剧脚本")

    response = TestClient(app).get(
        "/projects/genre/haomen/book/rounds/1/artifacts",
        params={"project_root": str(project_root)},
    )
    payload = response.json()

    assert response.status_code == 200
    assert payload["project_dir"] == str(project_dir)
    assert [artifact["name"] for artifact in payload["artifacts"]] == [
        "rendered_scripts.md",
        "round_result.json",
    ]


def test_api_project_artifact_rejects_round_directory_escape(tmp_path, happy_round_outputs):
    project_dir = tmp_path / "project"
    ProjectStore(project_dir).write_round_result(build_round_result(1, happy_round_outputs))

    response = TestClient(app).get(
        "/projects/artifact",
        params={
            "project_dir": str(project_dir),
            "round_number": 1,
            "name": "../round_001/round_result.json",
        },
    )

    assert response.status_code == 400
    assert (
        response.json()["detail"]
        == "artifact name must be a filename inside the round directory"
    )


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
            "deliverables": ["localization", "ad_assets", "video_brief"],
            "duration_seconds": 60,
        },
    )
    payload = response.json()

    assert response.status_code == 200
    assert payload["round_number"] == 1
    assert payload["deliverables"]["localization"]["locale"] == "en-US"
    assert payload["deliverables"]["ad_assets"]["platform"] == "TikTok/Reels"
    assert payload["deliverables"]["video_brief"]["episode_count"] == 1
    assert (project_dir / "round_001" / "round_result.json").exists()
    assert (project_dir / "round_001" / "localization_en-US_TikTok-Reels.json").exists()
    assert (project_dir / "round_001" / "marketing_assets_en-US_TikTok-Reels.md").exists()
    assert (project_dir / "round_001" / "video_brief.json").exists()
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


def test_api_run_full_project_uses_configured_llm_for_requested_deliverables(
    tmp_path,
    happy_round_outputs,
    monkeypatch,
):
    project_dir = tmp_path / "project"
    captured = {}

    def fake_build_api_llm(model=None):
        captured["model"] = model
        return StaticJsonLLM(
            [
                *happy_round_outputs,
                demo_localization_output("en-US", "TikTok/Reels"),
                demo_marketing_assets("en-US", "TikTok/Reels"),
            ]
        )

    monkeypatch.setattr(api, "build_api_llm", fake_build_api_llm)

    response = TestClient(app).post(
        "/projects/run-full",
        json={
            "project_dir": str(project_dir),
            "project_id": "api-demo",
            "source_text": "林晚被赶出生日宴。",
            "locale": "en-US",
            "platform": "TikTok/Reels",
            "model": "gpt-test",
            "deliverables": ["localization", "ad_assets"],
        },
    )
    payload = response.json()

    assert response.status_code == 200
    assert captured["model"] == "gpt-test"
    assert payload["round_number"] == 1
    assert sorted(payload["deliverables"]) == ["ad_assets", "localization"]
    assert (project_dir / "round_001" / "round_result.json").exists()
    assert (project_dir / "round_001" / "localization_en-US_TikTok-Reels.json").exists()
    assert (project_dir / "round_001" / "marketing_assets_en-US_TikTok-Reels.json").exists()


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


def test_api_export_video_brief_writes_outputs(tmp_path, happy_round_outputs):
    project_dir = tmp_path / "project"
    ProjectStore(project_dir).write_round_result(build_round_result(1, happy_round_outputs))

    response = TestClient(app).post(
        "/projects/export-video-brief",
        json={
            "project_dir": str(project_dir),
            "duration_seconds": 60,
            "aspect_ratio": "9:16",
        },
    )
    payload = response.json()

    assert response.status_code == 200
    assert payload["round_number"] == 1
    assert payload["brief"]["episodes"][0]["target_duration_seconds"] == 60
    assert payload["project_status"]["rounds"][0]["video_brief"] is True
    assert (project_dir / "round_001" / "video_brief.json").exists()
    assert (project_dir / "round_001" / "video_brief.md").exists()


def test_api_delivery_preflight_reports_ready_round(tmp_path, happy_round_outputs):
    project_dir = tmp_path / "project"
    store = ProjectStore(project_dir)
    store.write_round_result(build_round_result(1, happy_round_outputs))
    store.write_text_artifact(1, "rendered_scripts.md", "script text")

    response = TestClient(app).get(
        "/projects/delivery",
        params={"project_dir": str(project_dir), "round_number": 1},
    )
    payload = response.json()

    assert response.status_code == 200
    assert payload["project_dir"] == str(project_dir)
    assert payload["preflight"]["ready"] is True
    assert payload["preflight"]["warnings"] == []
    assert payload["preflight"]["round_number"] == 1


def test_api_export_delivery_writes_package(tmp_path, happy_round_outputs):
    project_dir = tmp_path / "project"
    store = ProjectStore(project_dir)
    store.write_round_result(build_round_result(1, happy_round_outputs))
    store.write_text_artifact(1, "rendered_scripts.md", "script text")

    response = TestClient(app).post(
        "/projects/export-delivery",
        json={"project_dir": str(project_dir), "round_number": 1},
    )
    payload = response.json()
    zip_path = project_dir / "round_001" / "delivery_round_001.zip"

    assert response.status_code == 200
    assert payload["package_path"] == str(zip_path)
    assert payload["preflight"]["ready"] is True
    assert payload["project_status"]["rounds"][0]["delivery"]["ready"] is True
    assert zip_path.exists()


def test_api_delivery_package_downloads_exported_zip(tmp_path, happy_round_outputs):
    project_dir = tmp_path / "project"
    store = ProjectStore(project_dir)
    store.write_round_result(build_round_result(1, happy_round_outputs))
    store.write_text_artifact(1, "rendered_scripts.md", "script text")
    client = TestClient(app)
    client.post(
        "/projects/export-delivery",
        json={"project_dir": str(project_dir), "round_number": 1},
    )

    response = client.get(
        "/projects/delivery/package",
        params={"project_dir": str(project_dir), "round_number": 1},
    )

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/zip"
    assert "delivery_round_001.zip" in response.headers["content-disposition"]
    assert response.content.startswith(b"PK")


def test_api_delivery_package_reports_missing_zip(tmp_path, happy_round_outputs):
    project_dir = tmp_path / "project"
    ProjectStore(project_dir).write_round_result(build_round_result(1, happy_round_outputs))

    response = TestClient(app).get(
        "/projects/delivery/package",
        params={"project_dir": str(project_dir), "round_number": 1},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Delivery package not found"


def test_api_export_delivery_blocks_when_preflight_has_warnings(
    tmp_path,
    happy_round_outputs,
):
    project_dir = tmp_path / "project"
    ProjectStore(project_dir).write_round_result(build_round_result(1, happy_round_outputs))

    response = TestClient(app).post(
        "/projects/export-delivery",
        json={"project_dir": str(project_dir), "round_number": 1},
    )
    payload = response.json()

    assert response.status_code == 409
    assert "missing required artifact: rendered_scripts.md" in payload["detail"]["warnings"]
    assert payload["detail"]["preflight"]["ready"] is False
    assert not (project_dir / "round_001" / "delivery_round_001.zip").exists()


def test_api_project_round_delivery_endpoints_support_nested_project_ids(
    tmp_path,
    happy_round_outputs,
):
    project_root = tmp_path / "projects"
    project_dir = project_root / "genre" / "haomen" / "book"
    store = ProjectStore(project_dir)
    store.write_round_result(build_round_result(1, happy_round_outputs))

    preflight_response = TestClient(app).get(
        "/projects/genre/haomen/book/rounds/1/delivery",
        params={"project_root": str(project_root)},
    )
    export_response = TestClient(app).post(
        "/projects/genre/haomen/book/rounds/1/delivery/export",
        params={"project_root": str(project_root), "allow_issues": "true"},
    )
    export_payload = export_response.json()

    assert preflight_response.status_code == 200
    assert preflight_response.json()["preflight"]["ready"] is False
    assert export_response.status_code == 200
    assert export_payload["preflight"]["ready"] is False
    assert (
        export_payload["package_path"]
        == str(project_dir / "round_001" / "delivery_round_001.zip")
    )
    assert (project_dir / "round_001" / "delivery_round_001.zip").exists()


def test_api_project_round_delivery_package_downloads_nested_project_zip(
    tmp_path,
    happy_round_outputs,
):
    project_root = tmp_path / "projects"
    project_dir = project_root / "genre" / "haomen" / "book"
    store = ProjectStore(project_dir)
    store.write_round_result(build_round_result(1, happy_round_outputs))
    store.write_text_artifact(1, "rendered_scripts.md", "script text")
    client = TestClient(app)
    client.post(
        "/projects/genre/haomen/book/rounds/1/delivery/export",
        params={"project_root": str(project_root)},
    )

    response = client.get(
        "/projects/genre/haomen/book/rounds/1/delivery/package",
        params={"project_root": str(project_root)},
    )

    assert response.status_code == 200
    assert response.content.startswith(b"PK")


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
