"""
Settings Pydantic Schemas.

Request/response models for application settings endpoints.
Includes Slack settings and UI preferences.
"""

from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel, ConfigDict, Field, HttpUrl


# ============================================================================
# Slack Settings
# ============================================================================

class SlackSettingsUpdate(BaseModel):
    """Slack settings update request schema."""
    is_enabled: Optional[bool] = None
    webhook_url: Optional[str] = Field(None, description="Slack webhook URL")
    channel: Optional[str] = Field(None, max_length=255, description="Default Slack channel")


class SlackSettingsResponse(BaseModel):
    """Slack settings response schema."""
    model_config = ConfigDict(from_attributes=True)
    
    id: str
    is_enabled: bool
    webhook_url: Optional[str] = None
    channel: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class SlackTestRequest(BaseModel):
    """Slack test message request."""
    message: Optional[str] = Field(
        default="Test notification from Cron Job Scheduler",
        max_length=1000
    )


class SlackTestResponse(BaseModel):
    """Slack test message response."""
    success: bool
    message: str


# ============================================================================
# UI Preferences
# ============================================================================

class UiPreferencesUpdate(BaseModel):
    """UI preferences update request schema."""
    jobs_table_columns: Optional[Dict[str, Any]] = Field(
        None,
        description="Column visibility/order configuration for jobs table"
    )


class UiPreferencesResponse(BaseModel):
    """UI preferences response schema."""
    model_config = ConfigDict(from_attributes=True)
    
    id: str
    user_id: str
    jobs_table_columns: Optional[Dict[str, Any]] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


# ============================================================================
# App Settings / Health
# ============================================================================

class AppSettingsResponse(BaseModel):
    """Application settings response (non-sensitive)."""
    scheduler_timezone: str
    default_github_owner: str
    mail_enabled: bool
    slack_enabled: bool
    frontend_base_url: str


class HealthResponse(BaseModel):
    """Health check response."""
    status: str = "healthy"
    service: str
    version: str
    timestamp: datetime
    api: str = "v2"
    scheduler_running: bool = False
    scheduled_jobs_count: int = 0
    docs_url: Optional[str] = None
