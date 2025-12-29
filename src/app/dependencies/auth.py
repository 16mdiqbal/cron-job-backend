"""
Authentication Dependencies.

Provides FastAPI dependency functions for:
- JWT token verification using PyJWT
- Current user extraction
- Role-based access control

Compatible with Flask-JWT-Extended tokens for cross-stack SSO.
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Annotated, Optional, Callable

import jwt
from jwt.exceptions import InvalidTokenError, ExpiredSignatureError
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials, OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import get_settings
from ...database.session import get_db
from ...models.user import User

logger = logging.getLogger(__name__)


# Security schemes for Swagger UI
http_bearer = HTTPBearer(
    scheme_name="JWT Bearer",
    description="Enter your JWT access token (without 'Bearer' prefix)",
    auto_error=True
)

http_bearer_optional = HTTPBearer(
    scheme_name="JWT Bearer (Optional)",
    description="Optional JWT access token",
    auto_error=False
)

# OAuth2 scheme (alternative, shows login button in Swagger)
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/api/v2/auth/login",
    auto_error=True
)

oauth2_scheme_optional = OAuth2PasswordBearer(
    tokenUrl="/api/v2/auth/login",
    auto_error=False
)


class TokenData:
    """Decoded JWT token data."""
    
    def __init__(
        self,
        user_id: str,
        role: str,
        email: Optional[str] = None,
        exp: Optional[datetime] = None,
        iat: Optional[datetime] = None,
        token_type: str = "access"
    ):
        self.user_id = user_id
        self.role = role
        self.email = email
        self.exp = exp
        self.iat = iat
        self.token_type = token_type


def _require_token_type(token_data: TokenData, allowed_types: set[str]) -> None:
    if token_data.token_type not in allowed_types:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type",
            headers={"WWW-Authenticate": "Bearer"},
        )


def create_access_token(
    user_id: str,
    role: str,
    email: Optional[str] = None,
    expires_delta: Optional[timedelta] = None
) -> str:
    """
    Create a new JWT access token.
    
    Compatible with Flask-JWT-Extended token format.
    
    Args:
        user_id: User's unique identifier
        role: User's role (admin, user, viewer)
        email: User's email address
        expires_delta: Custom expiration time
    
    Returns:
        Encoded JWT token string
    """
    settings = get_settings()
    
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(seconds=settings.jwt_access_token_expires)
    
    # Flask-JWT-Extended compatible payload structure
    payload = {
        "sub": user_id,           # Subject (user identity)
        "role": role,             # Custom claim
        "email": email,           # Custom claim
        "exp": expire,            # Expiration
        "iat": datetime.now(timezone.utc),  # Issued at
        "type": "access",         # Token type
        "fresh": True,            # Flask-JWT-Extended compatibility
    }
    
    token = jwt.encode(
        payload,
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm
    )
    
    return token


def create_refresh_token(
    user_id: str,
    role: str,
    email: Optional[str] = None,
    expires_delta: Optional[timedelta] = None
) -> str:
    """
    Create a new JWT refresh token.
    
    Args:
        user_id: User's unique identifier
        role: User's role
        email: User's email
        expires_delta: Custom expiration time
    
    Returns:
        Encoded JWT refresh token string
    """
    settings = get_settings()
    
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(seconds=settings.jwt_refresh_token_expires)
    
    payload = {
        "sub": user_id,
        "role": role,
        "email": email,
        "exp": expire,
        "iat": datetime.now(timezone.utc),
        "type": "refresh",
    }
    
    token = jwt.encode(
        payload,
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm
    )
    
    return token


def decode_token(token: str) -> TokenData:
    """
    Decode and verify a JWT token.
    
    Args:
        token: JWT token string
    
    Returns:
        TokenData with decoded claims
    
    Raises:
        HTTPException: 401 if token is invalid or expired
    """
    settings = get_settings()
    
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm]
        )
        
        user_id = payload.get("sub")
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token: missing subject",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        return TokenData(
            user_id=user_id,
            role=payload.get("role", "viewer"),
            email=payload.get("email"),
            exp=datetime.fromtimestamp(payload.get("exp", 0), tz=timezone.utc),
            iat=datetime.fromtimestamp(payload.get("iat", 0), tz=timezone.utc),
            token_type=payload.get("type", "access")
        )
        
    except ExpiredSignatureError:
        logger.warning("Token expired")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except InvalidTokenError as e:
        logger.warning(f"Invalid token: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(http_bearer)],
    db: Annotated[AsyncSession, Depends(get_db)]
) -> User:
    """
    Dependency to get the current authenticated user.
    
    Decodes JWT token and fetches user from database.
    
    Args:
        credentials: JWT bearer token from Authorization header
        db: Database session
    
    Returns:
        User: The authenticated user object
    
    Raises:
        HTTPException: 401 if token is invalid or user not found
    """
    token = credentials.credentials
    token_data = decode_token(token)
    _require_token_type(token_data, {"access"})
    
    # Fetch user from database
    result = await db.execute(
        select(User).where(User.id == token_data.user_id)
    )
    user = result.scalar_one_or_none()
    
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account is deactivated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return user


async def get_current_refresh_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(http_bearer)],
    db: Annotated[AsyncSession, Depends(get_db)]
) -> User:
    """
    Dependency to get the current user from a refresh token.
    """
    token = credentials.credentials
    token_data = decode_token(token)
    _require_token_type(token_data, {"refresh"})

    result = await db.execute(
        select(User).where(User.id == token_data.user_id)
    )
    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account is deactivated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user


async def get_current_active_user(
    current_user: Annotated[User, Depends(get_current_user)]
) -> User:
    """
    Dependency to get current user and verify they are active.
    
    Args:
        current_user: User from get_current_user dependency
    
    Returns:
        Active user
    
    Raises:
        HTTPException: 401 if user is inactive
    """
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account is deactivated"
        )
    return current_user


async def get_optional_user(
    credentials: Annotated[Optional[HTTPAuthorizationCredentials], Depends(http_bearer_optional)],
    db: Annotated[AsyncSession, Depends(get_db)]
) -> Optional[User]:
    """
    Dependency for optional authentication.
    
    Returns user if valid token provided, None otherwise.
    Does not raise exceptions for missing/invalid tokens.
    
    Args:
        credentials: Optional JWT bearer token
        db: Database session
    
    Returns:
        User or None
    """
    if credentials is None:
        return None
    
    try:
        token = credentials.credentials
        token_data = decode_token(token)
        _require_token_type(token_data, {"access"})
        
        result = await db.execute(
            select(User).where(User.id == token_data.user_id, User.is_active == True)
        )
        return result.scalar_one_or_none()
    except HTTPException:
        return None


def require_role(*allowed_roles: str) -> Callable:
    """
    Factory function to create role-checking dependencies.
    
    Usage:
        @app.get("/admin-only")
        async def admin_endpoint(user: User = Depends(require_role("admin"))):
            ...
        
        @app.get("/users-and-admins")
        async def user_endpoint(user: User = Depends(require_role("admin", "user"))):
            ...
    
    Args:
        allowed_roles: Role names that are permitted
    
    Returns:
        Dependency function that checks user role
    """
    async def role_checker(
        current_user: Annotated[User, Depends(get_current_user)]
    ) -> User:
        if current_user.role not in allowed_roles:
            logger.warning(
                f"Access denied for user {current_user.username} with role '{current_user.role}'. "
                f"Required: {allowed_roles}"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required role: {', '.join(allowed_roles)}"
            )
        return current_user
    
    return role_checker


# Pre-built role dependencies for convenience
async def require_admin(
    current_user: Annotated[User, Depends(get_current_user)]
) -> User:
    """Dependency that requires admin role."""
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return current_user


async def require_user_or_admin(
    current_user: Annotated[User, Depends(get_current_user)]
) -> User:
    """Dependency that requires user or admin role."""
    if current_user.role not in ("admin", "user"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User or admin access required"
        )
    return current_user


async def require_any_authenticated(
    current_user: Annotated[User, Depends(get_current_user)]
) -> User:
    """Dependency that requires any authenticated user (including viewer)."""
    return current_user


# Type aliases for cleaner route signatures
CurrentUser = Annotated[User, Depends(get_current_user)]
RefreshUser = Annotated[User, Depends(get_current_refresh_user)]
CurrentActiveUser = Annotated[User, Depends(get_current_active_user)]
OptionalUser = Annotated[Optional[User], Depends(get_optional_user)]
AdminUser = Annotated[User, Depends(require_admin)]
UserOrAdmin = Annotated[User, Depends(require_user_or_admin)]
