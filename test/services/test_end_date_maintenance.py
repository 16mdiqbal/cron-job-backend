from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pytest

from src.models.job import Job
from src.models.job_category import JobCategory
from src.models.notification import Notification
from src.models.pic_team import PicTeam
from src.models.slack_settings import SlackSettings


@dataclass
class _DummyScheduler:
    existing_job_ids: set[str] = field(default_factory=set)
    removed_job_ids: list[str] = field(default_factory=list)

    def get_job(self, job_id: str):
        return job_id if job_id in self.existing_job_ids else None

    def remove_job(self, job_id: str) -> None:
        self.removed_job_ids.append(job_id)
        self.existing_job_ids.discard(job_id)


def _today_jst() -> datetime.date:
    return datetime.now(ZoneInfo("Asia/Tokyo")).date()


def test_end_date_maintenance_auto_pauses_expired_jobs_and_notifies(db_session, setup_test_db, monkeypatch):
    # Arrange
    today = _today_jst()

    general = JobCategory(slug="general", name="General", is_active=True)
    team = PicTeam(slug="team-a", name="Team A", slack_handle="@team-a", is_active=True)
    db_session.add_all([general, team])
    db_session.commit()

    creator = setup_test_db["user"]
    expired_job = Job(
        name="Expired Job",
        cron_expression="*/5 * * * *",
        target_url="https://example.com/hook",
        category="general",
        pic_team="team-a",
        end_date=today - timedelta(days=1),
        created_by=creator.id,
        is_active=True,
    )
    db_session.add(expired_job)
    db_session.commit()

    # Force Slack to be enabled and patch the Slack sender.
    slack = SlackSettings(is_enabled=True, webhook_url="https://example.com/webhook", channel="#ops")
    db_session.add(slack)
    db_session.commit()

    slack_calls: list[dict] = []

    def _fake_send_slack_message(webhook_url: str, text: str, channel: str | None = None) -> bool:
        slack_calls.append({"webhook_url": webhook_url, "text": text, "channel": channel})
        return True

    monkeypatch.setenv("SCHEDULER_TIMEZONE", "Asia/Tokyo")
    monkeypatch.setenv("FRONTEND_BASE_URL", "http://frontend.local")
    monkeypatch.setattr("src.services.end_date_maintenance.send_slack_message", _fake_send_slack_message)

    dummy_scheduler = _DummyScheduler(existing_job_ids={expired_job.id})
    import src.scheduler as scheduler_module

    monkeypatch.setattr(scheduler_module, "scheduler", dummy_scheduler, raising=True)

    # Act
    from src.services.end_date_maintenance import run_end_date_maintenance

    summary = run_end_date_maintenance()

    # Assert: job got auto-paused
    db_session.refresh(expired_job)
    assert expired_job.is_active is False
    assert summary["paused_expired_jobs"] == 1

    # Assert: scheduler cleanup attempted
    assert dummy_scheduler.removed_job_ids == [expired_job.id]

    # Assert: notifications created for creator + admins
    recipients = {creator.id, setup_test_db["admin"].id}
    rows = (
        db_session.query(Notification)
        .filter(Notification.title == "Job auto-paused (end date passed)")
        .all()
    )
    assert {n.user_id for n in rows} == recipients
    assert all(n.related_job_id == expired_job.id for n in rows)

    # Assert: Slack posted with team mention
    assert slack_calls, "Expected at least one Slack call"
    assert any("@team-a" in call["text"] for call in slack_calls)


def test_end_date_maintenance_sends_ending_soon_reminders(db_session, setup_test_db, monkeypatch):
    # Arrange
    today = _today_jst()

    general = JobCategory(slug="general", name="General", is_active=True)
    team = PicTeam(slug="team-a", name="Team A", slack_handle="@team-a", is_active=True)
    db_session.add_all([general, team])
    db_session.commit()

    creator = setup_test_db["user"]
    soon_job = Job(
        name="Ending Soon Job",
        cron_expression="0 * * * *",
        target_url="https://example.com/hook",
        category="general",
        pic_team="team-a",
        end_date=today + timedelta(days=7),
        created_by=creator.id,
        is_active=True,
    )
    db_session.add(soon_job)
    db_session.commit()

    slack = SlackSettings(is_enabled=True, webhook_url="https://example.com/webhook", channel="#ops")
    db_session.add(slack)
    db_session.commit()

    slack_calls: list[dict] = []

    def _fake_send_slack_message(webhook_url: str, text: str, channel: str | None = None) -> bool:
        slack_calls.append({"webhook_url": webhook_url, "text": text, "channel": channel})
        return True

    monkeypatch.setenv("SCHEDULER_TIMEZONE", "Asia/Tokyo")
    monkeypatch.setenv("FRONTEND_BASE_URL", "http://frontend.local")
    monkeypatch.setattr("src.services.end_date_maintenance.send_slack_message", _fake_send_slack_message)

    # Act
    from src.services.end_date_maintenance import run_end_date_maintenance

    summary = run_end_date_maintenance()

    # Assert: reminder notification created
    recipients = {creator.id, setup_test_db["admin"].id}
    rows = (
        db_session.query(Notification)
        .filter(Notification.title == "Job ending soon")
        .all()
    )
    assert {n.user_id for n in rows} == recipients
    assert all(n.related_job_id == soon_job.id for n in rows)

    assert summary["ending_soon_jobs"] >= 1
    assert summary["notifications_created"] >= len(recipients)

    # Assert: Slack posted with team mention
    assert slack_calls, "Expected at least one Slack call"
    assert any("@team-a" in call["text"] for call in slack_calls)
