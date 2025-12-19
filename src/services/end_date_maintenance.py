import logging
from datetime import datetime, timedelta
from typing import Optional
from zoneinfo import ZoneInfo

from ..models import db
from ..models.job import Job
from ..models.pic_team import PicTeam
from ..models.slack_settings import SlackSettings
from ..models.user import User
from ..utils.notifications import create_notification
from ..utils.slack import send_slack_message

logger = logging.getLogger(__name__)


def _scheduler_timezone_name(app) -> str:
    return app.config.get('SCHEDULER_TIMEZONE', 'Asia/Tokyo')


def _now_jst(app) -> datetime:
    return datetime.now(ZoneInfo(_scheduler_timezone_name(app)))


def _notify_recipients_for_job(job: Job) -> list[str]:
    recipients: set[str] = set()
    if job.created_by:
        recipients.add(job.created_by)

    admins = User.query.filter_by(role='admin', is_active=True).all()
    for admin in admins:
        recipients.add(admin.id)

    return [r for r in recipients if r]


def _create_job_warning(job: Job, title: str, message: str):
    recipients = _notify_recipients_for_job(job)
    for user_id in recipients:
        try:
            create_notification(
                user_id=user_id,
                title=title,
                message=message,
                notification_type='warning',
                related_job_id=job.id,
            )
        except Exception as e:
            logger.warning(f"Failed to create notification for user {user_id}: {e}")


def run_end_date_maintenance(app, scheduler=None):
    """
    Weekly maintenance (run on Mondays, JST):
      - Auto-pause jobs whose end_date has passed (quietly, but with a warning notification)
      - Remind about jobs ending within 30 days (weekly warning notification)

    Sends in-app notifications always; optionally sends Slack when configured in Settings.
    """
    now = _now_jst(app)
    today = now.date()
    cutoff = today + timedelta(days=30)

    slack = SlackSettings.query.first()
    slack_enabled = bool(getattr(slack, 'is_enabled', False) and getattr(slack, 'webhook_url', None))
    slack_webhook = getattr(slack, 'webhook_url', None) if slack_enabled else None
    slack_channel = getattr(slack, 'channel', None) if slack_enabled else None
    frontend_base_url = (app.config.get('FRONTEND_BASE_URL') or 'http://localhost:5173').rstrip('/')

    def _team_handle(job: Job) -> Optional[str]:
        if not job.pic_team:
            return None
        team = PicTeam.query.filter_by(slug=job.pic_team).first()
        return (team.slack_handle or '').strip() if team else None

    def _job_link(job: Job) -> str:
        return f"{frontend_base_url}/jobs/{job.id}/edit"

    def _slack_post(text: str):
        if slack_webhook:
            send_slack_message(slack_webhook, text=text, channel=slack_channel)

    # 1) Auto-pause expired jobs that are still active
    expired_active = (
        Job.query.filter(Job.is_active.is_(True))
        .filter(Job.end_date.isnot(None))
        .filter(Job.end_date < today)
        .all()
    )
    for job in expired_active:
        job.is_active = False
        db.session.add(job)
        try:
            if scheduler and scheduler.get_job(job.id):
                scheduler.remove_job(job.id)
        except Exception:
            pass
        _create_job_warning(
            job,
            title='Job auto-paused (end date passed)',
            message=f'Job "{job.name}" passed its end_date ({job.end_date.isoformat()} JST) and was auto-paused. PIC Team: {job.pic_team or "-"}',
        )
        if slack_enabled:
            handle = _team_handle(job)
            mention = f"{handle} " if handle else ""
            _slack_post(
                f":warning: {mention}Job auto-paused (end date passed): <{_job_link(job)}|{job.name}> "
                f"(end_date {job.end_date.isoformat()} JST)"
            )

    # 2) Weekly reminders for jobs ending soon (0..30 days)
    ending_soon = (
        Job.query.filter(Job.end_date.isnot(None))
        .filter(Job.end_date >= today)
        .filter(Job.end_date <= cutoff)
        .all()
    )
    for job in ending_soon:
        days_left = (job.end_date - today).days if job.end_date else None
        _create_job_warning(
            job,
            title='Job ending soon',
            message=f'Job "{job.name}" ends on {job.end_date.isoformat()} JST ({days_left} day(s) left). PIC Team: {job.pic_team or "-"}',
        )
        if slack_enabled:
            handle = _team_handle(job)
            mention = f"{handle} " if handle else ""
            _slack_post(
                f":warning: {mention}Job ending soon ({days_left}d): <{_job_link(job)}|{job.name}> "
                f"(end_date {job.end_date.isoformat()} JST)"
            )

    db.session.commit()
