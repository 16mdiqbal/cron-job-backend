"""
User Pydantic Schemas.

Request/response models for user-related API endpoints.
"""

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class UserRole(str, Enum):
    """User role enumeration."""
    ADMIN = "admin"
    USER = "user"
    VIEWER = "viewer"


# ============================================================================
# Request Schemas
# ============================================================================

class UserLogin(BaseModel):
    """Login request schema."""
    username: Optional[str] = Field(None, min_length=3, max_length=80, description="Username for login")
    email: Optional[EmailStr] = Field(None, description="Email for login")
    password: str = Field(..., min_length=6, description="User password")
    
    @field_validator('password')
    @classmethod
    def password_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError('Password cannot be empty')
        return v
    
    def model_post_init(self, __context) -> None:
        """Validate that either username or email is provided."""
        if not self.username and not self.email:
            raise ValueError('Either username or email must be provided')


class UserCreate(BaseModel):
    """User creation request schema."""
    username: str = Field(..., min_length=3, max_length=80, pattern=r'^[a-zA-Z0-9_-]+$')
    email: EmailStr
    password: str = Field(..., min_length=6)
    role: UserRole = Field(default=UserRole.VIEWER)
    is_active: bool = Field(default=True)
    
    @field_validator('username')
    @classmethod
    def username_alphanumeric(cls, v: str) -> str:
        if not v.replace('_', '').replace('-', '').isalnum():
            raise ValueError('Username must be alphanumeric with optional underscores or hyphens')
        return v.lower()


class UserUpdate(BaseModel):
    """User update request schema."""
    username: Optional[str] = Field(None, min_length=3, max_length=80)
    email: Optional[EmailStr] = None
    role: Optional[UserRole] = None
    is_active: Optional[bool] = None


class PasswordChange(BaseModel):
    """Password change request schema."""
    current_password: str = Field(..., min_length=1)
    new_password: str = Field(..., min_length=6)
    
    @field_validator('new_password')
    @classmethod
    def passwords_different(cls, v: str, info) -> str:
        current = info.data.get('current_password')
        if current and v == current:
            raise ValueError('New password must be different from current password')
        return v


class PasswordReset(BaseModel):
    """Password reset request schema (admin only)."""
    new_password: str = Field(..., min_length=6)


# ============================================================================
# Response Schemas
# ============================================================================

class UserResponse(BaseModel):
    """User response schema (excludes password)."""
    model_config = ConfigDict(from_attributes=True)
    
    id: str
    username: str
    email: str
    role: UserRole
    is_active: bool
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class UserListResponse(BaseModel):
    """Paginated user list response."""
    success: bool = True
    users: list[UserResponse]
    total: int
    page: int
    per_page: int
    pages: int


class TokenResponse(BaseModel):
    """JWT token response schema."""
    access_token: str
    refresh_token: Optional[str] = None
    token_type: str = "bearer"
    expires_in: int = Field(description="Token expiry in seconds")


class LoginResponse(BaseModel):
    """Login response with user info and tokens."""
    success: bool = True
    message: str = "Login successful"
    user: UserResponse
    access_token: str
    refresh_token: Optional[str] = None
    token_type: str = "bearer"


class UserCreateResponse(BaseModel):
    """User creation response."""
    success: bool = True
    message: str = "User created successfully"
    user: UserResponse
