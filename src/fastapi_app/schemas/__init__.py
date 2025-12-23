"""
Pydantic Schemas Package.

Contains Pydantic models for:
- Request validation
- Response serialization
- API documentation

Organized by domain:
- auth: Login, token, user schemas
- jobs: Job CRUD schemas
- notifications: Notification schemas
- common: Shared/base schemas
"""

# Common schemas
from .common import (
    ErrorDetail,
    ErrorResponse,
    ValidationErrorItem,
    ValidationErrorResponse,
    SuccessResponse,
    DeleteResponse,
    PaginationParams,
    PaginationMeta,
    PaginatedResponse,
    SortParams,
    DateRangeFilter,
    BulkDeleteRequest,
    BulkOperationResult,
    SearchParams,
)

# User schemas
from .user import (
    UserRole,
    UserLogin,
    UserCreate,
    UserUpdate,
    PasswordChange,
    PasswordReset,
    UserResponse,
    UserListResponse,
    TokenResponse,
    LoginResponse,
    UserCreateResponse,
)

# Job schemas
from .job import (
    JobCreate,
    JobUpdate,
    JobBulkUpload,
    JobTrigger,
    JobResponse,
    JobListResponse,
    JobCreateResponse,
    JobTriggerResponse,
    JobBulkUploadResponse,
    JobStatsResponse,
)

# Execution schemas
from .execution import (
    ExecutionStatus,
    TriggerType,
    ExecutionType,
    ExecutionResponse,
    ExecutionListResponse,
    ExecutionStats,
    ExecutionTimelineItem,
    ExecutionTimelineResponse,
    JobExecutionSummary,
    DashboardStats,
)

# Notification schemas
from .notification import (
    NotificationType,
    NotificationMarkRead,
    NotificationPreferencesUpdate,
    NotificationResponse,
    NotificationListResponse,
    NotificationPreferencesResponse,
    NotificationCountResponse,
    NotificationMarkReadResponse,
)

# Category schemas
from .category import (
    CategoryCreate,
    CategoryUpdate,
    CategoryResponse,
    CategoryListResponse,
    CategoryCreateResponse,
)

# Team schemas
from .team import (
    TeamCreate,
    TeamUpdate,
    TeamResponse,
    TeamListResponse,
    TeamCreateResponse,
)

# Settings schemas
from .settings import (
    SlackSettingsUpdate,
    SlackSettingsResponse,
    SlackTestRequest,
    SlackTestResponse,
    UiPreferencesUpdate,
    UiPreferencesResponse,
    AppSettingsResponse,
    HealthResponse,
)


__all__ = [
    # Common
    "ErrorDetail",
    "ErrorResponse",
    "ValidationErrorItem",
    "ValidationErrorResponse",
    "SuccessResponse",
    "DeleteResponse",
    "PaginationParams",
    "PaginationMeta",
    "PaginatedResponse",
    "SortParams",
    "DateRangeFilter",
    "BulkDeleteRequest",
    "BulkOperationResult",
    "SearchParams",
    # User
    "UserRole",
    "UserLogin",
    "UserCreate",
    "UserUpdate",
    "PasswordChange",
    "PasswordReset",
    "UserResponse",
    "UserListResponse",
    "TokenResponse",
    "LoginResponse",
    "UserCreateResponse",
    # Job
    "JobCreate",
    "JobUpdate",
    "JobBulkUpload",
    "JobTrigger",
    "JobResponse",
    "JobListResponse",
    "JobCreateResponse",
    "JobTriggerResponse",
    "JobBulkUploadResponse",
    "JobStatsResponse",
    # Execution
    "ExecutionStatus",
    "TriggerType",
    "ExecutionType",
    "ExecutionResponse",
    "ExecutionListResponse",
    "ExecutionStats",
    "ExecutionTimelineItem",
    "ExecutionTimelineResponse",
    "JobExecutionSummary",
    "DashboardStats",
    # Notification
    "NotificationType",
    "NotificationMarkRead",
    "NotificationPreferencesUpdate",
    "NotificationResponse",
    "NotificationListResponse",
    "NotificationPreferencesResponse",
    "NotificationCountResponse",
    "NotificationMarkReadResponse",
    # Category
    "CategoryCreate",
    "CategoryUpdate",
    "CategoryResponse",
    "CategoryListResponse",
    "CategoryCreateResponse",
    # Team
    "TeamCreate",
    "TeamUpdate",
    "TeamResponse",
    "TeamListResponse",
    "TeamCreateResponse",
    # Settings
    "SlackSettingsUpdate",
    "SlackSettingsResponse",
    "SlackTestRequest",
    "SlackTestResponse",
    "UiPreferencesUpdate",
    "UiPreferencesResponse",
    "AppSettingsResponse",
    "HealthResponse",
]
