"""
Common Pydantic Schemas.

Shared request/response models used across multiple endpoints.
"""

from datetime import datetime
from typing import Any, Dict, Generic, List, Optional, TypeVar

from pydantic import BaseModel, Field


# Generic type for paginated data
T = TypeVar("T")


# ============================================================================
# Error Responses
# ============================================================================

class ErrorDetail(BaseModel):
    """Detailed error information."""
    type: str = Field(description="Error type identifier")
    message: str = Field(description="Human-readable error message")
    field: Optional[str] = Field(None, description="Field name for validation errors")
    details: Optional[str] = Field(None, description="Additional error details")


class ErrorResponse(BaseModel):
    """Standard error response wrapper."""
    success: bool = False
    error: ErrorDetail


class ValidationErrorItem(BaseModel):
    """Single validation error."""
    loc: List[str] = Field(description="Error location path")
    msg: str = Field(description="Error message")
    type: str = Field(description="Error type")


class ValidationErrorResponse(BaseModel):
    """Validation error response (422)."""
    success: bool = False
    error: ErrorDetail
    validation_errors: List[ValidationErrorItem]


# ============================================================================
# Success Responses
# ============================================================================

class SuccessResponse(BaseModel):
    """Generic success response."""
    success: bool = True
    message: str = "Operation completed successfully"


class DeleteResponse(BaseModel):
    """Delete operation response."""
    success: bool = True
    message: str = "Resource deleted successfully"
    deleted_id: str


# ============================================================================
# Pagination
# ============================================================================

class PaginationParams(BaseModel):
    """Pagination query parameters."""
    page: int = Field(default=1, ge=1, description="Page number")
    per_page: int = Field(default=20, ge=1, le=100, description="Items per page")
    
    @property
    def offset(self) -> int:
        return (self.page - 1) * self.per_page


class PaginationMeta(BaseModel):
    """Pagination metadata in responses."""
    page: int
    per_page: int
    total: int
    pages: int
    has_next: bool
    has_prev: bool


class PaginatedResponse(BaseModel, Generic[T]):
    """Generic paginated response wrapper."""
    success: bool = True
    data: List[T]
    pagination: PaginationMeta


# ============================================================================
# Filtering & Sorting
# ============================================================================

class SortParams(BaseModel):
    """Sorting parameters."""
    sort_by: str = Field(default="created_at", description="Field to sort by")
    sort_order: str = Field(default="desc", pattern="^(asc|desc)$", description="Sort order")


class DateRangeFilter(BaseModel):
    """Date range filter parameters."""
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None


# ============================================================================
# Bulk Operations
# ============================================================================

class BulkDeleteRequest(BaseModel):
    """Bulk delete request."""
    ids: List[str] = Field(..., min_length=1, max_length=100)


class BulkOperationResult(BaseModel):
    """Result of a bulk operation."""
    success: bool = True
    message: str
    total_requested: int
    successful_count: int
    failed_count: int
    failed_ids: Optional[List[str]] = None
    errors: Optional[List[Dict[str, Any]]] = None


# ============================================================================
# Search
# ============================================================================

class SearchParams(BaseModel):
    """Search parameters."""
    q: Optional[str] = Field(None, min_length=1, max_length=100, description="Search query")
    fields: Optional[List[str]] = Field(None, description="Fields to search in")
