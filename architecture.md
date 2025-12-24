# Backend Architecture — Cron Job Scheduler (FastAPI)

This document is meant to be a **rebuild-from-scratch reference**: if you have the requirements and this file, you should be able to recreate the project architecture, main modules, and runtime behavior.

## 1) System Overview

This repository is a **FastAPI-only** backend (Flask has been removed) that provides:

- A REST API (served under `GET/POST/... /api/v2/*`)
- Persistent storage via SQLAlchemy (default: SQLite; optional: MySQL)
- A background scheduler via APScheduler (leader-only; DB → scheduler reconciliation)
- Integrations:
  - GitHub Actions workflow dispatch (HTTP)
  - Generic webhook call (HTTP)
  - Slack incoming webhook (HTTP)
  - Email via SMTP (scheduler-safe; no web framework context required)

### 1.1 Runtime Topology (Mental Model)

```
Browser / Frontend / API Client
          |
          v
  FastAPI app (uvicorn)
    - auth / jobs / executions / notifications / settings / taxonomy
    - reads/writes DB via async SQLAlchemy
          |
          v
      Database
   (SQLite by default)

In the same process (optional/typical):
  APScheduler
    - leader-only via lock file
    - schedules per job row (id is job id)
    - executes job by HTTP calls (GitHub/workflow or webhook)
    - records executions + notifications
    - runs weekly end-date maintenance (JST)
```

### 1.2 Goals / Non-goals

**Goals**
- Provide a stable API for managing scheduled jobs and their executions.
- Ensure scheduled execution is **single-runner** even if the API is scaled horizontally.
- Make local development easy (SQLite; auto schema bootstrap; no Alembic required).

**Non-goals**
- Full database migration toolchain (no Alembic in this repo; SQLite uses a lightweight schema guard).
- Distributed job queue semantics (this is APScheduler + DB reconciliation, not Celery).

## 2) Codebase Layout (What Lives Where)

The code is intentionally split into a few layers:

- `src/fastapi_app/` — API layer + request validation + scheduler runtime wiring
- `src/models/` — SQLAlchemy declarative models (DB schema)
- `src/database/` — engine/session creation for sync+async usage
- `src/scheduler/` — APScheduler instance + lock + execution logic
- `src/services/` — background service logic (end-date reminders, etc.)
- `src/utils/` — cross-cutting utilities (SQLite schema guard, SMTP email, Slack helper)

Key entry points:
- API app: `src/fastapi_app/main.py` (`uvicorn src.fastapi_app.main:app`)
- Development start script: `start_fastapi.sh`
- DB init script: `scripts/init_fastapi_db.py`
- Create admin: `scripts/create_admin.py`

## 3) API Layer (FastAPI)

### 3.1 App Startup / Lifespan

`src/fastapi_app/main.py` is the canonical entrypoint.

Startup responsibilities:
- Load settings via `src/fastapi_app/config.py` (Pydantic settings from `.env` + environment)
- Initialize DB schema and seed baseline data via `src/database/bootstrap.py:init_db()`
- Start APScheduler lifecycle via `src/fastapi_app/scheduler_runtime.py:start_scheduler()`

Shutdown responsibilities:
- Stop scheduler via `src/fastapi_app/scheduler_runtime.py:stop_scheduler()`

### 3.2 Router Composition

Routers live under `src/fastapi_app/routers/` and are mounted by `register_routers(...)` in `src/fastapi_app/main.py`.

High-level groups:
- Auth: `src/fastapi_app/routers/auth.py` (`/api/v2/auth/*`)
- Jobs (read + write + bulk upload + execute): `src/fastapi_app/routers/jobs.py` (`/api/v2/jobs/*`)
- Executions: `src/fastapi_app/routers/executions.py` (`/api/v2/jobs/{id}/executions/*` + `/api/v2/executions/*`)
- Notifications: `src/fastapi_app/routers/notifications.py` (`/api/v2/notifications/*`)
- Taxonomy read: `src/fastapi_app/routers/taxonomy.py` (`/api/v2/job-categories`, `/api/v2/pic-teams`)
- Taxonomy write: `src/fastapi_app/routers/taxonomy_write.py` (admin-only writes)
- Slack settings: `src/fastapi_app/routers/settings.py`
- Scheduler ops: `src/fastapi_app/routers/scheduler.py` (`/api/v2/scheduler/status|resync`)

### 3.3 Error Handling

- Most routers return `JSONResponse` with a stable `{error, message}` shape on failures.
- `src/fastapi_app/main.py` also registers a global exception handler for unexpected errors.
- When `EXPOSE_ERROR_DETAILS=true`, errors may include exception strings for debugging.

## 4) Authentication & Authorization (JWT)

Auth is implemented with PyJWT and designed to be compatible with Flask-JWT-Extended token structure.

- Core helpers: `src/fastapi_app/dependencies/auth.py`
- Tokens:
  - Access token (`type=access`, default expiry `JWT_ACCESS_TOKEN_EXPIRES`, default 3600s)
  - Refresh token (`type=refresh`, default expiry `JWT_REFRESH_TOKEN_EXPIRES`, default 30d)
- Token payload includes `sub` (user id), `role`, `email`, `exp`, `iat`, `type`

Role model:
- `admin` — full access
- `user` — can manage own jobs (and trigger)
- `viewer` — read-only

Common dependencies:
- `CurrentUser` — any authenticated user (access token)
- `AdminUser` — admin-only
- `UserOrAdmin` — user or admin

## 5) Database Layer (SQLAlchemy)

### 5.1 Engines and Sessions

Files:
- Sync engine: `src/database/engine.py:get_engine()`
- Async engine: `src/database/engine.py:get_async_engine()`
- Sync sessions (scripts, scheduler execution writes): `src/database/session.py:get_db_session()`
- Async sessions (FastAPI request handlers): `src/database/session.py:get_db()` dependency

SQLite specifics:
- Sync engine uses `check_same_thread=False`
- Async engine uses `sqlite+aiosqlite:///...` and `NullPool` for test stability

### 5.2 Schema Bootstrap and Seed Data

`src/database/bootstrap.py:init_db()` is called on startup.

What it does:
- `Base.metadata.create_all()` (create missing tables)
- `src/utils/sqlite_schema.py:ensure_sqlite_schema()` (add safe missing columns without Alembic)
- If not `TESTING=true`:
  - seed default job categories
  - optionally create a default admin (controlled by `ALLOW_DEFAULT_ADMIN`)

### 5.3 Database Selection / Separation

Environment variables:
- `DATABASE_URL` — primary SQLAlchemy URL (sync)
- `FASTAPI_DATABASE_URL` — optional override used by async engine (defaults to `DATABASE_URL`)
- `TESTING=true` — switches FastAPI settings into test mode (isolated DB defaults)

Reference:
- `docs/database/DATABASE_SEPARATION.md`

### 5.4 Data Model (Tables & Relationships)

Authoritative model definitions live in `src/models/`.

Tables (current):
- `users`
- `jobs`
- `job_executions`
- `notifications`
- `job_categories`
- `pic_teams`
- `slack_settings`
- `user_notification_preferences`
- `user_ui_preferences`

MySQL baseline schema:
- `docs/database/DATABASE_SCHEMA_MYSQL.sql` (generated from models)

Important relationships:
- `jobs.created_by` → `users.id` (ownership)
- `job_executions.job_id` → `jobs.id` (cascade delete)
- `notifications.user_id` → `users.id` (cascade delete)
- `notifications.related_job_id` → `jobs.id` (set null)
- `notifications.related_execution_id` → `job_executions.id` (set null)

## 6) Scheduler Architecture (APScheduler)

### 6.1 Scheduler Instance and Locking

- APScheduler singleton: `src/scheduler/__init__.py` (imported as `src.scheduler.scheduler`)
- Leadership lock: `src/scheduler/lock.py:SchedulerLock`
- Runtime wiring: `src/fastapi_app/scheduler_runtime.py`

Key concept: **leader-only scheduling**
- Multiple API instances may run, but only one should execute scheduled jobs.
- `start_scheduler()` tries to acquire a lock file (`SCHEDULER_LOCK_PATH`).
  - If acquired → scheduler runs in that process.
  - If not acquired → process still serves APIs but does not schedule jobs.

Useful env vars:
- `SCHEDULER_ENABLED` (`true` unless explicitly `false`)
- `SCHEDULER_LOCK_PATH` (default `src/instance/scheduler.lock`)
- `SCHEDULER_LOCK_STALE_SECONDS` (optional stale lock recovery)
- `SCHEDULER_TIMEZONE` (default `Asia/Tokyo`)
- `SCHEDULER_POLL_SECONDS` (reconcile interval; clamped 10..300; default 60)

### 6.2 DB → Scheduler Reconciliation

Reconciler: `src/fastapi_app/scheduler_reconcile.py`

What it does:
- Reads all jobs from DB
- Auto-pauses expired jobs (end_date < today in scheduler TZ)
- Ensures active jobs are scheduled (id = job id; cron = `jobs.cron_expression`)
- Removes orphan scheduled jobs that do not exist in DB anymore

Ops endpoint:
- `POST /api/v2/scheduler/resync` (admin-only; leader-only)
- `GET /api/v2/scheduler/status` (admin-only)

### 6.3 Write-Side Scheduler Side Effects

Job CRUD endpoints try to keep the scheduler consistent immediately (best-effort):
- `src/fastapi_app/scheduler_side_effects.py:sync_job_schedule(...)`
- `src/fastapi_app/scheduler_side_effects.py:unschedule_job(...)`

Important behavior:
- These helpers **never fail** the API request if the scheduler is not leader/running.
- The periodic reconciler ensures eventual consistency.

## 7) Job Execution Flow

Execution logic: `src/scheduler/job_executor.py`

### 7.1 When an execution happens
- Scheduled run (APScheduler trigger) → `execute_job(..., trigger_type=\"scheduled\")`
- Manual trigger endpoint (`POST /api/v2/jobs/{id}/execute`) → same executor with `trigger_type=\"manual\"`

### 7.2 What happens during execution
1. Guard checks (job exists, active, not expired by end_date in scheduler TZ)
2. Create a `job_executions` row with `status=\"running\"`
3. Perform the action:
   - GitHub Actions workflow dispatch (if owner/repo/workflow are set)
   - Else webhook call (if `target_url` is set)
4. Mark execution as `success` or `failed` (store status code, output/error)
5. Create in-app notifications:
   - Job completed (success)
   - Job failed (failure)
   - Auto-paused due to end_date (warning)
6. Optionally send email notifications (SMTP) depending on job settings

## 8) Notifications & Settings

### 8.1 In-app Notifications

- Stored in table `notifications` (`src/models/notification.py`)
- Read/write APIs: `src/fastapi_app/routers/notifications.py`

Common notification types:
- `success`, `error`, `warning`, `info`

### 8.2 Slack Integration

- Global webhook + channel stored in `slack_settings` (admin-managed) via `src/fastapi_app/routers/settings.py`
- Each PIC team has an optional `slack_handle` for mention routing (`src/models/pic_team.py`)
- Weekly reminders + auto-pause messages can post to Slack:
  - Service: `src/services/end_date_maintenance.py`
  - HTTP helper: `src/utils/slack.py`

### 8.3 Email Integration (SMTP)

- Scheduler-safe SMTP helper: `src/utils/email.py`
- Controlled via env vars (examples):
  - `MAIL_ENABLED=true|false`
  - `MAIL_SERVER`, `MAIL_PORT`, `MAIL_USERNAME`, `MAIL_PASSWORD`, `MAIL_DEFAULT_SENDER`
  - or `SMTP_HOST`, `SMTP_PORT`, etc. (preferred aliases supported)

## 9) Local Development & Operations

### 9.1 Recommended dev start

- `./start_fastapi.sh` runs uvicorn with `--reload` and writes logs to `logs/fastapi.log` by default.

Log controls:
- `FASTAPI_LOG_FILE=/path/to/log` to override path
- `FASTAPI_LOG_TO_FILE=false` to disable file logging

### 9.2 Database initialization

For schema only:
- `./scripts/init_fastapi_db.py`

For schema + initial admin:
- `./scripts/initialize_db.sh`
  - wraps `python scripts/create_admin.py`

### 9.3 Running tests

- Tests live under `test/`
- `pytest` is configured via `pytest.ini` (asyncio mode auto; adds `src` to PYTHONPATH)
- Tests use an isolated DB via fixtures; they should never touch your real `src/instance/cron_jobs.db`

## 10) Rebuild Checklist (If You Were Recreating This Repo)

If you were recreating this project from scratch, implement in this order:

1. **Project bootstrapping**
   - Python `3.12`
   - `requirements.txt` (FastAPI + SQLAlchemy + APScheduler + auth + http clients)
2. **Data model**
   - Create `src/models/*` and `Base`
   - Add core tables: users/jobs/job_executions/notifications
   - Add taxonomy + prefs tables: job_categories/pic_teams/slack_settings/user_*_preferences
3. **Database primitives**
   - `src/database/engine.py` (sync/async engine selection by env)
   - `src/database/session.py` (sync context manager + async dependency)
   - `src/database/bootstrap.py` (create_all + seed + schema guard)
   - `src/utils/sqlite_schema.py` (safe column adds for SQLite)
4. **Authentication**
   - JWT encode/decode helpers; role enforcement dependencies
   - Auth router endpoints (`/login`, `/refresh`, `/me`, admin user mgmt)
5. **API domain routers**
   - Jobs CRUD + bulk upload + execute
   - Executions read endpoints
   - Notifications read/write endpoints
   - Taxonomy + Settings
6. **Scheduler**
   - APScheduler singleton + lock file
   - Scheduler runtime start/stop in FastAPI lifespan
   - Reconciler loop + admin ops endpoints
   - Side effects for CRUD (best-effort)
7. **Integrations**
   - GitHub dispatch + webhook execution (requests/httpx)
   - Slack helper
   - SMTP email helper
8. **Dev tooling**
   - `start_fastapi.sh` (reload + logs)
   - `scripts/init_fastapi_db.py`
   - tests under `test/` + `pytest.ini`

## 11) Reference Docs

- Migration history/runbook: `docs/migration/FASTAPI_MIGRATION_PLAN.md`
- Database separation: `docs/database/DATABASE_SEPARATION.md`
- MySQL baseline schema: `docs/database/DATABASE_SCHEMA_MYSQL.sql`
