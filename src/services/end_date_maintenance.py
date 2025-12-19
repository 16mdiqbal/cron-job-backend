import logging
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from ..models import db
from ..models.job import Job
from ..models.user import User
from ..utils.notifications import create_notification

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

    Slack integration is intentionally deferred; this uses in-app notifications.
    """
    tz_name = _scheduler_timezone_name(app)
    now = _now_jst(app)
    today = now.date()
    cutoff = today + timedelta(days=30)

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

    db.session.commit()

