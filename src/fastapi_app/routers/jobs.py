"""
Jobs Router (Read-Only).

Phase 4B: Migrate low-risk read endpoints first.

Implements:
- GET /api/v2/jobs
- GET /api/v2/jobs/{job_id}
- POST /api/v2/jobs (Phase 5A)
"""

import logging
import re
from datetime import date, datetime
from typing import Annotated, Optional, Any
from zoneinfo import ZoneInfo

from apscheduler.triggers.cron import CronTrigger
from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import get_settings
from ..dependencies.auth import CurrentUser, UserOrAdmin
from ..schemas.jobs_read import JobGetReadResponse, JobListReadResponse, JobReadPayload
from ...database.session import get_db
from ...models.job import Job
from ...models.job_category import JobCategory
from ...models.job_execution import JobExecution
from ...models.pic_team import PicTeam

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


def _slugify(value: str) -> str:
    v = (value or "").strip().lower()
    v = re.sub(r"[^a-z0-9]+", "-", v)
    v = re.sub(r"-{2,}", "-", v).strip("-")
    return v


def _today_jst() -> date:
    tz = _get_scheduler_timezone()
    return datetime.now(tz).date()


def _cron_validation_error(expression: str) -> Optional[str]:
    expr = (expression or "").strip()
    if not expr:
        return "Cron expression is required."

    parts = expr.split()
    if len(parts) != 5:
        return "Cron expression must have exactly 5 fields (minute hour day month day-of-week)."

    try:
        CronTrigger.from_crontab(expr, timezone=_get_scheduler_timezone())
    except Exception as exc:
        return str(exc) or "Invalid cron expression."
    return None


async def _resolve_category_slug(db: AsyncSession, raw: Optional[str]) -> str:
    """
    Resolve a category from either a slug or a display name.
    Falls back to 'general' when missing.
    """
    if raw is None:
        return "general"
    val = raw.strip()
    if not val:
        return "general"

    slug = _slugify(val)
    result = await db.execute(select(JobCategory).where(JobCategory.slug == slug).limit(1))
    category = result.scalar_one_or_none()
    if category:
        return category.slug

    result = await db.execute(select(JobCategory).where(func.lower(JobCategory.name) == val.lower()).limit(1))
    category = result.scalar_one_or_none()
    if category:
        return category.slug

    return slug


async def _validate_category_slug(db: AsyncSession, slug: str) -> Optional[str]:
    if slug == "general":
        return None
    result = await db.execute(select(JobCategory).where(JobCategory.slug == slug).limit(1))
    exists = result.scalar_one_or_none()
    if not exists:
        return "Unknown category. Create it in Settings → Categories first, or choose General."
    return None


async def _resolve_pic_team_slug(db: AsyncSession, raw: Optional[str]) -> Optional[str]:
    """
    Resolve a PIC team from either a slug or a display name.
    Returns a normalized slug (even if it doesn't exist) so validation can explain.
    """
    if raw is None:
        return None
    val = raw.strip()
    if not val:
        return None

    slug = _slugify(val)
    result = await db.execute(select(PicTeam).where(PicTeam.slug == slug).limit(1))
    team = result.scalar_one_or_none()
    if team:
        return team.slug

    result = await db.execute(select(PicTeam).where(func.lower(PicTeam.name) == val.lower()).limit(1))
    team = result.scalar_one_or_none()
    if team:
        return team.slug

    return slug


async def _validate_pic_team_slug(db: AsyncSession, slug: Optional[str]) -> Optional[str]:
    if not slug:
        return "PIC team is required. Create one in Settings → PIC Teams."
    result = await db.execute(select(PicTeam).where(PicTeam.slug == slug).limit(1))
    team = result.scalar_one_or_none()
    if not team:
        return "Unknown PIC team. Create it in Settings → PIC Teams first."
    if not team.is_active:
        return "PIC team is disabled. Enable it in Settings → PIC Teams or choose another."
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


@router.post(
    "",
    status_code=201,
    summary="Create job",
    description="Create a new job. Phase 5 is DB-first (no APScheduler scheduling side-effects in FastAPI).",
)
async def create_job(
    request: Request,
    current_user: UserOrAdmin,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    try:
        content_type = (request.headers.get("content-type") or "").lower()
        if "application/json" not in content_type:
            return JSONResponse(status_code=400, content={"error": "Content-Type must be application/json"})

        try:
            data: dict[str, Any] = await request.json()
        except Exception:
            return JSONResponse(status_code=400, content={"error": "Invalid JSON"})

        required_fields = ["name", "cron_expression", "end_date"]
        missing_fields = [field for field in required_fields if field not in data]
        if missing_fields:
            return JSONResponse(
                status_code=400,
                content={"error": "Missing required fields", "missing_fields": missing_fields},
            )

        name = str(data.get("name", "")).strip()
        cron_expression = str(data.get("cron_expression", "")).strip()
        if not name:
            return JSONResponse(status_code=400, content={"error": "Job name cannot be empty"})

        existing = await db.execute(select(Job).where(Job.name == name).limit(1))
        if existing.scalar_one_or_none():
            return JSONResponse(
                status_code=400,
                content={
                    "error": "Duplicate job name",
                    "message": f'A job with the name "{name}" already exists. Please use a unique name.',
                },
            )

        cron_err = _cron_validation_error(cron_expression)
        if cron_err:
            return JSONResponse(status_code=400, content={"error": "Invalid cron expression", "message": cron_err})

        target_url = str(data.get("target_url", "")).strip() or None
        github_owner = str(data.get("github_owner", "")).strip() or None
        github_repo = str(data.get("github_repo", "")).strip() or None
        github_workflow_name = str(data.get("github_workflow_name", "")).strip() or None

        category = await _resolve_category_slug(db, data.get("category"))
        category_error = await _validate_category_slug(db, category)
        if category_error:
            return JSONResponse(status_code=400, content={"error": "Invalid category", "message": category_error})

        metadata = data.get("metadata", {})
        if metadata is None:
            metadata = {}
        if not isinstance(metadata, dict):
            return JSONResponse(
                status_code=400,
                content={"error": "Invalid metadata", "message": "metadata must be a JSON object"},
            )

        enable_email_notifications = bool(data.get("enable_email_notifications", False))
        notification_emails = data.get("notification_emails", []) if enable_email_notifications else []
        notify_on_success = bool(data.get("notify_on_success", False)) if enable_email_notifications else False

        if not isinstance(notification_emails, list):
            return JSONResponse(
                status_code=400,
                content={"error": "Invalid notification_emails", "message": "notification_emails must be a list"},
            )

        end_date_raw = data.get("end_date")
        try:
            end_date = date.fromisoformat(str(end_date_raw).strip()) if end_date_raw else None
        except Exception:
            return JSONResponse(
                status_code=400,
                content={"error": "Invalid end_date", "message": "Invalid end_date. Use YYYY-MM-DD."},
            )
        if not end_date:
            return JSONResponse(
                status_code=400,
                content={"error": "Missing required fields", "message": '"end_date" is required (YYYY-MM-DD).'},
            )
        if end_date < _today_jst():
            return JSONResponse(
                status_code=400,
                content={
                    "error": "Invalid end_date",
                    "message": "end_date must be today or in the future (JST).",
                },
            )

        pic_team_raw = data.get("pic_team") or data.get("pic_team_slug")
        pic_team = await _resolve_pic_team_slug(db, str(pic_team_raw).strip() if pic_team_raw is not None else None)
        pic_team_error = await _validate_pic_team_slug(db, pic_team)
        if pic_team_error:
            return JSONResponse(status_code=400, content={"error": "Invalid PIC team", "message": pic_team_error})

        if not target_url and not (github_owner and github_repo and github_workflow_name):
            if github_repo and github_workflow_name and not github_owner:
                github_owner = get_settings().default_github_owner
            else:
                return JSONResponse(
                    status_code=400,
                    content={
                        "error": "Missing target configuration",
                        "message": 'Please provide either "target_url" or GitHub Actions configuration (github_owner, github_repo, github_workflow_name)',
                    },
                )

        if not target_url and github_repo and github_workflow_name and not github_owner:
            github_owner = get_settings().default_github_owner

        if not target_url and not (github_owner and github_repo and github_workflow_name):
            return JSONResponse(
                status_code=400,
                content={
                    "error": "Missing target configuration",
                    "message": 'Please provide either "target_url" or GitHub Actions configuration (github_owner, github_repo, github_workflow_name)',
                },
            )

        new_job = Job(
            name=name,
            cron_expression=cron_expression,
            target_url=target_url,
            github_owner=github_owner,
            github_repo=github_repo,
            github_workflow_name=github_workflow_name,
            category=category,
            end_date=end_date,
            pic_team=pic_team,
            created_by=current_user.id,
            is_active=True,
            enable_email_notifications=enable_email_notifications,
            notify_on_success=notify_on_success,
        )
        if metadata:
            new_job.set_metadata(metadata)
        if enable_email_notifications and notification_emails:
            new_job.set_notification_emails(notification_emails)

        db.add(new_job)
        await db.commit()
        await db.refresh(new_job)

        return JSONResponse(status_code=201, content={"message": "Job created successfully", "job": new_job.to_dict()})
    except Exception as exc:
        logger.exception("Error creating job")
        settings = get_settings()
        return JSONResponse(
            status_code=500,
            content={
                "error": ERROR_INTERNAL_SERVER,
                "message": str(exc) if settings.expose_error_details else ERROR_INTERNAL_SERVER,
            },
        )
