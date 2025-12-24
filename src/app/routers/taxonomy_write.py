"""
Taxonomy Write Router (Phase 7E/7F).

Phase 7E:
- POST /api/v2/job-categories
- PUT /api/v2/job-categories/{id}
- DELETE /api/v2/job-categories/{id}

Phase 7F (planned):
- PIC teams write endpoints
"""

import logging
import re
from typing import Annotated

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import get_settings
from ..dependencies.auth import AdminUser
from ...database.session import get_db
from ...models.job import Job
from ...models.job_category import JobCategory
from ...models.pic_team import PicTeam

logger = logging.getLogger(__name__)

ERROR_INTERNAL_SERVER = "Internal server error"

router = APIRouter(responses={401: {"description": "Unauthorized"}, 500: {"description": "Internal server error"}})


def _slugify(value: str) -> str:
    v = (value or "").strip().lower()
    v = re.sub(r"[^a-z0-9]+", "-", v)
    v = re.sub(r"-{2,}", "-", v).strip("-")
    return v


@router.post(
    "/job-categories",
    summary="Create job category",
    description="Admin-only. Matches Flask `/api/job-categories` response shape.",
    tags=["Categories"],
)
async def create_job_category(
    request: Request,
    _: AdminUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    content_type = (request.headers.get("content-type") or "").lower()
    if "application/json" not in content_type:
        return JSONResponse(status_code=400, content={"error": "Content-Type must be application/json"})

    try:
        data = await request.json()
    except Exception:
        return JSONResponse(status_code=400, content={"error": "Invalid JSON"})
    if not isinstance(data, dict):
        return JSONResponse(status_code=400, content={"error": "Invalid payload", "message": "JSON body must be an object."})

    name = (data.get("name") or "").strip()
    if not name:
        return JSONResponse(
            status_code=400,
            content={"error": "Missing required fields", "message": '"name" is required.'},
        )

    slug = (data.get("slug") or "").strip()
    slug = _slugify(slug or name)
    if not slug:
        return JSONResponse(
            status_code=400,
            content={"error": "Invalid slug", "message": "Unable to generate a valid slug from name."},
        )

    existing = await db.execute(select(JobCategory).where(JobCategory.slug == slug).limit(1))
    if existing.scalar_one_or_none():
        return JSONResponse(
            status_code=409,
            content={"error": "Duplicate slug", "message": f'Category slug "{slug}" already exists.'},
        )

    category = JobCategory(slug=slug, name=name, is_active=True)
    db.add(category)
    await db.commit()
    await db.refresh(category)

    return JSONResponse(status_code=201, content={"message": "Category created", "category": category.to_dict()})


@router.put(
    "/job-categories/{category_id}",
    summary="Update job category",
    description="Admin-only. Matches Flask `/api/job-categories/<id>` response shape.",
    tags=["Categories"],
)
async def update_job_category(
    category_id: str,
    request: Request,
    _: AdminUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    content_type = (request.headers.get("content-type") or "").lower()
    if "application/json" not in content_type:
        return JSONResponse(status_code=400, content={"error": "Content-Type must be application/json"})

    try:
        data = await request.json()
    except Exception:
        return JSONResponse(status_code=400, content={"error": "Invalid JSON"})
    if not isinstance(data, dict):
        return JSONResponse(status_code=400, content={"error": "Invalid payload", "message": "JSON body must be an object."})

    result = await db.execute(select(JobCategory).where(JobCategory.id == category_id).limit(1))
    category = result.scalar_one_or_none()
    if not category:
        return JSONResponse(
            status_code=404,
            content={"error": "Not found", "message": f"No category found with ID: {category_id}"},
        )

    jobs_updated = 0

    if "name" in data:
        name = (data.get("name") or "").strip()
        if not name:
            return JSONResponse(status_code=400, content={"error": "Invalid name", "message": "Name cannot be empty."})

        if category.slug == "general" and name != category.name:
            return JSONResponse(
                status_code=400,
                content={"error": "Invalid category", "message": 'The "General" category cannot be renamed.'},
            )

        desired_slug = _slugify(name)
        if not desired_slug:
            return JSONResponse(
                status_code=400,
                content={"error": "Invalid slug", "message": "Unable to generate a valid slug from name."},
            )

        if desired_slug != category.slug:
            existing = await db.execute(select(JobCategory).where(JobCategory.slug == desired_slug).limit(1))
            if existing.scalar_one_or_none():
                return JSONResponse(
                    status_code=409,
                    content={"error": "Duplicate slug", "message": f'Category slug "{desired_slug}" already exists.'},
                )

            old_slug = category.slug
            update_stmt = update(Job).where(Job.category == old_slug).values(category=desired_slug)
            update_result = await db.execute(update_stmt)
            jobs_updated = int(update_result.rowcount or 0)
            category.slug = desired_slug

        category.name = name

    if "slug" in data:
        return JSONResponse(
            status_code=400,
            content={"error": "Invalid payload", "message": "Slug cannot be edited directly; it is derived from name."},
        )

    if "is_active" in data:
        category.is_active = bool(data.get("is_active"))

    await db.commit()
    await db.refresh(category)

    return JSONResponse(
        status_code=200,
        content={"message": "Category updated", "category": category.to_dict(), "jobs_updated": jobs_updated},
    )


@router.delete(
    "/job-categories/{category_id}",
    summary="Disable job category",
    description="Admin-only. Matches Flask `/api/job-categories/<id>` response shape.",
    tags=["Categories"],
)
async def delete_job_category(
    category_id: str,
    _: AdminUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    result = await db.execute(select(JobCategory).where(JobCategory.id == category_id).limit(1))
    category = result.scalar_one_or_none()
    if not category:
        return JSONResponse(
            status_code=404,
            content={"error": "Not found", "message": f"No category found with ID: {category_id}"},
        )

    category.is_active = False
    await db.commit()
    await db.refresh(category)

    return JSONResponse(status_code=200, content={"message": "Category disabled", "category": category.to_dict()})


@router.post(
    "/pic-teams",
    summary="Create PIC team",
    description="Admin-only. Matches Flask `/api/pic-teams` response shape.",
    tags=["Teams"],
)
async def create_pic_team(
    request: Request,
    _: AdminUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    content_type = (request.headers.get("content-type") or "").lower()
    if "application/json" not in content_type:
        return JSONResponse(status_code=400, content={"error": "Content-Type must be application/json"})

    try:
        data = await request.json()
    except Exception:
        return JSONResponse(status_code=400, content={"error": "Invalid JSON"})
    if not isinstance(data, dict):
        return JSONResponse(status_code=400, content={"error": "Invalid payload", "message": "JSON body must be an object."})

    name = (data.get("name") or "").strip()
    if not name:
        return JSONResponse(
            status_code=400,
            content={"error": "Missing required fields", "message": '"name" is required.'},
        )

    slack_handle = (data.get("slack_handle") or "").strip()
    if not slack_handle:
        return JSONResponse(
            status_code=400,
            content={"error": "Missing required fields", "message": '"slack_handle" is required.'},
        )

    slug = (data.get("slug") or "").strip()
    slug = _slugify(slug or name)
    if not slug:
        return JSONResponse(
            status_code=400,
            content={"error": "Invalid slug", "message": "Unable to generate a valid slug from name."},
        )

    existing = await db.execute(select(PicTeam).where(PicTeam.slug == slug).limit(1))
    if existing.scalar_one_or_none():
        return JSONResponse(
            status_code=409,
            content={"error": "Duplicate slug", "message": f'PIC team slug "{slug}" already exists.'},
        )

    team = PicTeam(slug=slug, name=name, slack_handle=slack_handle, is_active=True)
    db.add(team)
    await db.commit()
    await db.refresh(team)

    return JSONResponse(status_code=201, content={"message": "PIC team created", "pic_team": team.to_dict()})


@router.put(
    "/pic-teams/{team_id}",
    summary="Update PIC team",
    description="Admin-only. Matches Flask `/api/pic-teams/<id>` response shape.",
    tags=["Teams"],
)
async def update_pic_team(
    team_id: str,
    request: Request,
    _: AdminUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    content_type = (request.headers.get("content-type") or "").lower()
    if "application/json" not in content_type:
        return JSONResponse(status_code=400, content={"error": "Content-Type must be application/json"})

    try:
        data = await request.json()
    except Exception:
        return JSONResponse(status_code=400, content={"error": "Invalid JSON"})
    if not isinstance(data, dict):
        return JSONResponse(status_code=400, content={"error": "Invalid payload", "message": "JSON body must be an object."})

    result = await db.execute(select(PicTeam).where(PicTeam.id == team_id).limit(1))
    team = result.scalar_one_or_none()
    if not team:
        return JSONResponse(
            status_code=404,
            content={"error": "Not found", "message": f"No PIC team found with ID: {team_id}"},
        )

    jobs_updated = 0

    if "name" in data:
        name = (data.get("name") or "").strip()
        if not name:
            return JSONResponse(status_code=400, content={"error": "Invalid name", "message": "Name cannot be empty."})

        desired_slug = _slugify(name)
        if not desired_slug:
            return JSONResponse(
                status_code=400,
                content={"error": "Invalid slug", "message": "Unable to generate a valid slug from name."},
            )

        if desired_slug != team.slug:
            existing = await db.execute(select(PicTeam).where(PicTeam.slug == desired_slug).limit(1))
            if existing.scalar_one_or_none():
                return JSONResponse(
                    status_code=409,
                    content={"error": "Duplicate slug", "message": f'PIC team slug "{desired_slug}" already exists.'},
                )

            old_slug = team.slug
            update_stmt = update(Job).where(Job.pic_team == old_slug).values(pic_team=desired_slug)
            update_result = await db.execute(update_stmt)
            jobs_updated = int(update_result.rowcount or 0)
            team.slug = desired_slug

        team.name = name

    if "slug" in data:
        return JSONResponse(
            status_code=400,
            content={"error": "Invalid payload", "message": "Slug cannot be edited directly; it is derived from name."},
        )

    if "is_active" in data:
        team.is_active = bool(data.get("is_active"))

    if "slack_handle" in data:
        slack_handle = (data.get("slack_handle") or "").strip()
        if not slack_handle:
            return JSONResponse(
                status_code=400,
                content={"error": "Invalid slack_handle", "message": "slack_handle cannot be empty."},
            )
        team.slack_handle = slack_handle

    await db.commit()
    await db.refresh(team)

    return JSONResponse(
        status_code=200,
        content={"message": "PIC team updated", "pic_team": team.to_dict(), "jobs_updated": jobs_updated},
    )


@router.delete(
    "/pic-teams/{team_id}",
    summary="Disable PIC team",
    description="Admin-only. Matches Flask `/api/pic-teams/<id>` response shape.",
    tags=["Teams"],
)
async def delete_pic_team(
    team_id: str,
    _: AdminUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    result = await db.execute(select(PicTeam).where(PicTeam.id == team_id).limit(1))
    team = result.scalar_one_or_none()
    if not team:
        return JSONResponse(
            status_code=404,
            content={"error": "Not found", "message": f"No PIC team found with ID: {team_id}"},
        )

    team.is_active = False
    await db.commit()
    await db.refresh(team)

    return JSONResponse(status_code=200, content={"message": "PIC team disabled", "pic_team": team.to_dict()})
