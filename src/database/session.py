"""
SQLAlchemy Session Management.

Provides session factories for both Flask (sync) and FastAPI (async).
"""

from contextlib import contextmanager, asynccontextmanager
from typing import Generator, AsyncGenerator

from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from .engine import get_engine, get_async_engine


# Sync session factory (for Flask)
_sync_session_factory = None

# Async session factory (for FastAPI)
_async_session_factory = None


def get_sync_session_factory() -> sessionmaker:
    """Get or create sync session factory."""
    global _sync_session_factory
    if _sync_session_factory is None:
        _sync_session_factory = sessionmaker(
            bind=get_engine(),
            autocommit=False,
            autoflush=False,
            expire_on_commit=False
        )
    return _sync_session_factory


def get_async_session_factory() -> async_sessionmaker:
    """Get or create async session factory."""
    global _async_session_factory
    if _async_session_factory is None:
        _async_session_factory = async_sessionmaker(
            bind=get_async_engine(),
            class_=AsyncSession,
            autocommit=False,
            autoflush=False,
            expire_on_commit=False
        )
    return _async_session_factory


@contextmanager
def get_db_session() -> Generator[Session, None, None]:
    """
    Context manager for sync database sessions.
    
    Usage (Flask or scripts):
        with get_db_session() as session:
            users = session.query(User).all()
    
    Yields:
        SQLAlchemy Session
    """
    session = get_sync_session_factory()()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


@asynccontextmanager
async def get_async_db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Async context manager for async database sessions.
    
    Usage (FastAPI):
        async with get_async_db_session() as session:
            result = await session.execute(select(User))
            users = result.scalars().all()
    
    Yields:
        SQLAlchemy AsyncSession
    """
    session = get_async_session_factory()()
    try:
        yield session
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()


# FastAPI Dependency
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency for database sessions.
    
    Usage in FastAPI route:
        @app.get("/users")
        async def get_users(db: AsyncSession = Depends(get_db)):
            result = await db.execute(select(User))
            return result.scalars().all()
    
    Yields:
        SQLAlchemy AsyncSession
    """
    async with get_async_db_session() as session:
        yield session
