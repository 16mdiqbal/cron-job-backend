"""
Notification Pydantic Schemas.

Request/response models for notification-related endpoints.
"""

from datetime import datetime
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


class NotificationType(str, Enum):
    """Notification type enumeration."""
    SUCCESS = "success"
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


# ============================================================================
# Request Schemas
# ============================================================================

class NotificationMarkRead(BaseModel):
    """Mark notification(s) as read request."""
    notification_ids: Optional[List[str]] = Field(
        None, 
        description="Specific notification IDs to mark. If null, marks all as read."
    )


class NotificationPreferencesUpdate(BaseModel):
    """Update notification preferences request."""
    email_on_job_success: Optional[bool] = None
    email_on_job_failure: Optional[bool] = None
    email_on_job_disabled: Optional[bool] = None
    browser_notifications: Optional[bool] = None
    daily_digest: Optional[bool] = None
    weekly_report: Optional[bool] = None


# ============================================================================
# Response Schemas
# ============================================================================

class NotificationResponse(BaseModel):
    """Notification response schema."""
    model_config = ConfigDict(from_attributes=True)
    
    id: str
    user_id: str
    title: str
    message: str
    type: NotificationType
    related_job_id: Optional[str] = None
    related_execution_id: Optional[str] = None
    is_read: bool
    read_at: Optional[datetime] = None
    created_at: datetime
    
    # Joined fields
    job_name: Optional[str] = None


class NotificationListResponse(BaseModel):
    """Paginated notification list response."""
    success: bool = True
    notifications: List[NotificationResponse]
    total: int
    unread_count: int
    page: int
    per_page: int
    pages: int


class NotificationPreferencesResponse(BaseModel):
    """Notification preferences response."""
    model_config = ConfigDict(from_attributes=True)
    
    id: str
    user_id: str
    email_on_job_success: bool = True
    email_on_job_failure: bool = True
    email_on_job_disabled: bool = False
    browser_notifications: bool = True
    daily_digest: bool = False
    weekly_report: bool = True
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class NotificationCountResponse(BaseModel):
    """Notification count response."""
    success: bool = True
    total: int
    unread: int


class NotificationMarkReadResponse(BaseModel):
    """Response after marking notifications as read."""
    success: bool = True
    message: str = "Notifications marked as read"
    marked_count: int
