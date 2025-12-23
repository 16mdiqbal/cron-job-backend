"""
Database Dependencies.

Provides FastAPI dependency functions for:
- Database session management
- Async database connections
"""

from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession

from ...database.session import get_db as _get_db


# Re-export the database dependency
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
    async for session in _get_db():
        yield session
