"""
Settings Router (Phase 7D).

Implements:
- GET /api/v2/settings/slack (admin-only)
- PUT /api/v2/settings/slack (admin-only)
"""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import get_settings
from ..dependencies.auth import AdminUser
from ...database.session import get_db
from ...models.slack_settings import SlackSettings

logger = logging.getLogger(__name__)

ERROR_INTERNAL_SERVER = "Internal server error"

router = APIRouter(responses={401: {"description": "Unauthorized"}, 500: {"description": "Internal server error"}})


async def _get_or_create_slack_settings(db: AsyncSession) -> SlackSettings:
    result = await db.execute(select(SlackSettings).limit(1))
    settings = result.scalar_one_or_none()
    if settings:
        return settings

    settings = SlackSettings(is_enabled=False, webhook_url=None, channel=None)
    db.add(settings)
    await db.commit()
    await db.refresh(settings)
    return settings


@router.get(
    "/settings/slack",
    summary="Get Slack settings",
    description="Admin-only. Matches Flask `/api/settings/slack` response shape.",
    tags=["Settings"],
)
async def get_slack_settings(
    _: AdminUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    try:
        settings = await _get_or_create_slack_settings(db)
        return JSONResponse(status_code=200, content={"slack_settings": settings.to_dict()})
    except Exception as exc:
        logger.exception("Error retrieving Slack settings")
        app_settings = get_settings()
        return JSONResponse(
            status_code=500,
            content={
                "error": ERROR_INTERNAL_SERVER,
                "message": str(exc) if app_settings.expose_error_details else ERROR_INTERNAL_SERVER,
            },
        )


@router.put(
    "/settings/slack",
    summary="Update Slack settings",
    description="Admin-only. Matches Flask `/api/settings/slack` response shape.",
    tags=["Settings"],
)
async def update_slack_settings(
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

    try:
        settings = await _get_or_create_slack_settings(db)

        if "is_enabled" in data:
            settings.is_enabled = bool(data.get("is_enabled"))

        if "webhook_url" in data:
            webhook_url = (data.get("webhook_url") or "").strip()
            settings.webhook_url = webhook_url or None

        if "channel" in data:
            channel = (data.get("channel") or "").strip()
            settings.channel = channel or None

        if settings.is_enabled and not settings.webhook_url:
            return JSONResponse(
                status_code=400,
                content={
                    "error": "Invalid settings",
                    "message": "webhook_url is required when Slack is enabled.",
                },
            )

        await db.commit()
        await db.refresh(settings)

        return JSONResponse(
            status_code=200,
            content={"message": "Slack settings updated", "slack_settings": settings.to_dict()},
        )
    except Exception as exc:
        logger.exception("Error updating Slack settings")
        app_settings = get_settings()
        return JSONResponse(
            status_code=500,
            content={
                "error": ERROR_INTERNAL_SERVER,
                "message": str(exc) if app_settings.expose_error_details else ERROR_INTERNAL_SERVER,
            },
        )

