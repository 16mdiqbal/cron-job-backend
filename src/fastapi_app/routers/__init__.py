"""
FastAPI Routers Package.

Contains API route handlers organized by domain:
- auth: Authentication endpoints
- jobs: Job management endpoints
- notifications: Notification endpoints
- users: User management endpoints
- categories: Category endpoints
- teams: PIC team endpoints

Routers are migrated incrementally from Flask.
"""

from .auth import router as auth_router
from .jobs import router as jobs_router
from .executions import router as executions_router
from .taxonomy import router as taxonomy_router
from .notifications import router as notifications_router
from .settings import router as settings_router

__all__ = [
    "auth_router",
    "jobs_router",
    "executions_router",
    "taxonomy_router",
    "notifications_router",
    "settings_router",
]
