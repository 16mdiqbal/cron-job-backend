"""
Async Notification Utilities (Phase 7G).

Small helper functions for notification DB writes under FastAPI.
"""

from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from ...models.notification import Notification


async def create_notification(
    db: AsyncSession,
    *,
    user_id: str,
    title: str,
    message: str,
    type: str,
    related_job_id: Optional[str] = None,
    related_execution_id: Optional[str] = None,
) -> Notification:
    notification = Notification(
        user_id=user_id,
        title=title,
        message=message,
        type=type,
        related_job_id=related_job_id,
        related_execution_id=related_execution_id,
        is_read=False,
        read_at=None,
    )
    db.add(notification)
    await db.commit()
    await db.refresh(notification)
    return notification

