"""
Async Notification Utilities (Phase 7G).

Small helper functions for notification DB writes under FastAPI.
"""

from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ...models.notification import Notification
from ...models.user import User


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


async def broadcast_notification(
    db: AsyncSession,
    *,
    title: str,
    message: str,
    type: str,
    related_job_id: Optional[str] = None,
    related_execution_id: Optional[str] = None,
) -> int:
    """
    Create a notification for every user (legacy "broadcast" behavior).
    Returns the number of notifications inserted.
    """
    user_ids = (await db.execute(select(User.id))).scalars().all()
    for user_id in user_ids:
        db.add(
            Notification(
                user_id=user_id,
                title=title,
                message=message,
                type=type,
                related_job_id=related_job_id,
                related_execution_id=related_execution_id,
                is_read=False,
                read_at=None,
            )
        )
    await db.commit()
    return len(user_ids)


async def broadcast_job_success(
    db: AsyncSession, *, job_name: str, job_id: str, execution_id: str
) -> int:
    return await broadcast_notification(
        db,
        title="Job Completed",
        message=f'Job "{job_name}" completed successfully.',
        type="success",
        related_job_id=job_id,
        related_execution_id=execution_id,
    )


async def broadcast_job_failure(
    db: AsyncSession, *, job_name: str, job_id: str, execution_id: str, error_message: str
) -> int:
    return await broadcast_notification(
        db,
        title="Job Failed",
        message=f'Job "{job_name}" failed: {error_message}',
        type="error",
        related_job_id=job_id,
        related_execution_id=execution_id,
    )


async def broadcast_job_created(db: AsyncSession, *, job_name: str, job_id: str, created_by_name: str) -> int:
    return await broadcast_notification(
        db,
        title="New Job Created",
        message=f'Job "{job_name}" was created by {created_by_name}.',
        type="info",
        related_job_id=job_id,
    )


async def broadcast_job_updated(db: AsyncSession, *, job_name: str, job_id: str, updated_by_name: str) -> int:
    return await broadcast_notification(
        db,
        title="Job Updated",
        message=f'Job "{job_name}" was updated by {updated_by_name}.',
        type="info",
        related_job_id=job_id,
    )


async def broadcast_job_deleted(db: AsyncSession, *, job_name: str, deleted_by_name: str) -> int:
    return await broadcast_notification(
        db,
        title="Job Deleted",
        message=f'Job "{job_name}" was deleted by {deleted_by_name}.',
        type="warning",
    )


async def broadcast_job_enabled(db: AsyncSession, *, job_name: str, job_id: str, enabled_by_name: str) -> int:
    return await broadcast_notification(
        db,
        title="Job Enabled",
        message=f'Job "{job_name}" was enabled by {enabled_by_name}.',
        type="info",
        related_job_id=job_id,
    )


async def broadcast_job_disabled(db: AsyncSession, *, job_name: str, job_id: str, disabled_by_name: str) -> int:
    return await broadcast_notification(
        db,
        title="Job Disabled",
        message=f'Job "{job_name}" was disabled by {disabled_by_name}.',
        type="warning",
        related_job_id=job_id,
    )
