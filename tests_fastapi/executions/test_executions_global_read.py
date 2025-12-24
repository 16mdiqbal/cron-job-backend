from datetime import datetime, timezone

import pytest


@pytest.fixture
def seed_global_executions(db_session, setup_test_db):
    from src.models.job import Job
    from src.models.job_execution import JobExecution

    user = setup_test_db["user"]

    job_1 = Job(
        name="job-global-1",
        cron_expression="0 * * * *",
        category="general",
        created_by=user.id,
        github_repo="repo-1",
        is_active=True,
    )
    job_2 = Job(
        name="job-global-2",
        cron_expression="15 * * * *",
        category="general",
        created_by=user.id,
        target_url="https://example.com/hook",
        is_active=True,
    )
    db_session.add_all([job_1, job_2])
    db_session.flush()

    exec_1 = JobExecution(
        job_id=job_1.id,
        status="success",
        trigger_type="manual",
        execution_type="github_actions",
        started_at=datetime(2025, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
        duration_seconds=10.0,
    )
    exec_2 = JobExecution(
        job_id=job_1.id,
        status="failed",
        trigger_type="scheduled",
        execution_type="github_actions",
        started_at=datetime(2025, 1, 2, 0, 0, 0, tzinfo=timezone.utc),
        duration_seconds=20.0,
    )
    exec_3 = JobExecution(
        job_id=job_2.id,
        status="running",
        trigger_type="manual",
        execution_type="webhook",
        started_at=datetime(2025, 1, 3, 0, 0, 0, tzinfo=timezone.utc),
    )

    db_session.add_all([exec_1, exec_2, exec_3])
    db_session.commit()

    return {
        "job_1_id": job_1.id,
        "job_2_id": job_2.id,
        "exec_1_id": exec_1.id,
        "exec_2_id": exec_2.id,
        "exec_3_id": exec_3.id,
    }


@pytest.mark.asyncio
async def test_list_executions_requires_auth(async_client, seed_global_executions):
    resp = await async_client.get("/api/v2/executions")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_list_executions_shape_and_fields(async_client, user_access_token, seed_global_executions):
    resp = await async_client.get(
        "/api/v2/executions",
        headers={"Authorization": f"Bearer {user_access_token}"},
    )
    assert resp.status_code == 200
    payload = resp.json()

    assert payload["total"] == 3
    assert payload["page"] == 1
    assert payload["limit"] == 20
    assert payload["total_pages"] == 1
    assert len(payload["executions"]) == 3

    # Ordered by started_at DESC
    assert [e["status"] for e in payload["executions"]] == ["running", "failed", "success"]

    running = payload["executions"][0]
    assert running["job_name"] == "job-global-2"
    assert running["github_repo"] is None

    failed = payload["executions"][1]
    assert failed["job_name"] == "job-global-1"
    assert failed["github_repo"] == "repo-1"


@pytest.mark.asyncio
async def test_list_executions_filters_and_pagination(async_client, user_access_token, seed_global_executions):
    job_1_id = seed_global_executions["job_1_id"]

    resp = await async_client.get(
        "/api/v2/executions",
        params={"job_id": job_1_id, "status": "success,failed", "limit": 1, "page": 2},
        headers={"Authorization": f"Bearer {user_access_token}"},
    )
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["total"] == 2
    assert payload["limit"] == 1
    assert payload["page"] == 2
    assert payload["total_pages"] == 2
    assert len(payload["executions"]) == 1


@pytest.mark.asyncio
async def test_get_execution_by_id(async_client, viewer_access_token, seed_global_executions):
    execution_id = seed_global_executions["exec_2_id"]
    resp = await async_client.get(
        f"/api/v2/executions/{execution_id}",
        headers={"Authorization": f"Bearer {viewer_access_token}"},
    )
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["execution"]["id"] == execution_id
    assert payload["execution"]["status"] == "failed"
    assert payload["execution"]["job_name"] == "job-global-1"
    assert payload["execution"]["github_repo"] == "repo-1"


@pytest.mark.asyncio
async def test_get_execution_not_found(async_client, user_access_token, seed_global_executions):
    resp = await async_client.get(
        "/api/v2/executions/does-not-exist",
        headers={"Authorization": f"Bearer {user_access_token}"},
    )
    assert resp.status_code == 404
    assert resp.json()["error"] == "Execution not found"


@pytest.mark.asyncio
async def test_execution_statistics(async_client, user_access_token, seed_global_executions):
    resp = await async_client.get(
        "/api/v2/executions/statistics",
        headers={"Authorization": f"Bearer {user_access_token}"},
    )
    assert resp.status_code == 200
    payload = resp.json()

    assert payload["total_executions"] == 3
    assert payload["successful_executions"] == 1
    assert payload["failed_executions"] == 1
    assert payload["running_executions"] == 1
    assert payload["success_rate"] == pytest.approx(33.333, abs=0.01)
    assert payload["average_duration_seconds"] == pytest.approx(15.0, abs=0.01)


@pytest.mark.asyncio
async def test_execution_statistics_job_filter_and_date_range(async_client, user_access_token, seed_global_executions):
    job_1_id = seed_global_executions["job_1_id"]

    resp = await async_client.get(
        "/api/v2/executions/statistics",
        params={"job_id": job_1_id, "from": "2025-01-01", "to": "2025-01-01"},
        headers={"Authorization": f"Bearer {user_access_token}"},
    )
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["total_executions"] == 1
    assert payload["successful_executions"] == 1
    assert payload["failed_executions"] == 0
    assert payload["running_executions"] == 0

    resp = await async_client.get(
        "/api/v2/executions/statistics",
        params={"from": "2025-01-02", "to": "2025-01-01"},
        headers={"Authorization": f"Bearer {user_access_token}"},
    )
    assert resp.status_code == 400
