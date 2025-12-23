from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

import pytest
from httpx import ASGITransport, AsyncClient


def _today_jst() -> date:
    return datetime.now(ZoneInfo("Asia/Tokyo")).date()


@pytest.fixture
def scheduler_env_with_resync(db_urls, setup_test_db, tmp_path, monkeypatch):
    monkeypatch.setenv("TESTING", "false")
    monkeypatch.setenv("SCHEDULER_ENABLED", "true")
    monkeypatch.setenv("SCHEDULER_LOCK_PATH", str(tmp_path / "scheduler.lock"))
    monkeypatch.setenv("SCHEDULER_POLL_SECONDS", "300")

    from src.fastapi_app.config import get_settings
    from src.fastapi_app import scheduler_runtime
    from src.scheduler import scheduler as apscheduler

    get_settings.cache_clear()
    scheduler_runtime.stop_scheduler()
    scheduler_runtime._reset_for_tests()

    from src.fastapi_app.main import create_app as create_fastapi_app

    app = create_fastapi_app()

    try:
        yield app
    finally:
        try:
            apscheduler.remove_all_jobs()
        finally:
            scheduler_runtime.stop_scheduler()


@pytest.mark.asyncio
async def test_startup_resync_bootstraps_existing_db_job(scheduler_env_with_resync, app, setup_test_db):
    with app.app_context():
        from src.models import db
        from src.models.job import Job

        job = Job(
            name="resync-existing-job",
            cron_expression="*/15 * * * *",
            target_url="https://example.com/hook",
            category="general",
            end_date=_today_jst() + timedelta(days=30),
            pic_team=None,
            created_by=setup_test_db["user"].id,
            is_active=True,
        )
        db.session.add(job)
        db.session.commit()
        db.session.refresh(job)
        job_id = job.id

    from src.fastapi_app import scheduler_runtime
    from src.scheduler import scheduler as apscheduler

    started = scheduler_runtime.start_scheduler()
    assert started is True
    assert apscheduler.get_job(job_id) is not None


@pytest.mark.asyncio
async def test_resync_endpoint_removes_orphaned_scheduler_jobs(scheduler_env_with_resync, admin_access_token):
    from src.fastapi_app import scheduler_runtime

    started = scheduler_runtime.start_scheduler()
    assert started is True

    from apscheduler.triggers.cron import CronTrigger
    from src.scheduler import scheduler as apscheduler

    apscheduler.add_job(
        func=lambda: None,
        trigger=CronTrigger.from_crontab("*/5 * * * *", timezone=ZoneInfo("Asia/Tokyo")),
        id="orphan-job-id",
        name="orphan-job",
        replace_existing=True,
    )
    assert apscheduler.get_job("orphan-job-id") is not None

    transport = ASGITransport(app=scheduler_env_with_resync)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/v2/scheduler/resync",
            headers={"Authorization": f"Bearer {admin_access_token}"},
        )
        assert resp.status_code == 200

    assert apscheduler.get_job("orphan-job-id") is None


@pytest.mark.asyncio
async def test_resync_auto_pauses_expired_jobs(scheduler_env_with_resync, app, setup_test_db):
    expired_date = _today_jst() - timedelta(days=1)

    with app.app_context():
        from src.models import db
        from src.models.job import Job

        job = Job(
            name="resync-expired-job",
            cron_expression="0 * * * *",
            target_url="https://example.com/hook",
            category="general",
            end_date=expired_date,
            pic_team=None,
            created_by=setup_test_db["user"].id,
            is_active=True,
        )
        db.session.add(job)
        db.session.commit()
        db.session.refresh(job)
        job_id = job.id

    from src.fastapi_app import scheduler_runtime
    from src.fastapi_app.scheduler_reconcile import resync_from_db
    from src.database.session import get_db_session
    from src.models.job import Job
    from src.scheduler import scheduler as apscheduler

    started = scheduler_runtime.start_scheduler()
    assert started is True

    resync_from_db()
    assert apscheduler.get_job(job_id) is None

    with get_db_session() as session:
        refreshed = session.get(Job, job_id)
        assert refreshed is not None
        assert refreshed.is_active is False
