"""
Category Pydantic Schemas.

Request/response models for job category endpoints.
"""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


# ============================================================================
# Request Schemas
# ============================================================================

class CategoryCreate(BaseModel):
    """Category creation request schema."""
    slug: str = Field(
        ..., 
        min_length=1, 
        max_length=100, 
        pattern=r'^[a-z0-9_-]+$',
        description="URL-friendly unique identifier"
    )
    name: str = Field(..., min_length=1, max_length=255, description="Display name")
    is_active: bool = Field(default=True)
    
    @field_validator('slug')
    @classmethod
    def slug_lowercase(cls, v: str) -> str:
        return v.lower()


class CategoryUpdate(BaseModel):
    """Category update request schema."""
    slug: Optional[str] = Field(None, min_length=1, max_length=100, pattern=r'^[a-z0-9_-]+$')
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    is_active: Optional[bool] = None
    
    @field_validator('slug')
    @classmethod
    def slug_lowercase(cls, v: Optional[str]) -> Optional[str]:
        return v.lower() if v else v


# ============================================================================
# Response Schemas
# ============================================================================

class CategoryResponse(BaseModel):
    """Category response schema."""
    model_config = ConfigDict(from_attributes=True)
    
    id: str
    slug: str
    name: str
    is_active: bool
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    # Computed field
    job_count: Optional[int] = None


class CategoryListResponse(BaseModel):
    """Category list response."""
    success: bool = True
    categories: List[CategoryResponse]
    total: int


class CategoryCreateResponse(BaseModel):
    """Category creation response."""
    success: bool = True
    message: str = "Category created successfully"
    category: CategoryResponse
