"""
Scheduler operational endpoints.

These endpoints are primarily for admins/operators to verify scheduler state and
trigger a DB -> APScheduler resync when needed.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from ..dependencies.auth import AdminUser
from ..schemas import SchedulerResyncResponse, SchedulerStatusResponse
from ..scheduler_runtime import get_status

router = APIRouter(prefix="/scheduler", tags=["Scheduler"])


@router.get(
    "/status",
    summary="Scheduler status",
    description="Return scheduler leadership and scheduled job counts (leader-only scheduling).",
    response_model=SchedulerStatusResponse,
)
def scheduler_status(_: AdminUser) -> SchedulerStatusResponse:
    sched = get_status()
    try:
        from ..scheduler_reconcile import get_last_resync

        last_resync_at, _ = get_last_resync()
    except Exception:
        last_resync_at = None

    return SchedulerStatusResponse(
        scheduler_running=sched.running,
        scheduler_is_leader=sched.is_leader,
        scheduled_jobs_count=sched.scheduled_jobs_count,
        last_resync_at=last_resync_at,
    )


@router.post(
    "/resync",
    summary="Resync scheduler from DB",
    description="Bootstrap/reconcile APScheduler jobs from the DB (Flask parity). Admin-only.",
    response_model=SchedulerResyncResponse,
)
def scheduler_resync(_: AdminUser) -> SchedulerResyncResponse:
    sched = get_status()
    if not (sched.running and sched.is_leader):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Scheduler is not running as leader in this process.",
        )

    from ..scheduler_reconcile import resync_from_db

    summary = resync_from_db()
    return SchedulerResyncResponse(
        message="Scheduler resync completed",
        ran_at=summary.ran_at,
        db_jobs_total=summary.db_jobs_total,
        db_jobs_active=summary.db_jobs_active,
        scheduled_now=summary.scheduled_now,
        scheduled_added=summary.scheduled_added,
        scheduled_removed=summary.scheduled_removed,
        expired_auto_paused=summary.expired_auto_paused,
        orphaned_removed=summary.orphaned_removed,
        invalid_cron=summary.invalid_cron,
    )

