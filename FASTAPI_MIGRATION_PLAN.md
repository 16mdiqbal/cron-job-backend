# Flask to FastAPI Migration Plan

> **Project:** cron-job-backend  
> **Migration Type:** Gradual (Side-by-Side)  
> **Created:** December 21, 2025  
> **Estimated Duration:** 30 working days (~6 weeks)

> **Status (Cutover):** ✅ Migration completed — FastAPI is the only backend and Flask code has been removed.

---

## Table of Contents

1. [Overview](#overview)
2. [Current Architecture](#current-architecture)
3. [Dependency Mapping](#dependency-mapping)
4. [Phase 1: Project Setup & Dual-Stack Infrastructure](#phase-1-project-setup--dual-stack-infrastructure-days-1-2)
5. [Phase 2: Database & Model Layer](#phase-2-database--model-layer-days-3-5)
6. [Phase 3: Authentication System](#phase-3-authentication-system-days-6-9)
7. [Phase 4: Health & Read-Only Endpoints](#phase-4-health--read-only-endpoints-days-10-12)
8. [Phase 5: Write Operations - Jobs CRUD](#phase-5-write-operations---jobs-crud-days-13-17)
9. [Phase 6: Auth & User Management](#phase-6-auth--user-management-days-18-21)
10. [Phase 7: Notifications & Settings](#phase-7-notifications--settings-days-22-24)
11. [Phase 8: Scheduler Migration & Cutover](#phase-8-scheduler-migration--cutover-days-25-30)
12. [Final Folder Structure](#final-folder-structure)
13. [Risk Mitigation](#risk-mitigation)
14. [Success Criteria](#success-criteria)
15. [Timeline Summary](#timeline-summary)
16. [Progress Log](#progress-log)
17. [Environment Setup Guide](#environment-setup-guide)
18. [API Contract Appendix](#api-contract-appendix)
19. [Validation Rules Reference](#validation-rules-reference)
20. [Testing Checklist](#testing-checklist)
21. [Rollback Procedures](#rollback-procedures)
22. [Database Migration Notes](#database-migration-notes)
23. [References](#references)

---

## Overview

This document outlines the gradual migration strategy from Flask to FastAPI for the cron-job-backend application. The migration enables running both frameworks side-by-side, allowing incremental migration while maintaining continuous deployment capability.

### Benefits After Migration

- **Performance**: Async I/O for DB queries and HTTP calls
- **Documentation**: Auto-generated OpenAPI/Swagger at `/docs`
- **Validation**: Pydantic models catch errors at API boundary
- **Type Safety**: Full IDE support with type hints
- **Modern Ecosystem**: Better tooling, wider community adoption

---

## Current Architecture

| Component | Current Technology | Scope |
|-----------|-------------------|-------|
| Framework | Flask 3.0.0 | Core |
| ORM | Flask-SQLAlchemy | SQLite DB |
| Auth | Flask-JWT-Extended | JWT tokens |
| Scheduler | APScheduler | Background jobs |
| Email | Flask-Mail | SMTP notifications |
| CORS | Flask-CORS | Cross-origin |
| Routes | 3 Blueprints (~3000+ LOC) | auth, jobs, notifications |
| Tests | pytest | ~100+ tests |

### Current Endpoints Summary

| Blueprint | Prefix | Endpoints |
|-----------|--------|-----------|
| auth | `/api/auth` | 12 endpoints |
| jobs | `/api` | 25+ endpoints |
| notifications | `/api/notifications` | 6 endpoints |

### Current Models

| Model | Key Purpose |
|-------|-------------|
| User | Authentication, roles (admin/user/viewer) |
| Job | Cron job definitions, GitHub Actions config |
| JobExecution | Execution history and status |
| Notification | User notifications |
| JobCategory | Job categorization |
| PicTeam | Team assignment |
| SlackSettings | Slack integration config |
| UserNotificationPreferences | Email/push preferences |
| UserUiPreferences | UI customization |

---

## Dependency Mapping

| Flask Package | FastAPI Equivalent | Notes |
|---------------|-------------------|-------|
| `Flask` | `fastapi` + `uvicorn` | Native async support |
| `Flask-SQLAlchemy` | `SQLAlchemy 2.0` + async sessions | Use dependency injection |
| `Flask-JWT-Extended` | `PyJWT` + existing `passlib` hashing | Keep JWT + password behavior compatible across stacks |
| `Flask-CORS` | `fastapi.middleware.cors` | Built-in |
| `Flask-Mail` | TBD (Phase 8) | Keep Flask-Mail until scheduler/cutover work is migrated |
| `APScheduler` | `APScheduler` | Keep as-is |

### New Requirements (to add)

```txt
fastapi>=0.109.0
uvicorn[standard]>=0.27.0
PyJWT[crypto]>=2.8.0
python-multipart
pydantic>=2.0
pydantic-settings
httpx
aiosqlite
greenlet
```

---

## Phase 1: Project Setup & Dual-Stack Infrastructure (Days 1-2)

### Status: ✅ Completed (2025-12-22)

### Objective
Set up FastAPI alongside Flask with shared database and configuration.

### Tasks

- [x] Create folder structure `src/fastapi_app/`
  - [x] `main.py` - FastAPI app instance
  - [x] `config.py` - Pydantic Settings
  - [x] `dependencies/` - Auth, database dependencies
  - [x] `routers/` - Empty router files
  - [x] `schemas/` - Pydantic models
- [x] Update `requirements.txt` with FastAPI dependencies
- [ ] Create reverse proxy configuration (nginx/Traefik) *(Deferred - not needed for local development)*
  - [ ] `/api/v2/*` → FastAPI (port 8001)
  - [ ] `/api/*` → Flask (port 5000)
- [x] Add `start_fastapi.sh` script
- [x] Verify both apps run simultaneously

### Deliverables
- [x] FastAPI app responding on port 8001
- [x] Flask app responding on port 5001 (macOS uses 5000 for AirPlay)
- [ ] Proxy routing under single port 8000 *(Deferred)*
- [x] Shared `.env` configuration working

### Notes
```
Phase 1 completed on 2025-12-22.

Files created:
- src/fastapi_app/__init__.py
- src/fastapi_app/main.py (FastAPI app with health endpoint)
- src/fastapi_app/config.py (Pydantic Settings)
- src/fastapi_app/dependencies/__init__.py
- src/fastapi_app/dependencies/auth.py (placeholder)
- src/fastapi_app/dependencies/database.py (placeholder)
- src/fastapi_app/routers/__init__.py
- src/fastapi_app/schemas/__init__.py (base schemas)
- start_fastapi.sh (startup script)

Endpoints available:
- GET /api/v2/health - Health check
- GET /docs - Swagger UI
- GET /redoc - ReDoc documentation

Both servers tested successfully:
- Flask: http://localhost:5001/api/health
- FastAPI: http://localhost:8001/api/v2/health
```

---

## Phase 2: Database & Model Layer (Days 3-5)

### Status: ✅ Completed (2025-12-22)

### Objective
Create shared SQLAlchemy setup that works for both Flask and FastAPI.

### Tasks

- [x] Create `src/database/` folder
  - [x] `engine.py` - SQLAlchemy engine creation (sync + async)
  - [x] `session.py` - Sync and async session factories
- [ ] Refactor models to use `DeclarativeBase` directly *(Deferred - Flask models work as-is)*
- [x] Create Pydantic schemas in `src/fastapi_app/schemas/`
  - [x] `user.py` - UserCreate, UserUpdate, UserResponse, UserLogin, PasswordChange, PasswordReset
  - [x] `job.py` - JobCreate, JobUpdate, JobResponse, JobBulkUpload, JobTrigger
  - [x] `execution.py` - ExecutionResponse, ExecutionStats, DashboardStats
  - [x] `notification.py` - NotificationResponse, NotificationPreferences
  - [x] `category.py` - CategoryCreate, CategoryUpdate, CategoryResponse
  - [x] `team.py` - TeamCreate, TeamUpdate, TeamResponse
  - [x] `settings.py` - SlackSettingsUpdate, UiPreferences
  - [x] `common.py` - ErrorResponse, PaginatedResponse, BulkOperationResult
- [x] Verify Flask app still works with models
- [ ] Test database migrations *(Deferred - no schema changes required)*

### Pydantic Schemas Required

| Schema File | Models |
|-------------|--------|
| `user.py` | UserCreate, UserUpdate, UserResponse, UserLogin, PasswordChange, PasswordReset, TokenResponse, LoginResponse |
| `job.py` | JobCreate, JobUpdate, JobResponse, JobBulkUpload, JobTrigger, JobTriggerResponse, JobStatsResponse |
| `execution.py` | ExecutionResponse, ExecutionStats, ExecutionTimeline, DashboardStats, JobExecutionSummary |
| `notification.py` | NotificationResponse, NotificationPreferencesResponse, NotificationMarkRead, NotificationCount |
| `category.py` | CategoryCreate, CategoryUpdate, CategoryResponse, CategoryListResponse |
| `team.py` | TeamCreate, TeamUpdate, TeamResponse, TeamListResponse |
| `settings.py` | SlackSettingsUpdate, SlackSettingsResponse, UiPreferencesUpdate, UiPreferencesResponse, HealthResponse |
| `common.py` | ErrorResponse, ErrorDetail, SuccessResponse, PaginationParams, PaginatedResponse, BulkOperationResult |

### Deliverables
- [x] Models compatible with both frameworks (Flask uses existing, FastAPI uses Pydantic)
- [x] ~50 Pydantic schemas created (exceeded target of ~25)
- [x] Database session dependency ready for FastAPI

### Notes
```
Phase 2 completed on 2025-12-22.

Files created:
- src/database/__init__.py
- src/database/engine.py (sync + async engine factories)
- src/database/session.py (sync + async session management)
- src/fastapi_app/schemas/user.py (8 schemas)
- src/fastapi_app/schemas/job.py (9 schemas)
- src/fastapi_app/schemas/execution.py (9 schemas)
- src/fastapi_app/schemas/notification.py (8 schemas)
- src/fastapi_app/schemas/category.py (5 schemas)
- src/fastapi_app/schemas/team.py (5 schemas)
- src/fastapi_app/schemas/settings.py (8 schemas)
- src/fastapi_app/schemas/common.py (12 schemas)
- src/fastapi_app/schemas/__init__.py (exports all 64 schemas)

Updated:
- src/fastapi_app/dependencies/database.py (uses new session module)

Verification:
- FastAPI health check: http://localhost:5001/api/v2/health ✅
- All schemas import successfully ✅
- Database module imports successfully ✅
```

---

## Phase 3: Authentication System (Days 6-9)

### Status: ✅ Completed (2025-12-23)

### Objective
Implement FastAPI authentication compatible with existing JWT tokens.

### Tasks

- [x] Create `src/fastapi_app/dependencies/auth.py`
  - [x] `get_current_user()` - Decode JWT, return User
  - [x] `get_current_active_user()` - Verify user is active
  - [x] `require_role(*roles)` - Role-based dependency factory
  - [x] `get_optional_user()` - For optional auth endpoints
- [x] Use same `JWT_SECRET_KEY` for token compatibility
- [x] Implement `/api/v2/auth/login` endpoint
- [x] Create token validation tests

### Auth Dependencies to Create

```python
# Dependency signatures
async def get_current_user(token: str = Depends(oauth2_scheme)) -> User
async def get_current_active_user(user: User = Depends(get_current_user)) -> User
def require_role(*roles: str) -> Callable  # Returns dependency
async def get_optional_user(token: str = Depends(oauth2_scheme_optional)) -> Optional[User]
```

### Cross-Stack Compatibility Tests

- [x] Token from Flask login → FastAPI endpoint ✓
- [x] Token from FastAPI login → Flask endpoint ✓
- [x] Token refresh works on both (refresh token required)
- [x] Role claims preserved

### Deliverables
- [x] FastAPI auth dependencies complete
- [x] Single Sign-On across both stacks
- [x] FastAPI tests passing (`tests_fastapi/`, 54 tests)

### Notes
```
Phase 3 completed on 2025-12-23.

Files created/updated:
- src/fastapi_app/dependencies/auth.py (394 lines)
  - Token creation (create_access_token, create_refresh_token)
  - Token decoding/verification (decode_token)
  - Auth dependencies (get_current_user, get_current_active_user, get_optional_user)
  - Role-based dependencies (require_role, require_admin, require_user_or_admin)

- src/fastapi_app/routers/auth.py (406 lines)
  - POST /api/v2/auth/login - Username/email login
  - POST /api/v2/auth/login/form - OAuth2 form login
  - POST /api/v2/auth/refresh - Token refresh
  - GET /api/v2/auth/me - Current user info
  - POST /api/v2/auth/register - User registration (admin only)
  - POST /api/v2/auth/logout - Logout endpoint
  - GET /api/v2/auth/verify - Token verification

- `tests_fastapi/auth/` (28 tests ✅)
  - Login, token refresh, user registration tests
  - Role-based access control tests
  - Cross-stack JWT compatibility (Flask ↔ FastAPI)

- `tests_fastapi/core/` + `tests_fastapi/database/` (3 tests ✅)
  - Phase 1 health/OpenAPI smoke tests
  - Phase 2 async session/model compatibility test

Cross-stack SSO verified:
- Flask JWT tokens → FastAPI ✅
- FastAPI JWT tokens → Flask ✅
```

### Database Separation (Added 2025-12-23)

To prevent Flask's background scheduler from interfering with FastAPI tests, FastAPI supports **separate database configuration**, with safe defaults:

- **Default (development/production)**: FastAPI shares the same database as Flask (`DATABASE_URL` / `src/instance/cron_jobs.db`) to keep users/auth in sync.
- **FastAPI Test Database (default when `TESTING=true`)**: `src/instance/fastapi_test.db`
- **Optional migration DB**: set `FASTAPI_DATABASE_URL` (e.g. `sqlite:///src/instance/fastapi_cron_jobs.db`) to run FastAPI against a separate database.

**Benefits**:
- ✅ No test freezing/hanging issues
- ✅ Clean isolation between stacks
- ✅ Safe independent development
- ✅ Easy rollback if needed

**Initialize databases**:
```bash
python scripts/init_fastapi_db.py
```

See [DATABASE_SEPARATION.md](DATABASE_SEPARATION.md) for details.

---

## Phase 4: Health & Read-Only Endpoints (Days 10-12)

### Status: ✅ Completed (4A ✅, 4B ✅, 4C ✅, 4D ✅, 4E ✅)

### Objective
Migrate low-risk, read-only endpoints first for validation.

### Split (Approved)

- **Phase 4A: Core & Docs (Done)**
  - [x] `GET /api/health` → `GET /api/v2/health` (no auth)
  - [x] OpenAPI available at `GET /api/v2/openapi.json`, Swagger UI at `GET /docs`

- **Phase 4B: Jobs (Read) (Done)**
  - [x] `GET /api/jobs` → `GET /api/v2/jobs` (JWT)
  - [x] `GET /api/jobs/<id>` → `GET /api/v2/jobs/{id}` (JWT)
  - [x] Response parity: returns `{count, jobs}` and `{job}` with `last_execution_at` + `next_execution_at`

- **Phase 4C: Job Executions (Read)**
  - ✅ Implemented with filter support (`limit`, `status`, `trigger_type`, `from`, `to`)
  - [x] `GET /api/jobs/<id>/executions` → `GET /api/v2/jobs/{id}/executions` (JWT)
  - [x] `GET /api/jobs/<id>/executions/<execution_id>` → `GET /api/v2/jobs/{id}/executions/{execution_id}` (JWT)
  - [x] `GET /api/jobs/<id>/executions/stats` → `GET /api/v2/jobs/{id}/executions/stats` (JWT)

- **Phase 4D: Executions (Read)**
  - ✅ Implemented with pagination + filters (`page`, `limit`, `job_id`, `status`, `trigger_type`, `execution_type`, `from`, `to`)
  - [x] `GET /api/executions` → `GET /api/v2/executions` (JWT)
  - [x] `GET /api/executions/<execution_id>` → `GET /api/v2/executions/{execution_id}` (JWT)
  - [x] `GET /api/executions/statistics` → `GET /api/v2/executions/statistics` (JWT)

- **Phase 4E: Taxonomy (Read)**
  - ✅ Implemented with role-aware `include_inactive` (admin-only)
  - [x] `GET /api/job-categories` → `GET /api/v2/job-categories` (JWT)
  - [x] `GET /api/pic-teams` → `GET /api/v2/pic-teams` (JWT)

### Tasks

- [x] Implement routers per group (recommended):
  - [x] `src/fastapi_app/routers/jobs.py` (Phase 4B)
  - [x] `src/fastapi_app/routers/executions.py` (Phase 4C/4D)
  - [x] `src/fastapi_app/routers/taxonomy.py` (Phase 4E: job-categories + pic-teams)
- [x] Add response-shape parity schemas for Phase 4
  - [x] `src/fastapi_app/schemas/jobs_read.py`
  - [x] `src/fastapi_app/schemas/executions_read.py`
  - [x] `src/fastapi_app/schemas/taxonomy_read.py`
- [x] Add automated tests (FastAPI response shape + auth enforcement)
- [x] Keep tests split by service under `tests_fastapi/` (e.g. `tests_fastapi/jobs/`, `tests_fastapi/executions/`, `tests_fastapi/taxonomy/`)
- [ ] Optional: add cross-stack JSON diff parity tests (Flask ↔ FastAPI) against a running local server

Phase 4B tests:
- [x] `tests_fastapi/jobs/test_jobs_read.py`

Phase 4C tests:
- [x] `tests_fastapi/executions/test_job_executions_read.py`

Phase 4D tests:
- [x] `tests_fastapi/executions/test_executions_global_read.py`

Phase 4E tests:
- [x] `tests_fastapi/taxonomy/test_taxonomy_read.py`

### Deliverables
- [x] Phase 4 endpoints on `/api/v2/` (4A–4E)
- [x] OpenAPI/Swagger updated automatically (see `http://127.0.0.1:8001/docs`)
- [x] Automated tests added for all Phase 4 endpoints

### Notes
Verified locally:
```bash
venv/bin/python -m pytest -q tests_fastapi
# 54 passed
```

---

## Phase 5: Write Operations - Jobs CRUD (Days 13-17)

### Status: ✅ Complete (5A–5F)

### Objective
Migrate job creation, update, and deletion with full validation.

### Scope (Confirmed)

- **DB-first (no scheduler side-effects):** FastAPI write endpoints will **not** add/reschedule/remove APScheduler jobs. Scheduler wiring stays in **Phase 8**.
- **Manual execute is allowed:** `POST /jobs/{id}/execute` can trigger an on-demand run (like Flask), but does not alter background schedules.
- **No Flask changes:** Flask remains the source of truth for background scheduling during this phase.

### Endpoints to Migrate

| # | Flask Endpoint | FastAPI Endpoint | Complexity | Status |
|---|----------------|------------------|------------|--------|
| 1 | `POST /api/jobs` | `POST /api/v2/jobs` | High | ✅ |
| 2 | `PUT /api/jobs/<id>` | `PUT /api/v2/jobs/{id}` | High | ✅ |
| 3 | `DELETE /api/jobs/<id>` | `DELETE /api/v2/jobs/{id}` | Medium | ✅ |
| 4 | `POST /api/jobs/<id>/execute` | `POST /api/v2/jobs/{id}/execute` | High | ✅ |
| 5 | `POST /api/jobs/bulk-upload` | `POST /api/v2/jobs/bulk-upload` | High | ✅ |
| 6 | `POST /api/jobs/validate-cron` | `POST /api/v2/jobs/validate-cron` | Low | ✅ |
| 7 | `POST /api/jobs/cron-preview` | `POST /api/v2/jobs/cron-preview` | Low | ✅ |
| 8 | `POST /api/jobs/test-run` | `POST /api/v2/jobs/test-run` | Medium | ✅ |

### Sub-Phases (Execution Order)

| Sub-Phase | Goal | Endpoints | Primary Test Location |
|----------:|------|-----------|------------------------|
| **5A** | Job create (validation + RBAC) | `POST /api/v2/jobs` | `tests_fastapi/jobs_write/test_create.py` ✅ |
| **5B** | Job update (partial update + ownership rules) | `PUT /api/v2/jobs/{id}` | `tests_fastapi/jobs_write/test_update.py` ✅ |
| **5C** | Job delete (parity behavior + RBAC) | `DELETE /api/v2/jobs/{id}` | `tests_fastapi/jobs_write/test_delete.py` ✅ |
| **5D** | Manual execute (execution record + trigger) | `POST /api/v2/jobs/{id}/execute` | `tests_fastapi/jobs_write/test_execute.py` ✅ |
| **5E** | Bulk CSV upload (validation + partial success) | `POST /api/v2/jobs/bulk-upload` | `tests_fastapi/jobs_write/test_bulk_upload.py` ✅ |
| **5F** | Cron utilities | `POST /api/v2/jobs/validate-cron`, `POST /api/v2/jobs/cron-preview`, `POST /api/v2/jobs/test-run` | `tests_fastapi/cron_tools/*` ✅ |

### Implementation Notes (Guidelines)

- Prefer adding write endpoints to the existing Jobs router (or a separate `jobs_write.py` router under the **Jobs** tag) while keeping read endpoints stable.
- Keep **response shapes** consistent with Flask where feasible (especially error keys like `error` + `message`), so frontend parity is predictable.
- Ensure all DB writes are done via async SQLAlchemy sessions (`src/database/session.py`).
- Avoid external calls in tests:
  - Stub/mocks for webhook/GitHub calls.
  - For manual execute, assert **execution rows** created and that the trigger function is called, without leaving the process.

### Test Strategy (Must-Haves)

- **RBAC matrix**:
  - `POST /api/v2/jobs` → `admin`, `user` allowed; `viewer` forbidden
  - `PUT /api/v2/jobs/{id}` → `admin` allowed; `user` allowed **only for own jobs**; `viewer` forbidden
  - `DELETE /api/v2/jobs/{id}` → `admin` allowed; `user` allowed **only for own jobs**; `viewer` forbidden
  - `POST /api/v2/jobs/{id}/execute` → `admin` allowed; `user` allowed **only for own jobs**; `viewer` forbidden
  - `POST /api/v2/jobs/bulk-upload` → `admin`, `user` allowed; `viewer` forbidden
  - `POST /api/v2/jobs/test-run` → `admin`, `user` allowed; `viewer` forbidden
  - `POST /api/v2/jobs/validate-cron`, `POST /api/v2/jobs/cron-preview` → **all authenticated roles** allowed (`admin`, `user`, `viewer`)
- **Validation coverage**:
  - Required fields (`name`, `cron_expression`, `category`, `pic_team`, `end_date`)
  - Target config: webhook vs GitHub fields (mutual requirements)
  - Duplicate name conflict behavior
  - Date range/cutoffs (`end_date` must be **today or future** in scheduler timezone, default JST)
- **Side-effect boundaries**:
  - Verify FastAPI does **not** register APScheduler jobs (no scheduler manipulation in Phase 5).
  - Manual execute should not persist scheduler state changes (but does create `JobExecution` rows, matching Flask).

### Deliverables
- [x] Phase 5A–5F endpoints implemented and documented
- [x] FastAPI tests added for each sub-phase and passing (`venv/bin/python -m pytest -q tests_fastapi`)
- [x] No APScheduler add/reschedule/remove logic in FastAPI (Phase 8 responsibility)
- [x] RBAC + validation coverage complete for write flows

### Notes
Implementation location:
- `src/fastapi_app/routers/jobs.py` (read + write endpoints under `/api/v2/jobs/*`)

#### 5A — Create job (`POST /api/v2/jobs`)
- Auth: `admin` or `user`
- Content-Type: `application/json`
- Validations (high-level):
  - `name` required + unique
  - `cron_expression` must be a 5-field crontab string and parseable in scheduler timezone (default JST)
  - `end_date` required and must be **today or future** (scheduler timezone)
  - `pic_team` required and must exist + active
  - `category` resolves from slug or name; defaults to `general`; must exist if not `general`
  - Target config must be present: either `target_url` OR full GitHub config (`github_owner` optional default, `github_repo`, `github_workflow_name`)
  - `metadata` must be a JSON object (dict)
  - Notification fields are persisted but no email/slack/broadcast side-effects are executed in Phase 5
- Response:
  - `201`: `{"message":"Job created successfully","job":{...}}`
  - Errors use `{"error": "...", "message": "..."}` where applicable
- Tests: `tests_fastapi/jobs_write/test_create.py`

#### 5B — Update job (`PUT /api/v2/jobs/{id}`)
- Auth: `admin` or `user` (ownership enforced for `user`)
- Content-Type: `application/json`
- Validations (high-level):
  - Cannot rename to an existing job name
  - `cron_expression` must be valid 5-field crontab when present
  - `end_date` must be **today or future** (scheduler timezone) when present
  - `pic_team`/`category` validation rules same as create
  - Target config must remain valid after update (cannot clear everything)
  - Guard: cannot enable an expired job without updating `end_date`
- Response:
  - `200`: `{"message":"Job updated successfully","job":{...}}`
- Tests: `tests_fastapi/jobs_write/test_update.py`

#### 5C — Delete job (`DELETE /api/v2/jobs/{id}`)
- Auth: `admin` or `user` (ownership enforced for `user`)
- Scope note: no APScheduler removal here; deferred to Phase 8
- Response:
  - `200`: `{"message":"Job deleted successfully","deleted_job":{"id":"...","name":"..."}}`
- Tests: `tests_fastapi/jobs_write/test_delete.py`

#### 5D — Manual execute (`POST /api/v2/jobs/{id}/execute`)
- Auth: `admin` or `user` (ownership enforced for `user`)
- Behavior:
  - Overrides are **not persisted** (metadata and target overrides apply only to the run)
  - Creates a `JobExecution` row with `trigger_type="manual"` and updates it to `success`/`failed`
  - If job `end_date` is in the past (scheduler timezone): auto-pauses the job (`is_active=false`) and returns `400`
  - Webhook runs perform HTTP calls; GitHub runs dispatch workflows (requires token via payload `github_token` or env `GITHUB_TOKEN`)
- Response:
  - `200`: `{"message":"Job triggered successfully","job_id":"..."}`
- Tests: `tests_fastapi/jobs_write/test_execute.py`

#### 5E — Bulk CSV upload (`POST /api/v2/jobs/bulk-upload`)
- Auth: `admin` or `user`
- Content-Type: `multipart/form-data`
- Form fields:
  - `file` (required): CSV file
  - `default_github_owner` (optional): default owner used when Repo column contains `repo` only
  - `dry_run` (optional truthy): validate only (no DB writes)
- CSV normalization:
  - Drops columns with empty headers
  - Removes fully-empty rows
- Row mapping (supports multiple header variants):
  - `Job Name`/`name`, `Cron Schedule (JST)`/`cron_expression`, `Status`, `Target URL`
  - `Repo` (supports `owner/repo`), `Workflow Name`, optional `GitHub Owner`
  - `Category`, `End Date`, `PIC Team`
  - `Request Body` JSON object → job metadata; optional `Branch` → `metadata.branchDetails` when absent
- Response:
  - `200` always for row-level partial success (even with errors)
  - `400` for structural CSV issues (e.g., empty file)
  - Shape matches Flask: includes `dry_run`, `stats`, `created_count`, `error_count`, `errors`, `jobs`
- Tests: `tests_fastapi/jobs_write/test_bulk_upload.py`

#### 5F — Cron utilities
- `POST /api/v2/jobs/validate-cron`:
  - Auth: any authenticated role
  - Returns `200` always with `{"valid": true/false, ...}` (matches Flask behavior)
- `POST /api/v2/jobs/cron-preview`:
  - Auth: any authenticated role
  - Invalid cron returns `400`; valid cron returns `200` with `timezone`, `next_runs`, `count`
- `POST /api/v2/jobs/test-run`:
  - Auth: `admin` or `user`
  - One-off test run without creating a Job or JobExecution
  - Webhook path hits `target_url`; GitHub path dispatches workflow (requires env `GITHUB_TOKEN`)
  - Returns `200` with `{ok,type,status_code,message}`; missing GitHub token returns `200` with `ok:false`
- Tests: `tests_fastapi/cron_tools/*`

Phase 5A implemented:
- Endpoint: `POST /api/v2/jobs` (DB-first; no APScheduler scheduling side-effects)
- Tests: `tests_fastapi/jobs_write/test_create.py`

Phase 5B implemented:
- Endpoint: `PUT /api/v2/jobs/{id}` (DB-first; ownership enforced)
- Tests: `tests_fastapi/jobs_write/test_update.py`

Phase 5C implemented:
- Endpoint: `DELETE /api/v2/jobs/{id}` (DB-first; ownership enforced)
- Tests: `tests_fastapi/jobs_write/test_delete.py`

Phase 5D implemented:
- Endpoint: `POST /api/v2/jobs/{id}/execute` (manual run; overrides not persisted; DB-first re: scheduler side-effects)
- Tests: `tests_fastapi/jobs_write/test_execute.py`

Phase 5E implemented:
- Endpoint: `POST /api/v2/jobs/bulk-upload` (CSV normalization + partial success; DB-first)
- Tests: `tests_fastapi/jobs_write/test_bulk_upload.py`

Phase 5F implemented:
- Endpoints: `POST /api/v2/jobs/validate-cron`, `POST /api/v2/jobs/cron-preview`, `POST /api/v2/jobs/test-run`
- Tests: `tests_fastapi/cron_tools/*`

Verified:
```bash
venv/bin/python -m pytest -q tests_fastapi
# 108 passed
```

---

## Phase 6: Auth & User Management (Days 18-21)

### Status: ✅ Complete (6A–6E)

### Objective
Complete user management + preference endpoints that are not covered by Phase 3.

### Endpoints to Migrate

| # | Flask Endpoint | FastAPI Endpoint | Auth | Status |
|---|----------------|------------------|------|--------|
| 1 | `POST /api/auth/login` | `POST /api/v2/auth/login` | None | ✅ |
| 2 | `POST /api/auth/refresh` | `POST /api/v2/auth/refresh` | Refresh | ✅ |
| 3 | `POST /api/auth/register` | `POST /api/v2/auth/register` | Admin | ✅ |
| 4 | `GET /api/auth/me` | `GET /api/v2/auth/me` | JWT | ✅ |
| 5 | `GET /api/auth/users` | `GET /api/v2/auth/users` | Admin | ✅ |
| 6 | `GET /api/auth/users/<id>` | `GET /api/v2/auth/users/{id}` | JWT | ✅ |
| 7 | `PUT /api/auth/users/<id>` | `PUT /api/v2/auth/users/{id}` | JWT | ✅ |
| 8 | `DELETE /api/auth/users/<id>` | `DELETE /api/v2/auth/users/{id}` | Admin | ✅ |
| 9 | `GET /api/auth/users/<id>/preferences` | `GET /api/v2/auth/users/{id}/preferences` | JWT | ✅ |
| 10 | `PUT /api/auth/users/<id>/preferences` | `PUT /api/v2/auth/users/{id}/preferences` | JWT | ✅ |
| 11 | `GET /api/auth/users/<id>/ui-preferences` | `GET /api/v2/auth/users/{id}/ui-preferences` | JWT | ✅ |
| 12 | `PUT /api/auth/users/<id>/ui-preferences` | `PUT /api/v2/auth/users/{id}/ui-preferences` | JWT | ✅ |

### Sub-Phases (Execution Order)

| Sub-Phase | Goal | Endpoints | Primary Test Location |
|----------:|------|-----------|------------------------|
| **6A** | Users read (admin list + self/admin get) | `GET /api/v2/auth/users`, `GET /api/v2/auth/users/{id}` | `tests_fastapi/users/test_users_read.py` ✅ |
| **6B** | User update (self + admin controls) | `PUT /api/v2/auth/users/{id}` | `tests_fastapi/users/test_users_update.py` ✅ |
| **6C** | User delete (admin-only + self-delete guard) | `DELETE /api/v2/auth/users/{id}` | `tests_fastapi/users/test_users_delete.py` ✅ |
| **6D** | Notification preferences (get-or-create + update) | `GET/PUT /api/v2/auth/users/{id}/preferences` | `tests_fastapi/users/test_notification_preferences.py` ✅ |
| **6E** | UI preferences (get-or-create + update) | `GET/PUT /api/v2/auth/users/{id}/ui-preferences` | `tests_fastapi/users/test_ui_preferences.py` ✅ |

### Tasks

- [x] `src/fastapi_app/routers/auth.py` (login/refresh/register/me/logout/verify)
- [x] Password hashing remains `passlib.hash.pbkdf2_sha256` via `src/models/user.py`
- [x] Implement Phase 6A: users read endpoints + tests
- [x] Implement Phase 6B: user update endpoint + tests
- [x] Implement Phase 6C: user delete endpoint + tests
- [x] Implement Phase 6D: notification preferences endpoints + tests
- [x] Implement Phase 6E: UI preferences endpoints + tests
- [x] Ensure response shapes match Flask where feasible (`error` + `message` keys, and payload nesting like `user`, `preferences`)

### Deliverables
- [x] Full auth flow on FastAPI (login/refresh/register/me/logout/verify)
- [x] User management CRUD (list/get/update/delete)
- [x] Preference management (notification + UI)
- [x] Password change working (self and admin)

### Notes
Implementation location:
- `src/fastapi_app/routers/auth.py` (all Phase 6 endpoints under `/api/v2/auth/*`)
- Models: `src/models/user.py`, `src/models/notification_preferences.py`, `src/models/ui_preferences.py`
- Tests: `tests_fastapi/users/*`

#### 6A — Users read
- `GET /api/v2/auth/users` (admin-only)
  - Response: `{"count": N, "users": [User.to_dict(), ...]}`
- `GET /api/v2/auth/users/{id}` (JWT)
  - RBAC: admin can view any user; non-admin can view only self
  - Response: `{"user": User.to_dict()}`
  - Forbidden response matches Flask: `{"error": "Forbidden. You can only view your own profile."}`
- Tests: `tests_fastapi/users/test_users_read.py`

#### 6B — User update
- `PUT /api/v2/auth/users/{id}` (JWT)
  - RBAC:
    - Self-update: `email`, `password`
    - Admin-update: `email`, `password`, `role`, `is_active`
  - Validations:
    - `email` unique → 409 `{"error":"Email already exists"}`
    - `password` length ≥ 6 → 400
    - `role` ∈ {admin,user,viewer} → 400 with `{"error":"Invalid role","message":"Role must be one of: admin, user, viewer"}`
    - Reject empty/no-op updates → 400 `{"error":"No valid fields to update"}`
  - Response: `{"message":"User updated successfully","updated_fields":[...],"user": User.to_dict()}`
- Tests: `tests_fastapi/users/test_users_update.py`

#### 6C — User delete
- `DELETE /api/v2/auth/users/{id}` (admin-only)
  - Guard: cannot delete yourself → 400 `{"error":"Cannot delete your own account"}`
  - Response: `{"message":"User deleted successfully","deleted_user":{"id":"...","username":"..."}}`
- Tests: `tests_fastapi/users/test_users_delete.py`

#### 6D — Notification preferences
- `GET /api/v2/auth/users/{id}/preferences` (JWT)
  - RBAC: admin can access any; non-admin only self
  - Get-or-create defaults match Flask (on first GET):
    - `email_on_job_success=True`, `email_on_job_failure=True`, `email_on_job_disabled=False`
    - `browser_notifications=False`, `daily_digest=False`, `weekly_report=False`
  - Response: `{"message":"Notification preferences retrieved successfully","preferences": {...}}`
- `PUT /api/v2/auth/users/{id}/preferences` (JWT)
  - RBAC: admin any; non-admin only self
  - Partial update allowed; missing row is created if needed (matches Flask)
  - Response: `{"message":"Notification preferences updated successfully","preferences": {...}}`
- Tests: `tests_fastapi/users/test_notification_preferences.py`

#### 6E — UI preferences
- `GET /api/v2/auth/users/{id}/ui-preferences` (JWT)
  - RBAC: admin can access any; non-admin only self
  - Get-or-create defaults match Flask, returning:
    - `{"preferences":{"jobs_table_columns":{...}}}`
- `PUT /api/v2/auth/users/{id}/ui-preferences` (JWT)
  - RBAC: admin any; non-admin only self
  - Requires `jobs_table_columns` object; normalizes to allowed keys (Flask default keys)
  - Response: `{"preferences":{"jobs_table_columns":{...}}}`
- Tests: `tests_fastapi/users/test_ui_preferences.py`

Verified:
```bash
venv/bin/python -m pytest -q tests_fastapi
# 146 passed
```

---

## Phase 7: Notifications & Settings (Days 22-24)

### Status: ✅ Complete (7A–7G)

### Objective
Complete remaining endpoints (Notifications, Slack Settings, Category/Team write) and any required supporting utilities.

### Endpoints to Migrate

| # | Flask Endpoint | FastAPI Endpoint | Status |
|---|----------------|------------------|--------|
| 1 | `GET /api/notifications` | `GET /api/v2/notifications` | ✅ |
| 2 | `GET /api/notifications/unread-count` | `GET /api/v2/notifications/unread-count` | ✅ |
| 3 | `PUT /api/notifications/<id>/read` | `PUT /api/v2/notifications/{id}/read` | ✅ |
| 4 | `PUT /api/notifications/read-all` | `PUT /api/v2/notifications/read-all` | ✅ |
| 5 | `DELETE /api/notifications/<id>` | `DELETE /api/v2/notifications/{id}` | ✅ |
| 6 | `DELETE /api/notifications/delete-read` | `DELETE /api/v2/notifications/delete-read` | ✅ |
| 7 | `GET /api/settings/slack` | `GET /api/v2/settings/slack` | ✅ |
| 8 | `PUT /api/settings/slack` | `PUT /api/v2/settings/slack` | ✅ |
| 9 | `POST /api/job-categories` | `POST /api/v2/job-categories` | ✅ |
| 10 | `PUT /api/job-categories/<id>` | `PUT /api/v2/job-categories/{id}` | ✅ |
| 11 | `DELETE /api/job-categories/<id>` | `DELETE /api/v2/job-categories/{id}` | ✅ |
| 12 | `POST /api/pic-teams` | `POST /api/v2/pic-teams` | ✅ |
| 13 | `PUT /api/pic-teams/<id>` | `PUT /api/v2/pic-teams/{id}` | ✅ |
| 14 | `DELETE /api/pic-teams/<id>` | `DELETE /api/v2/pic-teams/{id}` | ✅ |

### Sub-Phases (Execution Order)

This phase is intentionally split by **logical API grouping** to keep each unit reviewable and testable end-to-end.

| Sub-Phase | Scope | Endpoints | Primary Tests |
|----------|-------|-----------|---------------|
| **7A ✅** | Notifications (Read) | `GET /api/v2/notifications`, `GET /api/v2/notifications/unread-count` | `tests_fastapi/notifications/test_notifications_read.py` |
| **7B ✅** | Notifications (Mark Read) | `PUT /api/v2/notifications/{id}/read`, `PUT /api/v2/notifications/read-all` | `tests_fastapi/notifications/test_notifications_mark_read.py` |
| **7C ✅** | Notifications (Delete) | `DELETE /api/v2/notifications/{id}`, `DELETE /api/v2/notifications/delete-read` | `tests_fastapi/notifications/test_notifications_delete.py` |
| **7D ✅** | Settings (Slack) | `GET /api/v2/settings/slack`, `PUT /api/v2/settings/slack` | `tests_fastapi/settings/test_slack_settings.py` |
| **7E ✅** | Job Categories (Write) | `POST/PUT/DELETE /api/v2/job-categories` | `tests_fastapi/taxonomy_write/test_job_categories_write.py` |
| **7F ✅** | PIC Teams (Write) | `POST/PUT/DELETE /api/v2/pic-teams` | `tests_fastapi/taxonomy_write/test_pic_teams_write.py` |
| **7G ✅** | Utilities (Optional / Last) | Async Slack client + notifications helpers (no API) | `tests_fastapi/utils/test_slack_async.py`, `tests_fastapi/utils/test_notifications_helper.py` |

### Detailed Plan (Per Sub-Phase)

#### 7A — Notifications (Read)
- Router: `src/fastapi_app/routers/notifications.py` + include in `src/fastapi_app/main.py`
- Query params match Flask:
  - `page` (default 1), `per_page` (default 20, max 100), `unread_only` (default false)
  - `from`/`to` ISO date/datetime parsing:
    - Accept `YYYY-MM-DD` or ISO datetime (`Z` or offset supported)
    - Date-only `to` treated as inclusive day (`+1 day` then use `< to_dt`)
    - Invalid format → `400 {"error":"Invalid date","message":"Invalid date"}`
    - Invalid range (`from >= to`) → `400 {"error":"Invalid date range","message":"\"from\" must be earlier than \"to\"."}`
- Response shapes match Flask:
  - `GET /notifications`: `{"notifications":[...],"total":...,"page":...,"per_page":...,"total_pages":...,"range":{"from":...,"to":...}}`
  - `GET /notifications/unread-count`: `{"unread_count":...,"range":{"from":...,"to":...}}`
- Tests:
  - Pagination defaults + max cap
  - `unread_only` behavior
  - Date parsing: `from` only, `to` date-only inclusive, invalid formats, invalid range
  - Data isolation: only current user’s notifications returned

#### 7B — Notifications (Mark Read)
- `PUT /api/v2/notifications/{id}/read`:
  - 404 `{"error":"Notification not found"}`
  - 403 `{"error":"Forbidden: Cannot access other users notifications"}`
  - 200 `{"message":"Notification marked as read","notification":{...}}`
- `PUT /api/v2/notifications/read-all`:
  - 200 `{"message":"All notifications marked as read","updated_count":...}`
- Tests:
  - Marking own notification sets `is_read=true` and `read_at` set
  - Other user notification → 403
  - `read-all` updates only unread rows and returns correct `updated_count`

#### 7C — Notifications (Delete)
- `DELETE /api/v2/notifications/{id}`:
  - 404 `{"error":"Notification not found"}`
  - 403 `{"error":"Forbidden: Cannot delete other users notifications"}`
  - 200 `{"message":"Notification deleted successfully"}`
- `DELETE /api/v2/notifications/delete-read`:
  - Supports same `from`/`to` parsing behavior as 7A
  - 200 `{"deleted_count": ...}`
- Tests:
  - Delete single: own vs other user; not-found
  - Delete-read: deletes only read notifications; honors date range; invalid date/range → 400

#### 7D — Settings (Slack)
- Router: `src/fastapi_app/routers/settings.py` + include in `src/fastapi_app/main.py`
- Admin-only RBAC (matches Flask)
- Get-or-create behavior:
  - On first access, create a single `SlackSettings` row with defaults (`is_enabled=false`, `webhook_url=null`, `channel=null`)
- Response shapes match Flask:
  - GET: `{"slack_settings": {...}}`
  - PUT: `{"message":"Slack settings updated","slack_settings": {...}}`
- Validation rules (Flask parity):
  - Values are trimmed; empty strings become `null`
  - If `is_enabled=true` and `webhook_url` missing/empty → `400 {"error":"Invalid settings","message":"webhook_url is required when Slack is enabled."}`
- Tests:
  - Admin can GET/PUT; non-admin forbidden
  - PUT validation for enabled-without-webhook_url
  - Empty string normalization

#### 7E — Job Categories (Write)
- Router: new `src/fastapi_app/routers/taxonomy_write.py` (keeps `src/fastapi_app/routers/taxonomy.py` read-only)
- Admin-only RBAC (matches Flask)
- `POST /api/v2/job-categories`:
  - Requires `name`; optional `slug` (fallback to name), slugify and validate
  - Duplicate slug → `409 {"error":"Duplicate slug","message":"Category slug \"...\" already exists."}`
  - 201 `{"message":"Category created","category":{...}}`
- `PUT /api/v2/job-categories/{id}`:
  - Not found → `404 {"error":"Not found","message":"No category found with ID: ..."}`
  - If `name` present: derive slug from name and keep slug strictly aligned
  - Special case: `"general"` cannot be renamed → `400 {"error":"Invalid category","message":"The \"General\" category cannot be renamed."}`
  - Reject explicit slug edits → `400 {"error":"Invalid payload","message":"Slug cannot be edited directly; it is derived from name."}`
  - If slug changes: update `Job.category` values from old slug → new slug; return `jobs_updated`
  - 200 `{"message":"Category updated","category":{...},"jobs_updated":...}`
- `DELETE /api/v2/job-categories/{id}`:
  - Soft-disable (`is_active=false`)
  - 200 `{"message":"Category disabled","category":{...}}`
- Tests:
  - Create: required name; duplicate slug 409; slugify behavior
  - Update: rename general rejected; slug key rejected; slug change updates jobs and returns `jobs_updated`
  - Delete: sets `is_active=false`

#### 7F — PIC Teams (Write)
- Router: `src/fastapi_app/routers/taxonomy_write.py`
- Admin-only RBAC (matches Flask)
- `POST /api/v2/pic-teams`:
  - Requires `name` and `slack_handle`; optional `slug` (fallback to name), slugify and validate
  - Duplicate slug → `409 {"error":"Duplicate slug","message":"PIC team slug \"...\" already exists."}`
  - 201 `{"message":"PIC team created","pic_team":{...}}`
- `PUT /api/v2/pic-teams/{id}`:
  - Not found → `404 {"error":"Not found","message":"No PIC team found with ID: ..."}`
  - If `name` present: derive slug from name; reject explicit slug key; if slug changes update `Job.pic_team` values and return `jobs_updated`
  - `slack_handle` cannot be empty → `400 {"error":"Invalid slack_handle","message":"slack_handle cannot be empty."}`
  - 200 `{"message":"PIC team updated","pic_team":{...},"jobs_updated":...}`
- `DELETE /api/v2/pic-teams/{id}`:
  - Soft-disable (`is_active=false`)
  - 200 `{"message":"PIC team disabled","pic_team":{...}}`
- Tests:
  - Create: required `slack_handle`; duplicate slug 409
  - Update: slug key rejected; name change updates jobs + returns `jobs_updated`; slack_handle empty rejected
  - Delete: sets `is_active=false`

#### 7G — Utilities (Optional / Last)
- Implemented:
  - Async Slack webhook sender: `src/fastapi_app/utils/slack.py`
  - Async notification creation helper: `src/fastapi_app/utils/notifications.py`
- Tests:
  - `tests_fastapi/utils/test_slack_async.py`
  - `tests_fastapi/utils/test_notifications_helper.py`

### Deliverables
- [x] Sub-phases 7A–7F implemented + tests passing (`venv/bin/python -m pytest -q tests_fastapi`)
- [x] Swagger updated automatically via FastAPI routers/schemas
- [x] Feature parity with Flask for the endpoints above

Verified:
```bash
venv/bin/python -m pytest -q tests_fastapi
# 229 passed
```

### Notes
```
<!-- Add implementation notes here -->
```

---

## Phase 8: Scheduler Migration & Cutover (Days 25-30)

### Status: 🟨 In Progress (8A ✅, 8B ✅, 8C ✅, 8D ✅, 8E ✅, 8G ✅, 8F ✅ — local cutover smoke done; proxy/stability pending)

### Objective
Migrate APScheduler runtime + scheduler side-effects to FastAPI and complete the cutover from Flask.

This phase explicitly includes the **scheduler side-effects deferred from Phase 5**, such as scheduling/rescheduling/removing jobs when jobs are created/updated/deleted.

### Scope (What moves here from Phase 5)

- **APScheduler job registration** on job create/update/delete
- **Enable/disable behavior**: adding/removing jobs from the scheduler when `is_active` changes
- **Scheduler startup/shutdown** under FastAPI lifespan
- **Single-runner guarantees** (lock file / leader election)
- **DB → scheduler bootstrap + reconciliation loop** (Flask parity) so scheduled executions work after restarts/cutover

### Sub-Phases (Execution Order)

Phase 8 is split to keep scheduler changes safe and reviewable. **No Phase 8 implementation should start until you confirm the sub-phase plan.**

| Sub-Phase | Scope | Key Deliverables | Planned Tests |
|----------|-------|------------------|--------------|
| **8A ✅** | Scheduler core refactor (framework-agnostic) | `src/scheduler` no longer depends on Flask app context for DB work; uses `src/database/session.py` | `tests_fastapi/scheduler/test_scheduler_core.py` |
| **8B ✅** | Single-runner guarantees | Shared atomic lock file utility with stale lock handling | `tests_fastapi/scheduler/test_scheduler_lock.py` |
| **8C ✅** | FastAPI lifecycle integration | Start/stop APScheduler in FastAPI lifespan; expose status via health | `tests_fastapi/scheduler/test_scheduler_lifecycle.py` |
| **8D ✅** | Job write side-effects wiring | Create/update/delete/enable/disable schedule updates (best-effort when scheduler not running in-process) | `tests_fastapi/scheduler/test_scheduler_side_effects.py` |
| **8E ✅** | Scheduler regression tests | Timezone correctness (JST), end_date behavior, duplicate prevention | `tests_fastapi/scheduler/test_scheduler_regression.py` |
| **8G ✅** | DB reconciliation / bootstrap | Startup DB → APScheduler resync + periodic reconciliation + operator endpoint | `tests_fastapi/scheduler/test_scheduler_resync.py` |
| **8F ✅** | Cutover plan + deprecation | Frontend base URL/proxy cutover, monitoring, rollback steps | Docs + runbooks |

### Detailed Plan (Per Sub-Phase)

#### 8A — Scheduler core refactor (framework-agnostic)
- Goal: remove Flask coupling from scheduler execution path.
- Tasks:
  - Refactor `src/scheduler/job_executor.py` to avoid Flask `app_context()` patterns.
  - Use async DB sessions via `src/database/session.py` where needed (or a thin adapter layer if scheduler remains sync).
  - Ensure cron timezone behavior matches current Flask production behavior (`Asia/Tokyo` interpretation).
- Output: scheduler logic callable from both Flask and FastAPI without importing either framework.

Implemented:
- `src/scheduler/job_executor.py` now performs DB work via `src/database/session.py` (no Flask globals); Flask-Mail email sending stays injectable for later phases.
- Tests: `tests_fastapi/scheduler/test_scheduler_core.py`

#### 8B — Single-runner guarantees (lock/leader election)
- Goal: prevent multiple schedulers running in multi-process deployments.
- Tasks:
  - Implement lock mechanism similar to Flask `src/instance/scheduler.lock` (file lock or DB lock).
  - Ensure lock is acquired on startup and released on shutdown; tolerate stale locks.
  - Ensure only the leader process performs scheduling; non-leaders do not schedule but still serve API.

Implemented:
- Shared lock utility: `src/scheduler/lock.py`
- Tests: `tests_fastapi/scheduler/test_scheduler_lock.py`

#### 8C — FastAPI lifecycle integration
- Goal: run APScheduler under FastAPI lifespan when enabled.
- Tasks:
  - Start scheduler in FastAPI lifespan when `SCHEDULER_ENABLED=true` and lock acquired.
  - Gracefully stop scheduler on shutdown and release lock.
  - Update `/api/v2/health` to report `scheduler_running` and `scheduled_jobs_count`.

Implemented:
- Scheduler runtime: `src/fastapi_app/scheduler_runtime.py`
- FastAPI lifespan start/stop: `src/fastapi_app/main.py`
- Health reports scheduler status: `GET /api/v2/health`
- Tests: `tests_fastapi/scheduler/test_scheduler_lifecycle.py`

#### 8D — Job write side-effects wiring
- Goal: ensure job CRUD impacts the scheduler.
- Tasks:
  - On `POST /api/v2/jobs`: schedule job if `is_active=true`.
  - On `PUT /api/v2/jobs/{id}`: reschedule if cron changes; add/remove schedule if `is_active` toggles.
  - On `DELETE /api/v2/jobs/{id}`: remove from scheduler (or disable, matching Flask behavior).
  - Safety: if scheduler is not running in this process (no lock), API still succeeds and only DB state changes.

Implemented:
- Best-effort scheduler helpers: `src/fastapi_app/scheduler_side_effects.py`
- Wired into job write endpoints: `src/fastapi_app/routers/jobs.py` (create/update/delete + bulk upload)
- Tests: `tests_fastapi/scheduler/test_scheduler_side_effects.py`

#### 8E — Scheduler regression tests
- Add scheduler test suite under `tests_fastapi/scheduler/`:
  - Lock/leader election behavior (single runner)
  - Side-effects only when scheduler enabled + leader
  - Timezone correctness (JST cron)
  - No duplicate schedules

Implemented:
- Regression coverage: `tests_fastapi/scheduler/test_scheduler_regression.py`

#### 8G — DB reconciliation / bootstrap (Flask parity)
- Goal: ensure scheduled jobs produce execution rows even after restarts/cutover (no “touch job to schedule” requirement).
- Tasks:
  - On scheduler start (leader-only): resync all DB jobs into APScheduler.
  - Periodically reconcile DB → APScheduler (`SCHEDULER_POLL_SECONDS`, clamped 10–300s).
  - Auto-pause expired jobs during reconciliation (matches Flask’s periodic sync behavior).
  - Provide admin/operator endpoint to trigger resync on-demand.

Implemented:
- Reconcile loop + resync logic: `src/fastapi_app/scheduler_reconcile.py`
- Runtime hooks: `src/fastapi_app/scheduler_runtime.py`
- Admin endpoints:
  - `GET /api/v2/scheduler/status`
  - `POST /api/v2/scheduler/resync`
- Tests: `tests_fastapi/scheduler/test_scheduler_resync.py`

#### 8F — Cutover plan + deprecation

**Goal:** Make FastAPI (`/api/v2`) the default production API and migrate scheduler ownership from Flask → FastAPI safely, with a clear rollback path. This sub-phase is primarily **runbook/documentation** plus a deployment checklist.

##### Cutover Preconditions (Must be true before switching traffic)
- `venv/bin/python -m pytest -q tests_fastapi` is green (CI or locally).
- FastAPI is deployed with the same `SECRET_KEY`/`JWT_SECRET_KEY` as Flask (tokens remain compatible).
- Database URLs are correct:
  - If using a **single shared DB**, ensure both Flask and FastAPI point at the same DB during cutover.
  - If using separate DBs, ensure data migration/replication plan exists (not recommended for cutover).
- Scheduler topology chosen (see “Scheduler Ownership” below) so only **one** scheduler runs.

##### Scheduler Ownership (Recommended Deployment Topology)
APScheduler is started by FastAPI when:
- `SCHEDULER_ENABLED=true` and `TESTING=false`
- the process acquires the scheduler lock

**Important limitation:** the current leader election is a **file lock** (`SCHEDULER_LOCK_PATH`). This only provides single-runner guarantees when all scheduler candidates share the same filesystem path (single host, or shared volume). For multi-node deployments without a shared lock path, prefer a dedicated scheduler instance or migrate to a distributed lock (DB/Redis) later.

Recommended options:
- **Option A (recommended): dedicated scheduler instance**
  - Deploy one FastAPI instance with `SCHEDULER_ENABLED=true`
  - Deploy all other FastAPI instances with `SCHEDULER_ENABLED=false`
  - This avoids relying on a shared lock path across hosts.
- **Option B (single host / shared volume): leader-only via lock**
  - Set `SCHEDULER_ENABLED=true` on all instances
  - Set `SCHEDULER_LOCK_PATH` to a shared location
  - Verify only one instance reports `scheduler_running=true` in `/api/v2/health`

##### Traffic Cutover (API)
Preferred sequence:
1. **Deploy FastAPI** alongside Flask (no traffic change yet).
2. Validate endpoints manually via Swagger:
   - `GET /api/v2/health` (confirm `scheduler_running` as expected for your topology)
   - `POST /api/v2/scheduler/resync` (admin) then re-check `GET /api/v2/health` to confirm `scheduled_jobs_count` is sane
   - Smoke a few critical flows: login, list jobs, create job, update job, execute job.
3. **Switch frontend** to FastAPI:
   - Update frontend `API_BASE` to `/api/v2` (or environment-specific base URL).
4. Keep Flask available for rollback during the observation window.

Optional (later, once stable): proxy `/api/*` → `/api/v2/*` to make v2 the default path without frontend changes. Do this only after you are confident rollback is not needed.

##### Monitoring During Observation Window (Recommended 7 days)
- Health:
  - `GET /api/v2/health` → verify `scheduler_running` and `scheduled_jobs_count` are sane
- Scheduler logs:
  - Confirm only the expected instance is running the scheduler (leader)
  - Watch for repeated lock acquisition failures or rapid restarts
- Business metrics:
  - Job executions continue to be created (`job_executions` table grows)
  - Notifications still delivered (Slack, email if enabled)
- Error budgets:
  - Monitor FastAPI 5xx rate, latency, and auth failures (401/403 spikes)

##### Rollback Plan (FastAPI → Flask)
Rollback should be quick and reversible:
1. Switch frontend back to Flask base (`/api`) or revert proxy to Flask.
2. Disable FastAPI scheduler:
   - Set `SCHEDULER_ENABLED=false` on FastAPI instances (or scale down the scheduler instance).
3. Ensure Flask scheduler is enabled (if rollback requires Flask scheduling):
   - Set `SCHEDULER_ENABLED=true` for Flask (and verify it is running).
4. Validate:
   - `GET /api/health` (Flask) and `GET /api/v2/health` (FastAPI) return expected values.

##### Deprecation Checklist (After Stability Window)
Only after stable operation:
- Freeze Flask endpoints (read-only or stop serving `/api`).
- Remove Flask server runtime from deploy stack.
- Remove Flask-only deps and scripts:
  - `start_server.sh`, `src/app.py`, Flask middleware/config
- Delete or archive legacy Flask tests under `test/` once no longer needed.
- Update README and ops docs to state FastAPI as the only supported runtime.

Implemented (documentation/runbook):
- This section (8F) defines the cutover/rollback/deprecation checklist.

### Validation & Regression
- FastAPI suite (must pass): `venv/bin/python -m pytest -q tests_fastapi`
- Legacy Flask suite (target to pass by Phase 8 end): `venv/bin/python -m pytest -q test`

### Frontend Changes Required

```typescript
// cron-job-frontend: set v2 base URL
// Files:
// - cron-job-frontend/src/services/api/client.ts
// - cron-job-frontend/src/config/env.ts
//
// Example (dev):
// VITE_API_URL=http://localhost:5001/api/v2
```

### Scheduler Refactoring

```python
# Before (Flask)
def execute_job_with_app_context(job_id):
    with _flask_app.app_context():
        execute_job(job_id)

# After (FastAPI)
async def execute_job_async(job_id):
    async with async_session() as session:
        await execute_job(session, job_id)
```

### Deliverables
- [x] Scheduler running under FastAPI lifespan (single runner)
- [x] Scheduler side-effects wired into FastAPI job write endpoints (create/update/delete/enable/disable)
- [x] Cutover/rollback/deprecation runbook documented (Phase 8F)
- [x] Frontend fully migrated to `/api/v2` (cron-job-frontend `VITE_API_URL`)
- [x] Local cutover smoke test completed (FastAPI on `:5001` + frontend on `:5173`)
- [ ] Proxy cutover completed with rollback option
- [ ] Flask code removed after stability window
- [ ] All tests passing (FastAPI suite ✅; legacy Flask suite currently failing locally)

### Notes
```
Local cutover execution (2025-12-24):
- FastAPI started on `http://localhost:5001` via `./start_fastapi.sh` (scheduler enabled; lock: `src/instance/scheduler.lock`)
- Frontend dev points to `VITE_API_URL=http://localhost:5001/api/v2`
- Verified:
  - `GET /api/v2/health` -> `scheduler_running=true`
  - `GET /api/v2/scheduler/status` + `POST /api/v2/scheduler/resync` (admin)
  - `POST /api/v2/auth/login` (admin/admin123)
  - Created PIC team + created job + manual execute -> execution row created

Current local test status:
- FastAPI: `venv/bin/python -m pytest -q tests_fastapi` -> 229 passed
- Flask (legacy): `venv/bin/python -m pytest -q test` -> failing (see pytest output)
```

---

## Final Folder Structure

```
src/
├── app.py                     # Flask app (during migration)
├── database/
│   ├── __init__.py
│   ├── engine.py              # SQLAlchemy engine
│   └── session.py             # Async session factory
├── models/                    # SQLAlchemy models (unchanged)
│   ├── __init__.py
│   ├── job.py
│   ├── user.py
│   ├── job_execution.py
│   ├── notification.py
│   ├── job_category.py
│   ├── pic_team.py
│   ├── slack_settings.py
│   ├── notification_preferences.py
│   └── ui_preferences.py
├── fastapi_app/
│   ├── __init__.py
│   ├── main.py                # FastAPI app entry
│   ├── config.py              # Pydantic Settings
│   ├── dependencies/
│   │   ├── __init__.py
│   │   ├── auth.py
│   │   └── database.py
│   ├── routers/
│   │   ├── __init__.py
│   │   ├── auth.py
│   │   ├── jobs.py
│   │   ├── executions.py
│   │   ├── notifications.py
│   │   ├── taxonomy.py
│   │   ├── taxonomy_write.py
│   │   └── settings.py
│   ├── schemas/
│   │   ├── __init__.py
│   │   └── ...
│   └── utils/
│       ├── __init__.py
│       ├── slack.py
│       └── notifications.py
├── services/                  # Business logic
│   ├── __init__.py
│   └── end_date_maintenance.py
├── scheduler/                 # APScheduler (Phase 8)
│   ├── __init__.py
│   └── job_executor.py
└── utils/                     # Flask utilities (sync)
    ├── __init__.py
    ├── slack.py
    └── ...
```

---

## Risk Mitigation

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| Token incompatibility | High | Low | Use same JWT secret, validate cross-stack before Phase 4 |
| Database conflicts | High | Medium | Single DB, careful session management, test transactions |
| Scheduler race conditions | High | Medium | Keep scheduler on Flask until Phase 8, lock mechanism |
| Frontend breaking | Medium | Low | Version API as `/api/v2/`, gradual frontend switch |
| Test coverage gaps | Medium | Medium | Run `tests_fastapi/` and validate key UI flows |
| Performance regression | Medium | Low | Benchmark before/after migration |

---

## Success Criteria

| Phase | Validation Criteria | Verified |
|-------|---------------------|----------|
| 1 | Both apps respond on respective ports | ✅ |
| 2 | Models import in both Flask and FastAPI | ✅ |
| 3 | Login token works on both stacks | ✅ |
| 4 | Read endpoints return expected shapes (FastAPI) | ✅ |
| 5 | Job CRUD operations work end-to-end (FastAPI) | ✅ |
| 6 | Full auth flow on FastAPI only | ✅ |
| 7 | All Phase 7 endpoints migrated + tested | ✅ |
| 8 | Flask removed, all tests pass | ✅ |

---

## Timeline Summary

| Phase | Description | Duration | Start | End | Status |
|-------|-------------|----------|-------|-----|--------|
| 1 | Project Setup | 2 days | - | - | ✅ |
| 2 | Database & Models | 3 days | - | - | ✅ |
| 3 | Authentication | 4 days | - | - | ✅ |
| 4 | Read-Only Endpoints | 3 days | - | - | ✅ |
| 5 | Jobs CRUD | 5 days | - | - | ✅ |
| 6 | User Management | 4 days | - | - | ✅ |
| 7 | Notifications & Settings | 3 days | - | - | ✅ |
| 8 | Cutover | 6 days | - | - | ✅ |
| **Total** | | **30 days** | | | |

---

## Progress Log

### Week 1
```
<!-- Add daily progress notes -->
```

### Week 2
```
<!-- Add daily progress notes -->
```

### Week 3
```
<!-- Add daily progress notes -->
```

### Week 4
```
<!-- Add daily progress notes -->
```

### Week 5
```
<!-- Add daily progress notes -->
```

### Week 6
```
<!-- Add daily progress notes -->
```

---

## Environment Setup Guide

### Prerequisites

```bash
# Python 3.9+ required
python --version  # Should be 3.9+

# Create virtual environment (if not exists)
python -m venv venv
source venv/bin/activate  # macOS/Linux
```

### Step 1: Install Dependencies

```bash
# Install FastAPI dependencies
pip install -r requirements.txt
```

### Step 2: Run Locally

**Terminal 1 - FastAPI (Port 5001 default):**
```bash
cd /path/to/cron-job-backend
source venv/bin/activate
./start_fastapi.sh
# Or: uvicorn src.fastapi_app.main:app --reload --port 5001
```

### Step 3: Verify

```bash
# FastAPI health check
curl http://localhost:5001/api/v2/health

# FastAPI OpenAPI docs
open http://localhost:5001/docs
```

### Step 4: Proxy Configuration (Optional)

For unified access on port 8000, create `nginx.conf`:

```nginx
upstream flask {
    server 127.0.0.1:5001;
}

upstream fastapi {
    server 127.0.0.1:8001;
}

server {
    listen 8000;

    # FastAPI endpoints (new)
    location /api/v2/ {
        proxy_pass http://fastapi;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    # Flask endpoints (legacy)
    location /api/ {
        proxy_pass http://flask;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    # FastAPI docs
    location /docs {
        proxy_pass http://fastapi;
    }

    location /openapi.json {
        proxy_pass http://fastapi;
    }
}
```

---

## API Contract Appendix

### Standard Response Formats

#### Success Response
```json
{
  "data": { ... },
  "message": "Operation successful"
}
```

#### Error Response
```json
{
  "error": "Error type",
  "message": "Human-readable error message",
  "details": { ... }  // Optional field-level errors
}
```

#### Paginated Response
```json
{
  "items": [ ... ],
  "total": 100,
  "page": 1,
  "per_page": 20,
  "total_pages": 5
}
```

---

### Authentication Endpoints

#### POST `/api/v2/auth/login`

**Request:**
```json
{
  "username": "john_doe",      // OR "email": "john@example.com"
  "password": "secure_password"
}
```

**Response (200):**
```json
{
  "message": "Login successful",
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIs...",
  "user": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "username": "john_doe",
    "email": "john@example.com",
    "role": "user",
    "is_active": true,
    "created_at": "2025-01-15T10:30:00Z",
    "updated_at": "2025-01-15T10:30:00Z"
  }
}
```

**Error (401):**
```json
{
  "error": "Invalid credentials",
  "message": "Invalid email/username or password"
}
```

#### POST `/api/v2/auth/register` (Admin only)

**Request:**
```json
{
  "username": "new_user",
  "email": "new@example.com",
  "password": "secure_password",
  "role": "user"  // Optional, defaults to "viewer"
}
```

**Response (201):**
```json
{
  "message": "User registered successfully",
  "user": {
    "id": "...",
    "username": "new_user",
    "email": "new@example.com",
    "role": "user",
    "is_active": true,
    "created_at": "2025-12-22T10:30:00Z",
    "updated_at": "2025-12-22T10:30:00Z"
  }
}
```

#### POST `/api/v2/auth/refresh`

**Request:**
```json
{
  "refresh_token": "eyJhbGciOiJIUzI1NiIs..."
}
```

**Response (200):**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIs..."
}
```

#### GET `/api/v2/auth/me`

**Headers:** `Authorization: Bearer <access_token>`

**Response (200):**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "username": "john_doe",
  "email": "john@example.com",
  "role": "admin",
  "is_active": true,
  "created_at": "2025-01-15T10:30:00Z",
  "updated_at": "2025-01-15T10:30:00Z"
}
```

---

### Jobs Endpoints

#### GET `/api/v2/jobs`

**Headers:** `Authorization: Bearer <access_token>`

**Notes (Phase 4B):**
- This endpoint intentionally matches Flask v1 response shape for parity testing.
- Pagination/filter/sort query parameters are deferred until Phase 4 stabilization is complete.

**Response (200):**
```json
{
  "count": 1,
  "jobs": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "name": "Daily Backup Job",
      "cron_expression": "0 2 * * *",
      "target_url": null,
      "github_owner": "myorg",
      "github_repo": "myrepo",
      "github_workflow_name": "backup.yml",
      "metadata": {"env": "production"},
      "category": "maintenance",
      "pic_team": "devops",
      "end_date": "2025-12-31",
      "enable_email_notifications": true,
      "notification_emails": ["admin@example.com"],
      "notify_on_success": false,
      "created_by": "user-uuid",
      "is_active": true,
      "created_at": "2025-01-15T10:30:00Z",
      "updated_at": "2025-01-15T10:30:00Z",
      "last_execution_at": "2025-01-15T12:00:00Z",
      "next_execution_at": "2025-12-23T02:00:00+09:00"
    }
  ]
}
```

#### GET `/api/v2/jobs/{id}`

**Headers:** `Authorization: Bearer <access_token>`

**Response (200):**
```json
{
  "job": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "name": "Daily Backup Job",
    "cron_expression": "0 2 * * *",
    "target_url": null,
    "github_owner": "myorg",
    "github_repo": "myrepo",
    "github_workflow_name": "backup.yml",
    "metadata": {"env": "production"},
    "category": "maintenance",
    "pic_team": "devops",
    "end_date": "2025-12-31",
    "enable_email_notifications": true,
    "notification_emails": ["admin@example.com"],
    "notify_on_success": false,
    "created_by": "user-uuid",
    "is_active": true,
    "created_at": "2025-01-15T10:30:00Z",
    "updated_at": "2025-01-15T10:30:00Z",
    "last_execution_at": "2025-01-15T12:00:00Z",
    "next_execution_at": "2025-12-23T02:00:00+09:00"
  }
}
```

### Job Execution Endpoints

#### GET `/api/v2/jobs/{id}/executions`

**Headers:** `Authorization: Bearer <access_token>`

**Query Parameters (optional):**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `limit` | int | 50 | Max executions (max: 200) |
| `status` | string | - | `success|failed|running` (or comma-separated list) |
| `trigger_type` | string | - | `scheduled|manual` |
| `from` | string | - | ISO date/datetime (inclusive, UTC) |
| `to` | string | - | ISO date/datetime (exclusive, UTC). Date-only treated as inclusive day |

**Response (200):**
```json
{
  "job_id": "job-uuid",
  "job_name": "Daily Backup Job",
  "total_executions": 2,
  "executions": [
    {
      "id": "exec-uuid",
      "job_id": "job-uuid",
      "status": "success",
      "trigger_type": "manual",
      "started_at": "2025-01-15T12:00:00Z",
      "completed_at": "2025-01-15T12:00:10Z",
      "duration_seconds": 10.0,
      "execution_type": "github_actions",
      "target": "owner/repo/actions/workflows/backup.yml",
      "response_status": 204,
      "error_message": null,
      "output": null
    }
  ]
}
```

#### GET `/api/v2/jobs/{id}/executions/{execution_id}`

**Headers:** `Authorization: Bearer <access_token>`

**Response (200):**
```json
{
  "job": { "id": "job-uuid", "name": "Daily Backup Job" },
  "execution": {
    "id": "exec-uuid",
    "job_id": "job-uuid",
    "status": "failed",
    "trigger_type": "scheduled",
    "started_at": "2025-01-15T12:00:00Z",
    "completed_at": "2025-01-15T12:00:10Z",
    "duration_seconds": 10.0,
    "execution_type": "webhook",
    "target": "https://api.example.com/webhook",
    "response_status": 500,
    "error_message": "Request failed",
    "output": null
  }
}
```

#### GET `/api/v2/jobs/{id}/executions/stats`

**Headers:** `Authorization: Bearer <access_token>`

**Response (200):**
```json
{
  "job_id": "job-uuid",
  "job_name": "Daily Backup Job",
  "statistics": {
    "total_executions": 10,
    "success_count": 8,
    "failed_count": 2,
    "running_count": 0,
    "success_rate": 80.0,
    "average_duration_seconds": 12.34
  },
  "latest_execution": {
    "id": "exec-uuid",
    "job_id": "job-uuid",
    "status": "success",
    "trigger_type": "manual",
    "started_at": "2025-01-15T12:00:00Z"
  }
}
```

#### POST `/api/v2/jobs`

**Request:**
```json
{
  "name": "Daily Backup Job",
  "cron_expression": "0 2 * * *",
  "category": "maintenance",
  "pic_team": "devops",
  "end_date": "2025-12-31",
  
  // GitHub Actions (Option A)
  "github_owner": "myorg",
  "github_repo": "myrepo",
  "github_workflow_name": "backup.yml",
  
  // OR Webhook (Option B)
  "target_url": "https://api.example.com/webhook",
  
  // Optional
  "metadata": {"env": "production", "priority": "high"},
  "enable_email_notifications": true,
  "notification_emails": ["admin@example.com", "ops@example.com"],
  "notify_on_success": false,
  "is_active": true
}
```

**Response (201):**
```json
{
  "message": "Job created successfully",
  "job": { ... }
}
```

#### PUT `/api/v2/jobs/{id}`

**Request:** Same as POST, all fields optional (partial update)

**Response (200):**
```json
{
  "message": "Job updated successfully",
  "job": { ... }
}
```

#### DELETE `/api/v2/jobs/{id}`

**Response (200):**
```json
{
  "message": "Job deleted successfully"
}
```

#### POST `/api/v2/jobs/{id}/execute`

**Request (optional):**
```json
{
  "inputs": {"key": "value"}  // Optional workflow inputs
}
```

**Response (200):**
```json
{
  "message": "Job triggered successfully",
  "execution": {
    "id": "exec-uuid",
    "job_id": "job-uuid",
    "status": "running",
    "trigger_type": "manual",
    "started_at": "2025-12-22T10:30:00Z"
  }
}
```

#### POST `/api/v2/jobs/bulk-upload`

**Request:** `multipart/form-data` with CSV file

**CSV Format:**
```csv
name,cron_expression,category,pic_team,end_date,github_owner,github_repo,github_workflow_name,status
Job 1,0 0 * * *,maintenance,devops,2025-12-31,myorg,repo1,workflow.yml,enable
Job 2,0 6 * * 1,reports,analytics,2025-12-31,myorg,repo2,report.yml,enable
```

**Response (200):**
```json
{
  "message": "Bulk upload completed",
  "created": 5,
  "updated": 3,
  "failed": 1,
  "errors": [
    {"row": 7, "name": "Bad Job", "error": "Invalid cron expression"}
  ],
  "stats": {
    "original_row_count": 9,
    "removed_empty_row_count": 0
  }
}
```

---

### Cron Utility Endpoints

#### POST `/api/v2/jobs/validate-cron`

**Request:**
```json
{
  "cron_expression": "0 2 * * *"
}
```

**Response (200):**
```json
{
  "valid": true,
  "cron_expression": "0 2 * * *",
  "description": "At 02:00 AM every day"
}
```

**Response (400):**
```json
{
  "valid": false,
  "error": "Cron expression must have exactly 5 fields"
}
```

#### POST `/api/v2/jobs/cron-preview`

**Request:**
```json
{
  "cron_expression": "0 2 * * *",
  "count": 5
}
```

**Response (200):**
```json
{
  "cron_expression": "0 2 * * *",
  "next_runs": [
    "2025-12-23T02:00:00+09:00",
    "2025-12-24T02:00:00+09:00",
    "2025-12-25T02:00:00+09:00",
    "2025-12-26T02:00:00+09:00",
    "2025-12-27T02:00:00+09:00"
  ],
  "timezone": "Asia/Tokyo"
}
```

---

### Executions Endpoints

#### GET `/api/v2/executions`

**Headers:** `Authorization: Bearer <access_token>`

**Query Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `page` | int | 1 | Page number |
| `limit` | int | 20 | Page size (max: 200) |
| `job_id` | uuid | - | Filter by job id |
| `status` | string | - | `success|failed|running` (or comma-separated list) |
| `trigger_type` | string | - | `scheduled|manual` |
| `execution_type` | string | - | `github_actions|webhook` |
| `from` | string | - | ISO date/datetime (inclusive, UTC) |
| `to` | string | - | ISO date/datetime (exclusive, UTC). Date-only treated as inclusive day |

**Response (200):**
```json
{
  "executions": [
    {
      "id": "exec-uuid",
      "job_id": "job-uuid",
      "job_name": "Daily Backup Job",
      "github_repo": "myrepo",
      "status": "success",
      "trigger_type": "scheduled",
      "started_at": "2025-12-22T02:00:00Z",
      "completed_at": "2025-12-22T02:00:15Z",
      "duration_seconds": 15.234,
      "execution_type": "github_actions",
      "target": "myorg/myrepo/backup.yml",
      "response_status": 204,
      "error_message": null
    }
  ],
  "total": 1250,
  "page": 1,
  "limit": 20,
  "total_pages": 63
}
```

#### GET `/api/v2/executions/{execution_id}`

**Headers:** `Authorization: Bearer <access_token>`

**Response (200):**
```json
{
  "execution": {
    "id": "exec-uuid",
    "job_id": "job-uuid",
    "job_name": "Daily Backup Job",
    "github_repo": "myrepo",
    "status": "success",
    "trigger_type": "scheduled",
    "started_at": "2025-12-22T02:00:00Z",
    "completed_at": "2025-12-22T02:00:15Z",
    "duration_seconds": 15.234,
    "execution_type": "github_actions",
    "target": "myorg/myrepo/backup.yml",
    "response_status": 204,
    "error_message": null
  }
}
```

#### GET `/api/v2/executions/statistics`

**Query Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `job_id` | uuid | Optional: filter by job |
| `from` | string | Optional: ISO date/datetime (inclusive) |
| `to` | string | Optional: ISO date/datetime (exclusive). Date-only treated as inclusive day |

**Response (200):**
```json
{
  "total_executions": 1250,
  "successful_executions": 1180,
  "failed_executions": 65,
  "running_executions": 5,
  "success_rate": 94.4,
  "average_duration_seconds": 12.5,
  "range": {
    "from": "2025-12-01T00:00:00Z",
    "to": "2025-12-23T00:00:00Z"
  }
}
```

---

### Notifications Endpoints

#### GET `/api/v2/notifications`

**Query Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `page` | int | 1 | Page number |
| `per_page` | int | 20 | Items per page (max: 100) |
| `unread_only` | bool | false | Only unread notifications |
| `from` | string | - | ISO date/datetime (inclusive). Accepts `YYYY-MM-DD` |
| `to` | string | - | ISO date/datetime (exclusive). Date-only treated as inclusive day |

**Response (200):**
```json
{
  "notifications": [
    {
      "id": "notif-uuid",
      "user_id": "user-uuid",
      "title": "Job Failed",
      "message": "Job 'Daily Backup' failed with error: Connection timeout",
      "type": "error",
      "related_job_id": "job-uuid",
      "related_execution_id": "exec-uuid",
      "is_read": false,
      "read_at": null,
      "created_at": "2025-12-22T10:30:00Z"
    }
  ],
  "total": 45,
  "page": 1,
  "per_page": 20,
  "total_pages": 3,
  "range": {
    "from": "2025-12-01T00:00:00",
    "to": "2025-12-23T00:00:00"
  }
}
```

#### GET `/api/v2/notifications/unread-count`

**Query Parameters (optional):**
| Parameter | Type | Description |
|-----------|------|-------------|
| `from` | string | ISO date/datetime (inclusive). Accepts `YYYY-MM-DD` |
| `to` | string | ISO date/datetime (exclusive). Date-only treated as inclusive day |

**Response (200):**
```json
{
  "unread_count": 12,
  "range": {
    "from": "2025-12-01T00:00:00",
    "to": "2025-12-23T00:00:00"
  }
}
```

---

### Categories & Teams Endpoints

Read endpoints were migrated in Phase 4E; write endpoints were added in Phase 7E/7F.

#### GET `/api/v2/job-categories`

**Headers:** `Authorization: Bearer <access_token>`

**Query Parameters (optional):**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `include_inactive` | bool | false | Admin-only: include inactive categories |

**Response (200):**
```json
{
  "categories": [
    {
      "id": "cat-uuid",
      "slug": "maintenance",
      "name": "Maintenance Jobs",
      "is_active": true,
      "created_at": "2025-01-15T10:30:00Z",
      "updated_at": "2025-01-15T10:30:00Z"
    }
  ]
}
```

#### POST `/api/v2/job-categories`

**Status:** ✅ Implemented (Phase 7E)

**Request:**
```json
{
  "name": "Analytics Jobs",
  "slug": "analytics"
}
```

**Response (201):**
```json
{
  "message": "Category created",
  "category": {
    "id": "cat-uuid",
    "slug": "analytics",
    "name": "Analytics Jobs",
    "is_active": true,
    "created_at": "2025-01-15T10:30:00Z",
    "updated_at": "2025-01-15T10:30:00Z"
  }
}
```

#### PUT `/api/v2/job-categories/{id}` (Admin only)

**Response (200):**
```json
{
  "message": "Category updated",
  "category": {
    "id": "cat-uuid",
    "slug": "analytics-jobs",
    "name": "Analytics Jobs",
    "is_active": true,
    "created_at": "2025-01-15T10:30:00Z",
    "updated_at": "2025-01-15T10:30:00Z"
  },
  "jobs_updated": 3
}
```

#### DELETE `/api/v2/job-categories/{id}` (Admin only)

**Response (200):**
```json
{
  "message": "Category disabled",
  "category": {
    "id": "cat-uuid",
    "slug": "analytics-jobs",
    "name": "Analytics Jobs",
    "is_active": false,
    "created_at": "2025-01-15T10:30:00Z",
    "updated_at": "2025-01-15T10:30:00Z"
  }
}
```

#### GET `/api/v2/pic-teams`

**Headers:** `Authorization: Bearer <access_token>`

**Query Parameters (optional):**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `include_inactive` | bool | false | Admin-only: include inactive PIC teams |

**Response (200):**
```json
{
  "pic_teams": [
    {
      "id": "team-uuid",
      "slug": "devops",
      "name": "DevOps Team",
      "slack_handle": "@devops-team",
      "is_active": true,
      "created_at": "2025-01-15T10:30:00Z",
      "updated_at": "2025-01-15T10:30:00Z"
    }
  ]
}
```

#### POST `/api/v2/pic-teams`

**Status:** ✅ Implemented (Phase 7F)

**Request:**
```json
{
  "name": "QA Team",
  "slug": "qa",
  "slack_handle": "@qa-team"
}
```

**Response (201):**
```json
{
  "message": "PIC team created",
  "pic_team": {
    "id": "team-uuid",
    "slug": "qa",
    "name": "QA Team",
    "slack_handle": "@qa-team",
    "is_active": true,
    "created_at": "2025-01-15T10:30:00Z",
    "updated_at": "2025-01-15T10:30:00Z"
  }
}
```

#### PUT `/api/v2/pic-teams/{id}` (Admin only)

**Response (200):**
```json
{
  "message": "PIC team updated",
  "pic_team": {
    "id": "team-uuid",
    "slug": "qa-team",
    "name": "QA Team",
    "slack_handle": "@qa-team",
    "is_active": true,
    "created_at": "2025-01-15T10:30:00Z",
    "updated_at": "2025-01-15T10:30:00Z"
  },
  "jobs_updated": 2
}
```

#### DELETE `/api/v2/pic-teams/{id}` (Admin only)

**Response (200):**
```json
{
  "message": "PIC team disabled",
  "pic_team": {
    "id": "team-uuid",
    "slug": "qa-team",
    "name": "QA Team",
    "slack_handle": "@qa-team",
    "is_active": false,
    "created_at": "2025-01-15T10:30:00Z",
    "updated_at": "2025-01-15T10:30:00Z"
  }
}
```

---

### Settings Endpoints

#### GET `/api/v2/settings/slack` (Admin only)

**Response (200):**
```json
{
  "slack_settings": {
    "id": "settings-uuid",
    "is_enabled": true,
    "webhook_url": "https://hooks.slack.com/services/...",
    "channel": "#cron-alerts",
    "created_at": "2025-01-15T10:30:00Z",
    "updated_at": "2025-01-15T10:30:00Z"
  }
}
```

#### PUT `/api/v2/settings/slack` (Admin only)

**Request:**
```json
{
  "is_enabled": true,
  "webhook_url": "https://hooks.slack.com/services/...",
  "channel": "#cron-alerts"
}
```

**Response (200):**
```json
{
  "message": "Slack settings updated",
  "slack_settings": {
    "id": "settings-uuid",
    "is_enabled": true,
    "webhook_url": "https://hooks.slack.com/services/...",
    "channel": "#cron-alerts",
    "created_at": "2025-01-15T10:30:00Z",
    "updated_at": "2025-01-15T10:30:00Z"
  }
}
```

---

## Validation Rules Reference

### User Fields

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| `username` | string | Yes | 3-80 chars, unique, alphanumeric + underscore |
| `email` | string | Yes | Valid email format, unique, max 120 chars |
| `password` | string | Yes | Min 6 chars |
| `role` | enum | No | `admin`, `user`, `viewer` (default: `viewer`) |
| `is_active` | bool | No | Default: `true` |

### Job Fields

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| `name` | string | Yes | 1-255 chars, unique |
| `cron_expression` | string | Yes | Valid 5-field cron (minute hour day month dow) |
| `category` | string | Yes | Must exist in `job_categories` |
| `pic_team` | string | Yes | Must exist in `pic_teams` |
| `end_date` | date | Yes | Format: `YYYY-MM-DD`, must be future date |
| `target_url` | string | No* | Valid HTTPS URL, max 500 chars |
| `github_owner` | string | No* | 1-255 chars |
| `github_repo` | string | No* | 1-255 chars |
| `github_workflow_name` | string | No* | 1-255 chars, must end with `.yml` or `.yaml` |
| `metadata` | object | No | Valid JSON object |
| `enable_email_notifications` | bool | No | Default: `false` |
| `notification_emails` | array | No | List of valid email addresses |
| `notify_on_success` | bool | No | Default: `false` |
| `is_active` | bool | No | Default: `true` |

*Either `target_url` OR all three GitHub fields (`github_owner`, `github_repo`, `github_workflow_name`) must be provided.

### Cron Expression Rules

| Field | Position | Valid Values |
|-------|----------|--------------|
| Minute | 1 | 0-59, *, */N |
| Hour | 2 | 0-23, *, */N |
| Day of Month | 3 | 1-31, *, */N |
| Month | 4 | 1-12, *, */N |
| Day of Week | 5 | 0-6 (Sun=0), *, */N |

**Timezone:** All cron expressions are interpreted in `Asia/Tokyo` (JST) unless configured otherwise.

### Category & Team Fields

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| `name` | string | Yes | 1-255 chars |
| `slug` | string | No | 1-100 chars, lowercase, alphanumeric + hyphen, unique |
| `slack_handle` | string | No | Max 255 chars (teams only) |
| `is_active` | bool | No | Default: `true` |

---

## Testing Checklist

### Phases 1–3: Automated FastAPI Test Coverage

| Phase | Area | Tests | Status |
|------:|------|-------|--------|
| 1 | App bootstrap + health + OpenAPI smoke | `tests_fastapi/core/test_health.py` | ✅ |
| 2 | Async DB session + model compatibility | `tests_fastapi/database/test_async_session.py` | ✅ |
| 3 | Auth flows + cross-stack JWT | `tests_fastapi/auth/*` | ✅ |

### Phase 4: Automated FastAPI Endpoint Coverage

| Sub-phase | Area | Tests | Status |
|----------:|------|-------|--------|
| 4B | Jobs (read) | `tests_fastapi/jobs/test_jobs_read.py` | ✅ |
| 4C | Job executions (read) | `tests_fastapi/executions/test_job_executions_read.py` | ✅ |
| 4D | Executions (read) | `tests_fastapi/executions/test_executions_global_read.py` | ✅ |
| 4E | Taxonomy (read) | `tests_fastapi/taxonomy/test_taxonomy_read.py` | ✅ |

Run the FastAPI-only suite:
```bash
venv/bin/python -m pytest -q tests_fastapi
```

### Phase 3: Cross-Stack Token Compatibility

| Test Case | Expected Result | Status |
|-----------|-----------------|--------|
| Login via Flask → Use token on FastAPI | Token accepted, user data returned | ✅ |
| Login via FastAPI → Use token on Flask | Token accepted, user data returned | ✅ |
| Expired token on FastAPI | 401 Unauthorized | ✅ |
| Invalid token on FastAPI | 401 Unauthorized | ✅ |
| Admin token → Admin-only endpoint | Access granted | ✅ |
| User token → Admin-only endpoint | 403 Forbidden | ✅ |
| Viewer token → Write endpoint | 403 Forbidden | ✅ |

### Phase 4: Response Parity Tests

Automated tests cover response **shape** and auth enforcement for all Phase 4 endpoints. Use the curl/jq workflow below if you want to validate **cross-stack response parity** against a running Flask + FastAPI instance.

For each read-only endpoint, compare Flask and FastAPI responses:

```bash
# Example parity test script
flask_response=$(curl -s http://localhost:5001/api/jobs -H "Authorization: Bearer $TOKEN")
fastapi_response=$(curl -s http://localhost:8001/api/v2/jobs -H "Authorization: Bearer $TOKEN")

# Compare (ignoring order, timestamps may differ slightly)
diff <(echo "$flask_response" | jq -S '.jobs | sort_by(.id)') \
     <(echo "$fastapi_response" | jq -S '.jobs | sort_by(.id)')
```

| Endpoint | Parity Verified | Notes |
|----------|-----------------|-------|
| GET /jobs | ⬜ | Check pagination, filters |
| GET /jobs/{id} | ⬜ | |
| GET /jobs/{id}/executions | ⬜ | |
| GET /jobs/{id}/executions/{execution_id} | ⬜ | |
| GET /jobs/{id}/executions/stats | ⬜ | |
| GET /executions | ⬜ | Check pagination, filters |
| GET /executions/{execution_id} | ⬜ | |
| GET /executions/statistics | ⬜ | |
| GET /job-categories | ⬜ | |
| GET /pic-teams | ⬜ | |

### Phase 5: Write Operation Tests

| Test Case | Expected Result | Status |
|-----------|-----------------|--------|
| Create job with valid data | 201, job created | ✅ |
| Create job with invalid cron | 400, validation error | ✅ |
| Create job with duplicate name | 400, duplicate name error | ✅ |
| Update job as owner | 200, job updated | ✅ |
| Update job as non-owner (non-admin) | 403, forbidden | ✅ |
| Delete job as admin | 200, job deleted | ✅ |
| Execute job → Check execution created | `JobExecution` row created/updated | ✅ |
| Bulk upload valid CSV | 200, `created_count` > 0 | ✅ |
| Bulk upload invalid CSV rows | 200, partial success with row errors | ✅ |
| Bulk upload invalid CSV structure | 400, invalid CSV | ✅ |
| Cron validate | 200 with `valid=true/false` | ✅ |
| Cron preview | 200 next runs; invalid cron returns 400 | ✅ |
| Test-run | 200 with `{ok,type,status_code}` (GitHub missing token yields `ok=false`) | ✅ |

### Phase 7: Notifications & Settings Tests

| Sub-phase | Area | Tests | Status |
|----------:|------|-------|--------|
| 7A | Notifications (read) | `tests_fastapi/notifications/test_notifications_read.py` | ✅ |
| 7B | Notifications (mark read) | `tests_fastapi/notifications/test_notifications_mark_read.py` | ✅ |
| 7C | Notifications (delete) | `tests_fastapi/notifications/test_notifications_delete.py` | ✅ |
| 7D | Slack settings | `tests_fastapi/settings/test_slack_settings.py` | ✅ |
| 7E | Job categories (write) | `tests_fastapi/taxonomy_write/test_job_categories_write.py` | ✅ |
| 7F | PIC teams (write) | `tests_fastapi/taxonomy_write/test_pic_teams_write.py` | ✅ |
| 7G | Utilities | `tests_fastapi/utils/*` | ✅ |

### Phase 8: Scheduler Tests

| Test Case | Expected Result | Status |
|-----------|-----------------|--------|
| Create job → Appears in APScheduler | Job scheduled | ⬜ |
| Update cron → Schedule updated | Next run time changed | ⬜ |
| Disable job → Removed from scheduler | No longer scheduled | ⬜ |
| Job executes at scheduled time | Execution recorded | ⬜ |
| Job past end_date → Auto-paused | is_active = false | ⬜ |
| Failed execution → Notification created | Notification in DB | ⬜ |
| Failed execution → Email sent | Email received | ⬜ |
| Failed execution → Slack message | Slack message posted | ⬜ |

---

## Rollback Procedures

### Scenario 1: FastAPI Endpoint Bug (During Dual-Stack)

**Symptoms:** FastAPI endpoint returns incorrect data or errors.

**Rollback Steps:**
1. Frontend is still using Flask (`/api/`), so no user impact
2. Fix the FastAPI endpoint
3. Run parity tests again before proceeding

**No action needed for users.**

---

### Scenario 2: Database Corruption (During Migration)

**Symptoms:** Data integrity issues, foreign key violations.

**Rollback Steps:**
```bash
# 1. Stop FastAPI server
pkill -f "uvicorn"

# 2. Restore database from backup
cp src/instance/cron_jobs.db.backup src/instance/cron_jobs.db

# 3. Restart FastAPI
./start_fastapi.sh
```

**Prevention:** Take database backup before each phase:
```bash
cp src/instance/cron_jobs.db src/instance/cron_jobs.db.backup_phase_N
```

---

### Scenario 3: Scheduler Race Condition

**Symptoms:** Jobs executing twice, or not executing at all.

**Rollback Steps:**
1. Keep scheduler on Flask (Phase 8 not started)
2. Verify scheduler lock file: `src/instance/scheduler.lock`
3. Kill any duplicate processes:
   ```bash
   ps aux | grep -E "flask|uvicorn" | grep -v grep
   # Kill duplicates manually
   ```

**Prevention:** Only run scheduler on ONE process until Phase 8 complete.

---

### Scenario 4: Full Migration Failure (Phase 8)

**Symptoms:** FastAPI not stable enough to replace Flask.

**Rollback Steps:**
```bash
# 1. Revert frontend API base URL
# In cron-job-frontend, set VITE_API_URL back to Flask, e.g.:
#   VITE_API_URL=http://localhost:5001/api
# Files:
# - cron-job-frontend/.env.development
# - cron-job-frontend/.env.production

# 2. Rebuild and redeploy frontend
cd cron-job-frontend
npm run build

# 3. Stop FastAPI, keep Flask running
pkill -f "uvicorn"

# 4. Update proxy to route all traffic to Flask
# Remove /api/v2 → FastAPI routing

# 5. Keep FastAPI code for future attempt
# Don't delete - just don't route to it
```

---

### Scenario 5: Token Incompatibility

**Symptoms:** Users logged in via Flask can't access FastAPI, or vice versa.

**Diagnosis:**
```bash
# Decode token and verify claims
python -c "
from jose import jwt
token = 'YOUR_TOKEN_HERE'
secret = 'YOUR_JWT_SECRET'
print(jwt.decode(token, secret, algorithms=['HS256']))
"
```

**Fix:**
1. Ensure both apps use identical `JWT_SECRET_KEY`
2. Ensure both apps expect same claim structure (`sub`, `role`, `email`)
3. Check token expiry settings match

---

## Database Migration Notes

### Sync vs Async Sessions

**Flask (Sync):**
```python
from src.models import db

def get_user(user_id):
    return User.query.get(user_id)  # Sync

with app.app_context():
    user = get_user("uuid")
```

**FastAPI (Async):**
```python
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

async def get_user(session: AsyncSession, user_id: str):
    result = await session.execute(
        select(User).where(User.id == user_id)
    )
    return result.scalar_one_or_none()

async with async_session() as session:
    user = await get_user(session, "uuid")
```

### Session Dependency for FastAPI

```python
# src/fastapi_app/dependencies/database.py
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

DATABASE_URL = "sqlite+aiosqlite:///./src/instance/cron_jobs.db"

engine = create_async_engine(DATABASE_URL, echo=False)
async_session_maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
```

### Using in Routes

```python
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from ..dependencies.database import get_db

@router.get("/jobs/{job_id}")
async def get_job(job_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Job).where(Job.id == job_id))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job
```

### Critical: Shared Database Access

During dual-stack operation, both Flask and FastAPI access the same SQLite file:

1. **SQLite Limitations:** SQLite has limited concurrent write support
2. **Mitigation:** Use `check_same_thread=False`; for async SQLite, prefer `NullPool` to avoid thread/connection reuse issues
3. **Production:** Migrate to MySQL/PostgreSQL before heavy load

```python
# For SQLite during migration
from sqlalchemy.pool import NullPool

engine = create_async_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=NullPool,
)
```

---

## References

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [SQLAlchemy 2.0 Async](https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html)
- [Pydantic V2](https://docs.pydantic.dev/latest/)
- [PyJWT](https://pyjwt.readthedocs.io/)
- [passlib](https://passlib.readthedocs.io/)
- [APScheduler with FastAPI](https://apscheduler.readthedocs.io/)
- [aiosqlite](https://aiosqlite.omnilib.dev/)

---

*Last Updated: December 23, 2025*
