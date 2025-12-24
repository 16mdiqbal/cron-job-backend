from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pytest


def _today_jst():
    return datetime.now(ZoneInfo("Asia/Tokyo")).date()


@pytest.fixture
def seed_execute_jobs(db_session, setup_test_db):
    from src.models.job import Job

    admin = setup_test_db["admin"]
    user = setup_test_db["user"]

    webhook_job = Job(
        name="execute-webhook-job",
        cron_expression="0 * * * *",
        end_date=_today_jst(),
        created_by=user.id,
        target_url="https://example.com/hook",
        is_active=True,
    )
    webhook_job.set_metadata({"hello": "world"})
    db_session.add(webhook_job)

    github_job = Job(
        name="execute-github-job",
        cron_expression="15 * * * *",
        end_date=_today_jst(),
        created_by=user.id,
        target_url=None,
        github_owner="octo",
        github_repo="repo",
        github_workflow_name="workflow.yml",
        is_active=True,
    )
    db_session.add(github_job)

    expired_job = Job(
        name="execute-expired-job",
        cron_expression="0 * * * *",
        end_date=_today_jst() - timedelta(days=1),
        created_by=user.id,
        target_url="https://example.com/hook",
        is_active=True,
    )
    db_session.add(expired_job)

    admin_job = Job(
        name="execute-admin-job",
        cron_expression="30 * * * *",
        end_date=_today_jst(),
        created_by=admin.id,
        target_url="https://example.com/hook",
        is_active=True,
    )
    db_session.add(admin_job)

    db_session.commit()

    return {
        "webhook_job_id": webhook_job.id,
        "github_job_id": github_job.id,
        "expired_job_id": expired_job.id,
        "admin_job_id": admin_job.id,
        "original_webhook_target": webhook_job.target_url,
    }


@pytest.mark.asyncio
async def test_execute_job_requires_user_or_admin(async_client, viewer_access_token, seed_execute_jobs):
    resp = await async_client.post(
        f"/api/v2/jobs/{seed_execute_jobs['webhook_job_id']}/execute",
        headers={"Authorization": f"Bearer {viewer_access_token}"},
        json={},
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_execute_job_not_owner_forbidden(async_client, user_access_token, seed_execute_jobs):
    resp = await async_client.post(
        f"/api/v2/jobs/{seed_execute_jobs['admin_job_id']}/execute",
        headers={"Authorization": f"Bearer {user_access_token}"},
        json={},
    )
    assert resp.status_code == 403
    payload = resp.json()
    assert payload["error"] == "Insufficient permissions"
    assert payload["message"] == "You can only execute your own jobs"


@pytest.mark.asyncio
async def test_execute_job_expired_auto_pauses(async_client, user_access_token, seed_execute_jobs):
    job_id = seed_execute_jobs["expired_job_id"]
    resp = await async_client.post(
        f"/api/v2/jobs/{job_id}/execute",
        headers={"Authorization": f"Bearer {user_access_token}"},
        json={},
    )
    assert resp.status_code == 400
    payload = resp.json()
    assert payload["error"] == "Job expired"

    job_detail = await async_client.get(
        f"/api/v2/jobs/{job_id}",
        headers={"Authorization": f"Bearer {user_access_token}"},
    )
    assert job_detail.status_code == 200
    assert job_detail.json()["job"]["is_active"] is False

    executions = await async_client.get(
        f"/api/v2/jobs/{job_id}/executions",
        headers={"Authorization": f"Bearer {user_access_token}"},
    )
    assert executions.status_code == 200
    assert executions.json()["total_executions"] == 0


@pytest.mark.asyncio
async def test_execute_webhook_success_uses_overrides_and_records_execution(
    async_client, user_access_token, seed_execute_jobs, monkeypatch
):
    job_id = seed_execute_jobs["webhook_job_id"]
    captured = {"method": None, "url": None, "json": None}

    async def fake_http_request(method, url, *, headers=None, json_payload=None):
        captured["method"] = method
        captured["url"] = url
        captured["json"] = json_payload
        return 200, "ok"

    monkeypatch.setattr("src.app.routers.jobs._http_request", fake_http_request)

    override_url = "https://override.example.com/hook"
    override_metadata = {"run": "manual"}
    resp = await async_client.post(
        f"/api/v2/jobs/{job_id}/execute",
        headers={"Authorization": f"Bearer {user_access_token}"},
        json={"target_url": override_url, "metadata": override_metadata},
    )
    assert resp.status_code == 200

    assert captured["method"] == "POST"
    assert captured["url"] == override_url
    assert captured["json"] == override_metadata

    job_detail = await async_client.get(
        f"/api/v2/jobs/{job_id}",
        headers={"Authorization": f"Bearer {user_access_token}"},
    )
    assert job_detail.status_code == 200
    assert job_detail.json()["job"]["target_url"] == seed_execute_jobs["original_webhook_target"]

    executions = await async_client.get(
        f"/api/v2/jobs/{job_id}/executions",
        headers={"Authorization": f"Bearer {user_access_token}"},
    )
    assert executions.status_code == 200
    payload = executions.json()
    assert payload["total_executions"] == 1
    execution = payload["executions"][0]
    assert execution["status"] == "success"
    assert execution["trigger_type"] == "manual"
    assert execution["execution_type"] == "webhook"
    assert execution["target"] == override_url
    assert execution["response_status"] == 200


@pytest.mark.asyncio
async def test_execute_github_success_records_execution(async_client, user_access_token, seed_execute_jobs, monkeypatch):
    job_id = seed_execute_jobs["github_job_id"]
    captured = {"method": None, "url": None}

    async def fake_http_request(method, url, *, headers=None, json_payload=None):
        captured["method"] = method
        captured["url"] = url
        return 204, ""

    monkeypatch.setattr("src.app.routers.jobs._http_request", fake_http_request)

    resp = await async_client.post(
        f"/api/v2/jobs/{job_id}/execute",
        headers={"Authorization": f"Bearer {user_access_token}"},
        json={"github_token": "test-token", "metadata": {"branchDetails": "main"}},
    )
    assert resp.status_code == 200

    assert captured["method"] == "POST"
    assert "https://api.github.com/repos/" in captured["url"]

    executions = await async_client.get(
        f"/api/v2/jobs/{job_id}/executions",
        headers={"Authorization": f"Bearer {user_access_token}"},
    )
    assert executions.status_code == 200
    payload = executions.json()
    assert payload["total_executions"] == 1
    execution = payload["executions"][0]
    assert execution["status"] == "success"
    assert execution["trigger_type"] == "manual"
    assert execution["execution_type"] == "github_actions"
    assert execution["response_status"] == 204


@pytest.mark.asyncio
async def test_execute_job_invalid_dispatch_url(async_client, user_access_token, seed_execute_jobs):
    job_id = seed_execute_jobs["github_job_id"]
    resp = await async_client.post(
        f"/api/v2/jobs/{job_id}/execute",
        headers={"Authorization": f"Bearer {user_access_token}"},
        json={"dispatch_url": "github.com/not-a-valid-path"},
    )
    assert resp.status_code == 400
    payload = resp.json()
    assert payload["error"] == "Invalid payload"


@pytest.mark.asyncio
async def test_execute_job_metadata_override_must_be_object(async_client, user_access_token, seed_execute_jobs):
    job_id = seed_execute_jobs["webhook_job_id"]
    resp = await async_client.post(
        f"/api/v2/jobs/{job_id}/execute",
        headers={"Authorization": f"Bearer {user_access_token}"},
        json={"metadata": ["not", "a", "dict"]},
    )
    assert resp.status_code == 400
    payload = resp.json()
    assert payload["error"] == "Invalid payload"
