from datetime import datetime, timezone

import pytest


@pytest.fixture
def seed_jobs(app, setup_test_db):
    with app.app_context():
        from src.models import db
        from src.models.job import Job
        from src.models.job_execution import JobExecution

        user = setup_test_db["user"]

        job_1 = Job(
            name="job-1",
            cron_expression="0 * * * *",
            category="general",
            created_by=user.id,
            is_active=True,
        )
        job_1.set_metadata({"a": 1})
        db.session.add(job_1)

        job_2 = Job(
            name="job-2",
            cron_expression="15 * * * *",
            category="general",
            created_by=user.id,
            is_active=False,
        )
        db.session.add(job_2)
        db.session.flush()

        exec_1 = JobExecution(
            job_id=job_1.id,
            status="success",
            trigger_type="manual",
            started_at=datetime(2025, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
        )
        db.session.add(exec_1)
        db.session.commit()

        return {
            "job_1_id": job_1.id,
            "job_2_id": job_2.id,
            "exec_1_id": exec_1.id,
        }


@pytest.mark.asyncio
async def test_list_jobs_requires_auth(async_client, seed_jobs):
    response = await async_client.get("/api/v2/jobs")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_list_jobs_returns_expected_shape(async_client, user_access_token, seed_jobs):
    response = await async_client.get(
        "/api/v2/jobs",
        headers={"Authorization": f"Bearer {user_access_token}"},
    )
    assert response.status_code == 200
    payload = response.json()

    assert payload["count"] == 2
    assert isinstance(payload["jobs"], list)
    assert {job["name"] for job in payload["jobs"]} == {"job-1", "job-2"}

    job_1_payload = next(job for job in payload["jobs"] if job["name"] == "job-1")
    assert job_1_payload["last_execution_at"] is not None
    assert job_1_payload["next_execution_at"] is not None
    assert job_1_payload["metadata"] == {"a": 1}

    job_2_payload = next(job for job in payload["jobs"] if job["name"] == "job-2")
    assert job_2_payload["last_execution_at"] is None
    assert job_2_payload["next_execution_at"] is None


@pytest.mark.asyncio
async def test_get_job_by_id(async_client, viewer_access_token, seed_jobs):
    job_id = seed_jobs["job_1_id"]
    response = await async_client.get(
        f"/api/v2/jobs/{job_id}",
        headers={"Authorization": f"Bearer {viewer_access_token}"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["job"]["id"] == job_id
    assert payload["job"]["name"] == "job-1"
    assert payload["job"]["last_execution_at"] is not None
    assert payload["job"]["next_execution_at"] is not None


@pytest.mark.asyncio
async def test_get_job_not_found(async_client, user_access_token, seed_jobs):
    response = await async_client.get(
        "/api/v2/jobs/does-not-exist",
        headers={"Authorization": f"Bearer {user_access_token}"},
    )
    assert response.status_code == 404
    payload = response.json()
    assert payload["error"] == "Job not found"
