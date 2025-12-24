"""
Database bootstrap utilities for FastAPI-only runtime.

Responsibilities:
- Create missing tables (SQLAlchemy metadata `create_all`)
- Apply minimal SQLite schema guards (add columns where safe)
- Seed required baseline data (categories, optional default admin)
"""

from __future__ import annotations

import logging
import os

from sqlalchemy import select

from .engine import get_engine
from .session import get_db_session
from ..models import Base, JobCategory, User
from ..utils.sqlite_schema import ensure_sqlite_schema

logger = logging.getLogger(__name__)


def init_db() -> None:
    """
    Idempotent DB init for local/dev deployments.

    For production, prefer proper migrations; this keeps dev/test environments safe and simple.
    """
    engine = get_engine()

    # Create missing tables first.
    Base.metadata.create_all(bind=engine)

    # SQLite guard for adding columns without migrations.
    ensure_sqlite_schema(engine)

    if _is_testing():
        return

    _seed_job_categories()
    _seed_default_admin()


def _is_testing() -> bool:
    return (os.getenv("TESTING") or "").lower() in ("true", "1", "yes")


def _seed_job_categories() -> None:
    seed = [
        ("general", "General"),
        ("regression", "Regression"),
        ("dr-testing", "DR Testing"),
        ("feature-testing", "Feature Testing"),
        ("prod-canary", "Prod/Canary"),
        ("refund", "Refund"),
        ("backward-compatibility", "Backward Compatibility"),
    ]

    with get_db_session() as session:
        existing = (session.execute(select(JobCategory.slug))).scalars().all()
        existing_slugs = {slug for slug in existing if slug}

        created = 0
        for slug, name in seed:
            if slug in existing_slugs:
                continue
            session.add(JobCategory(slug=slug, name=name, is_active=True))
            created += 1
        if created:
            logger.info("✅ Seeded %s default job categories", created)


def _seed_default_admin() -> None:
    """
    Dev-only convenience. Controlled via env:
      - ALLOW_DEFAULT_ADMIN=true|false
      - DEFAULT_ADMIN_USERNAME / DEFAULT_ADMIN_PASSWORD / DEFAULT_ADMIN_EMAIL
    """
    allow = os.getenv("ALLOW_DEFAULT_ADMIN")
    if allow is None:
        # Mirror the legacy default: enabled unless explicitly production.
        allow = "false" if os.getenv("FLASK_ENV", "development").lower() == "production" else "true"
    if allow.lower() in ("false", "0", "no"):
        return

    username = (os.getenv("DEFAULT_ADMIN_USERNAME") or "admin").strip() or "admin"
    password = os.getenv("DEFAULT_ADMIN_PASSWORD") or "admin123"
    email = (os.getenv("DEFAULT_ADMIN_EMAIL") or "admin@example.com").strip() or "admin@example.com"

    with get_db_session() as session:
        user = session.execute(select(User).where(User.username == username).limit(1)).scalar_one_or_none()
        if user:
            return
        admin = User(username=username, email=email, role="admin", is_active=True)
        admin.set_password(password)
        session.add(admin)
        logger.warning("✅ Default admin user created (dev): username=%s password=%s", username, password)
