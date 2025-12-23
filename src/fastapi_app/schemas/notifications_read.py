"""
Notification Read Schemas (Phase 7A).

Response models for notification read endpoints, matching Flask response shapes.
"""

from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


class NotificationsRangePayload(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    from_: Optional[str] = Field(default=None, alias="from")
    to: Optional[str] = None


class NotificationReadPayload(BaseModel):
    id: str
    user_id: str
    title: str
    message: str
    type: str
    related_job_id: Optional[str] = None
    related_execution_id: Optional[str] = None
    is_read: bool
    read_at: Optional[str] = None
    created_at: str


class NotificationsReadResponse(BaseModel):
    notifications: List[NotificationReadPayload]
    total: int
    page: int
    per_page: int
    total_pages: int
    range: NotificationsRangePayload


class NotificationsUnreadCountResponse(BaseModel):
    unread_count: int
    range: NotificationsRangePayload

