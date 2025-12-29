"""
FastAPI Main Application Entry Point.

This module initializes the FastAPI application with:
- CORS middleware
- Health check endpoint
- API versioning (v2)
- Swagger/OpenAPI documentation
"""

import logging
import os
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from fastapi.responses import JSONResponse

from .config import get_settings
from .schemas import HealthResponse, ErrorResponse

logger = logging.getLogger(__name__)


# OpenAPI Tags for documentation organization
OPENAPI_TAGS = [
    {
        "name": "Health",
        "description": "Health check and status endpoints",
    },
    {
        "name": "Scheduler",
        "description": "Scheduler operational endpoints (admin only).",
    },
    {
        "name": "Authentication",
        "description": "User authentication and token management. Login, logout, token refresh.",
    },
    {
        "name": "Users",
        "description": "User management (Admin only). Create, update, delete users.",
    },
    {
        "name": "Jobs",
        "description": "Cron job management. Create, update, delete, and trigger scheduled jobs.",
    },
    {
        "name": "Executions",
        "description": "Job execution history and statistics.",
    },
    {
        "name": "Notifications",
        "description": "User notifications and preferences.",
    },
    {
        "name": "Categories",
        "description": "Job category management.",
    },
    {
        "name": "Teams",
        "description": "PIC team management for job ownership.",
    },
    {
        "name": "Settings",
        "description": "Application settings including Slack integration.",
    },
]


# Lifespan context manager for startup/shutdown events
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Manage application lifespan events.
    
    Startup:
        - Initialize database connections
        - Start scheduler (when migrated)
    
    Shutdown:
        - Close database connections
        - Stop scheduler gracefully
    """
    # Startup
    settings = get_settings()
    print(f"🚀 Starting {settings.app_name} v{settings.app_version}")
    print(f"📚 API Documentation available at: http://{settings.host}:{settings.port}/docs")
    print(f"📖 ReDoc available at: http://{settings.host}:{settings.port}/redoc")

    try:
        from sqlalchemy.engine.url import make_url

        from ..database.engine import get_database_url

        def _safe_db_ref(url: str) -> str:
            parsed = make_url(url)
            driver = parsed.drivername
            if driver.startswith("sqlite"):
                return parsed.database or "<memory>"
            host = parsed.host or ""
            port = f":{parsed.port}" if parsed.port else ""
            db = parsed.database or ""
            user = f"{parsed.username}@" if parsed.username else ""
            return f"{driver}://{user}{host}{port}/{db}"

        sync_url = get_database_url(async_mode=False)
        async_url = get_database_url(async_mode=True)
        print(f"🗄️  DB (sync):  {_safe_db_ref(sync_url)}")
        print(f"🗄️  DB (async): {_safe_db_ref(async_url)}")

        env_sync = (os.getenv("DATABASE_URL") or "").strip()
        env_async = (os.getenv("FASTAPI_DATABASE_URL") or "").strip()
        if env_sync and env_async and env_sync != env_async:
            logger.warning(
                "DATABASE_URL and FASTAPI_DATABASE_URL differ. This can make executions appear to 'disappear' "
                "(scheduler writes to one DB while the API reads from another)."
            )
        if settings.testing:
            logger.warning("TESTING=true: FastAPI may use an isolated DB (fastapi_test.db).")
    except Exception:
        pass

    # Ensure DB schema + baseline seed data exists before scheduler starts.
    from ..database.bootstrap import init_db

    init_db()

    # Phase 8C: Scheduler lifecycle under FastAPI lifespan (leader-only via lock).
    from .scheduler_runtime import start_scheduler
    start_scheduler()
    
    yield  # Application runs here
    
    # Shutdown
    from .scheduler_runtime import stop_scheduler
    stop_scheduler()
    print("👋 Shutting down FastAPI application...")


def create_app() -> FastAPI:
    """
    FastAPI application factory.
    
    Returns:
        FastAPI: Configured FastAPI application instance
    """
    settings = get_settings()
    
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description="""
## Cron Job Scheduler API v2

A FastAPI-based REST API for managing scheduled cron jobs with:
- 🔐 **JWT Authentication** - Secure token-based authentication
- 👥 **Role-based Access Control** - Admin, User, and Viewer roles
- ⏰ **APScheduler Integration** - Reliable cron job scheduling
- 🔔 **Email & Slack Notifications** - Get notified on job status
- 📊 **Execution History** - Track all job executions
- 🔄 **GitHub Actions Integration** - Trigger GitHub workflows

### API Endpoints

| Category | Endpoints | Description |
|----------|-----------|-------------|
| Auth | `/api/v2/auth/*` | Login, logout, token refresh |
| Jobs | `/api/v2/jobs/*` | CRUD operations for cron jobs |
| Executions | `/api/v2/executions/*` | Execution history and stats |
| Notifications | `/api/v2/notifications/*` | User notifications |
| Users | `/api/v2/users/*` | User management (Admin) |
| Categories | `/api/v2/categories/*` | Job categories |
| Teams | `/api/v2/teams/*` | PIC team management |
| Settings | `/api/v2/settings/*` | App settings |

### Authentication

All protected endpoints require a JWT token in the Authorization header:
```
Authorization: Bearer <your_jwt_token>
```

### Status
✅ FastAPI is the only backend (Flask removed).
        """,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/api/v2/openapi.json",
        openapi_tags=OPENAPI_TAGS,
        lifespan=lifespan,
        license_info={
            "name": "MIT License",
            "url": "https://opensource.org/licenses/MIT",
        },
        contact={
            "name": "QA Automation Team",
            "email": "qa-automation@paypay.ne.jp",
        },
    )
    
    # Configure CORS
    allow_origins = settings.cors_origins_list
    # If allow_origins is wildcard, credentials must be disabled to avoid invalid CORS responses.
    allow_credentials = False if allow_origins == ["*"] else True
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allow_origins,
        allow_credentials=allow_credentials,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Register exception handlers
    register_exception_handlers(app)
    
    # Register routers
    register_routers(app)
    
    return app


def register_exception_handlers(app: FastAPI) -> None:
    """Register global exception handlers."""
    
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        """Handle unexpected exceptions."""
        settings = get_settings()
        
        error_response = {
            "success": False,
            "error": {
                "type": "internal_error",
                "message": "An unexpected error occurred"
            }
        }
        
        if settings.expose_error_details:
            error_response["error"]["details"] = str(exc)
        
        return JSONResponse(
            status_code=500,
            content=error_response
        )


def register_routers(app: FastAPI) -> None:
    """
    Register all API routers.
    
    Routers are organized by domain:
    - /api/v2/health - Health check
    - /api/v2/auth - Authentication (to be migrated)
    - /api/v2/jobs - Job management (to be migrated)
    - /api/v2/notifications - Notifications (to be migrated)
    """
    # Health endpoint using Pydantic response model
    @app.get(
        "/api/v2/health",
        tags=["Health"],
        summary="Health Check",
        description="Check if the API is running and responsive. Returns service info and timestamp.",
        response_model=HealthResponse,
        responses={
            200: {
                "description": "API is healthy",
                "model": HealthResponse,
            },
            500: {
                "description": "Internal server error",
                "model": ErrorResponse,
            }
        }
    )
    async def health_check() -> HealthResponse:
        """
        Health check endpoint.
        
        Returns service status, version, and timestamp.
        Use this endpoint for monitoring and load balancer health checks.
        """
        settings = get_settings()
        from .scheduler_runtime import get_status

        sched = get_status()
        return HealthResponse(
            status="healthy",
            service="cron-job-scheduler-fastapi",
            version=settings.app_version,
            timestamp=datetime.now(timezone.utc),
            api="v2",
            scheduler_running=sched.running,
            scheduled_jobs_count=sched.scheduled_jobs_count,
            docs_url=f"http://localhost:{settings.port}/docs"
        )
    
    # Root redirect to docs
    @app.get(
        "/",
        include_in_schema=False
    )
    async def root():
        """Redirect root to API documentation."""
        return JSONResponse(
            content={
                "message": "Welcome to Cron Job Scheduler API v2",
                "docs": "/docs",
                "redoc": "/redoc",
                "health": "/api/v2/health"
            }
        )
    
    # Import and register routers
    from .routers import (
        auth_router,
        jobs_router,
        executions_router,
        taxonomy_router,
        taxonomy_write_router,
        notifications_router,
        settings_router,
        scheduler_router,
    )
    app.include_router(auth_router, prefix="/api/v2")
    app.include_router(jobs_router, prefix="/api/v2")
    app.include_router(executions_router, prefix="/api/v2")
    app.include_router(taxonomy_router, prefix="/api/v2")
    app.include_router(taxonomy_write_router, prefix="/api/v2")
    app.include_router(notifications_router, prefix="/api/v2")
    app.include_router(settings_router, prefix="/api/v2")
    app.include_router(scheduler_router, prefix="/api/v2")


# Create the application instance
app = create_app()
