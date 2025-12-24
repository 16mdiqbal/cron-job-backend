"""
Taxonomy Router (Read-Only).

Phase 4E: Migrate low-risk taxonomy read endpoints first.

Implements:
- GET /api/v2/job-categories
- GET /api/v2/pic-teams
"""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import get_settings
from ..dependencies.auth import CurrentUser
from ..schemas.taxonomy_read import (
    JobCategoriesReadResponse,
    JobCategoryReadPayload,
    PicTeamReadPayload,
    PicTeamsReadResponse,
)
from ...database.session import get_db
from ...models.job_category import JobCategory
from ...models.pic_team import PicTeam

logger = logging.getLogger(__name__)

ERROR_INTERNAL_SERVER = "Internal server error"

router = APIRouter(responses={401: {"description": "Unauthorized"}, 500: {"description": "Internal server error"}})


@router.get(
    "/job-categories",
    response_model=JobCategoriesReadResponse,
    tags=["Categories"],
    summary="List job categories (read-only)",
    description="Matches Flask `/api/job-categories` response shape.",
)
async def list_job_categories(
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    include_inactive: bool = Query(False, description="Admin-only: include inactive categories"),
):
    try:
        query = select(JobCategory)
        if current_user.role != "admin" or not include_inactive:
            query = query.where(JobCategory.is_active.is_(True))

        query = query.order_by(func.lower(JobCategory.name))
        rows = (await db.execute(query)).scalars().all()
        categories = [JobCategoryReadPayload.model_validate(category.to_dict()) for category in rows]
        return JobCategoriesReadResponse(categories=categories)
    except Exception as exc:
        logger.exception("Error listing job categories")
        settings = get_settings()
        return JSONResponse(
            status_code=500,
            content={
                "error": ERROR_INTERNAL_SERVER,
                "message": str(exc) if settings.expose_error_details else ERROR_INTERNAL_SERVER,
            },
        )


@router.get(
    "/pic-teams",
    response_model=PicTeamsReadResponse,
    tags=["Teams"],
    summary="List PIC teams (read-only)",
    description="Matches Flask `/api/pic-teams` response shape.",
)
async def list_pic_teams(
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    include_inactive: bool = Query(False, description="Admin-only: include inactive PIC teams"),
):
    try:
        query = select(PicTeam)
        if current_user.role != "admin" or not include_inactive:
            query = query.where(PicTeam.is_active.is_(True))

        query = query.order_by(func.lower(PicTeam.name))
        rows = (await db.execute(query)).scalars().all()
        teams = [PicTeamReadPayload.model_validate(team.to_dict()) for team in rows]
        return PicTeamsReadResponse(pic_teams=teams)
    except Exception as exc:
        logger.exception("Error listing PIC teams")
        settings = get_settings()
        return JSONResponse(
            status_code=500,
            content={
                "error": ERROR_INTERNAL_SERVER,
                "message": str(exc) if settings.expose_error_details else ERROR_INTERNAL_SERVER,
            },
        )

