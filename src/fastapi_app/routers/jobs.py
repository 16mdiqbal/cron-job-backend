"""
Jobs Router (Read-Only).

Phase 4B: Migrate low-risk read endpoints first.

Implements:
- GET /api/v2/jobs
- GET /api/v2/jobs/{job_id}
- POST /api/v2/jobs (Phase 5A)
- PUT /api/v2/jobs/{job_id} (Phase 5B)
- DELETE /api/v2/jobs/{job_id} (Phase 5C)
- POST /api/v2/jobs/{job_id}/execute (Phase 5D)
"""

import logging
import os
import re
from datetime import date, datetime
from typing import Annotated, Optional, Any
from urllib.parse import urlparse
from zoneinfo import ZoneInfo

from apscheduler.triggers.cron import CronTrigger
from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
import httpx
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


@router.put(
    "/{job_id}",
    status_code=200,
    summary="Update job",
    description="Update an existing job. Phase 5 is DB-first (no APScheduler scheduling side-effects in FastAPI).",
)
async def update_job(
    job_id: str,
    request: Request,
    current_user: UserOrAdmin,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    try:
        job_result = await db.execute(select(Job).where(Job.id == job_id).limit(1))
        job = job_result.scalar_one_or_none()
        if not job:
            return JSONResponse(
                status_code=404,
                content={"error": ERROR_JOB_NOT_FOUND, "message": f"No job found with ID: {job_id}"},
            )

        if current_user.role != "admin" and job.created_by != current_user.id:
            return JSONResponse(
                status_code=403,
                content={"error": "Insufficient permissions", "message": "You can only update your own jobs"},
            )

        content_type = (request.headers.get("content-type") or "").lower()
        if "application/json" not in content_type:
            return JSONResponse(status_code=400, content={"error": "Content-Type must be application/json"})

        try:
            data: dict[str, Any] = await request.json()
        except Exception:
            return JSONResponse(status_code=400, content={"error": "Invalid JSON"})

        if "name" in data:
            new_name = str(data.get("name", "")).strip()
            if not new_name:
                return JSONResponse(status_code=400, content={"error": "Job name cannot be empty"})
            if new_name != job.name:
                existing = await db.execute(
                    select(Job).where(Job.name == new_name, Job.id != job.id).limit(1)
                )
                if existing.scalar_one_or_none():
                    return JSONResponse(
                        status_code=400,
                        content={"error": "Duplicate job name", "message": f'A job with the name "{new_name}" already exists.'},
                    )
                job.name = new_name

        if "cron_expression" in data:
            new_cron = str(data.get("cron_expression", "")).strip()
            cron_err = _cron_validation_error(new_cron)
            if cron_err:
                return JSONResponse(status_code=400, content={"error": "Invalid cron expression", "message": cron_err})
            job.cron_expression = new_cron

        if "target_url" in data:
            job.target_url = str(data.get("target_url", "")).strip() or None

        if "github_owner" in data:
            job.github_owner = str(data.get("github_owner", "")).strip() or None
        if "github_repo" in data:
            job.github_repo = str(data.get("github_repo", "")).strip() or None
        if "github_workflow_name" in data:
            job.github_workflow_name = str(data.get("github_workflow_name", "")).strip() or None

        if not job.target_url and job.github_repo and job.github_workflow_name and not job.github_owner:
            job.github_owner = get_settings().default_github_owner

        if "metadata" in data:
            metadata = data.get("metadata")
            if metadata is None:
                metadata = {}
            if not isinstance(metadata, dict):
                return JSONResponse(
                    status_code=400,
                    content={"error": "Invalid metadata", "message": "metadata must be a JSON object"},
                )
            job.set_metadata(metadata)

        if "category" in data:
            category = await _resolve_category_slug(db, data.get("category"))
            category_error = await _validate_category_slug(db, category)
            if category_error:
                return JSONResponse(status_code=400, content={"error": "Invalid category", "message": category_error})
            job.category = category

        if "end_date" in data:
            end_date_raw = data.get("end_date")
            try:
                parsed_end_date = date.fromisoformat(str(end_date_raw).strip()) if end_date_raw else None
            except Exception:
                return JSONResponse(
                    status_code=400,
                    content={"error": "Invalid end_date", "message": "Invalid end_date. Use YYYY-MM-DD."},
                )
            if not parsed_end_date:
                return JSONResponse(
                    status_code=400,
                    content={"error": "Invalid end_date", "message": "end_date is required (YYYY-MM-DD)."},
                )
            if parsed_end_date < _today_jst():
                return JSONResponse(
                    status_code=400,
                    content={"error": "Invalid end_date", "message": "end_date must be today or in the future (JST)."},
                )
            job.end_date = parsed_end_date

        if "pic_team" in data or "pic_team_slug" in data:
            pic_team_raw = data.get("pic_team") or data.get("pic_team_slug")
            pic_team = await _resolve_pic_team_slug(db, str(pic_team_raw).strip() if pic_team_raw is not None else None)
            pic_team_error = await _validate_pic_team_slug(db, pic_team)
            if pic_team_error:
                return JSONResponse(status_code=400, content={"error": "Invalid PIC team", "message": pic_team_error})
            job.pic_team = pic_team

        if "enable_email_notifications" in data:
            job.enable_email_notifications = bool(data.get("enable_email_notifications"))
            if not job.enable_email_notifications:
                job.set_notification_emails([])
                job.notify_on_success = False

        if "notification_emails" in data:
            emails = data.get("notification_emails")
            if emails is None:
                emails = []
            if not isinstance(emails, list):
                return JSONResponse(
                    status_code=400,
                    content={"error": "Invalid notification_emails", "message": "notification_emails must be a list"},
                )
            if job.enable_email_notifications:
                job.set_notification_emails(emails)
            else:
                job.set_notification_emails([])

        if "notify_on_success" in data:
            job.notify_on_success = bool(data.get("notify_on_success")) if job.enable_email_notifications else False

        if "is_active" in data:
            job.is_active = bool(data.get("is_active"))

        if job.is_active and job.end_date and job.end_date < _today_jst():
            return JSONResponse(
                status_code=400,
                content={
                    "error": "Job expired",
                    "message": "Job cannot be enabled after end_date has passed. Update end_date first.",
                },
            )

        if not job.target_url and not (job.github_owner and job.github_repo and job.github_workflow_name):
            return JSONResponse(
                status_code=400,
                content={
                    "error": "Missing target configuration",
                    "message": "Job must have either target_url or complete GitHub Actions configuration",
                },
            )

        await db.commit()
        await db.refresh(job)

        return JSONResponse(status_code=200, content={"message": "Job updated successfully", "job": job.to_dict()})
    except Exception as exc:
        await db.rollback()
        logger.exception("Error updating job %s", job_id)
        settings = get_settings()
        return JSONResponse(
            status_code=500,
            content={
                "error": ERROR_INTERNAL_SERVER,
                "message": str(exc) if settings.expose_error_details else ERROR_INTERNAL_SERVER,
            },
        )


@router.delete(
    "/{job_id}",
    status_code=200,
    summary="Delete job",
    description="Delete a job. Phase 5 is DB-first (no APScheduler scheduling side-effects in FastAPI).",
)
async def delete_job(
    job_id: str,
    current_user: UserOrAdmin,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    try:
        job_result = await db.execute(select(Job).where(Job.id == job_id).limit(1))
        job = job_result.scalar_one_or_none()
        if not job:
            return JSONResponse(
                status_code=404,
                content={"error": ERROR_JOB_NOT_FOUND, "message": f"No job found with ID: {job_id}"},
            )

        if current_user.role != "admin" and job.created_by != current_user.id:
            return JSONResponse(
                status_code=403,
                content={"error": "Insufficient permissions", "message": "You can only delete your own jobs"},
            )

        deleted_job = {"id": job.id, "name": job.name}

        await db.delete(job)
        await db.commit()

        return JSONResponse(status_code=200, content={"message": "Job deleted successfully", "deleted_job": deleted_job})
    except Exception as exc:
        await db.rollback()
        logger.exception("Error deleting job %s", job_id)
        settings = get_settings()
        return JSONResponse(
            status_code=500,
            content={
                "error": ERROR_INTERNAL_SERVER,
                "message": str(exc) if settings.expose_error_details else ERROR_INTERNAL_SERVER,
            },
        )


def _truncate_output(value: str, limit: int = 1000) -> str:
    if not value:
        return ""
    return value[:limit] if len(value) > limit else value


def _parse_dispatch_url(value: str) -> tuple[str, str, str]:
    candidate = value if "://" in value else f"https://{value}"
    parsed = urlparse(candidate)
    path = (parsed.path or "").strip("/")
    parts = [p for p in path.split("/") if p]
    if len(parts) >= 5 and parts[2] == "actions" and parts[3] == "workflows":
        return parts[0], parts[1], parts[4]
    raise ValueError("Invalid dispatch URL format. Expected /<owner>/<repo>/actions/workflows/<workflow>.")


async def _http_request(
    method: str,
    url: str,
    *,
    headers: Optional[dict[str, str]] = None,
    json_payload: Any = None,
) -> tuple[int, str]:
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.request(method, url, headers=headers, json=json_payload)
        return int(resp.status_code), resp.text or ""


@router.post(
    "/{job_id}/execute",
    status_code=200,
    summary="Execute job now",
    description="Execute a job immediately (manual trigger). Overrides are not persisted. Phase 5 is DB-first (no APScheduler side-effects).",
)
async def execute_job_now(
    job_id: str,
    request: Request,
    current_user: UserOrAdmin,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    try:
        job_result = await db.execute(select(Job).where(Job.id == job_id).limit(1))
        job = job_result.scalar_one_or_none()
        if not job:
            return JSONResponse(
                status_code=404,
                content={"error": ERROR_JOB_NOT_FOUND, "message": f"No job found with ID: {job_id}"},
            )

        if current_user.role != "admin" and job.created_by != current_user.id:
            return JSONResponse(
                status_code=403,
                content={"error": "Insufficient permissions", "message": "You can only execute your own jobs"},
            )

        if job.end_date and job.end_date < _today_jst():
            if job.is_active:
                job.is_active = False
                await db.commit()
                await db.refresh(job)
            return JSONResponse(
                status_code=400,
                content={"error": "Job expired", "message": "This job has passed its end_date and was auto-paused."},
            )

        raw_body = await request.body()
        if not raw_body or not raw_body.strip():
            data: dict[str, Any] = {}
        else:
            content_type = (request.headers.get("content-type") or "").lower()
            if "application/json" not in content_type:
                return JSONResponse(status_code=400, content={"error": "Content-Type must be application/json"})
            try:
                data = await request.json()
            except Exception:
                return JSONResponse(status_code=400, content={"error": "Invalid JSON"})
            if not isinstance(data, dict):
                return JSONResponse(
                    status_code=400,
                    content={"error": "Invalid payload", "message": "JSON body must be an object."},
                )

        override_metadata = data.get("metadata")
        if override_metadata is not None and not isinstance(override_metadata, dict):
            return JSONResponse(
                status_code=400,
                content={"error": "Invalid payload", "message": '"metadata" must be a JSON object.'},
            )

        github_token = (data.get("github_token") or "").strip() or None
        dispatch_url = (data.get("dispatch_url") or "").strip() or None

        base_config: dict[str, Any] = {
            "target_url": job.target_url,
            "github_owner": job.github_owner,
            "github_repo": job.github_repo,
            "github_workflow_name": job.github_workflow_name,
            "metadata": job.get_metadata(),
        }

        if job.target_url:
            if "target_url" in data:
                base_config["target_url"] = (data.get("target_url") or "").strip() or job.target_url
        else:
            if dispatch_url:
                try:
                    owner, repo, workflow_name = _parse_dispatch_url(dispatch_url)
                except ValueError as exc:
                    return JSONResponse(status_code=400, content={"error": "Invalid payload", "message": str(exc)})
                base_config["github_owner"] = owner
                base_config["github_repo"] = repo
                base_config["github_workflow_name"] = workflow_name

            if "github_owner" in data:
                base_config["github_owner"] = (data.get("github_owner") or "").strip() or job.github_owner
            if "github_repo" in data:
                base_config["github_repo"] = (data.get("github_repo") or "").strip() or job.github_repo
            if "github_workflow_name" in data:
                base_config["github_workflow_name"] = (data.get("github_workflow_name") or "").strip() or job.github_workflow_name
            if github_token:
                base_config["github_token"] = github_token

        if override_metadata is not None:
            base_config["metadata"] = override_metadata

        if not base_config.get("target_url") and not (
            base_config.get("github_owner") and base_config.get("github_repo") and base_config.get("github_workflow_name")
        ):
            return JSONResponse(
                status_code=400,
                content={"error": "Missing target configuration", "message": "Job has no valid target configuration to execute."},
            )

        execution = JobExecution(job_id=job.id, trigger_type="manual", status="running")
        db.add(execution)
        await db.commit()
        await db.refresh(execution)

        try:
            if base_config.get("github_owner") and base_config.get("github_repo") and base_config.get("github_workflow_name"):
                owner = base_config["github_owner"]
                repo = base_config["github_repo"]
                workflow_name = base_config["github_workflow_name"]
                metadata = base_config.get("metadata") if isinstance(base_config.get("metadata"), dict) else {}

                execution.execution_type = "github_actions"
                execution.target = f"{owner}/{repo}/{workflow_name}"
                await db.commit()

                token = base_config.get("github_token") or os.getenv("GITHUB_TOKEN")
                if not token:
                    error_msg = f"GitHub token not configured. Cannot trigger workflow for job '{job.name}'"
                    execution.mark_completed("failed", error_message=error_msg)
                    await db.commit()
                    return JSONResponse(status_code=200, content={"message": "Job triggered successfully", "job_id": job.id})

                url = f"https://api.github.com/repos/{owner}/{repo}/actions/workflows/{workflow_name}/dispatches"
                headers = {
                    "Authorization": f"Bearer {token}",
                    "Accept": "application/vnd.github+json",
                    "Content-Type": "application/json",
                }
                ref = metadata.get("branchDetails", "master")
                payload = {"ref": ref, "inputs": metadata}

                status_code, text = await _http_request("POST", url, headers=headers, json_payload=payload)
                if status_code == 204:
                    execution.mark_completed("success", response_status=204, output=f"Workflow triggered successfully on branch {ref}")
                else:
                    error_msg = f"GitHub Actions dispatch failed. Status: {status_code}, Response: {_truncate_output(text)}"
                    execution.mark_completed("failed", response_status=status_code, error_message=error_msg, output=_truncate_output(text))
                await db.commit()
            else:
                target_url = base_config.get("target_url")
                execution.execution_type = "webhook"
                execution.target = target_url
                await db.commit()

                payload = base_config.get("metadata") if isinstance(base_config.get("metadata"), dict) else None
                if payload:
                    status_code, text = await _http_request("POST", target_url, json_payload=payload)
                else:
                    status_code, text = await _http_request("GET", target_url)

                output = _truncate_output(text)
                if 200 <= status_code < 300:
                    execution.mark_completed("success", response_status=status_code, output=output)
                else:
                    execution.mark_completed(
                        "failed",
                        response_status=status_code,
                        error_message=f"Webhook returned status {status_code}",
                        output=output,
                    )
                await db.commit()
        except Exception as exc:
            execution.mark_completed("failed", error_message=f"Request failed: {exc}")
            await db.commit()

        return JSONResponse(status_code=200, content={"message": "Job triggered successfully", "job_id": job.id})
    except Exception as exc:
        await db.rollback()
        logger.exception("Error executing job %s", job_id)
        settings = get_settings()
        return JSONResponse(
            status_code=500,
            content={
                "error": ERROR_INTERNAL_SERVER,
                "message": str(exc) if settings.expose_error_details else ERROR_INTERNAL_SERVER,
            },
        )
