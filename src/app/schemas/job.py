"""
Job Pydantic Schemas.

Request/response models for job-related API endpoints.
"""

from datetime import date, datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


# ============================================================================
# Request Schemas
# ============================================================================

class JobCreate(BaseModel):
    """Job creation request schema."""
    name: str = Field(..., min_length=1, max_length=255, description="Unique job name")
    cron_expression: str = Field(..., min_length=9, max_length=100, description="Cron expression (e.g., '0 9 * * *')")
    
    # Target configuration (one of these should be provided)
    target_url: Optional[str] = Field(None, max_length=500, description="Webhook URL for non-GitHub workflows")
    github_owner: Optional[str] = Field(None, max_length=255)
    github_repo: Optional[str] = Field(None, max_length=255)
    github_workflow_name: Optional[str] = Field(None, max_length=255)
    
    # Metadata
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)
    
    # Required fields
    category: str = Field(..., min_length=1, max_length=100)
    end_date: date = Field(..., description="Job expiration date")
    pic_team: str = Field(..., min_length=1, max_length=100, description="PIC team slug")
    
    # Email notifications
    enable_email_notifications: bool = Field(default=False)
    notification_emails: Optional[List[EmailStr]] = Field(default=None)
    notify_on_success: bool = Field(default=False)
    
    is_active: bool = Field(default=True)
    
    @field_validator('cron_expression')
    @classmethod
    def validate_cron(cls, v: str) -> str:
        """Basic cron expression validation."""
        parts = v.strip().split()
        if len(parts) != 5:
            raise ValueError('Cron expression must have exactly 5 fields (minute hour day month weekday)')
        return v.strip()
    
    @field_validator('end_date')
    @classmethod
    def validate_end_date(cls, v: date) -> date:
        """Ensure end_date is in the future."""
        if v < date.today():
            raise ValueError('end_date must be in the future')
        return v


class JobUpdate(BaseModel):
    """Job update request schema (all fields optional)."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    cron_expression: Optional[str] = Field(None, min_length=9, max_length=100)
    target_url: Optional[str] = Field(None, max_length=500)
    github_owner: Optional[str] = Field(None, max_length=255)
    github_repo: Optional[str] = Field(None, max_length=255)
    github_workflow_name: Optional[str] = Field(None, max_length=255)
    metadata: Optional[Dict[str, Any]] = None
    category: Optional[str] = Field(None, max_length=100)
    end_date: Optional[date] = None
    pic_team: Optional[str] = Field(None, max_length=100)
    enable_email_notifications: Optional[bool] = None
    notification_emails: Optional[List[EmailStr]] = None
    notify_on_success: Optional[bool] = None
    is_active: Optional[bool] = None
    
    @field_validator('cron_expression')
    @classmethod
    def validate_cron(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        parts = v.strip().split()
        if len(parts) != 5:
            raise ValueError('Cron expression must have exactly 5 fields')
        return v.strip()


class JobBulkUpload(BaseModel):
    """Bulk job upload request schema."""
    jobs: List[JobCreate] = Field(..., min_length=1, max_length=100)


class JobTrigger(BaseModel):
    """Manual job trigger request schema."""
    reason: Optional[str] = Field(None, max_length=500, description="Reason for manual trigger")


# ============================================================================
# Response Schemas
# ============================================================================

class JobResponse(BaseModel):
    """Job response schema."""
    model_config = ConfigDict(from_attributes=True)
    
    id: str
    name: str
    cron_expression: str
    target_url: Optional[str] = None
    github_owner: Optional[str] = None
    github_repo: Optional[str] = None
    github_workflow_name: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    category: str
    end_date: Optional[date] = None
    pic_team: Optional[str] = None
    enable_email_notifications: bool = False
    notification_emails: Optional[List[str]] = None
    notify_on_success: bool = False
    created_by: Optional[str] = None
    is_active: bool = True
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    # Computed fields (added during response)
    next_run_time: Optional[datetime] = None
    last_run_status: Optional[str] = None
    owner_username: Optional[str] = None


class JobListResponse(BaseModel):
    """Paginated job list response."""
    success: bool = True
    jobs: List[JobResponse]
    total: int
    page: int
    per_page: int
    pages: int


class JobCreateResponse(BaseModel):
    """Job creation response."""
    success: bool = True
    message: str = "Job created successfully"
    job: JobResponse


class JobTriggerResponse(BaseModel):
    """Manual job trigger response."""
    success: bool = True
    message: str = "Job triggered successfully"
    job_id: str
    execution_id: str


class JobBulkUploadResponse(BaseModel):
    """Bulk upload response."""
    success: bool = True
    message: str
    created_count: int
    failed_count: int
    errors: Optional[List[Dict[str, Any]]] = None


class JobStatsResponse(BaseModel):
    """Job statistics response."""
    total_jobs: int
    active_jobs: int
    inactive_jobs: int
    jobs_by_category: Dict[str, int]
    jobs_by_team: Dict[str, int]
    expiring_soon: int = Field(description="Jobs expiring within 7 days")
