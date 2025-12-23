from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pytest
from apscheduler.triggers.cron import CronTrigger


def _today_jst_str() -> str:
    today = datetime.now(ZoneInfo("Asia/Tokyo")).date()
    return today.isoformat()


@pytest.fixture
def scheduler_env(db_urls, setup_test_db, tmp_path, monkeypatch):
    monkeypatch.setenv("TESTING", "false")
    monkeypatch.setenv("SCHEDULER_ENABLED", "true")
    monkeypatch.setenv("SCHEDULER_LOCK_PATH", str(tmp_path / "scheduler.lock"))
    monkeypatch.setenv("SCHEDULER_TIMEZONE", "Asia/Tokyo")

    from src.fastapi_app.config import get_settings
    from src.fastapi_app import scheduler_runtime
    from src.scheduler import scheduler as apscheduler

    get_settings.cache_clear()
    scheduler_runtime.stop_scheduler()
    scheduler_runtime._reset_for_tests()

    started = scheduler_runtime.start_scheduler()
    assert started is True

    apscheduler.remove_all_jobs()
    try:
        yield
    finally:
        try:
            apscheduler.remove_all_jobs()
        finally:
            scheduler_runtime.stop_scheduler()


def _seed_team_and_category(app):
    with app.app_context():
        from src.models import db
        from src.models.job_category import JobCategory
        from src.models.pic_team import PicTeam

        team = PicTeam(slug="team-a", name="Team A", slack_handle="@team-a", is_active=True)
        category = JobCategory(slug="maintenance", name="Maintenance Jobs", is_active=True)
        db.session.add_all([team, category])
        db.session.commit()
        return {"team_slug": team.slug, "category_slug": category.slug}


def _get_user_id(app, username: str = "testuser") -> str:
    with app.app_context():
        from src.models.user import User

        user = User.query.filter_by(username=username).first()
        assert user is not None
        return user.id


@pytest.mark.asyncio
async def test_timezone_correctness_on_scheduled_job(scheduler_env, app, user_access_token):
    seed = _seed_team_and_category(app)

    from httpx import ASGITransport, AsyncClient
    from src.fastapi_app.main import create_app as create_fastapi_app

    fastapi_app = create_fastapi_app()
    transport = ASGITransport(app=fastapi_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/v2/jobs",
            headers={"Authorization": f"Bearer {user_access_token}"},
            json={
                "name": "job-tz-regression",
                "cron_expression": "0 * * * *",
                "end_date": _today_jst_str(),
                "pic_team": seed["team_slug"],
                "category": seed["category_slug"],
                "target_url": "https://example.com/hook",
            },
        )
        assert resp.status_code == 201
        job_id = resp.json()["job"]["id"]

    from src.scheduler import scheduler as apscheduler

    scheduled = apscheduler.get_job(job_id)
    assert scheduled is not None
    tz = getattr(scheduled.trigger, "timezone", None)
    tz_key = getattr(tz, "key", str(tz))
    assert tz_key == "Asia/Tokyo"


def test_duplicate_prevention_replace_existing(scheduler_env, app):
    seed = _seed_team_and_category(app)
    user_id = _get_user_id(app)

    from src.models import db
    from src.models.job import Job
    from src.fastapi_app.scheduler_side_effects import sync_job_schedule
    from src.scheduler import scheduler as apscheduler

    with app.app_context():
        job = Job(
            name="job-dup-regression",
            cron_expression="*/15 * * * *",
            target_url="https://example.com/hook",
            category=seed["category_slug"],
            end_date=datetime.now(ZoneInfo("Asia/Tokyo")).date(),
            pic_team=seed["team_slug"],
            created_by=user_id,
            is_active=True,
            enable_email_notifications=False,
            notify_on_success=False,
        )
        db.session.add(job)
        db.session.commit()
        db.session.refresh(job)

        assert sync_job_schedule(job) is True
        assert sync_job_schedule(job) is True
        assert len(apscheduler.get_jobs()) == 1

        job.name = "job-dup-regression-renamed"
        db.session.commit()
        db.session.refresh(job)

        assert sync_job_schedule(job) is True
        scheduled = apscheduler.get_job(job.id)
        assert scheduled is not None
        assert scheduled.name == "job-dup-regression-renamed"
        assert len(apscheduler.get_jobs()) == 1


def test_leader_only_guard_prevents_side_effects(scheduler_env, app):
    seed = _seed_team_and_category(app)
    user_id = _get_user_id(app)

    from src.models import db
    from src.models.job import Job
    from src.fastapi_app import scheduler_runtime
    from src.fastapi_app.scheduler_side_effects import sync_job_schedule
    from src.scheduler import scheduler as apscheduler

    with app.app_context():
        job = Job(
            name="job-leader-guard",
            cron_expression="*/30 * * * *",
            target_url="https://example.com/hook",
            category=seed["category_slug"],
            end_date=datetime.now(ZoneInfo("Asia/Tokyo")).date(),
            pic_team=seed["team_slug"],
            created_by=user_id,
            is_active=True,
            enable_email_notifications=False,
            notify_on_success=False,
        )
        db.session.add(job)
        db.session.commit()
        db.session.refresh(job)

        scheduler_runtime._is_leader = False
        assert sync_job_schedule(job) is False
        assert apscheduler.get_job(job.id) is None


def test_end_date_expired_job_is_unscheduled_on_sync(scheduler_env, app):
    seed = _seed_team_and_category(app)
    user_id = _get_user_id(app)

    from src.models import db
    from src.models.job import Job
    from src.fastapi_app.scheduler_side_effects import sync_job_schedule
    from src.scheduler import scheduler as apscheduler

    with app.app_context():
        job = Job(
            name="job-expiry-sync",
            cron_expression="*/5 * * * *",
            target_url="https://example.com/hook",
            category=seed["category_slug"],
            end_date=datetime.now(ZoneInfo("Asia/Tokyo")).date(),
            pic_team=seed["team_slug"],
            created_by=user_id,
            is_active=True,
            enable_email_notifications=False,
            notify_on_success=False,
        )
        db.session.add(job)
        db.session.commit()
        db.session.refresh(job)

        assert sync_job_schedule(job) is True
        assert apscheduler.get_job(job.id) is not None

        job.end_date = (datetime.now(ZoneInfo("Asia/Tokyo")).date() - timedelta(days=1))
        db.session.commit()
        db.session.refresh(job)

        assert sync_job_schedule(job) is True
        assert apscheduler.get_job(job.id) is None


def test_execute_job_auto_pauses_expired_job_and_removes_schedule(scheduler_env, app):
    seed = _seed_team_and_category(app)
    user_id = _get_user_id(app)

    from src.models import db
    from src.models.job import Job
    from src.scheduler import scheduler as apscheduler
    from src.scheduler.job_executor import execute_job

    with app.app_context():
        expired_job = Job(
            name="job-expiry-exec",
            cron_expression="0 * * * *",
            target_url="https://example.com/hook",
            category=seed["category_slug"],
            end_date=(datetime.now(ZoneInfo("Asia/Tokyo")).date() - timedelta(days=1)),
            pic_team=seed["team_slug"],
            created_by=user_id,
            is_active=True,
            enable_email_notifications=False,
            notify_on_success=False,
        )
        db.session.add(expired_job)
        db.session.commit()
        db.session.refresh(expired_job)

        apscheduler.add_job(
            func=execute_job,
            trigger=CronTrigger.from_crontab("*/5 * * * *", timezone=ZoneInfo("Asia/Tokyo")),
            args=[expired_job.id, expired_job.name, {"target_url": expired_job.target_url}],
            kwargs={"scheduler_timezone": "Asia/Tokyo"},
            id=expired_job.id,
            replace_existing=True,
        )
        assert apscheduler.get_job(expired_job.id) is not None

    execute_job(expired_job.id, expired_job.name, {"target_url": expired_job.target_url}, scheduler_timezone="Asia/Tokyo")

    with app.app_context():
        from src.models.job import Job as JobModel

        persisted = JobModel.query.get(expired_job.id)
        assert persisted is not None
        assert persisted.is_active is False

    assert apscheduler.get_job(expired_job.id) is None
