"""
Notifications Router (Phase 7A: Read Endpoints).

Implements:
- GET /api/v2/notifications
- GET /api/v2/notifications/unread-count
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
from ..schemas.notifications_read import (
    NotificationsRangePayload,
    NotificationsReadResponse,
    NotificationsUnreadCountResponse,
    NotificationMarkReadResponse,
    NotificationsReadAllResponse,
    NotificationDeleteResponse,
    NotificationsDeleteReadResponse,
    NotificationReadPayload,
)
from ...database.session import get_db
from ...models.notification import Notification

logger = logging.getLogger(__name__)

ERROR_INTERNAL_SERVER = "Internal server error"

router = APIRouter(responses={401: {"description": "Unauthorized"}, 500: {"description": "Internal server error"}})


def _parse_iso_date_or_datetime_utc_naive(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None

    raw = (value or "").strip()
    if not raw:
        return None

    try:
        if len(raw) == 10 and raw[4] == "-" and raw[7] == "-":
            parsed_date = date.fromisoformat(raw)
            return datetime.combine(parsed_date, time.min)
    except Exception:
        raise ValueError("Invalid date format. Use YYYY-MM-DD or ISO datetime.")

    normalized = raw.replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise ValueError("Invalid date format. Use YYYY-MM-DD or ISO datetime.") from exc

    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt


@router.get(
    "/notifications",
    response_model=NotificationsReadResponse,
    tags=["Notifications"],
    summary="List notifications (read-only)",
    description="Matches Flask `/api/notifications` response shape.",
)
async def list_notifications(
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1),
    unread_only: bool = Query(False),
    from_: Optional[str] = Query(None, alias="from"),
    to: Optional[str] = Query(None),
):
    try:
        per_page = min(per_page, 100)

        try:
            from_dt = _parse_iso_date_or_datetime_utc_naive(from_)
            to_dt = _parse_iso_date_or_datetime_utc_naive(to)
        except ValueError:
            return JSONResponse(status_code=400, content={"error": "Invalid date", "message": "Invalid date"})

        if to and to_dt and len(to.strip()) == 10:
            to_dt = to_dt + timedelta(days=1)

        if from_dt and to_dt and from_dt >= to_dt:
            return JSONResponse(
                status_code=400,
                content={"error": "Invalid date range", "message": '"from" must be earlier than "to".'},
            )

        conditions = [Notification.user_id == current_user.id]
        if unread_only:
            conditions.append(Notification.is_read.is_(False))
        if from_dt:
            conditions.append(Notification.created_at >= from_dt)
        if to_dt:
            conditions.append(Notification.created_at < to_dt)

        total_query = select(func.count()).select_from(Notification).where(*conditions)
        total = (await db.execute(total_query)).scalar_one() or 0

        offset = (page - 1) * per_page
        items_query = (
            select(Notification)
            .where(*conditions)
            .order_by(desc(Notification.created_at))
            .offset(offset)
            .limit(per_page)
        )
        rows = (await db.execute(items_query)).scalars().all()
        notifications = [NotificationReadPayload.model_validate(row.to_dict()) for row in rows]

        total_pages = (total + per_page - 1) // per_page if total else 0

        return NotificationsReadResponse(
            notifications=notifications,
            total=total,
            page=page,
            per_page=per_page,
            total_pages=total_pages,
            range=NotificationsRangePayload(
                from_=from_dt.isoformat() if from_dt else None,
                to=to_dt.isoformat() if to_dt else None,
            ),
        )
    except Exception as exc:
        logger.exception("Error listing notifications")
        settings = get_settings()
        return JSONResponse(
            status_code=500,
            content={
                "error": ERROR_INTERNAL_SERVER,
                "message": str(exc) if settings.expose_error_details else ERROR_INTERNAL_SERVER,
            },
        )


@router.get(
    "/notifications/unread-count",
    response_model=NotificationsUnreadCountResponse,
    tags=["Notifications"],
    summary="Get unread notification count",
    description="Matches Flask `/api/notifications/unread-count` response shape.",
)
async def get_unread_count(
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    from_: Optional[str] = Query(None, alias="from"),
    to: Optional[str] = Query(None),
):
    try:
        try:
            from_dt = _parse_iso_date_or_datetime_utc_naive(from_)
            to_dt = _parse_iso_date_or_datetime_utc_naive(to)
        except ValueError:
            return JSONResponse(status_code=400, content={"error": "Invalid date", "message": "Invalid date"})

        if to and to_dt and len(to.strip()) == 10:
            to_dt = to_dt + timedelta(days=1)

        if from_dt and to_dt and from_dt >= to_dt:
            return JSONResponse(
                status_code=400,
                content={"error": "Invalid date range", "message": '"from" must be earlier than "to".'},
            )

        conditions = [Notification.user_id == current_user.id, Notification.is_read.is_(False)]
        if from_dt:
            conditions.append(Notification.created_at >= from_dt)
        if to_dt:
            conditions.append(Notification.created_at < to_dt)

        count_query = select(func.count()).select_from(Notification).where(*conditions)
        unread_count = (await db.execute(count_query)).scalar_one() or 0

        return NotificationsUnreadCountResponse(
            unread_count=unread_count,
            range=NotificationsRangePayload(
                from_=from_dt.isoformat() if from_dt else None,
                to=to_dt.isoformat() if to_dt else None,
            ),
        )
    except Exception as exc:
        logger.exception("Error fetching unread notifications count")
        settings = get_settings()
        return JSONResponse(
            status_code=500,
            content={
                "error": ERROR_INTERNAL_SERVER,
                "message": str(exc) if settings.expose_error_details else ERROR_INTERNAL_SERVER,
            },
        )


@router.put(
    "/notifications/{notification_id}/read",
    response_model=NotificationMarkReadResponse,
    tags=["Notifications"],
    summary="Mark notification as read",
    description="Matches Flask `/api/notifications/<id>/read` response shape.",
)
async def mark_notification_read(
    notification_id: str,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    try:
        result = await db.execute(select(Notification).where(Notification.id == notification_id))
        notification = result.scalar_one_or_none()
        if not notification:
            return JSONResponse(status_code=404, content={"error": "Notification not found"})

        if notification.user_id != current_user.id:
            return JSONResponse(
                status_code=403,
                content={"error": "Forbidden: Cannot access other users notifications"},
            )

        if not notification.is_read:
            notification.is_read = True
            notification.read_at = datetime.utcnow()
            await db.commit()
            await db.refresh(notification)

        return NotificationMarkReadResponse(
            message="Notification marked as read",
            notification=NotificationReadPayload.model_validate(notification.to_dict()),
        )
    except Exception as exc:
        logger.exception("Error marking notification as read")
        settings = get_settings()
        return JSONResponse(
            status_code=500,
            content={
                "error": ERROR_INTERNAL_SERVER,
                "message": str(exc) if settings.expose_error_details else ERROR_INTERNAL_SERVER,
            },
        )


@router.put(
    "/notifications/read-all",
    response_model=NotificationsReadAllResponse,
    tags=["Notifications"],
    summary="Mark all notifications as read",
    description="Matches Flask `/api/notifications/read-all` response shape.",
)
async def mark_all_notifications_read(
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    try:
        now = datetime.utcnow()
        update_stmt = (
            Notification.__table__.update()
            .where(Notification.user_id == current_user.id)
            .where(Notification.is_read.is_(False))
            .values(is_read=True, read_at=now)
        )
        result = await db.execute(update_stmt)
        await db.commit()

        updated_count = int(result.rowcount or 0)
        return NotificationsReadAllResponse(message="All notifications marked as read", updated_count=updated_count)
    except Exception as exc:
        logger.exception("Error marking all notifications as read")
        settings = get_settings()
        return JSONResponse(
            status_code=500,
            content={
                "error": ERROR_INTERNAL_SERVER,
                "message": str(exc) if settings.expose_error_details else ERROR_INTERNAL_SERVER,
            },
        )


@router.delete(
    "/notifications/delete-read",
    response_model=NotificationsDeleteReadResponse,
    tags=["Notifications"],
    summary="Delete read notifications",
    description="Matches Flask `/api/notifications/delete-read` response shape.",
)
async def delete_read_notifications(
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    from_: Optional[str] = Query(None, alias="from"),
    to: Optional[str] = Query(None),
):
    try:
        try:
            from_dt = _parse_iso_date_or_datetime_utc_naive(from_)
            to_dt = _parse_iso_date_or_datetime_utc_naive(to)
        except ValueError:
            return JSONResponse(status_code=400, content={"error": "Invalid date", "message": "Invalid date"})

        if to and to_dt and len(to.strip()) == 10:
            to_dt = to_dt + timedelta(days=1)

        if from_dt and to_dt and from_dt >= to_dt:
            return JSONResponse(
                status_code=400,
                content={"error": "Invalid date range", "message": '"from" must be earlier than "to".'},
            )

        conditions = [Notification.user_id == current_user.id, Notification.is_read.is_(True)]
        if from_dt:
            conditions.append(Notification.created_at >= from_dt)
        if to_dt:
            conditions.append(Notification.created_at < to_dt)

        count_query = select(func.count()).select_from(Notification).where(*conditions)
        deleted_count = int((await db.execute(count_query)).scalar_one() or 0)

        if deleted_count:
            delete_stmt = Notification.__table__.delete().where(*conditions)
            await db.execute(delete_stmt)
            await db.commit()

        return NotificationsDeleteReadResponse(deleted_count=deleted_count)
    except Exception as exc:
        logger.exception("Error deleting read notifications")
        settings = get_settings()
        return JSONResponse(
            status_code=500,
            content={
                "error": ERROR_INTERNAL_SERVER,
                "message": str(exc) if settings.expose_error_details else ERROR_INTERNAL_SERVER,
            },
        )


@router.delete(
    "/notifications/{notification_id}",
    response_model=NotificationDeleteResponse,
    tags=["Notifications"],
    summary="Delete notification",
    description="Matches Flask `/api/notifications/<id>` response shape.",
)
async def delete_notification(
    notification_id: str,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    try:
        result = await db.execute(select(Notification).where(Notification.id == notification_id))
        notification = result.scalar_one_or_none()
        if not notification:
            return JSONResponse(status_code=404, content={"error": "Notification not found"})

        if notification.user_id != current_user.id:
            return JSONResponse(
                status_code=403,
                content={"error": "Forbidden: Cannot delete other users notifications"},
            )

        await db.delete(notification)
        await db.commit()
        return NotificationDeleteResponse(message="Notification deleted successfully")
    except Exception as exc:
        logger.exception("Error deleting notification")
        settings = get_settings()
        return JSONResponse(
            status_code=500,
            content={
                "error": ERROR_INTERNAL_SERVER,
                "message": str(exc) if settings.expose_error_details else ERROR_INTERNAL_SERVER,
            },
        )
