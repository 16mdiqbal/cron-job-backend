"""
Jobs Router (Read-Only).

Phase 4B: Migrate low-risk read endpoints first.

Implements:
- GET /api/v2/jobs
- GET /api/v2/jobs/{job_id}
"""

import logging
from datetime import datetime
from typing import Annotated, Optional
from zoneinfo import ZoneInfo

from apscheduler.triggers.cron import CronTrigger
from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import get_settings
from ..dependencies.auth import CurrentUser
from ..schemas.jobs_read import JobGetReadResponse, JobListReadResponse, JobReadPayload
from ...database.session import get_db
from ...models.job import Job
from ...models.job_execution import JobExecution

logger = logging.getLogger(__name__)

ERROR_INTERNAL_SERVER = "Internal server error"
ERROR_JOB_NOT_FOUND = "Job not found"


router = APIRouter(
    prefix="/jobs",
    tags=["Jobs"],
    responses={
        401: {"description": "Unauthorized - Invalid or missing token"},
        500: {"description": "Internal server error"},
    },
)


def _get_scheduler_timezone() -> ZoneInfo:
    tz_name = get_settings().scheduler_timezone or "Asia/Tokyo"
    try:
        return ZoneInfo(tz_name)
    except Exception:
        logger.warning("Invalid SCHEDULER_TIMEZONE '%s', falling back to UTC", tz_name)
        return ZoneInfo("UTC")


def _compute_next_execution_at(job: Job) -> Optional[str]:
    try:
        if not job.is_active:
            return None
        tz = _get_scheduler_timezone()
        now = datetime.now(tz)
        trigger = CronTrigger.from_crontab(job.cron_expression, timezone=tz)
        next_run_time = trigger.get_next_fire_time(None, now)
        return next_run_time.isoformat() if next_run_time else None
    except Exception:
        return None


@router.get(
    "",
    response_model=JobListReadResponse,
    summary="List jobs (read-only)",
    description="List all jobs. Matches Flask `/api/jobs` response shape.",
)
async def list_jobs(
    _: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    try:
        result = await db.execute(select(Job).order_by(desc(Job.created_at)))
        jobs = result.scalars().all()

        last_exec_rows = await db.execute(
            select(JobExecution.job_id, func.max(JobExecution.started_at))
            .group_by(JobExecution.job_id)
        )
        last_exec_by_job_id = {job_id: started_at for job_id, started_at in last_exec_rows.all()}

        jobs_payload: list[JobReadPayload] = []
        for job in jobs:
            payload = job.to_dict()
            last_execution_at = last_exec_by_job_id.get(job.id)
            payload["last_execution_at"] = last_execution_at.isoformat() if last_execution_at else None
            payload["next_execution_at"] = _compute_next_execution_at(job)
            jobs_payload.append(JobReadPayload.model_validate(payload))

        return JobListReadResponse(count=len(jobs_payload), jobs=jobs_payload)
    except Exception as exc:
        logger.exception("Error listing jobs")
        settings = get_settings()
        return JSONResponse(
            status_code=500,
            content={
                "error": ERROR_INTERNAL_SERVER,
                "message": str(exc) if settings.expose_error_details else ERROR_INTERNAL_SERVER,
            },
        )


@router.get(
    "/{job_id}",
    response_model=JobGetReadResponse,
    summary="Get job by id (read-only)",
    description="Get a job by id. Matches Flask `/api/jobs/<id>` response shape.",
)
async def get_job(
    job_id: str,
    _: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    try:
        result = await db.execute(select(Job).where(Job.id == job_id))
        job = result.scalar_one_or_none()
        if not job:
            return JSONResponse(
                status_code=404,
                content={
                    "error": ERROR_JOB_NOT_FOUND,
                    "message": f"No job found with ID: {job_id}",
                },
            )

        payload = job.to_dict()

        last_execution_at_result = await db.execute(
            select(func.max(JobExecution.started_at)).where(JobExecution.job_id == job.id)
        )
        last_execution_at = last_execution_at_result.scalar_one_or_none()
        payload["last_execution_at"] = last_execution_at.isoformat() if last_execution_at else None
        payload["next_execution_at"] = _compute_next_execution_at(job)

        return JobGetReadResponse(job=JobReadPayload.model_validate(payload))
    except Exception as exc:
        logger.exception("Error retrieving job %s", job_id)
        settings = get_settings()
        return JSONResponse(
            status_code=500,
            content={
                "error": ERROR_INTERNAL_SERVER,
                "message": str(exc) if settings.expose_error_details else ERROR_INTERNAL_SERVER,
            },
        )
