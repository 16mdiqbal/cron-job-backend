"""
FastAPI Scheduler Runtime (Phase 8C).

Starts/stops APScheduler under FastAPI lifespan, guarded by a single-runner lock.

Phase 8C deliberately keeps APScheduler configuration minimal. CRUD side-effects are wired
in Phase 8D; DB -> scheduler bootstrap/reconciliation is added for Flask parity (Phase 8G).
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional
from urllib.parse import urlparse
from zoneinfo import ZoneInfo

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from .config import get_settings
from ..scheduler import scheduler as _scheduler
from ..scheduler.lock import SchedulerLock


@dataclass(frozen=True)
class SchedulerStatus:
    running: bool
    is_leader: bool
    scheduled_jobs_count: int


_lock: Optional[SchedulerLock] = None
_is_leader: bool = False


def _scheduler_enabled() -> bool:
    # Mirrors Flask behavior: enabled unless explicitly set to 'false'.
    return os.getenv("SCHEDULER_ENABLED", "true").lower() != "false"


def _default_lock_path() -> str:
    """
    Default lock location:
    - For sqlite:///path/to/db.sqlite -> /path/to/scheduler.lock
    - Otherwise -> ./scheduler.lock
    """
    settings = get_settings()
    db_url = settings.database_url or os.getenv("DATABASE_URL", "")
    try:
        parsed = urlparse(db_url)
        if parsed.scheme.startswith("sqlite") and parsed.path:
            return os.path.join(os.path.dirname(parsed.path), "scheduler.lock")
    except Exception:
        pass
    return os.path.abspath("scheduler.lock")


def _get_scheduler() -> BackgroundScheduler:
    return _scheduler


def _ensure_end_date_maintenance_job(scheduler: BackgroundScheduler, tz: ZoneInfo) -> None:
    try:
        from ..services.end_date_maintenance import run_end_date_maintenance

        scheduler.add_job(
            func=run_end_date_maintenance,
            trigger=CronTrigger(day_of_week="mon", hour=9, minute=0, timezone=tz),
            id="end_date_maintenance",
            name="End date maintenance",
            replace_existing=True,
        )
    except Exception:
        # Never fail scheduler startup due to a maintenance job.
        pass


def start_scheduler() -> bool:
    """
    Attempt to start the scheduler in this process.
    Returns True if running in this process (leader), else False.
    """
    global _lock, _is_leader

    scheduler = _get_scheduler()
    if scheduler.running:
        _is_leader = True
        try:
            settings = get_settings()
            tz = ZoneInfo(settings.scheduler_timezone)
        except Exception:
            tz = ZoneInfo("UTC")
        _ensure_end_date_maintenance_job(scheduler, tz)
        return True

    settings = get_settings()
    if settings.testing or not _scheduler_enabled():
        _is_leader = False
        return False

    lock_path = os.getenv("SCHEDULER_LOCK_PATH") or _default_lock_path()
    stale_seconds_raw = (os.getenv("SCHEDULER_LOCK_STALE_SECONDS") or "").strip()
    stale_after_seconds = int(stale_seconds_raw) if stale_seconds_raw.isdigit() else None

    lock = SchedulerLock(lock_path=lock_path, stale_after_seconds=stale_after_seconds)
    if not lock.try_acquire():
        _is_leader = False
        return False

    _lock = lock
    _is_leader = True

    # Keep scheduler config minimal for Phase 8C (no jobstore wiring yet).
    try:
        tz = ZoneInfo(settings.scheduler_timezone)
    except Exception:
        tz = ZoneInfo("UTC")

    scheduler.configure(timezone=tz)

    scheduler.start()
    _ensure_end_date_maintenance_job(scheduler, tz)

    # Flask parity: bootstrap schedules from DB and keep them reconciled.
    try:
        from .scheduler_reconcile import resync_from_db, start_reconciler

        resync_from_db()
        start_reconciler()
    except Exception:
        # Never fail startup; health endpoint will reflect scheduled_jobs_count.
        pass
    return True


def stop_scheduler() -> None:
    """Stop scheduler if running and release leadership lock if held."""
    global _lock, _is_leader

    try:
        from .scheduler_reconcile import stop_reconciler

        stop_reconciler()
    except Exception:
        pass

    scheduler = _get_scheduler()
    try:
        if scheduler.running:
            scheduler.shutdown(wait=False)
    finally:
        if _lock is not None:
            _lock.release()
        _lock = None
        _is_leader = False


def get_status() -> SchedulerStatus:
    scheduler = _get_scheduler()
    running = bool(getattr(scheduler, "running", False))
    if not running:
        count = 0
    else:
        jobs = scheduler.get_jobs()
        try:
            from .scheduler_reconcile import _RESERVED_JOB_IDS

            jobs = [j for j in jobs if str(j.id) not in _RESERVED_JOB_IDS]
        except Exception:
            pass
        count = len(jobs)
    return SchedulerStatus(running=running, is_leader=_is_leader and running, scheduled_jobs_count=count)


def _reset_for_tests() -> None:
    """Test helper to reset global state. Not part of public API."""
    global _lock, _is_leader
    _lock = None
    _is_leader = False
