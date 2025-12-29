import logging
from sqlalchemy import text
from sqlalchemy.engine import Engine

logger = logging.getLogger(__name__)


def _get_sqlite_columns(conn, table_name: str) -> set[str]:
    rows = conn.execute(text(f"PRAGMA table_info('{table_name}')")).fetchall()
    # PRAGMA table_info columns: cid, name, type, notnull, dflt_value, pk
    return {r[1] for r in rows}


def ensure_sqlite_schema(engine: Engine) -> None:
    """
    Lightweight SQLite schema guard for when Alembic migrations are not used.

    - Creates new tables via SQLAlchemy `create_all()` (handled elsewhere)
    - Adds missing columns via `ALTER TABLE ... ADD COLUMN ...` where safe

    Keep this minimal and backwards-compatible: do NOT add NOT NULL constraints here.
    Enforce "required" fields at the API layer.
    """
    try:
        if engine.url.get_backend_name() != 'sqlite':
            return

        with engine.begin() as conn:
            existing = _get_sqlite_columns(conn, 'jobs')

            # Job End Date (date-only, compared in JST at runtime)
            if 'end_date' not in existing:
                conn.execute(text('ALTER TABLE jobs ADD COLUMN end_date DATE'))
                logger.info("✅ SQLite migration: added jobs.end_date")

            # PIC Team slug (string identifier; validated against pic_teams.slug)
            if 'pic_team' not in existing:
                conn.execute(text('ALTER TABLE jobs ADD COLUMN pic_team VARCHAR(100)'))
                logger.info("✅ SQLite migration: added jobs.pic_team")

            # Pic teams table evolves too (admin-managed; created via create_all)
            try:
                pic_team_cols = _get_sqlite_columns(conn, 'pic_teams')
                if 'slack_handle' not in pic_team_cols:
                    conn.execute(text('ALTER TABLE pic_teams ADD COLUMN slack_handle VARCHAR(255)'))
                    logger.info("✅ SQLite migration: added pic_teams.slack_handle")
            except Exception:
                # Table may not exist yet in a fresh DB before create_all, or could be absent in tests.
                pass

    except Exception as e:
        logger.warning(f"SQLite schema ensure skipped/failed: {e}")
