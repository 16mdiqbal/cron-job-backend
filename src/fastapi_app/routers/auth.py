"""
Authentication Router.

Provides endpoints for:
- User login (username or email)
- Token refresh
- Current user info
- User registration (admin only)

Compatible with Flask-JWT-Extended for cross-stack SSO.
"""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.responses import JSONResponse
from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession

from ..dependencies.auth import (
    create_access_token,
    create_refresh_token,
    decode_token,
    get_current_user,
    require_admin,
    http_bearer,
    CurrentUser,
    RefreshUser,
    AdminUser,
)
from ..schemas.user import (
    UserLogin,
    UserCreate,
    UserResponse,
    LoginResponse,
    TokenResponse,
    UserCreateResponse,
)
from ...database.session import get_db
from ...models.user import User

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/auth",
    tags=["Authentication"],
    responses={
        401: {"description": "Unauthorized - Invalid credentials or token"},
        403: {"description": "Forbidden - Insufficient permissions"},
        500: {"description": "Internal server error"},
    },
)


# ============================================================================
# Login Endpoints
# ============================================================================

@router.post(
    "/login",
    response_model=LoginResponse,
    summary="User login",
    description="""
    Authenticate user and receive JWT tokens.
    
    Supports login with either:
    - Username + Password
    - Email + Password
    
    Returns access token (1 hour) and refresh token (30 days).
    
    **Cross-Stack Compatibility**: Tokens are compatible with both Flask and FastAPI endpoints.
    """,
    responses={
        200: {"description": "Login successful", "model": LoginResponse},
        400: {"description": "Bad request - Missing credentials"},
        401: {"description": "Unauthorized - Invalid credentials or inactive account"},
    },
)
async def login(
    credentials: UserLogin,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Login with username or email.
    
    - **username**: Username for login (optional if email provided)
    - **email**: Email for login (optional if username provided)
    - **password**: User password (required)
    """
    # Determine login identifier
    login_identifier = credentials.username or credentials.email
    if not login_identifier:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username or email is required",
        )
    
    login_identifier = login_identifier.strip()
    
    # Find user by username OR email
    result = await db.execute(
        select(User).where(
            or_(
                User.username == login_identifier,
                User.email == login_identifier
            )
        )
    )
    user = result.scalar_one_or_none()
    
    if not user:
        logger.warning(f"Login attempt with non-existent username/email: {login_identifier}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email/username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Check if user is active
    if not user.is_active:
        logger.warning(f"Login attempt for inactive user: {user.username}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Account is inactive. Contact administrator.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Verify password
    if not user.check_password(credentials.password):
        logger.warning(f"Failed login attempt for user: {user.username}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email/username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Create tokens
    access_token = create_access_token(
        user_id=user.id,
        role=user.role,
        email=user.email,
    )
    
    refresh_token = create_refresh_token(
        user_id=user.id,
        role=user.role,
        email=user.email,
    )
    
    logger.info(f"User logged in successfully: {user.username}")
    
    return LoginResponse(
        success=True,
        message="Login successful",
        user=UserResponse.model_validate(user),
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
    )


@router.post(
    "/login/form",
    response_model=LoginResponse,
    summary="OAuth2 form login",
    description="""
    OAuth2 compatible login using form data.
    
    This endpoint is for Swagger UI's "Authorize" button.
    Uses standard OAuth2 password flow with username (can be email) and password.
    """,
    include_in_schema=True,
)
async def login_form(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    OAuth2 compatible login (for Swagger UI).
    
    - **username**: Username or email
    - **password**: User password
    """
    # Reuse the login logic with a UserLogin object
    credentials = UserLogin(username=form_data.username, password=form_data.password)
    return await login(credentials, db)


# ============================================================================
# Token Endpoints
# ============================================================================

@router.post(
    "/refresh",
    response_model=TokenResponse,
    summary="Refresh access token",
    description="""
    Get a new access token using a valid refresh token.
    
    Send the refresh token in the Authorization header.
    Returns a new access token with updated user claims.
    """,
    responses={
        200: {"description": "Token refreshed successfully", "model": TokenResponse},
        401: {"description": "Invalid or expired refresh token"},
    },
)
async def refresh_token(
    current_user: RefreshUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Refresh access token.
    
    Requires a valid refresh token in the Authorization header.
    """
    # Create new access token with current user data
    new_access_token = create_access_token(
        user_id=current_user.id,
        role=current_user.role,
        email=current_user.email,
    )
    
    logger.info(f"Token refreshed for user: {current_user.username}")
    
    return TokenResponse(
        access_token=new_access_token,
        token_type="bearer",
        expires_in=3600,  # 1 hour in seconds
    )


# ============================================================================
# User Info Endpoints
# ============================================================================

@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get current user",
    description="""
    Get the current authenticated user's profile information.
    
    Requires a valid access token in the Authorization header.
    """,
    responses={
        200: {"description": "Current user info", "model": UserResponse},
        401: {"description": "Unauthorized - Invalid or missing token"},
        404: {"description": "User not found"},
    },
)
async def get_me(current_user: CurrentUser):
    """
    Get current user info.
    
    Returns the authenticated user's profile data.
    """
    return UserResponse.model_validate(current_user)


# ============================================================================
# User Management Endpoints (Phase 6A)
# ============================================================================

@router.get(
    "/users",
    summary="List users",
    description="Admin-only. Matches Flask `/api/auth/users` response shape.",
    tags=["Users"],
)
async def list_users(
    _: AdminUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    result = await db.execute(select(User))
    users = result.scalars().all()
    return JSONResponse(status_code=200, content={"count": len(users), "users": [user.to_dict() for user in users]})


@router.get(
    "/users/{user_id}",
    summary="Get user",
    description="Admins can view any user; non-admins can only view themselves. Matches Flask `/api/auth/users/<id>` response shape.",
    tags=["Users"],
)
async def get_user(
    user_id: str,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    if current_user.role != "admin" and current_user.id != user_id:
        return JSONResponse(
            status_code=403,
            content={"error": "Forbidden. You can only view your own profile."},
        )

    result = await db.execute(select(User).where(User.id == user_id).limit(1))
    user = result.scalar_one_or_none()
    if not user:
        return JSONResponse(status_code=404, content={"error": "User not found"})

    return JSONResponse(status_code=200, content={"user": user.to_dict()})


# ============================================================================
# User Registration (Admin Only)
# ============================================================================

@router.post(
    "/register",
    response_model=UserCreateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register new user (Admin only)",
    description="""
    Register a new user account.
    
    **Admin access required.**
    
    Creates a new user with the specified credentials and role.
    Default role is 'viewer' if not specified.
    """,
    responses={
        201: {"description": "User created successfully", "model": UserCreateResponse},
        400: {"description": "Bad request - Validation errors"},
        403: {"description": "Forbidden - Admin access required"},
        409: {"description": "Conflict - Username or email already exists"},
    },
)
async def register_user(
    user_data: UserCreate,
    admin_user: AdminUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Register a new user (Admin only).
    
    - **username**: Unique username (3-80 chars, alphanumeric with _ -)
    - **email**: Unique email address
    - **password**: Password (min 6 chars)
    - **role**: User role (admin, user, viewer) - defaults to viewer
    - **is_active**: Account status - defaults to true
    """
    # Check if username already exists
    result = await db.execute(
        select(User).where(User.username == user_data.username.lower())
    )
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username already exists",
        )
    
    # Check if email already exists
    result = await db.execute(
        select(User).where(User.email == user_data.email.lower())
    )
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already exists",
        )
    
    # Create new user
    new_user = User(
        username=user_data.username.lower(),
        email=user_data.email.lower(),
        role=user_data.role.value,
        is_active=user_data.is_active,
    )
    new_user.set_password(user_data.password)
    
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    
    logger.info(f"New user registered by {admin_user.username}: {new_user.username} ({new_user.role})")
    
    return UserCreateResponse(
        success=True,
        message="User created successfully",
        user=UserResponse.model_validate(new_user),
    )


# ============================================================================
# Logout Endpoint (Optional - JWT is stateless)
# ============================================================================

@router.post(
    "/logout",
    summary="Logout",
    description="""
    Logout the current user.
    
    **Note**: JWT tokens are stateless, so this endpoint doesn't invalidate the token.
    The client should discard the token on logout.
    
    For server-side token invalidation, implement a token blacklist.
    """,
    responses={
        200: {"description": "Logout successful"},
    },
)
async def logout(current_user: CurrentUser):
    """
    Logout current user.
    
    Returns a success message. Client should discard tokens.
    """
    logger.info(f"User logged out: {current_user.username}")
    
    return {
        "success": True,
        "message": "Logout successful",
        "detail": "Please discard your tokens on the client side",
    }


# ============================================================================
# Token Verification Endpoint (For Testing/Debugging)
# ============================================================================

@router.get(
    "/verify",
    summary="Verify token",
    description="""
    Verify that the current access token is valid.
    
    Useful for testing token validity and debugging authentication issues.
    """,
    responses={
        200: {"description": "Token is valid"},
        401: {"description": "Token is invalid or expired"},
    },
)
async def verify_token(current_user: CurrentUser):
    """
    Verify access token validity.
    
    Returns token status and user info if valid.
    """
    return {
        "valid": True,
        "user_id": current_user.id,
        "username": current_user.username,
        "role": current_user.role,
        "message": "Token is valid",
    }
