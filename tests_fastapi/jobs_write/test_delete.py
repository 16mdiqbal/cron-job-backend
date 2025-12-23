from datetime import datetime
from zoneinfo import ZoneInfo

import pytest


def _today_jst():
    return datetime.now(ZoneInfo("Asia/Tokyo")).date()


@pytest.fixture
def seed_delete_jobs(app, setup_test_db):
    with app.app_context():
        from src.models import db
        from src.models.job import Job

        admin = setup_test_db["admin"]
        user = setup_test_db["user"]

        user_job = Job(
            name="delete-user-job",
            cron_expression="0 * * * *",
            end_date=_today_jst(),
            created_by=user.id,
            target_url="https://example.com/hook",
            is_active=True,
        )
        db.session.add(user_job)

        admin_job = Job(
            name="delete-admin-job",
            cron_expression="15 * * * *",
            end_date=_today_jst(),
            created_by=admin.id,
            target_url="https://example.com/hook",
            is_active=True,
        )
        db.session.add(admin_job)

        db.session.commit()

        return {"user_job_id": user_job.id, "admin_job_id": admin_job.id}


@pytest.mark.asyncio
async def test_delete_job_requires_user_or_admin(async_client, viewer_access_token, seed_delete_jobs):
    resp = await async_client.delete(
        f"/api/v2/jobs/{seed_delete_jobs['user_job_id']}",
        headers={"Authorization": f"Bearer {viewer_access_token}"},
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_delete_job_not_owner_forbidden(async_client, user_access_token, seed_delete_jobs):
    resp = await async_client.delete(
        f"/api/v2/jobs/{seed_delete_jobs['admin_job_id']}",
        headers={"Authorization": f"Bearer {user_access_token}"},
    )
    assert resp.status_code == 403
    payload = resp.json()
    assert payload["error"] == "Insufficient permissions"
    assert payload["message"] == "You can only delete your own jobs"


@pytest.mark.asyncio
async def test_delete_job_owner_can_delete(async_client, user_access_token, seed_delete_jobs):
    job_id = seed_delete_jobs["user_job_id"]
    resp = await async_client.delete(
        f"/api/v2/jobs/{job_id}",
        headers={"Authorization": f"Bearer {user_access_token}"},
    )
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["message"] == "Job deleted successfully"
    assert payload["deleted_job"]["id"] == job_id
    assert payload["deleted_job"]["name"] == "delete-user-job"

    check = await async_client.get(
        f"/api/v2/jobs/{job_id}",
        headers={"Authorization": f"Bearer {user_access_token}"},
    )
    assert check.status_code == 404


@pytest.mark.asyncio
async def test_delete_job_admin_can_delete_any(async_client, admin_access_token, seed_delete_jobs):
    job_id = seed_delete_jobs["user_job_id"]
    resp = await async_client.delete(
        f"/api/v2/jobs/{job_id}",
        headers={"Authorization": f"Bearer {admin_access_token}"},
    )
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["deleted_job"]["id"] == job_id


@pytest.mark.asyncio
async def test_delete_job_not_found(async_client, admin_access_token):
    resp = await async_client.delete(
        "/api/v2/jobs/does-not-exist",
        headers={"Authorization": f"Bearer {admin_access_token}"},
    )
    assert resp.status_code == 404
    payload = resp.json()
    assert payload["error"] == "Job not found"

