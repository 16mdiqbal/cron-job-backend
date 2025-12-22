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
| `Flask-JWT-Extended` | `python-jose` + `passlib` | Custom dependencies |
| `Flask-CORS` | `fastapi.middleware.cors` | Built-in |
| `Flask-Mail` | `fastapi-mail` | Similar API |
| `APScheduler` | `APScheduler` | Keep as-is |

### New Requirements (to add)

```txt
fastapi>=0.109.0
uvicorn[standard]>=0.27.0
python-jose[cryptography]
python-multipart
fastapi-mail
pydantic>=2.0
pydantic-settings
httpx
```

---

## Phase 1: Project Setup & Dual-Stack Infrastructure (Days 1-2)

### Status: ⬜ Not Started

### Objective
Set up FastAPI alongside Flask with shared database and configuration.

### Tasks

- [ ] Create folder structure `src/fastapi_app/`
  - [ ] `main.py` - FastAPI app instance
  - [ ] `config.py` - Pydantic Settings
  - [ ] `dependencies/` - Auth, database dependencies
  - [ ] `routers/` - Empty router files
  - [ ] `schemas/` - Pydantic models
- [ ] Update `requirements.txt` with FastAPI dependencies
- [ ] Create reverse proxy configuration (nginx/Traefik)
  - [ ] `/api/v2/*` → FastAPI (port 8001)
  - [ ] `/api/*` → Flask (port 5000)
- [ ] Add `start_fastapi.sh` script
- [ ] Verify both apps run simultaneously

### Deliverables
- [ ] FastAPI app responding on port 8001
- [ ] Flask app responding on port 5000
- [ ] Proxy routing under single port 8000
- [ ] Shared `.env` configuration working

### Notes
```
<!-- Add implementation notes here -->
```

---

## Phase 2: Database & Model Layer (Days 3-5)

### Status: ⬜ Not Started

### Objective
Create shared SQLAlchemy setup that works for both Flask and FastAPI.

### Tasks

- [ ] Create `src/database/` folder
  - [ ] `engine.py` - SQLAlchemy engine creation
  - [ ] `session.py` - Sync and async session factories
- [ ] Refactor models to use `DeclarativeBase` directly
- [ ] Create Pydantic schemas in `src/fastapi_app/schemas/`
  - [ ] `user.py` - UserCreate, UserUpdate, UserResponse
  - [ ] `job.py` - JobCreate, JobUpdate, JobResponse
  - [ ] `execution.py` - ExecutionResponse
  - [ ] `notification.py` - NotificationResponse
  - [ ] `category.py` - CategoryCreate, CategoryResponse
  - [ ] `team.py` - TeamCreate, TeamResponse
  - [ ] `settings.py` - SlackSettingsUpdate
- [ ] Verify Flask app still works with models
- [ ] Test database migrations

### Pydantic Schemas Required

| Schema File | Models |
|-------------|--------|
| `user.py` | UserCreate, UserUpdate, UserResponse, UserLogin |
| `job.py` | JobCreate, JobUpdate, JobResponse, JobBulkUpload |
| `execution.py` | ExecutionResponse, ExecutionStats |
| `notification.py` | NotificationResponse, NotificationPrefs |
| `category.py` | CategoryCreate, CategoryUpdate, CategoryResponse |
| `team.py` | TeamCreate, TeamUpdate, TeamResponse |
| `settings.py` | SlackSettingsUpdate, SlackSettingsResponse |
| `common.py` | PaginatedResponse, ErrorResponse |

### Deliverables
- [ ] Models compatible with both frameworks
- [ ] ~25 Pydantic schemas created
- [ ] Database operations working

### Notes
```
<!-- Add implementation notes here -->
```

---

## Phase 3: Authentication System (Days 6-9)

### Status: ⬜ Not Started

### Objective
Implement FastAPI authentication compatible with existing JWT tokens.

### Tasks

- [ ] Create `src/fastapi_app/dependencies/auth.py`
  - [ ] `get_current_user()` - Decode JWT, return User
  - [ ] `get_current_active_user()` - Verify user is active
  - [ ] `require_role(*roles)` - Role-based dependency factory
  - [ ] `get_optional_user()` - For optional auth endpoints
- [ ] Use same `JWT_SECRET_KEY` for token compatibility
- [ ] Implement `/api/v2/auth/login` endpoint
- [ ] Create token validation tests

### Auth Dependencies to Create

```python
# Dependency signatures
async def get_current_user(token: str = Depends(oauth2_scheme)) -> User
async def get_current_active_user(user: User = Depends(get_current_user)) -> User
def require_role(*roles: str) -> Callable  # Returns dependency
async def get_optional_user(token: str = Depends(oauth2_scheme_optional)) -> Optional[User]
```

### Cross-Stack Compatibility Tests

- [ ] Token from Flask login → FastAPI endpoint ✓
- [ ] Token from FastAPI login → Flask endpoint ✓
- [ ] Token refresh works on both
- [ ] Role claims preserved

### Deliverables
- [ ] FastAPI auth dependencies complete
- [ ] Single Sign-On across both stacks
- [ ] Auth integration tests passing

### Notes
```
<!-- Add implementation notes here -->
```

---

## Phase 4: Health & Read-Only Endpoints (Days 10-12)

### Status: ⬜ Not Started

### Objective
Migrate low-risk, read-only endpoints first for validation.

### Endpoints to Migrate

| # | Flask Endpoint | FastAPI Endpoint | Auth | Status |
|---|----------------|------------------|------|--------|
| 1 | `GET /health` | `GET /api/v2/health` | None | ⬜ |
| 2 | `GET /api/jobs` | `GET /api/v2/jobs` | JWT | ⬜ |
| 3 | `GET /api/jobs/<id>` | `GET /api/v2/jobs/{id}` | JWT | ⬜ |
| 4 | `GET /api/jobs/<id>/executions` | `GET /api/v2/jobs/{id}/executions` | JWT | ⬜ |
| 5 | `GET /api/executions` | `GET /api/v2/executions` | JWT | ⬜ |
| 6 | `GET /api/executions/<id>` | `GET /api/v2/executions/{id}` | JWT | ⬜ |
| 7 | `GET /api/stats/executions` | `GET /api/v2/stats/executions` | JWT | ⬜ |
| 8 | `GET /api/categories` | `GET /api/v2/categories` | JWT | ⬜ |
| 9 | `GET /api/teams` | `GET /api/v2/teams` | JWT | ⬜ |

### Tasks

- [ ] Create `src/fastapi_app/routers/jobs.py`
- [ ] Create `src/fastapi_app/routers/executions.py`
- [ ] Create `src/fastapi_app/routers/categories.py`
- [ ] Implement pagination with Pydantic
- [ ] Implement filtering and sorting
- [ ] Add response models
- [ ] Verify OpenAPI docs at `/api/v2/docs`
- [ ] Run parity tests (Flask vs FastAPI responses)

### Deliverables
- [ ] 9 read-only endpoints on `/api/v2/`
- [ ] OpenAPI documentation
- [ ] Response parity validated

### Notes
```
<!-- Add implementation notes here -->
```

---

## Phase 5: Write Operations - Jobs CRUD (Days 13-17)

### Status: ⬜ Not Started

### Objective
Migrate job creation, update, and deletion with full validation.

### Endpoints to Migrate

| # | Flask Endpoint | FastAPI Endpoint | Complexity | Status |
|---|----------------|------------------|------------|--------|
| 1 | `POST /api/jobs` | `POST /api/v2/jobs` | High | ⬜ |
| 2 | `PUT /api/jobs/<id>` | `PUT /api/v2/jobs/{id}` | High | ⬜ |
| 3 | `DELETE /api/jobs/<id>` | `DELETE /api/v2/jobs/{id}` | Medium | ⬜ |
| 4 | `POST /api/jobs/<id>/execute` | `POST /api/v2/jobs/{id}/execute` | High | ⬜ |
| 5 | `POST /api/jobs/bulk-upload` | `POST /api/v2/jobs/bulk-upload` | High | ⬜ |
| 6 | `POST /api/cron/validate` | `POST /api/v2/cron/validate` | Low | ⬜ |
| 7 | `POST /api/cron/next-runs` | `POST /api/v2/cron/next-runs` | Low | ⬜ |
| 8 | `POST /api/cron/test-run` | `POST /api/v2/cron/test-run` | Medium | ⬜ |

### Tasks

- [ ] Create `JobCreate` Pydantic model with validators
  - [ ] Cron expression validation
  - [ ] Email list parsing
  - [ ] GitHub fields validation
  - [ ] End date must be future
- [ ] Create `JobUpdate` Pydantic model
- [ ] Implement authorization dependencies
  - [ ] Admin can modify any job
  - [ ] User can modify own jobs only
  - [ ] Viewer cannot modify
- [ ] Port CSV bulk upload with async file handling
- [ ] Integrate with APScheduler
- [ ] Add notification broadcasts on changes

### Deliverables
- [ ] Complete Jobs CRUD on FastAPI
- [ ] CSV file upload working
- [ ] Scheduler integration verified
- [ ] Authorization working correctly

### Notes
```
<!-- Add implementation notes here -->
```

---

## Phase 6: Auth & User Management (Days 18-21)

### Status: ⬜ Not Started

### Objective
Migrate authentication and user management endpoints.

### Endpoints to Migrate

| # | Flask Endpoint | FastAPI Endpoint | Auth | Status |
|---|----------------|------------------|------|--------|
| 1 | `POST /api/auth/login` | `POST /api/v2/auth/login` | None | ⬜ |
| 2 | `POST /api/auth/refresh` | `POST /api/v2/auth/refresh` | Refresh | ⬜ |
| 3 | `POST /api/auth/register` | `POST /api/v2/auth/register` | Admin | ⬜ |
| 4 | `GET /api/auth/me` | `GET /api/v2/auth/me` | JWT | ⬜ |
| 5 | `GET /api/auth/users` | `GET /api/v2/auth/users` | Admin | ⬜ |
| 6 | `GET /api/auth/users/<id>` | `GET /api/v2/auth/users/{id}` | JWT | ⬜ |
| 7 | `PUT /api/auth/users/<id>` | `PUT /api/v2/auth/users/{id}` | JWT | ⬜ |
| 8 | `DELETE /api/auth/users/<id>` | `DELETE /api/v2/auth/users/{id}` | Admin | ⬜ |
| 9 | `GET .../preferences` | `GET .../preferences` | JWT | ⬜ |
| 10 | `PUT .../preferences` | `PUT .../preferences` | JWT | ⬜ |
| 11 | `GET .../ui-preferences` | `GET .../ui-preferences` | JWT | ⬜ |
| 12 | `PUT .../ui-preferences` | `PUT .../ui-preferences` | JWT | ⬜ |

### Tasks

- [ ] Create `src/fastapi_app/routers/auth.py`
- [ ] Implement OAuth2PasswordBearer flow
- [ ] Use same password hashing (passlib pbkdf2_sha256)
- [ ] Add preference endpoints
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
| 9 | `POST /api/categories` | `POST /api/v2/categories` | ⬜ |
| 10 | `PUT /api/categories/<id>` | `PUT /api/v2/categories/{id}` | ⬜ |
| 11 | `DELETE /api/categories/<id>` | `DELETE /api/v2/categories/{id}` | ⬜ |
| 12 | `POST /api/teams` | `POST /api/v2/teams` | ⬜ |
| 13 | `PUT /api/teams/<id>` | `PUT /api/v2/teams/{id}` | ⬜ |
| 14 | `DELETE /api/teams/<id>` | `DELETE /api/v2/teams/{id}` | ⬜ |

### Tasks

- [ ] Create `src/fastapi_app/routers/notifications.py`
- [ ] Create `src/fastapi_app/routers/settings.py`
- [ ] Implement pagination for notifications
- [ ] Port utility functions to async:
  - [ ] `notifications.py` → async broadcast
  - [ ] `email.py` → fastapi-mail
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
Migrate scheduler to FastAPI lifespan and complete transition.

### Tasks

- [ ] Refactor `src/scheduler/job_executor.py`
  - [ ] Remove `_flask_app` global
  - [ ] Remove `app.app_context()` pattern
  - [ ] Use standalone async database sessions
- [ ] Implement FastAPI lifespan events
- [ ] Update frontend API base URL
  - [ ] Modify `cron-job-frontend/src/constants/api.ts`
- [ ] Run full regression tests
- [ ] Configure proxy redirect `/api/*` → `/api/v2/*`
- [ ] Monitor for 1 week with fallback
- [ ] Remove Flask code and dependencies
- [ ] Update `requirements.txt` (remove Flask packages)
- [ ] Update documentation

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
- [ ] Scheduler running under FastAPI
- [ ] Frontend fully migrated
- [ ] Flask code removed
- [ ] Clean FastAPI-only codebase
- [ ] All tests passing

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

## References

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [SQLAlchemy 2.0 Async](https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html)
- [Pydantic V2](https://docs.pydantic.dev/latest/)
- [python-jose](https://github.com/mpdavis/python-jose)
- [fastapi-mail](https://sabuhish.github.io/fastapi-mail/)

---

*Last Updated: December 21, 2025*
