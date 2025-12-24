import logging
import os
from datetime import date, datetime, timedelta
from typing import Optional
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database.session import get_db_session
from ..models.job import Job
from ..models.notification import Notification
from ..models.pic_team import PicTeam
from ..models.slack_settings import SlackSettings
from ..models.user import User
from ..utils.slack import send_slack_message

logger = logging.getLogger(__name__)


def _scheduler_timezone() -> ZoneInfo:
    tz_name = (os.getenv("SCHEDULER_TIMEZONE") or "Asia/Tokyo").strip() or "Asia/Tokyo"
    try:
        return ZoneInfo(tz_name)
    except Exception:
        return ZoneInfo("UTC")


def _frontend_base_url() -> str:
    return (os.getenv("FRONTEND_BASE_URL") or "http://localhost:5173").rstrip("/")


def _team_handle(session: Session, job: Job) -> Optional[str]:
    if not job.pic_team:
        return None
    team = session.execute(select(PicTeam).where(PicTeam.slug == job.pic_team)).scalars().first()
    if not team:
        return None
    return (team.slack_handle or "").strip() or None


def _job_link(job: Job) -> str:
    return f"{_frontend_base_url()}/jobs/{job.id}/edit"


def _slack_config(session: Session) -> tuple[bool, Optional[str], Optional[str]]:
    settings = session.execute(select(SlackSettings)).scalars().first()
    enabled = bool(getattr(settings, "is_enabled", False) and getattr(settings, "webhook_url", None))
    if not enabled:
        return False, None, None
    return True, getattr(settings, "webhook_url", None), getattr(settings, "channel", None)


def _notify_recipients(session: Session, job: Job) -> set[str]:
    recipients: set[str] = set()
    if job.created_by:
        recipients.add(job.created_by)
    admin_ids = session.execute(select(User.id).where(User.role == "admin", User.is_active.is_(True))).scalars().all()
    recipients.update({uid for uid in admin_ids if uid})
    return recipients


def _create_job_warning(session: Session, job: Job, *, title: str, message: str) -> int:
    recipients = _notify_recipients(session, job)
    created = 0
    for user_id in recipients:
        try:
            session.add(
                Notification(
                    user_id=user_id,
                    title=title,
                    message=message,
                    type="warning",
                    related_job_id=job.id,
                )
            )
            created += 1
        except Exception:
            pass
    return created


def run_end_date_maintenance() -> dict:
    """
    Weekly maintenance (Mondays, JST):
      - Auto-pause jobs whose end_date has passed (and notify)
      - Remind about jobs ending within 30 days (weekly warning notification)

    In-app notifications are always created. Slack is optional (Settings).
    """
    tz = _scheduler_timezone()
    now = datetime.now(tz)
    today: date = now.date()
    cutoff = today + timedelta(days=30)

    paused = 0
    reminders = 0
    notifications_created = 0

    with get_db_session() as session:
        slack_enabled, slack_webhook, slack_channel = _slack_config(session)

        def _slack_post(text: str) -> None:
            if slack_enabled and slack_webhook:
                try:
                    send_slack_message(slack_webhook, text=text, channel=slack_channel)
                except Exception:
                    pass

        # 1) Auto-pause expired jobs that are still active
        expired_active = (
            session.execute(
                select(Job).where(Job.is_active.is_(True), Job.end_date.is_not(None), Job.end_date < today)
            )
            .scalars()
            .all()
        )
        for job in expired_active:
            job.is_active = False
            paused += 1
            try:
                from ..scheduler import scheduler as apscheduler

                if apscheduler.get_job(job.id):
                    apscheduler.remove_job(job.id)
            except Exception:
                pass

            notifications_created += _create_job_warning(
                session,
                job,
                title="Job auto-paused (end date passed)",
                message=(
                    f'Job "{job.name}" passed its end_date ({job.end_date.isoformat()} JST) and was auto-paused. '
                    f'PIC Team: {job.pic_team or "-"}'
                ),
            )

            if slack_enabled:
                handle = _team_handle(session, job)
                mention = f"{handle} " if handle else ""
                _slack_post(
                    f":warning: {mention}Job auto-paused (end date passed): <{_job_link(job)}|{job.name}> "
                    f"(end_date {job.end_date.isoformat()} JST)"
                )

        # 2) Weekly reminders for jobs ending soon (0..30 days)
        ending_soon = (
            session.execute(select(Job).where(Job.end_date.is_not(None), Job.end_date >= today, Job.end_date <= cutoff))
            .scalars()
            .all()
        )
        for job in ending_soon:
            reminders += 1
            days_left = (job.end_date - today).days if job.end_date else None
            notifications_created += _create_job_warning(
                session,
                job,
                title="Job ending soon",
                message=(
                    f'Job "{job.name}" ends on {job.end_date.isoformat()} JST ({days_left} day(s) left). '
                    f'PIC Team: {job.pic_team or "-"}'
                ),
            )

            if slack_enabled:
                handle = _team_handle(session, job)
                mention = f"{handle} " if handle else ""
                _slack_post(
                    f":warning: {mention}Job ending soon ({days_left}d): <{_job_link(job)}|{job.name}> "
                    f"(end_date {job.end_date.isoformat()} JST)"
                )

        session.commit()

    summary = {
        "ran_at": now.isoformat(),
        "paused_expired_jobs": paused,
        "ending_soon_jobs": reminders,
        "notifications_created": notifications_created,
    }
    logger.info("End-date maintenance summary: %s", summary)
    return summary

