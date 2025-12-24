"""
Team (PIC Team) Pydantic Schemas.

Request/response models for PIC team endpoints.
"""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


# ============================================================================
# Request Schemas
# ============================================================================

class TeamCreate(BaseModel):
    """Team creation request schema."""
    slug: str = Field(
        ..., 
        min_length=1, 
        max_length=100, 
        pattern=r'^[a-z0-9_-]+$',
        description="URL-friendly unique identifier"
    )
    name: str = Field(..., min_length=1, max_length=255, description="Display name")
    slack_handle: Optional[str] = Field(
        None, 
        max_length=255, 
        description="Slack handle for notifications (e.g., @qa-team)"
    )
    is_active: bool = Field(default=True)
    
    @field_validator('slug')
    @classmethod
    def slug_lowercase(cls, v: str) -> str:
        return v.lower()


class TeamUpdate(BaseModel):
    """Team update request schema."""
    slug: Optional[str] = Field(None, min_length=1, max_length=100, pattern=r'^[a-z0-9_-]+$')
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    slack_handle: Optional[str] = Field(None, max_length=255)
    is_active: Optional[bool] = None
    
    @field_validator('slug')
    @classmethod
    def slug_lowercase(cls, v: Optional[str]) -> Optional[str]:
        return v.lower() if v else v


# ============================================================================
# Response Schemas
# ============================================================================

class TeamResponse(BaseModel):
    """Team response schema."""
    model_config = ConfigDict(from_attributes=True)
    
    id: str
    slug: str
    name: str
    slack_handle: Optional[str] = None
    is_active: bool
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    # Computed field
    job_count: Optional[int] = None


class TeamListResponse(BaseModel):
    """Team list response."""
    success: bool = True
    teams: List[TeamResponse]
    total: int


class TeamCreateResponse(BaseModel):
    """Team creation response."""
    success: bool = True
    message: str = "Team created successfully"
    team: TeamResponse
