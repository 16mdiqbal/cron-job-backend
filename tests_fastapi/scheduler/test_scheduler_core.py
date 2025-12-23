from datetime import date

import pytest
from sqlalchemy import func, select

from src.database.session import get_db_session
from src.models.job import Job
from src.models.job_execution import JobExecution
from src.models.notification import Notification
from src.scheduler import job_executor


class _DummyResponse:
    def __init__(self, status_code: int, text: str = "ok"):
        self.status_code = status_code
        self.text = text


@pytest.fixture
def seed_job_for_webhook(app, setup_test_db):
    with app.app_context():
        from src.models import db

        user = setup_test_db["user"]
        job = Job(
            name="webhook-job",
            cron_expression="0 0 * * *",
            target_url="https://example.com/hook",
            created_by=user.id,
            is_active=True,
            end_date=date(2099, 1, 1),
            category="general",
            pic_team=None,
        )
        job.set_metadata({"hello": "world"})  # Forces webhook POST path in executor.
        db.session.add(job)
        db.session.commit()
        return job.id


@pytest.fixture
def seed_job_for_github(app, setup_test_db):
    with app.app_context():
        from src.models import db

        user = setup_test_db["user"]
        job = Job(
            name="github-job",
            cron_expression="0 0 * * *",
            github_owner="Pay-Baymax",
            github_repo="qa-automate-apiqa",
            github_workflow_name="API_Launcher",
            created_by=user.id,
            is_active=True,
            end_date=date(2099, 1, 1),
            category="general",
            pic_team=None,
        )
        db.session.add(job)
        db.session.commit()
        return job.id


@pytest.fixture
def seed_job_inactive(app, setup_test_db):
    with app.app_context():
        from src.models import db

        user = setup_test_db["user"]
        job = Job(
            name="inactive-job",
            cron_expression="0 0 * * *",
            target_url="https://example.com/hook",
            created_by=user.id,
            is_active=False,
            end_date=date(2099, 1, 1),
            category="general",
            pic_team=None,
        )
        db.session.add(job)
        db.session.commit()
        return job.id


@pytest.fixture
def seed_job_expired(app, setup_test_db):
    with app.app_context():
        from src.models import db

        user = setup_test_db["user"]
        job = Job(
            name="expired-job",
            cron_expression="0 0 * * *",
            target_url="https://example.com/hook",
            created_by=user.id,
            is_active=True,
            end_date=date(2000, 1, 1),
            category="general",
            pic_team=None,
        )
        db.session.add(job)
        db.session.commit()
        return job.id


def _count(session, model) -> int:
    return int(session.execute(select(func.count()).select_from(model)).scalar_one() or 0)


def test_execute_job_skips_inactive_job(seed_job_inactive, app):
    with app.app_context():
        job = Job.query.get(seed_job_inactive)
        job_executor.execute_job(job.id, job.name, job.to_dict(), scheduler_timezone="UTC")

    with get_db_session() as session:
        assert _count(session, JobExecution) == 0


def test_execute_job_end_date_guard_auto_pauses_and_notifies(seed_job_expired, setup_test_db, app):
    user_id = setup_test_db["user"].id
    admin_id = setup_test_db["admin"].id

    with app.app_context():
        job = Job.query.get(seed_job_expired)
        assert job.is_active is True
        job_executor.execute_job(job.id, job.name, job.to_dict(), scheduler_timezone="Asia/Tokyo")

    with get_db_session() as session:
        job = session.get(Job, seed_job_expired)
        assert job.is_active is False
        assert _count(session, JobExecution) == 0

        rows = session.execute(select(Notification).where(Notification.title == "Job auto-paused (end date passed)")).scalars().all()
        assert {n.user_id for n in rows} == {user_id, admin_id}


def test_execute_job_webhook_success_creates_execution_and_broadcasts(seed_job_for_webhook, app, monkeypatch):
    def fake_post(url, json=None, timeout=None, headers=None):
        assert url == "https://example.com/hook"
        assert json == {"hello": "world"}
        return _DummyResponse(200, text="ok")

    with app.app_context():
        job = Job.query.get(seed_job_for_webhook)
        assert job is not None

    with app.app_context():
        job = Job.query.get(seed_job_for_webhook)
        monkeypatch.setattr(job_executor.requests, "post", fake_post)
        job_executor.execute_job(job.id, job.name, job.to_dict(), scheduler_timezone="UTC")

    with get_db_session() as session:
        executions = session.execute(select(JobExecution).where(JobExecution.job_id == seed_job_for_webhook)).scalars().all()
        assert len(executions) == 1
        execution = executions[0]
        assert execution.status == "success"
        assert execution.execution_type == "webhook"
        assert execution.response_status == 200

        # Broadcast creates notifications for all users (including inactive), matching legacy behavior.
        assert _count(session, Notification) >= 4
        titles = {n.title for n in session.execute(select(Notification)).scalars().all()}
        assert "Job Completed" in titles


def test_execute_job_github_missing_token_records_target(seed_job_for_github, app, monkeypatch):
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)

    with app.app_context():
        job = Job.query.get(seed_job_for_github)
        job_executor.execute_job(job.id, job.name, job.to_dict(), scheduler_timezone="UTC")

    with get_db_session() as session:
        execution = (
            session.execute(select(JobExecution).where(JobExecution.job_id == seed_job_for_github))
            .scalars()
            .one()
        )
        assert execution.status == "failed"
        assert execution.execution_type == "github_actions"
        assert execution.target == "Pay-Baymax/qa-automate-apiqa/API_Launcher"
