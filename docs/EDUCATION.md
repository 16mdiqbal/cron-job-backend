# Project Education Guide (Backend)

This document is a “learn the system” guide for developers and operators working on the **Cron Job Scheduler Backend** (FastAPI + APScheduler).

For setup and commands, start with `README.md`. For deeper architecture, see `architecture.md`.

---

## 1) Mental model (what this system does)

This backend provides:

- **CRUD APIs** for cron jobs (create/update/delete/enable/disable).
- **Two execution modes**:
  - **Webhook**: call a target URL.
  - **GitHub Actions**: trigger a workflow dispatch.
- **A scheduler runtime** (APScheduler) that runs jobs on schedule.
- **Execution history** stored as `job_executions` rows.
- **Notifications** (in-app + optional Slack/email hooks).

In practice:

1. Admin/users create jobs in the DB via `/api/v2/jobs/*`.
2. The scheduler process periodically reconciles DB → APScheduler.
3. At runtime, APScheduler triggers the executor which:
   - Creates a `job_executions` record (running → success/failed).
   - Emits notifications (success/failure/updates) depending on settings.

---

## 2) Core domain objects

These are the core DB-backed entities (see `src/models/`):

- **User**: authenticated principal, with role-based access (`admin`, `user`, `viewer`).
- **Job**: a scheduled unit of work.
  - Must have: `name`, `cron_expression`, `end_date` (JST date semantics), and **exactly one** target configuration:
    - `target_url` for webhook OR
    - (`github_owner`, `github_repo`, `github_workflow_name`) for GitHub Actions dispatch.
  - Optional: `pic_team` (stores a PIC team *slug*), `metadata` (JSON).
- **JobExecution**: immutable-ish run history of a job (`running|success|failed`).
  - Created on every **manual** execution and every **scheduled** run.
- **Notification**: in-app messages tied to jobs and/or executions (used by the frontend bell).
- **JobCategory**: admin-managed taxonomy for jobs.
- **PicTeam**: admin-managed team list (bulk upload validates PIC team slugs).
- **SlackSettings / NotificationPreferences / UiPreferences**: admin/user preferences and integration configuration.

---

## 3) Timezones (JST rules)

The product uses **Asia/Tokyo (JST)** for business rules:

- `end_date` is treated as a **date-only** cutoff in JST.
- Some scheduler logic and reminders use JST comparisons.

The DB stores timestamps in UTC (`started_at`, `completed_at`) and the frontend should format appropriately.

---

## 4) How scheduling works (APScheduler, leader-only)

APScheduler runs **inside the backend process** (not a separate service).

Key ideas:

- **Leader-only scheduler**: a file lock prevents multiple processes from running schedules at the same time.
  - Lock file: `src/instance/scheduler.lock`
  - If you run multiple workers/instances, only one becomes the scheduler leader; others only serve APIs.
- **DB → Scheduler reconciliation**:
  - On startup and periodically, the system reconciles the DB jobs with APScheduler jobs.
  - This ensures schedules survive restarts and DB writes done by non-leader instances.
- **Operational endpoints**:
  - `GET /api/v2/scheduler/status` (admin): confirms leader + scheduled job count.
  - `POST /api/v2/scheduler/resync` (admin): forces a DB → scheduler resync.

Files to know:

- `src/app/scheduler_runtime.py`: starts/stops scheduler and lock acquisition.
- `src/app/scheduler_reconcile.py`: periodic reconciliation loop.
- `src/app/scheduler_side_effects.py`: “best effort” schedule update hooks for create/update/delete.

---

## 5) How executions are recorded

Executions are stored in the `job_executions` table.

There are two creation paths:

- **Manual execution**: `/api/v2/jobs/{job_id}/execute`
  - Creates `job_executions` via the FastAPI async DB session.
- **Scheduled execution**: APScheduler triggers the executor
  - Creates `job_executions` via a sync DB session (scheduler/runtime code path).

Important: both paths must point to the **same database**, otherwise executions can look like they “disappear”.

---

## 6) Database and persistence (SQLite dev defaults)

### Default DB location

Local/dev uses SQLite by default:

- DB file: `src/instance/cron_jobs.db`

### DB configuration variables

- `DATABASE_URL`: used by sync code paths (scheduler/scripts).
- `FASTAPI_DATABASE_URL`: used by async API code paths.

`start_fastapi.sh` defaults these to the same DB file to avoid mismatch.

### Why executions can “disappear”

The typical causes are:

- You restored a DB backup that didn’t include executions, or you intentionally reset tables.
- You deleted/recreated jobs (executions are job-linked; depending on FK behavior they can be removed or no longer visible).
- The API and scheduler wrote to different DBs due to env mismatch or `TESTING=true`.

On startup, the backend prints the resolved **sync/async DB targets** to help diagnose this.

---

## 7) API overview (what the frontend calls)

All routes are under `/api/v2`.

Common areas:

- **Auth**: login/refresh/logout + `/me`
- **Jobs**: list/detail/create/update/delete, bulk upload, execute now
- **Executions**: per-job executions + global execution list/stats
- **Notifications**: list/mark read/delete
- **Taxonomy + Settings**: job categories, PIC teams, Slack settings, UI prefs

OpenAPI/Swagger is built-in:

- `http://localhost:5001/docs`

---

## 8) Local development workflows

### Start backend (hot reload)

- Run: `./start_fastapi.sh`
- Health: `GET http://localhost:5001/api/v2/health`
- Docs: `http://localhost:5001/docs`

### Initialize DB schema

- Run: `./scripts/init_fastapi_db.py`

### Create an admin user

- Run: `./scripts/create_admin.py`

### Run tests

- Run: `pytest`

The test suite is under `test/` and is expected to run without touching your real `cron_jobs.db`.

---

## 9) Bulk upload CSV (practical guidance)

Bulk upload validates and creates jobs from CSV.

Key rules:

- `end_date` is required (`YYYY-MM-DD`).
- `pic_team` must match an existing **PIC team slug** (create teams first in Settings → PIC Teams).
- Each row must include either:
  - `target_url` (webhook), OR
  - GitHub dispatch config (`dispatch_url` or repo/workflow columns).

If you’re troubleshooting CSV failures, compare the backend error list with what exists in Settings (categories, PIC teams).

---

## 10) Troubleshooting checklist

- **Swagger not visible**: confirm backend is listening on `:5001` and check `logs/fastapi.log`.
- **Scheduler not creating executions**:
  - Check `GET /api/v2/scheduler/status` (admin) → `scheduler_is_leader=true`.
  - Confirm jobs are active and have valid cron + end_date not expired.
- **Executions missing**:
  - Confirm DB file used by backend: startup prints sync/async DB targets.
  - Check whether jobs were deleted/reset/restored from backup.
- **Notifications empty**:
  - Ensure notification endpoints return data.
  - Verify notification creation hooks around job create/update/delete and execution outcomes.

---

## 11) Extending the system safely

When adding features:

- Update models in `src/models/` (schema source of truth).
- If SQLite dev schema needs a new column, update `src/utils/sqlite_schema.py` (minimal, backwards-compatible).
- Add/extend FastAPI routers under `src/app/routers/`.
- Add tests under `test/` in the corresponding feature folder.

