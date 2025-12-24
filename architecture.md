# Backend Architecture for Cron Job Scheduler (FastAPI)

## Overview
This backend is a **FastAPI** service that manages cron jobs stored in a database and runs schedules using **APScheduler**. Jobs can trigger either:
- a generic **Webhook URL**, or
- a **GitHub Actions workflow dispatch**.

The primary API surface is served under **`/api/v2/*`**.

## Key Components

### 1. FastAPI Application
- **Entry point:** `src/fastapi_app/main.py`
- **Routers:** `src/fastapi_app/routers/` (Auth, Jobs, Executions, Notifications, Taxonomy, Settings, Scheduler)
- **Docs:** `GET /docs` (Swagger UI), `GET /redoc`
- **Health:** `GET /api/v2/health`

### 2. Database Layer
- **Models:** `src/models/` (plain SQLAlchemy declarative models)
- **Engines:** `src/database/engine.py` (sync + async engines)
- **Sessions:** `src/database/session.py` (sync + async session factories)
- **Bootstrap:** `src/database/bootstrap.py` (creates tables + lightweight schema guard)

### 3. Scheduler Layer (APScheduler)
- **Scheduler instance:** `src/scheduler/__init__.py`
- **Execution logic:** `src/scheduler/job_executor.py`
- **FastAPI runtime:** `src/fastapi_app/scheduler_runtime.py`
  - leader-only start via lock file
  - periodic **DB → scheduler** reconciliation (`src/fastapi_app/scheduler_reconcile.py`)
  - internal weekly maintenance job `end_date_maintenance`

### 4. Services
- **End-date maintenance:** `src/services/end_date_maintenance.py`
  - auto-pause expired jobs
  - weekly reminders for jobs ending soon (in-app + optional Slack)

### 5. Notifications
- Stored in DB as `notifications` and surfaced via `src/fastapi_app/routers/notifications.py`.
- Scheduler/job execution publishes notifications (success/failure/auto-pause).

## API Groups (High Level)
- `POST /api/v2/auth/login`, `POST /api/v2/auth/refresh`, `GET /api/v2/auth/me`
- `GET/POST/PUT/DELETE /api/v2/jobs` (+ bulk upload + execute)
- `GET /api/v2/executions` (+ per-job and stats endpoints)
- `GET/PUT/DELETE /api/v2/notifications` (+ unread-count + read-all)
- `GET/POST/PUT/DELETE /api/v2/job-categories`
- `GET/POST/PUT/DELETE /api/v2/pic-teams`
- `GET/PUT /api/v2/settings/slack`
- `POST /api/v2/scheduler/resync` (admin only)

## Testing
- FastAPI tests live in `test/` and run against a per-test temporary SQLite DB.

