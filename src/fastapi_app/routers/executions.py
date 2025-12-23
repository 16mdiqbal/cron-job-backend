"""
Job Executions Router (Read-Only).

Phase 4C: Migrate job executions read endpoints.

Implements:
- GET /api/v2/jobs/{job_id}/executions
- GET /api/v2/jobs/{job_id}/executions/{execution_id}
- GET /api/v2/jobs/{job_id}/executions/stats
"""

import logging
from datetime import date, datetime, time, timedelta, timezone
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import get_settings
from ..dependencies.auth import CurrentUser
from ..schemas.executions_read import (
    ExecutionReadPayload,
    ExecutionGetReadResponse,
    ExecutionStatisticsReadResponse,
    ExecutionWithJobReadPayload,
    ExecutionsListReadResponse,
    JobExecutionDetailReadResponse,
    JobExecutionStatistics,
    JobExecutionStatsReadResponse,
    JobExecutionsReadResponse,
    JobSummary,
)
from ...database.session import get_db
from ...models.job import Job
from ...models.job_execution import JobExecution

logger = logging.getLogger(__name__)

ERROR_INTERNAL_SERVER = "Internal server error"
ERROR_JOB_NOT_FOUND = "Job not found"


router = APIRouter(
    tags=["Executions"],
    responses={
        401: {"description": "Unauthorized - Invalid or missing token"},
        500: {"description": "Internal server error"},
    },
)


def _parse_iso_date_or_datetime(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None

    raw = value.strip()
    if not raw:
        return None

    # Date-only inputs like "2025-12-18"
    try:
        if len(raw) == 10 and raw[4] == "-" and raw[7] == "-":
            parsed = date.fromisoformat(raw)
            return datetime.combine(parsed, time.min, tzinfo=timezone.utc)
    except Exception:
        pass

    # Datetime inputs like "2025-12-18T12:34:56Z" or with offset
    normalized = raw.replace("Z", "+00:00")
    dt = datetime.fromisoformat(normalized)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    else:
        dt = dt.astimezone(timezone.utc)
    return dt


@router.get(
    "/jobs/{job_id}/executions",
    response_model=JobExecutionsReadResponse,
    summary="Get job executions (read-only)",
    description="Matches Flask `/api/jobs/<job_id>/executions` response shape.",
)
async def get_job_executions(
    job_id: str,
    _: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    limit: int = Query(50, ge=1, le=200),
    status: Optional[str] = Query(None, description="success|failed|running (or comma-separated list)"),
    trigger_type: Optional[str] = Query(None, description="scheduled|manual"),
    from_: Optional[str] = Query(None, alias="from"),
    to: Optional[str] = Query(None),
):
    try:
        job_result = await db.execute(select(Job).where(Job.id == job_id))
        job = job_result.scalar_one_or_none()
        if not job:
            return JSONResponse(
                status_code=404,
                content={"error": ERROR_JOB_NOT_FOUND, "message": f"No job found with ID: {job_id}"},
            )

        from_dt = _parse_iso_date_or_datetime(from_)
        to_dt = _parse_iso_date_or_datetime(to)
        if to and to_dt and len(to.strip()) == 10:
            to_dt = to_dt + timedelta(days=1)
        if from_dt and to_dt and from_dt >= to_dt:
            return JSONResponse(
                status_code=400,
                content={"error": "Invalid date range", "message": '"from" must be earlier than "to".'},
            )

        query = select(JobExecution).where(JobExecution.job_id == job_id)

        if status:
            statuses = [s.strip() for s in status.split(",") if s.strip()]
            if len(statuses) == 1:
                query = query.where(JobExecution.status == statuses[0])
            elif len(statuses) > 1:
                query = query.where(JobExecution.status.in_(statuses))
        if trigger_type:
            query = query.where(JobExecution.trigger_type == trigger_type)
        if from_dt:
            query = query.where(JobExecution.started_at >= from_dt)
        if to_dt:
            query = query.where(JobExecution.started_at < to_dt)

        query = query.order_by(desc(JobExecution.started_at)).limit(limit)
        executions_result = await db.execute(query)
        executions = executions_result.scalars().all()
        payload = [ExecutionReadPayload.model_validate(execution.to_dict()) for execution in executions]

        return JobExecutionsReadResponse(
            job_id=job_id,
            job_name=job.name,
            total_executions=len(payload),
            executions=payload,
        )
    except Exception as exc:
        logger.exception("Error fetching executions for job %s", job_id)
        settings = get_settings()
        return JSONResponse(
            status_code=500,
            content={
                "error": ERROR_INTERNAL_SERVER,
                "message": str(exc) if settings.expose_error_details else ERROR_INTERNAL_SERVER,
            },
        )


@router.get(
    "/jobs/{job_id}/executions/stats",
    response_model=JobExecutionStatsReadResponse,
    summary="Get job execution statistics (read-only)",
    description="Matches Flask `/api/jobs/<job_id>/executions/stats` response shape.",
)
async def get_job_execution_stats(
    job_id: str,
    _: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    try:
        job_result = await db.execute(select(Job).where(Job.id == job_id))
        job = job_result.scalar_one_or_none()
        if not job:
            return JSONResponse(
                status_code=404,
                content={"error": ERROR_JOB_NOT_FOUND, "message": f"No job found with ID: {job_id}"},
            )

        total_result = await db.execute(select(func.count()).select_from(JobExecution).where(JobExecution.job_id == job_id))
        total = int(total_result.scalar_one() or 0)

        success_result = await db.execute(
            select(func.count()).select_from(JobExecution).where(JobExecution.job_id == job_id, JobExecution.status == "success")
        )
        success = int(success_result.scalar_one() or 0)

        failed_result = await db.execute(
            select(func.count()).select_from(JobExecution).where(JobExecution.job_id == job_id, JobExecution.status == "failed")
        )
        failed = int(failed_result.scalar_one() or 0)

        running_result = await db.execute(
            select(func.count()).select_from(JobExecution).where(JobExecution.job_id == job_id, JobExecution.status == "running")
        )
        running = int(running_result.scalar_one() or 0)

        latest_result = await db.execute(
            select(JobExecution).where(JobExecution.job_id == job_id).order_by(desc(JobExecution.started_at)).limit(1)
        )
        latest_execution = latest_result.scalar_one_or_none()

        success_rate = (success / total * 100.0) if total else 0.0

        avg_duration_result = await db.execute(
            select(func.avg(JobExecution.duration_seconds)).where(
                JobExecution.job_id == job_id,
                JobExecution.status == "success",
                JobExecution.duration_seconds.is_not(None),
            )
        )
        avg_duration = avg_duration_result.scalar_one_or_none()
        avg_duration_val = round(float(avg_duration), 2) if avg_duration is not None else None

        stats = JobExecutionStatistics(
            total_executions=total,
            success_count=success,
            failed_count=failed,
            running_count=running,
            success_rate=round(success_rate, 2),
            average_duration_seconds=avg_duration_val,
        )

        return JobExecutionStatsReadResponse(
            job_id=job_id,
            job_name=job.name,
            statistics=stats,
            latest_execution=ExecutionReadPayload.model_validate(latest_execution.to_dict()) if latest_execution else None,
        )
    except Exception as exc:
        logger.exception("Error fetching execution stats for job %s", job_id)
        settings = get_settings()
        return JSONResponse(
            status_code=500,
            content={
                "error": ERROR_INTERNAL_SERVER,
                "message": str(exc) if settings.expose_error_details else ERROR_INTERNAL_SERVER,
            },
        )


@router.get(
    "/jobs/{job_id}/executions/{execution_id}",
    response_model=JobExecutionDetailReadResponse,
    summary="Get job execution details (read-only)",
    description="Matches Flask `/api/jobs/<job_id>/executions/<execution_id>` response shape.",
)
async def get_job_execution_details(
    job_id: str,
    execution_id: str,
    _: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    try:
        job_result = await db.execute(select(Job).where(Job.id == job_id))
        job = job_result.scalar_one_or_none()
        if not job:
            return JSONResponse(
                status_code=404,
                content={"error": ERROR_JOB_NOT_FOUND, "message": f"No job found with ID: {job_id}"},
            )

        execution_result = await db.execute(
            select(JobExecution).where(JobExecution.id == execution_id, JobExecution.job_id == job_id)
        )
        execution = execution_result.scalar_one_or_none()
        if not execution:
            return JSONResponse(
                status_code=404,
                content={
                    "error": "Execution not found",
                    "message": f"No execution found with ID: {execution_id} for job: {job_id}",
                },
            )

        return JobExecutionDetailReadResponse(
            job=JobSummary(id=job.id, name=job.name),
            execution=ExecutionReadPayload.model_validate(execution.to_dict()),
        )
    except Exception as exc:
        logger.exception("Error fetching execution %s for job %s", execution_id, job_id)
        settings = get_settings()
        return JSONResponse(
            status_code=500,
            content={
                "error": ERROR_INTERNAL_SERVER,
                "message": str(exc) if settings.expose_error_details else ERROR_INTERNAL_SERVER,
            },
        )


@router.get(
    "/executions",
    response_model=ExecutionsListReadResponse,
    summary="List executions (read-only)",
    description="Matches Flask `/api/executions` response shape.",
)
async def list_executions(
    _: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=200),
    job_id: Optional[str] = Query(None),
    status: Optional[str] = Query(None, description="success|failed|running (or comma-separated list)"),
    trigger_type: Optional[str] = Query(None, description="scheduled|manual"),
    execution_type: Optional[str] = Query(None, description="github_actions|webhook"),
    from_: Optional[str] = Query(None, alias="from"),
    to: Optional[str] = Query(None),
):
    try:
        from_dt = _parse_iso_date_or_datetime(from_)
        to_dt = _parse_iso_date_or_datetime(to)
        if to and to_dt and len(to.strip()) == 10:
            to_dt = to_dt + timedelta(days=1)
        if from_dt and to_dt and from_dt >= to_dt:
            return JSONResponse(
                status_code=400,
                content={"error": "Invalid date range", "message": '"from" must be earlier than "to".'},
            )

        base = select(JobExecution, Job.name, Job.github_repo).join(Job, JobExecution.job_id == Job.id)

        if job_id:
            base = base.where(JobExecution.job_id == job_id)
        if status:
            statuses = [s.strip() for s in status.split(",") if s.strip()]
            if len(statuses) == 1:
                base = base.where(JobExecution.status == statuses[0])
            elif len(statuses) > 1:
                base = base.where(JobExecution.status.in_(statuses))
        if trigger_type:
            base = base.where(JobExecution.trigger_type == trigger_type)
        if execution_type:
            base = base.where(JobExecution.execution_type == execution_type)
        if from_dt:
            base = base.where(JobExecution.started_at >= from_dt)
        if to_dt:
            base = base.where(JobExecution.started_at < to_dt)

        total_result = await db.execute(select(func.count()).select_from(base.subquery()))
        total = int(total_result.scalar_one() or 0)
        total_pages = (total + limit - 1) // limit if total else 0

        page_query = base.order_by(desc(JobExecution.started_at)).offset((page - 1) * limit).limit(limit)
        rows = (await db.execute(page_query)).all()

        executions: list[ExecutionWithJobReadPayload] = []
        for execution, job_name, github_repo in rows:
            data = execution.to_dict()
            data["job_name"] = job_name
            data["github_repo"] = github_repo
            executions.append(ExecutionWithJobReadPayload.model_validate(data))

        return ExecutionsListReadResponse(
            executions=executions,
            total=total,
            page=page,
            limit=limit,
            total_pages=total_pages,
        )
    except Exception as exc:
        logger.exception("Error listing executions")
        settings = get_settings()
        return JSONResponse(
            status_code=500,
            content={
                "error": ERROR_INTERNAL_SERVER,
                "message": str(exc) if settings.expose_error_details else ERROR_INTERNAL_SERVER,
            },
        )


@router.get(
    "/executions/statistics",
    response_model=ExecutionStatisticsReadResponse,
    summary="Get execution statistics (read-only)",
    description="Matches Flask `/api/executions/statistics` response shape.",
)
async def get_execution_statistics(
    _: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    job_id: Optional[str] = Query(None),
    from_: Optional[str] = Query(None, alias="from"),
    to: Optional[str] = Query(None),
):
    try:
        from_dt = _parse_iso_date_or_datetime(from_)
        to_dt = _parse_iso_date_or_datetime(to)

        if to and to_dt and len(to.strip()) == 10:
            to_dt = to_dt + timedelta(days=1)

        if from_dt and to_dt and from_dt >= to_dt:
            return JSONResponse(
                status_code=400,
                content={"error": "Invalid date range", "message": '"from" must be earlier than "to".'},
            )

        filters = []
        if job_id:
            filters.append(JobExecution.job_id == job_id)
        if from_dt:
            filters.append(JobExecution.started_at >= from_dt)
        if to_dt:
            filters.append(JobExecution.started_at < to_dt)

        total_result = await db.execute(select(func.count()).select_from(JobExecution).where(*filters))
        total = int(total_result.scalar_one() or 0)

        successful_result = await db.execute(
            select(func.count())
            .select_from(JobExecution)
            .where(*filters, JobExecution.status == "success")
        )
        successful = int(successful_result.scalar_one() or 0)

        failed_result = await db.execute(
            select(func.count())
            .select_from(JobExecution)
            .where(*filters, JobExecution.status == "failed")
        )
        failed = int(failed_result.scalar_one() or 0)

        running_result = await db.execute(
            select(func.count())
            .select_from(JobExecution)
            .where(*filters, JobExecution.status == "running")
        )
        running = int(running_result.scalar_one() or 0)

        avg_result = await db.execute(
            select(func.avg(JobExecution.duration_seconds))
            .select_from(JobExecution)
            .where(*filters)
        )
        avg_duration = float(avg_result.scalar_one() or 0.0)

        success_rate = (successful / total * 100.0) if total else 0.0

        return ExecutionStatisticsReadResponse(
            total_executions=total,
            successful_executions=successful,
            failed_executions=failed,
            running_executions=running,
            success_rate=success_rate,
            average_duration_seconds=avg_duration,
            range={
                "from": from_dt.isoformat() if from_dt else None,
                "to": to_dt.isoformat() if to_dt else None,
            },
        )
    except Exception as exc:
        logger.exception("Error getting execution statistics")
        settings = get_settings()
        return JSONResponse(
            status_code=500,
            content={
                "error": ERROR_INTERNAL_SERVER,
                "message": str(exc) if settings.expose_error_details else ERROR_INTERNAL_SERVER,
            },
        )


@router.get(
    "/executions/{execution_id}",
    response_model=ExecutionGetReadResponse,
    summary="Get execution by id (read-only)",
    description="Matches Flask `/api/executions/<execution_id>` response shape.",
)
async def get_execution(
    execution_id: str,
    _: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    try:
        result = await db.execute(
            select(JobExecution, Job.name, Job.github_repo)
            .join(Job, JobExecution.job_id == Job.id)
            .where(JobExecution.id == execution_id)
            .limit(1)
        )
        row = result.first()
        if not row:
            return JSONResponse(
                status_code=404,
                content={"error": "Execution not found", "message": f"No execution found with ID: {execution_id}"},
            )

        execution, job_name, github_repo = row
        data = execution.to_dict()
        data["job_name"] = job_name
        data["github_repo"] = github_repo

        return ExecutionGetReadResponse(execution=ExecutionWithJobReadPayload.model_validate(data))
    except Exception as exc:
        logger.exception("Error retrieving execution %s", execution_id)
        settings = get_settings()
        return JSONResponse(
            status_code=500,
            content={
                "error": ERROR_INTERNAL_SERVER,
                "message": str(exc) if settings.expose_error_details else ERROR_INTERNAL_SERVER,
            },
        )
