from datetime import datetime, timezone

import pytest


@pytest.fixture
def seed_job_executions(db_session, setup_test_db):
    from src.models.job import Job
    from src.models.job_execution import JobExecution

    user = setup_test_db["user"]

    job = Job(
        name="job-exec",
        cron_expression="0 * * * *",
        category="general",
        created_by=user.id,
        is_active=True,
    )
    db_session.add(job)
    db_session.flush()

    exec_success = JobExecution(
        job_id=job.id,
        status="success",
        trigger_type="manual",
        started_at=datetime(2025, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
        duration_seconds=10.0,
    )
    exec_failed = JobExecution(
        job_id=job.id,
        status="failed",
        trigger_type="scheduled",
        started_at=datetime(2025, 1, 2, 0, 0, 0, tzinfo=timezone.utc),
        duration_seconds=20.0,
    )
    exec_running = JobExecution(
        job_id=job.id,
        status="running",
        trigger_type="manual",
        started_at=datetime(2025, 1, 3, 0, 0, 0, tzinfo=timezone.utc),
    )

    db_session.add_all([exec_success, exec_failed, exec_running])
    db_session.commit()

    return {
        "job_id": job.id,
        "exec_success_id": exec_success.id,
        "exec_failed_id": exec_failed.id,
        "exec_running_id": exec_running.id,
    }


@pytest.mark.asyncio
async def test_job_executions_requires_auth(async_client, seed_job_executions):
    job_id = seed_job_executions["job_id"]
    resp = await async_client.get(f"/api/v2/jobs/{job_id}/executions")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_job_executions_list_default(async_client, user_access_token, seed_job_executions):
    job_id = seed_job_executions["job_id"]
    resp = await async_client.get(
        f"/api/v2/jobs/{job_id}/executions",
        headers={"Authorization": f"Bearer {user_access_token}"},
    )
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["job_id"] == job_id
    assert payload["job_name"] == "job-exec"
    assert payload["total_executions"] == 3
    assert [e["status"] for e in payload["executions"]] == ["running", "failed", "success"]


@pytest.mark.asyncio
async def test_job_executions_list_filters(async_client, user_access_token, seed_job_executions):
    job_id = seed_job_executions["job_id"]

    resp = await async_client.get(
        f"/api/v2/jobs/{job_id}/executions",
        params={"status": "success,failed", "trigger_type": "manual"},
        headers={"Authorization": f"Bearer {user_access_token}"},
    )
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["total_executions"] == 1
    assert payload["executions"][0]["status"] == "success"


@pytest.mark.asyncio
async def test_job_executions_list_date_range(async_client, user_access_token, seed_job_executions):
    job_id = seed_job_executions["job_id"]

    # Date-only `to` is treated as inclusive day in Flask (implemented by adding 1 day, exclusive upper bound).
    resp = await async_client.get(
        f"/api/v2/jobs/{job_id}/executions",
        params={"from": "2025-01-01", "to": "2025-01-01"},
        headers={"Authorization": f"Bearer {user_access_token}"},
    )
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["total_executions"] == 1
    assert payload["executions"][0]["status"] == "success"

    # Invalid range
    resp = await async_client.get(
        f"/api/v2/jobs/{job_id}/executions",
        params={"from": "2025-01-02", "to": "2025-01-01"},
        headers={"Authorization": f"Bearer {user_access_token}"},
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_job_execution_detail(async_client, viewer_access_token, seed_job_executions):
    job_id = seed_job_executions["job_id"]
    execution_id = seed_job_executions["exec_failed_id"]

    resp = await async_client.get(
        f"/api/v2/jobs/{job_id}/executions/{execution_id}",
        headers={"Authorization": f"Bearer {viewer_access_token}"},
    )
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["job"]["id"] == job_id
    assert payload["job"]["name"] == "job-exec"
    assert payload["execution"]["id"] == execution_id
    assert payload["execution"]["status"] == "failed"


@pytest.mark.asyncio
async def test_job_execution_detail_not_found(async_client, user_access_token, seed_job_executions):
    job_id = seed_job_executions["job_id"]
    resp = await async_client.get(
        f"/api/v2/jobs/{job_id}/executions/does-not-exist",
        headers={"Authorization": f"Bearer {user_access_token}"},
    )
    assert resp.status_code == 404
    assert resp.json()["error"] == "Execution not found"


@pytest.mark.asyncio
async def test_job_execution_stats(async_client, user_access_token, seed_job_executions):
    job_id = seed_job_executions["job_id"]

    resp = await async_client.get(
        f"/api/v2/jobs/{job_id}/executions/stats",
        headers={"Authorization": f"Bearer {user_access_token}"},
    )
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["job_id"] == job_id
    assert payload["job_name"] == "job-exec"

    stats = payload["statistics"]
    assert stats["total_executions"] == 3
    assert stats["success_count"] == 1
    assert stats["failed_count"] == 1
    assert stats["running_count"] == 1
    assert stats["success_rate"] == pytest.approx(33.33, abs=0.01)
    assert stats["average_duration_seconds"] == 10.0

    assert payload["latest_execution"]["status"] == "running"
