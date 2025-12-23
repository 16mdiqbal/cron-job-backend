# Flask to FastAPI Migration Plan

> **Project:** cron-job-backend  
> **Migration Type:** Gradual (Side-by-Side)  
> **Created:** December 21, 2025  
> **Estimated Duration:** 30 working days (~6 weeks)

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
| `Flask-Mail` | TBD (Phase 7) | Keep Flask-Mail until notifications/settings migrate |
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
- Flask health check: http://localhost:5001/api/health ✅
- FastAPI health check: http://localhost:8001/api/v2/health ✅
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

### Status: ⏳ Planned (split into sub-phases)

### Objective
Migrate job creation, update, and deletion with full validation.

### Scope (Confirmed)

- **DB-first (no scheduler side-effects):** FastAPI write endpoints will **not** add/reschedule/remove APScheduler jobs. Scheduler wiring stays in **Phase 8**.
- **Manual execute is allowed:** `POST /jobs/{id}/execute` can trigger an on-demand run (like Flask), but does not alter background schedules.
- **No Flask changes:** Flask remains the source of truth for background scheduling during this phase.

### Endpoints to Migrate

| # | Flask Endpoint | FastAPI Endpoint | Complexity | Status |
|---|----------------|------------------|------------|--------|
| 1 | `POST /api/jobs` | `POST /api/v2/jobs` | High | ⬜ |
| 2 | `PUT /api/jobs/<id>` | `PUT /api/v2/jobs/{id}` | High | ⬜ |
| 3 | `DELETE /api/jobs/<id>` | `DELETE /api/v2/jobs/{id}` | Medium | ⬜ |
| 4 | `POST /api/jobs/<id>/execute` | `POST /api/v2/jobs/{id}/execute` | High | ⬜ |
| 5 | `POST /api/jobs/bulk-upload` | `POST /api/v2/jobs/bulk-upload` | High | ⬜ |
| 6 | `POST /api/jobs/validate-cron` | `POST /api/v2/jobs/validate-cron` | Low | ⬜ |
| 7 | `POST /api/jobs/cron-preview` | `POST /api/v2/jobs/cron-preview` | Low | ⬜ |
| 8 | `POST /api/jobs/test-run` | `POST /api/v2/jobs/test-run` | Medium | ⬜ |

### Sub-Phases (Execution Order)

| Sub-Phase | Goal | Endpoints | Primary Test Location |
|----------:|------|-----------|------------------------|
| **5A** | Job create (validation + RBAC) | `POST /api/v2/jobs` | `tests_fastapi/jobs_write/test_create.py` |
| **5B** | Job update (partial update + ownership rules) | `PUT /api/v2/jobs/{id}` | `tests_fastapi/jobs_write/test_update.py` |
| **5C** | Job delete (parity behavior + RBAC) | `DELETE /api/v2/jobs/{id}` | `tests_fastapi/jobs_write/test_delete.py` |
| **5D** | Manual execute (execution record + trigger) | `POST /api/v2/jobs/{id}/execute` | `tests_fastapi/jobs_write/test_execute.py` |
| **5E** | Bulk CSV upload (validation + partial success) | `POST /api/v2/jobs/bulk-upload` | `tests_fastapi/jobs_write/test_bulk_upload.py` |
| **5F** | Cron utilities | `POST /api/v2/jobs/validate-cron`, `POST /api/v2/jobs/cron-preview`, `POST /api/v2/jobs/test-run` | `tests_fastapi/cron_tools/*` |

### Implementation Notes (Guidelines)

- Prefer adding write endpoints to the existing Jobs router (or a separate `jobs_write.py` router under the **Jobs** tag) while keeping read endpoints stable.
- Keep **response shapes** consistent with Flask where feasible (especially error keys like `error` + `message`), so frontend parity is predictable.
- Ensure all DB writes are done via async SQLAlchemy sessions (`src/database/session.py`).
- Avoid external calls in tests:
  - Stub/mocks for webhook/GitHub calls.
  - For manual execute, assert **execution rows** created and that the trigger function is called, without leaving the process.

### Test Strategy (Must-Haves)

- **RBAC matrix** for each endpoint:
  - `admin`: allowed
  - `user`: allowed on own jobs; forbidden for other users where applicable
  - `viewer`: forbidden for all write endpoints
- **Validation coverage**:
  - Required fields (`name`, `cron_expression`, `category`, `pic_team`, `end_date`)
  - Target config: webhook vs GitHub fields (mutual requirements)
  - Duplicate name conflict behavior
  - Date range/cutoffs (`end_date` must be future)
- **Side-effect boundaries**:
  - Verify FastAPI does **not** register APScheduler jobs (no scheduler manipulation in Phase 5).
  - Manual execute should not persist scheduler state changes.

### Deliverables
- [ ] Phase 5A–5F endpoints implemented and documented
- [ ] FastAPI tests added for each sub-phase and passing (`venv/bin/python -m pytest -q tests_fastapi`)
- [ ] No APScheduler add/reschedule/remove logic in FastAPI (Phase 8 responsibility)
- [ ] RBAC + validation coverage complete for write flows

### Notes
```
<!-- Add implementation notes here -->
```

---

## Phase 6: Auth & User Management (Days 18-21)

### Status: 🟨 Partially Complete (core auth ✅, user management pending)

### Objective
Complete user management + preference endpoints that are not covered by Phase 3.

### Endpoints to Migrate

| # | Flask Endpoint | FastAPI Endpoint | Auth | Status |
|---|----------------|------------------|------|--------|
| 1 | `POST /api/auth/login` | `POST /api/v2/auth/login` | None | ✅ |
| 2 | `POST /api/auth/refresh` | `POST /api/v2/auth/refresh` | Refresh | ✅ |
| 3 | `POST /api/auth/register` | `POST /api/v2/auth/register` | Admin | ✅ |
| 4 | `GET /api/auth/me` | `GET /api/v2/auth/me` | JWT | ✅ |
| 5 | `GET /api/auth/users` | `GET /api/v2/auth/users` | Admin | ⬜ |
| 6 | `GET /api/auth/users/<id>` | `GET /api/v2/auth/users/{id}` | JWT | ⬜ |
| 7 | `PUT /api/auth/users/<id>` | `PUT /api/v2/auth/users/{id}` | JWT | ⬜ |
| 8 | `DELETE /api/auth/users/<id>` | `DELETE /api/v2/auth/users/{id}` | Admin | ⬜ |
| 9 | `GET /api/auth/users/<id>/preferences` | `GET /api/v2/auth/users/{id}/preferences` | JWT | ⬜ |
| 10 | `PUT /api/auth/users/<id>/preferences` | `PUT /api/v2/auth/users/{id}/preferences` | JWT | ⬜ |
| 11 | `GET /api/auth/users/<id>/ui-preferences` | `GET /api/v2/auth/users/{id}/ui-preferences` | JWT | ⬜ |
| 12 | `PUT /api/auth/users/<id>/ui-preferences` | `PUT /api/v2/auth/users/{id}/ui-preferences` | JWT | ⬜ |

### Tasks

- [x] `src/fastapi_app/routers/auth.py` (login/refresh/register/me/logout/verify)
- [x] Password hashing remains `passlib.hash.pbkdf2_sha256` via `src/models/user.py`
- [ ] Add user management endpoints (`/users`, `/users/{id}`)
- [ ] Add preference endpoints (`/users/{id}/preferences`, `/users/{id}/ui-preferences`)
- [ ] Implement user self-update restrictions
- [ ] Add admin-only protections

### Deliverables
- [ ] Full auth flow on FastAPI
- [ ] User management CRUD
- [ ] Preference management
- [ ] Password change working

### Notes
```
<!-- Add implementation notes here -->
```

---

## Phase 7: Notifications & Settings (Days 22-24)

### Status: ⬜ Not Started

### Objective
Complete remaining endpoints and utilities.

### Endpoints to Migrate

| # | Flask Endpoint | FastAPI Endpoint | Status |
|---|----------------|------------------|--------|
| 1 | `GET /api/notifications` | `GET /api/v2/notifications` | ⬜ |
| 2 | `GET /api/notifications/unread-count` | `GET /api/v2/notifications/unread-count` | ⬜ |
| 3 | `PUT /api/notifications/<id>/read` | `PUT /api/v2/notifications/{id}/read` | ⬜ |
| 4 | `PUT /api/notifications/read-all` | `PUT /api/v2/notifications/read-all` | ⬜ |
| 5 | `DELETE /api/notifications/<id>` | `DELETE /api/v2/notifications/{id}` | ⬜ |
| 6 | `DELETE /api/notifications/read` | `DELETE /api/v2/notifications/read` | ⬜ |
| 7 | `GET /api/settings/slack` | `GET /api/v2/settings/slack` | ⬜ |
| 8 | `PUT /api/settings/slack` | `PUT /api/v2/settings/slack` | ⬜ |
| 9 | `POST /api/job-categories` | `POST /api/v2/job-categories` | ⬜ |
| 10 | `PUT /api/job-categories/<id>` | `PUT /api/v2/job-categories/{id}` | ⬜ |
| 11 | `DELETE /api/job-categories/<id>` | `DELETE /api/v2/job-categories/{id}` | ⬜ |
| 12 | `POST /api/pic-teams` | `POST /api/v2/pic-teams` | ⬜ |
| 13 | `PUT /api/pic-teams/<id>` | `PUT /api/v2/pic-teams/{id}` | ⬜ |
| 14 | `DELETE /api/pic-teams/<id>` | `DELETE /api/v2/pic-teams/{id}` | ⬜ |

### Tasks

- [ ] Create `src/fastapi_app/routers/notifications.py`
- [ ] Create `src/fastapi_app/routers/settings.py`
- [ ] Implement pagination for notifications
- [ ] Port utility functions to async:
  - [ ] `notifications.py` → async broadcast
  - [ ] `email.py` → TBD (keep Flask-Mail until migrated)
  - [ ] `slack.py` → httpx async client

### Deliverables
- [ ] All endpoints on `/api/v2/`
- [ ] Async email/Slack utilities
- [ ] Feature parity with Flask

### Notes
```
<!-- Add implementation notes here -->
```

---

## Phase 8: Scheduler Migration & Cutover (Days 25-30)

### Status: ⬜ Not Started

### Objective
Migrate APScheduler runtime + scheduler side-effects to FastAPI and complete the cutover from Flask.

This phase explicitly includes the **scheduler side-effects deferred from Phase 5**, such as scheduling/rescheduling/removing jobs when jobs are created/updated/deleted.

### Scope (What moves here from Phase 5)

- **APScheduler job registration** on job create/update/delete
- **Enable/disable behavior**: adding/removing jobs from the scheduler when `is_active` changes
- **Scheduler startup/shutdown** under FastAPI lifespan
- **Single-runner guarantees** (lock file / leader election)

### Tasks

- [ ] Refactor scheduler runtime to be framework-agnostic
  - [ ] Refactor `src/scheduler/job_executor.py` to remove Flask app context coupling
  - [ ] Use shared DB utilities (`src/database/session.py`) instead of `current_app`/Flask globals
  - [ ] Ensure all timestamps/timezones match Flask behavior (JST cron interpretation)

- [ ] Implement scheduler lifecycle in FastAPI
  - [ ] Start scheduler in FastAPI lifespan when `SCHEDULER_ENABLED=true`
  - [ ] Add/keep a lock mechanism (similar to Flask’s `src/instance/scheduler.lock`) so only one process runs schedules
  - [ ] Graceful shutdown: stop scheduler and release lock

- [ ] Implement scheduler side-effects for job writes (deferred from Phase 5)
  - [ ] On `POST /api/v2/jobs`: schedule new job if active
  - [ ] On `PUT /api/v2/jobs/{id}`: reschedule if cron/active state changes
  - [ ] On `DELETE /api/v2/jobs/{id}`: remove from scheduler (or disable, matching Flask behavior)
  - [ ] Ensure behavior is safe when scheduler is not running in the current process (best-effort + no hard failure)

- [ ] Scheduler + cutover test plan
  - [ ] Add integration tests for scheduler leadership/lock (single runner)
  - [ ] Add tests asserting side-effects happen only when scheduler is running/enabled
  - [ ] Run full regression:
    - [ ] `venv/bin/python -m pytest -q tests_fastapi`
    - [ ] `venv/bin/python -m pytest -q test`

- [ ] Cutover steps
  - [ ] Update frontend API base URL to `/api/v2`
  - [ ] Configure proxy redirect `/api/*` → `/api/v2/*` (or switch frontend env)
  - [ ] Monitor for 1 week with fallback plan
  - [ ] Remove Flask code and dependencies after stability window
  - [ ] Update docs + `requirements.txt` cleanup

### Frontend Changes Required

```typescript
// cron-job-frontend/src/constants/api.ts
// Change from:
export const API_BASE = '/api';
// To:
export const API_BASE = '/api/v2';
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
- [ ] Scheduler running under FastAPI lifespan (single runner)
- [ ] Scheduler side-effects wired into FastAPI job write endpoints (create/update/delete/enable/disable)
- [ ] Frontend fully migrated to `/api/v2`
- [ ] Proxy cutover completed with rollback option
- [ ] Flask code removed after stability window
- [ ] All tests passing (Flask + FastAPI suites)

### Notes
```
<!-- Add implementation notes here -->
```

---

## Final Folder Structure

```
src/
├── main.py                    # FastAPI app entry
├── config.py                  # Pydantic Settings
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
├── schemas/                   # Pydantic models
│   ├── __init__.py
│   ├── user.py
│   ├── job.py
│   ├── execution.py
│   ├── notification.py
│   ├── category.py
│   ├── team.py
│   ├── settings.py
│   └── common.py
├── routers/                   # FastAPI routers
│   ├── __init__.py
│   ├── auth.py
│   ├── jobs.py
│   ├── executions.py
│   ├── notifications.py
│   ├── categories.py
│   ├── teams.py
│   └── settings.py
├── dependencies/              # FastAPI dependencies
│   ├── __init__.py
│   ├── auth.py
│   └── database.py
├── services/                  # Business logic
│   ├── __init__.py
│   └── end_date_maintenance.py
├── scheduler/                 # APScheduler (refactored)
│   ├── __init__.py
│   └── job_executor.py
└── utils/                     # Utilities (async)
    ├── __init__.py
    ├── email.py
    ├── slack.py
    ├── notifications.py
    └── api_errors.py
```

---

## Risk Mitigation

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| Token incompatibility | High | Low | Use same JWT secret, validate cross-stack before Phase 4 |
| Database conflicts | High | Medium | Single DB, careful session management, test transactions |
| Scheduler race conditions | High | Medium | Keep scheduler on Flask until Phase 8, lock mechanism |
| Frontend breaking | Medium | Low | Version API as `/api/v2/`, gradual frontend switch |
| Test coverage gaps | Medium | Medium | Run Flask tests against FastAPI endpoints |
| Performance regression | Medium | Low | Benchmark before/after migration |

---

## Success Criteria

| Phase | Validation Criteria | Verified |
|-------|---------------------|----------|
| 1 | Both apps respond on respective ports | ⬜ |
| 2 | Models import in both Flask and FastAPI | ⬜ |
| 3 | Login token works on both stacks | ⬜ |
| 4 | Read endpoints return identical data | ⬜ |
| 5 | Job CRUD operations work end-to-end | ⬜ |
| 6 | Full auth flow on FastAPI only | ⬜ |
| 7 | All 40+ endpoints on FastAPI | ⬜ |
| 8 | Flask removed, all tests pass | ⬜ |

---

## Timeline Summary

| Phase | Description | Duration | Start | End | Status |
|-------|-------------|----------|-------|-----|--------|
| 1 | Project Setup | 2 days | - | - | ⬜ |
| 2 | Database & Models | 3 days | - | - | ⬜ |
| 3 | Authentication | 4 days | - | - | ⬜ |
| 4 | Read-Only Endpoints | 3 days | - | - | ⬜ |
| 5 | Jobs CRUD | 5 days | - | - | ⬜ |
| 6 | User Management | 4 days | - | - | ⬜ |
| 7 | Notifications | 3 days | - | - | ⬜ |
| 8 | Cutover | 6 days | - | - | ⬜ |
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
# Install Flask + FastAPI dependencies
pip install -r requirements.txt
```

### Step 2: Run Dual-Stack Locally

**Terminal 1 - Flask (Port 5001):**
```bash
cd /path/to/cron-job-backend
source venv/bin/activate
./start_server.sh
```

**Terminal 2 - FastAPI (Port 8001):**
```bash
cd /path/to/cron-job-backend
source venv/bin/activate
./start_fastapi.sh
# Or: uvicorn src.fastapi_app.main:app --reload --port 8001
```

### Step 3: Verify Both Running

```bash
# Flask health check
curl http://localhost:5001/api/health

# FastAPI health check
curl http://localhost:8001/api/v2/health

# FastAPI OpenAPI docs
open http://localhost:8001/docs
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
| `from` | datetime | - | Filter by created_at start |
| `to` | datetime | - | Filter by created_at end |

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
  "total_pages": 3
}
```

#### GET `/api/v2/notifications/unread-count`

**Response (200):**
```json
{
  "unread_count": 12
}
```

---

### Categories & Teams Endpoints (Read-Only in Phase 4)

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

**Status:** Not implemented yet (planned in Phase 7)

**Request:**
```json
{
  "name": "Analytics Jobs",
  "slug": "analytics"  // Optional, auto-generated from name if omitted
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

**Status:** Not implemented yet (planned in Phase 7)

**Request:**
```json
{
  "name": "QA Team",
  "slug": "qa",  // Optional
  "slack_handle": "@qa-team"  // Optional
}
```

---

### Settings Endpoints

#### GET `/api/v2/settings/slack` (Admin only)

**Response (200):**
```json
{
  "id": "settings-uuid",
  "is_enabled": true,
  "webhook_url": "https://hooks.slack.com/services/...",
  "channel": "#cron-alerts",
  "created_at": "2025-01-15T10:30:00Z",
  "updated_at": "2025-01-15T10:30:00Z"
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
| Create job with valid data | 201, job created | ⬜ |
| Create job with invalid cron | 400, validation error | ⬜ |
| Create job with duplicate name | 409, conflict | ⬜ |
| Update job as owner | 200, job updated | ⬜ |
| Update job as non-owner (non-admin) | 403, forbidden | ⬜ |
| Delete job as admin | 200, job deleted | ⬜ |
| Execute job → Check execution created | Execution in DB | ⬜ |
| Bulk upload valid CSV | Jobs created/updated | ⬜ |
| Bulk upload invalid CSV | Partial success with errors | ⬜ |

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
# 1. Stop both servers
pkill -f "flask" && pkill -f "uvicorn"

# 2. Restore database from backup
cp src/instance/cron_jobs.db.backup src/instance/cron_jobs.db

# 3. Restart Flask only
./start_server.sh
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
# In cron-job-frontend/src/constants/api.ts
# Change back: export const API_BASE = '/api';

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
