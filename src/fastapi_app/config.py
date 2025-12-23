"""
FastAPI Configuration using Pydantic Settings.

Shares the same environment variables as Flask for consistency during migration.
"""

import os
from functools import lru_cache
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.
    
    All settings are shared with Flask to ensure consistency during migration.
    """
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )
    
    # Application
    app_name: str = "Cron Job Scheduler API"
    app_version: str = "2.0.0"
    debug: bool = False
    
    # Server
    host: str = "0.0.0.0"
    port: int = 8001
    
    # Security
    secret_key: str = "dev-secret-key-please-change-in-production"
    jwt_secret_key: str = ""
    jwt_algorithm: str = "HS256"
    jwt_access_token_expires: int = 3600  # 1 hour
    jwt_refresh_token_expires: int = 2592000  # 30 days
    
    # Database
    database_url: str = ""
    fastapi_database_url: str = ""  # Separate DB for FastAPI during migration
    testing: bool = False
    
    def model_post_init(self, __context):
        """Post-initialization hook to check environment variables."""
        # Check for testing mode from environment
        if os.getenv('TESTING', '').lower() in ('true', '1', 'yes'):
            self.testing = True
    
    # CORS
    cors_origins: str = "*"
    
    # Scheduler
    scheduler_timezone: str = "Asia/Tokyo"
    
    # GitHub
    github_token: str = ""
    default_github_owner: str = "Pay-Baymax"
    
    # Frontend
    frontend_base_url: str = "http://localhost:5173"
    
    # Email
    mail_server: str = "smtp.gmail.com"
    mail_port: int = 587
    mail_use_tls: bool = True
    mail_username: str = ""
    mail_password: str = ""
    mail_default_sender: str = "noreply@cronjobscheduler.local"
    mail_enabled: bool = True
    
    # Error handling
    expose_error_details: bool = True
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Use secret_key as fallback for jwt_secret_key
        if not self.jwt_secret_key:
            self.jwt_secret_key = self.secret_key
        
        # Build database URLs if not provided
        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
        
        # Flask database (legacy)
        if not self.database_url:
            db_path = os.path.join(base_dir, 'src', 'instance', 'cron_jobs.db')
            self.database_url = f"sqlite:///{db_path}"
        
        # FastAPI database
        #
        # Default behavior:
        # - Non-testing: share the same database as Flask to keep auth/users in sync.
        # - Testing: default to an isolated database to avoid interference from Flask scheduler/tests.
        #
        # To explicitly separate FastAPI from Flask in any environment, set FASTAPI_DATABASE_URL.
        if not self.fastapi_database_url:
            if self.testing:
                # Use separate test database for FastAPI to avoid Flask scheduler interference
                test_db_path = os.path.join(base_dir, "src", "instance", "fastapi_test.db")
                self.fastapi_database_url = f"sqlite:///{test_db_path}"
            else:
                self.fastapi_database_url = self.database_url

        # Export resolved URLs for lower-level shared database utilities.
        # These are treated as defaults; callers can still override via env.
        os.environ.setdefault("DATABASE_URL", self.database_url)
        os.environ.setdefault("FASTAPI_DATABASE_URL", self.fastapi_database_url)
    
    @property
    def cors_origins_list(self) -> List[str]:
        """Parse CORS origins from comma-separated string."""
        if self.cors_origins == "*":
            return ["*"]
        return [origin.strip() for origin in self.cors_origins.split(",")]
    
    @property
    def async_database_url(self) -> str:
        """Convert FastAPI database URL to async version."""
        db_url = self.fastapi_database_url if self.fastapi_database_url else self.database_url
        if db_url.startswith("sqlite:///"):
            return db_url.replace("sqlite:///", "sqlite+aiosqlite:///")
        return db_url


@lru_cache()
def get_settings() -> Settings:
    """
    Get cached settings instance.
    
    Uses lru_cache to ensure settings are only loaded once.
    """
    return Settings()
