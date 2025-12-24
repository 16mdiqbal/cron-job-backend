"""
Scheduler Side-Effects (Phase 8D).

Best-effort APScheduler updates for FastAPI job write endpoints.
If the scheduler is not running in this process (not leader), these helpers
become no-ops and never fail the API request.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Optional
from zoneinfo import ZoneInfo

from apscheduler.triggers.cron import CronTrigger

from .config import get_settings
from .scheduler_runtime import get_status
from ..models.job import Job
from ..scheduler import scheduler as apscheduler
from ..scheduler.job_executor import execute_job

logger = logging.getLogger(__name__)


def _scheduler_timezone() -> ZoneInfo:
    tz_name = get_settings().scheduler_timezone or "Asia/Tokyo"
    try:
        return ZoneInfo(tz_name)
    except Exception:
        return ZoneInfo("UTC")


def _should_schedule(job: Job, tz: ZoneInfo) -> bool:
    if not job or not job.id:
        return False
    if not bool(job.is_active):
        return False
    if job.end_date:
        today = datetime.now(tz).date()
        if job.end_date < today:
            return False
    return True


def _build_job_config(job: Job) -> dict:
    return {
        "target_url": job.target_url,
        "github_owner": job.github_owner,
        "github_repo": job.github_repo,
        "github_workflow_name": job.github_workflow_name,
        "metadata": job.get_metadata(),
        "enable_email_notifications": bool(job.enable_email_notifications),
        "notification_emails": job.get_notification_emails(),
        "notify_on_success": bool(job.notify_on_success),
    }


def sync_job_schedule(job: Job) -> bool:
    """
    Ensure APScheduler state matches the given job.
    Returns True if a scheduler change was applied in this process, else False.
    """
    status = get_status()
    if not (status.running and status.is_leader):
        return False

    tz = _scheduler_timezone()
    if not _should_schedule(job, tz):
        return unschedule_job(job.id if job else None)

    try:
        trigger = CronTrigger.from_crontab((job.cron_expression or "").strip(), timezone=tz)
    except Exception as exc:
        logger.warning("Skipping schedule update for job %s due to invalid cron: %s", job.id, exc)
        return False

    job_config = _build_job_config(job)
    tz_name = get_settings().scheduler_timezone or "Asia/Tokyo"

    try:
        apscheduler.add_job(
            func=execute_job,
            trigger=trigger,
            args=[job.id, job.name, job_config],
            kwargs={"scheduler_timezone": tz_name},
            id=job.id,
            name=job.name,
            replace_existing=True,
        )
        return True
    except Exception as exc:
        logger.warning("Scheduler side-effect failed for job %s: %s", job.id, exc)
        return False


def unschedule_job(job_id: Optional[str]) -> bool:
    """
    Remove a scheduled job if present (leader-only). Returns True if removed.
    """
    if not job_id:
        return False
    status = get_status()
    if not (status.running and status.is_leader):
        return False

    try:
        if apscheduler.get_job(job_id):
            apscheduler.remove_job(job_id)
            return True
    except Exception as exc:
        logger.warning("Failed to unschedule job %s: %s", job_id, exc)
    return False

