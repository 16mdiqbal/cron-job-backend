from datetime import datetime
from zoneinfo import ZoneInfo

import pytest
from httpx import ASGITransport, AsyncClient


def _today_jst_str() -> str:
    today = datetime.now(ZoneInfo("Asia/Tokyo")).date()
    return today.isoformat()


@pytest.fixture
def seed_team_and_category(db_session, setup_test_db):
    from src.models.job_category import JobCategory
    from src.models.pic_team import PicTeam

    team = PicTeam(slug="team-a", name="Team A", slack_handle="@team-a", is_active=True)
    category = JobCategory(slug="maintenance", name="Maintenance Jobs", is_active=True)
    db_session.add_all([team, category])
    db_session.commit()
    return {"team_slug": team.slug, "category_slug": category.slug}


@pytest.fixture
async def scheduler_client(db_url, setup_test_db, tmp_path, monkeypatch):
    monkeypatch.setenv("TESTING", "false")
    monkeypatch.setenv("SCHEDULER_ENABLED", "true")
    monkeypatch.setenv("SCHEDULER_LOCK_PATH", str(tmp_path / "scheduler.lock"))

    from src.app.config import get_settings
    from src.app import scheduler_runtime

    get_settings.cache_clear()
    scheduler_runtime.stop_scheduler()
    scheduler_runtime._reset_for_tests()

    from src.app.main import create_app as create_fastapi_app

    app = create_fastapi_app()

    started = scheduler_runtime.start_scheduler()
    assert started is True

    from src.scheduler import scheduler as apscheduler

    apscheduler.remove_all_jobs()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        try:
            yield client
        finally:
            try:
                apscheduler.remove_all_jobs()
            finally:
                scheduler_runtime.stop_scheduler()


@pytest.mark.asyncio
async def test_create_job_schedules_apscheduler_job(scheduler_client, user_access_token, seed_team_and_category):
    resp = await scheduler_client.post(
        "/api/v2/jobs",
        headers={"Authorization": f"Bearer {user_access_token}"},
        json={
            "name": "job-schedule-create",
            "cron_expression": "*/5 * * * *",
            "end_date": _today_jst_str(),
            "pic_team": seed_team_and_category["team_slug"],
            "category": seed_team_and_category["category_slug"],
            "target_url": "https://example.com/hook",
        },
    )
    assert resp.status_code == 201
    job_id = resp.json()["job"]["id"]

    from src.scheduler import scheduler as apscheduler

    assert apscheduler.get_job(job_id) is not None


@pytest.mark.asyncio
async def test_update_job_unschedules_when_disabled(scheduler_client, user_access_token, seed_team_and_category):
    create_resp = await scheduler_client.post(
        "/api/v2/jobs",
        headers={"Authorization": f"Bearer {user_access_token}"},
        json={
            "name": "job-schedule-disable",
            "cron_expression": "*/10 * * * *",
            "end_date": _today_jst_str(),
            "pic_team": seed_team_and_category["team_slug"],
            "target_url": "https://example.com/hook",
        },
    )
    assert create_resp.status_code == 201
    job_id = create_resp.json()["job"]["id"]

    from src.scheduler import scheduler as apscheduler

    assert apscheduler.get_job(job_id) is not None

    update_resp = await scheduler_client.put(
        f"/api/v2/jobs/{job_id}",
        headers={"Authorization": f"Bearer {user_access_token}"},
        json={"is_active": False},
    )
    assert update_resp.status_code == 200
    assert apscheduler.get_job(job_id) is None


@pytest.mark.asyncio
async def test_delete_job_unschedules(scheduler_client, user_access_token, seed_team_and_category):
    create_resp = await scheduler_client.post(
        "/api/v2/jobs",
        headers={"Authorization": f"Bearer {user_access_token}"},
        json={
            "name": "job-schedule-delete",
            "cron_expression": "0 * * * *",
            "end_date": _today_jst_str(),
            "pic_team": seed_team_and_category["team_slug"],
            "target_url": "https://example.com/hook",
        },
    )
    assert create_resp.status_code == 201
    job_id = create_resp.json()["job"]["id"]

    from src.scheduler import scheduler as apscheduler

    assert apscheduler.get_job(job_id) is not None

    delete_resp = await scheduler_client.delete(
        f"/api/v2/jobs/{job_id}",
        headers={"Authorization": f"Bearer {user_access_token}"},
    )
    assert delete_resp.status_code == 200
    assert apscheduler.get_job(job_id) is None
