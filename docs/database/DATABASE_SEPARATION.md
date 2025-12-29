# Database Configuration (FastAPI)

## Overview
This backend is **FastAPI-only** and uses SQLAlchemy with a SQLite default. You can override the database using environment variables.

## Environment Variables
- `DATABASE_URL`: Base SQLAlchemy URL used for sync operations/scripts (default: `sqlite:///.../src/instance/cron_jobs.db`)
- `FASTAPI_DATABASE_URL`: Optional override for FastAPI async operations (defaults to `DATABASE_URL`)
- `TESTING=true`: Enables test mode (used by the FastAPI settings layer)

Notes:
- For SQLite, the async engine uses `sqlite+aiosqlite:///...` internally.
- In `test/`, tests use a **per-test temporary SQLite DB** via fixtures (no shared `cron_jobs.db` access).

## Initializing the DB
To create tables (and run the lightweight SQLite schema guard), run:

```bash
./scripts/init_fastapi_db.py
```

Or specify a custom DB URL:

```bash
./scripts/init_fastapi_db.py --database-url sqlite:////tmp/cron_jobs.db
```

## Local Defaults
- Default DB path: `src/instance/cron_jobs.db`
- Scheduler lock path: `src/instance/scheduler.lock`

