"""
SQLAlchemy Engine Configuration.

Creates database engines that can be shared between Flask and FastAPI.
Supports both sync (Flask) and async (FastAPI) connections.
"""

import os
from functools import lru_cache
from typing import Optional

from sqlalchemy import create_engine, Engine
from sqlalchemy.ext.asyncio import create_async_engine, AsyncEngine
from sqlalchemy.pool import NullPool


def get_database_url(async_mode: bool = False) -> str:
    """
    Get database URL from environment or use default SQLite.
    
    Args:
        async_mode: If True, returns async-compatible URL
    
    Returns:
        Database connection URL
    """
    # For FastAPI (async), allow overriding via FASTAPI_DATABASE_URL.
    # Defaults to DATABASE_URL to keep Flask/FastAPI in sync unless explicitly separated.
    if async_mode:
        db_url = os.environ.get("FASTAPI_DATABASE_URL") or os.environ.get("DATABASE_URL", "")
    else:
        db_url = os.environ.get("DATABASE_URL", "")
    
    if not db_url:
        # Default to SQLite in instance folder
        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
        db_path = os.path.join(base_dir, 'instance', 'cron_jobs.db')
        db_url = f"sqlite:///{db_path}"
    
    # Convert to async URL if needed
    if async_mode:
        if db_url.startswith("sqlite:///"):
            return db_url.replace("sqlite:///", "sqlite+aiosqlite:///")
        elif db_url.startswith("mysql://"):
            return db_url.replace("mysql://", "mysql+aiomysql://")
        elif db_url.startswith("mysql+pymysql://"):
            return db_url.replace("mysql+pymysql://", "mysql+aiomysql://")
        elif db_url.startswith("postgresql://"):
            return db_url.replace("postgresql://", "postgresql+asyncpg://")
    
    return db_url


@lru_cache()
def get_engine() -> Engine:
    """
    Get or create synchronous SQLAlchemy engine.
    
    Used by Flask and for sync database operations.
    Cached for reuse across requests.
    
    Returns:
        SQLAlchemy Engine instance
    """
    db_url = get_database_url(async_mode=False)
    
    # SQLite-specific configuration
    if db_url.startswith("sqlite"):
        return create_engine(
            db_url,
            echo=os.environ.get('SQL_ECHO', 'false').lower() == 'true',
            connect_args={"check_same_thread": False}
        )
    
    # MySQL/PostgreSQL configuration
    return create_engine(
        db_url,
        echo=os.environ.get('SQL_ECHO', 'false').lower() == 'true',
        pool_size=5,
        max_overflow=10,
        pool_pre_ping=True,
        pool_recycle=3600
    )


@lru_cache()
def get_async_engine() -> AsyncEngine:
    """
    Get or create asynchronous SQLAlchemy engine.
    
    Used by FastAPI for async database operations.
    Cached for reuse across requests.
    
    Returns:
        SQLAlchemy AsyncEngine instance
    """
    db_url = get_database_url(async_mode=True)
    
    # SQLite-specific configuration
    if "sqlite" in db_url:
        return create_async_engine(
            db_url,
            echo=os.environ.get('SQL_ECHO', 'false').lower() == 'true',
            connect_args={"check_same_thread": False},
            poolclass=NullPool,
        )
    
    # MySQL/PostgreSQL configuration
    return create_async_engine(
        db_url,
        echo=os.environ.get('SQL_ECHO', 'false').lower() == 'true',
        pool_size=5,
        max_overflow=10,
        pool_pre_ping=True,
        pool_recycle=3600
    )
