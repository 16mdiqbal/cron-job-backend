from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pytest


def _today_jst():
    return datetime.now(ZoneInfo("Asia/Tokyo")).date()


@pytest.fixture
def seed_update_jobs(app, setup_test_db):
    with app.app_context():
        from src.models import db
        from src.models.job import Job
        from src.models.job_category import JobCategory
        from src.models.pic_team import PicTeam

        admin = setup_test_db["admin"]
        user = setup_test_db["user"]

        category = JobCategory(slug="maintenance", name="Maintenance Jobs", is_active=True)
        team = PicTeam(slug="team-a", name="Team A", slack_handle="@team-a", is_active=True)
        disabled_team = PicTeam(slug="team-b", name="Team B", slack_handle="@team-b", is_active=False)
        db.session.add_all([category, team, disabled_team])
        db.session.flush()

        job_user = Job(
            name="user-job",
            cron_expression="0 * * * *",
            category=category.slug,
            end_date=_today_jst(),
            pic_team=team.slug,
            created_by=user.id,
            target_url="https://example.com/hook",
            enable_email_notifications=True,
            notify_on_success=True,
            is_active=True,
        )
        job_user.set_notification_emails(["a@example.com"])
        db.session.add(job_user)

        job_admin = Job(
            name="admin-job",
            cron_expression="15 * * * *",
            category=category.slug,
            end_date=_today_jst(),
            pic_team=team.slug,
            created_by=admin.id,
            target_url="https://example.com/hook",
            is_active=True,
        )
        db.session.add(job_admin)

        job_dup = Job(
            name="dup-job",
            cron_expression="30 * * * *",
            category=category.slug,
            end_date=_today_jst(),
            pic_team=team.slug,
            created_by=user.id,
            target_url="https://example.com/hook",
            is_active=True,
        )
        db.session.add(job_dup)

        expired_job = Job(
            name="expired-job",
            cron_expression="0 * * * *",
            category=category.slug,
            end_date=_today_jst() - timedelta(days=1),
            pic_team=team.slug,
            created_by=user.id,
            target_url="https://example.com/hook",
            is_active=False,
        )
        db.session.add(expired_job)

        db.session.commit()

        return {
            "category_slug": category.slug,
            "category_name": category.name,
            "team_slug": team.slug,
            "disabled_team_slug": disabled_team.slug,
            "job_user_id": job_user.id,
            "job_admin_id": job_admin.id,
            "job_dup_id": job_dup.id,
            "expired_job_id": expired_job.id,
        }


@pytest.mark.asyncio
async def test_update_job_requires_user_or_admin(async_client, viewer_access_token, seed_update_jobs):
    resp = await async_client.put(
        f"/api/v2/jobs/{seed_update_jobs['job_user_id']}",
        headers={"Authorization": f"Bearer {viewer_access_token}"},
        json={"name": "x"},
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_update_job_not_owner_forbidden(async_client, user_access_token, seed_update_jobs):
    resp = await async_client.put(
        f"/api/v2/jobs/{seed_update_jobs['job_admin_id']}",
        headers={"Authorization": f"Bearer {user_access_token}"},
        json={"name": "nope"},
    )
    assert resp.status_code == 403
    payload = resp.json()
    assert payload["error"] == "Insufficient permissions"


@pytest.mark.asyncio
async def test_update_job_owner_can_update_name_and_cron(async_client, user_access_token, seed_update_jobs):
    job_id = seed_update_jobs["job_user_id"]
    resp = await async_client.put(
        f"/api/v2/jobs/{job_id}",
        headers={"Authorization": f"Bearer {user_access_token}"},
        json={"name": "user-job-updated", "cron_expression": "5 * * * *"},
    )
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["message"] == "Job updated successfully"
    assert payload["job"]["id"] == job_id
    assert payload["job"]["name"] == "user-job-updated"
    assert payload["job"]["cron_expression"] == "5 * * * *"


@pytest.mark.asyncio
async def test_update_job_duplicate_name(async_client, user_access_token, seed_update_jobs):
    job_id = seed_update_jobs["job_user_id"]
    resp = await async_client.put(
        f"/api/v2/jobs/{job_id}",
        headers={"Authorization": f"Bearer {user_access_token}"},
        json={"name": "dup-job"},
    )
    assert resp.status_code == 400
    payload = resp.json()
    assert payload["error"] == "Duplicate job name"


@pytest.mark.asyncio
async def test_update_job_invalid_cron(async_client, user_access_token, seed_update_jobs):
    job_id = seed_update_jobs["job_user_id"]
    resp = await async_client.put(
        f"/api/v2/jobs/{job_id}",
        headers={"Authorization": f"Bearer {user_access_token}"},
        json={"cron_expression": "0 * * *"},
    )
    assert resp.status_code == 400
    payload = resp.json()
    assert payload["error"] == "Invalid cron expression"


@pytest.mark.asyncio
async def test_update_job_invalid_category(async_client, user_access_token, seed_update_jobs):
    job_id = seed_update_jobs["job_user_id"]
    resp = await async_client.put(
        f"/api/v2/jobs/{job_id}",
        headers={"Authorization": f"Bearer {user_access_token}"},
        json={"category": "Does Not Exist"},
    )
    assert resp.status_code == 400
    payload = resp.json()
    assert payload["error"] == "Invalid category"


@pytest.mark.asyncio
async def test_update_job_disable_email_notifications_clears_fields(async_client, user_access_token, seed_update_jobs):
    job_id = seed_update_jobs["job_user_id"]
    resp = await async_client.put(
        f"/api/v2/jobs/{job_id}",
        headers={"Authorization": f"Bearer {user_access_token}"},
        json={"enable_email_notifications": False, "notify_on_success": True, "notification_emails": ["x@example.com"]},
    )
    assert resp.status_code == 200
    job = resp.json()["job"]
    assert job["enable_email_notifications"] is False
    assert job["notification_emails"] == []
    assert job["notify_on_success"] is False


@pytest.mark.asyncio
async def test_update_job_cannot_enable_expired(async_client, user_access_token, seed_update_jobs):
    job_id = seed_update_jobs["expired_job_id"]
    resp = await async_client.put(
        f"/api/v2/jobs/{job_id}",
        headers={"Authorization": f"Bearer {user_access_token}"},
        json={"is_active": True},
    )
    assert resp.status_code == 400
    payload = resp.json()
    assert payload["error"] == "Job expired"


@pytest.mark.asyncio
async def test_update_job_missing_target_configuration(async_client, user_access_token, seed_update_jobs):
    job_id = seed_update_jobs["job_user_id"]
    resp = await async_client.put(
        f"/api/v2/jobs/{job_id}",
        headers={"Authorization": f"Bearer {user_access_token}"},
        json={"target_url": "", "github_owner": "", "github_repo": "", "github_workflow_name": ""},
    )
    assert resp.status_code == 400
    payload = resp.json()
    assert payload["error"] == "Missing target configuration"

