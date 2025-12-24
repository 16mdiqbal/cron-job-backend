"""
Scheduler DB Reconciliation (Flask parity).

Flask runs an initial DB -> APScheduler sync plus a periodic reconciliation loop
to ensure schedules exist even when:
- the scheduler process restarts
- writes happen on a non-scheduler process
- jobs pre-exist in the DB before scheduler starts

FastAPI mirrors that behavior here.
"""

from __future__ import annotations

import logging
import os
import threading
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional
from zoneinfo import ZoneInfo

from sqlalchemy import select

from ..database.session import get_db_session
from ..models.job import Job
from ..scheduler import scheduler as apscheduler
from .config import get_settings
from .scheduler_runtime import get_status
from .scheduler_side_effects import sync_job_schedule

logger = logging.getLogger(__name__)

_reconcile_thread: Optional[threading.Thread] = None
_reconcile_stop: Optional[threading.Event] = None

_last_resync_at: Optional[datetime] = None
_last_summary: Optional["ResyncSummary"] = None

# Scheduler internal jobs that should not be removed during orphan cleanup.
_RESERVED_JOB_IDS: set[str] = {"end_date_maintenance"}


@dataclass(frozen=True)
class ResyncSummary:
    ran_at: datetime
    db_jobs_total: int
    db_jobs_active: int
    scheduled_now: int
    scheduled_added: int
    scheduled_removed: int
    expired_auto_paused: int
    orphaned_removed: int
    invalid_cron: int


def get_last_resync() -> tuple[Optional[datetime], Optional[ResyncSummary]]:
    return _last_resync_at, _last_summary


def _scheduler_timezone() -> ZoneInfo:
    tz_name = (get_settings().scheduler_timezone or "Asia/Tokyo").strip() or "Asia/Tokyo"
    try:
        return ZoneInfo(tz_name)
    except Exception:
        return ZoneInfo("UTC")


def _poll_seconds() -> int:
    raw = (os.getenv("SCHEDULER_POLL_SECONDS") or "").strip()
    poll = int(raw) if raw.isdigit() else 60
    return max(10, min(poll, 300))


def resync_from_db(*, remove_orphans: bool = True, auto_pause_expired: bool = True) -> ResyncSummary:
    """
    Reconcile the jobs table -> APScheduler state (leader-only).

    This is safe to call multiple times; it uses replace_existing scheduling.
    """
    status = get_status()
    if not (status.running and status.is_leader):
        raise RuntimeError("Scheduler is not running as leader in this process.")

    tz = _scheduler_timezone()
    today = datetime.now(tz).date()

    db_jobs_total = 0
    db_jobs_active = 0
    scheduled_added = 0
    scheduled_removed = 0
    expired_auto_paused = 0
    invalid_cron = 0

    with get_db_session() as session:
        jobs = session.execute(select(Job)).scalars().all()
        db_jobs_total = len(jobs)

        db_ids: set[str] = set()
        for job in jobs:
            if not job.id:
                continue
            db_ids.add(job.id)

            if auto_pause_expired and job.is_active and job.end_date and job.end_date < today:
                job.is_active = False
                expired_auto_paused += 1

            should_be_active = bool(job.is_active) and not (job.end_date and job.end_date < today)
            if should_be_active:
                db_jobs_active += 1

            before = apscheduler.get_job(job.id) is not None
            applied = sync_job_schedule(job)
            after = apscheduler.get_job(job.id) is not None

            if should_be_active:
                if (not before) and after:
                    scheduled_added += 1
                if (not after) and applied is False:
                    # Most common reason: invalid cron expression.
                    invalid_cron += 1
            else:
                if before and not after:
                    scheduled_removed += 1

        orphaned_removed = 0
        if remove_orphans:
            # Remove scheduled jobs that no longer exist in DB (excluding reserved IDs).
            scheduled_ids = {str(j.id) for j in apscheduler.get_jobs()}
            for scheduled_id in scheduled_ids:
                if scheduled_id in _RESERVED_JOB_IDS:
                    continue
                if scheduled_id not in db_ids:
                    try:
                        if apscheduler.get_job(scheduled_id):
                            apscheduler.remove_job(scheduled_id)
                            orphaned_removed += 1
                    except Exception:
                        pass

    scheduled_now = len(apscheduler.get_jobs())
    summary = ResyncSummary(
        ran_at=datetime.now(timezone.utc),
        db_jobs_total=db_jobs_total,
        db_jobs_active=db_jobs_active,
        scheduled_now=scheduled_now,
        scheduled_added=scheduled_added,
        scheduled_removed=scheduled_removed,
        expired_auto_paused=expired_auto_paused,
        orphaned_removed=orphaned_removed,
        invalid_cron=invalid_cron,
    )

    global _last_resync_at, _last_summary
    _last_resync_at = summary.ran_at
    _last_summary = summary
    return summary


def start_reconciler() -> None:
    """
    Start a background reconciliation loop (leader-only).

    The loop runs in a daemon thread and stops automatically on shutdown via
    stop_reconciler().
    """
    global _reconcile_thread, _reconcile_stop

    status = get_status()
    if not (status.running and status.is_leader):
        return

    if _reconcile_thread and _reconcile_thread.is_alive():
        return

    stop_event = threading.Event()
    _reconcile_stop = stop_event

    poll_seconds = _poll_seconds()

    def _loop() -> None:
        # Flask parity: do an initial sync at startup, then reconcile periodically.
        if stop_event.wait(poll_seconds):
            return
        while not stop_event.is_set():
            try:
                resync_from_db()
            except Exception as exc:
                logger.warning("Scheduler DB reconcile loop error: %s", exc)
            if stop_event.wait(poll_seconds):
                return

    _reconcile_thread = threading.Thread(target=_loop, name="fastapi-scheduler-reconcile", daemon=True)
    _reconcile_thread.start()


def stop_reconciler() -> None:
    global _reconcile_thread, _reconcile_stop

    if _reconcile_stop is not None:
        _reconcile_stop.set()
    if _reconcile_thread is not None and _reconcile_thread.is_alive():
        _reconcile_thread.join(timeout=2)
    _reconcile_thread = None
    _reconcile_stop = None
