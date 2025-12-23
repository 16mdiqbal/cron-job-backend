"""
Database Package.

Provides shared database configuration for Flask and FastAPI.
"""

from .engine import get_engine, get_async_engine
from .session import get_db_session, get_async_db_session
