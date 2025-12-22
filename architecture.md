# Cron Job Scheduler - Backend Architecture

> **Version:** 2.0  
> **Last Updated:** December 22, 2025  
> **Tech Stack:** Python 3.11+ | Flask 3.0 | SQLAlchemy | APScheduler | JWT Auth

---

## Table of Contents

1. [Overview](#overview)
2. [System Purpose](#system-purpose)
3. [Technology Stack](#technology-stack)
4. [Project Structure](#project-structure)
5. [Database Schema](#database-schema)
6. [API Endpoints Reference](#api-endpoints-reference)
7. [Authentication & Authorization](#authentication--authorization)
8. [Scheduler Architecture](#scheduler-architecture)
9. [Notification System](#notification-system)
10. [Configuration Management](#configuration-management)
11. [Development Philosophy](#development-philosophy)
12. [Incremental Development Plan](#incremental-development-plan)

---

## Overview

This document provides the complete architecture specification for a **Cron Job Scheduling System** backend. The system enables users to create, manage, and monitor scheduled jobs that trigger **GitHub Actions workflows** or **generic webhooks** based on cron expressions.

### Key Features

- **Job Scheduling**: Define jobs with 5-field cron expressions (minute hour day month day-of-week)
- **GitHub Actions Integration**: Trigger workflow_dispatch events on GitHub repositories
- **Webhook Support**: Call generic HTTP endpoints on schedule
- **Multi-tenant Authorization**: Role-based access control (Admin, User, Viewer)
- **Execution Tracking**: Full history of job executions with status, duration, and errors
- **Notifications**: In-app notifications, email alerts, and Slack integration
- **Team Management**: Assign jobs to PIC teams for ownership tracking
- **Category Organization**: Group jobs into categories for better management
- **Bulk Operations**: CSV upload for creating/updating multiple jobs

---

## System Purpose

The Cron Job Scheduler solves the problem of managing scheduled automation tasks across distributed systems:

1. **Centralized Scheduling**: Single source of truth for all scheduled tasks
2. **Visibility**: Dashboard view of all jobs, their schedules, and execution history
3. **Alerting**: Immediate notification on job failures via email/Slack
4. **Governance**: Track job ownership, expiration dates, and responsible teams
5. **Audit Trail**: Complete execution history for compliance and debugging

---

## Technology Stack

| Layer | Technology | Version | Purpose |
|-------|------------|---------|---------|
| **Framework** | Flask | 3.0.0 | REST API web framework |
| **ORM** | Flask-SQLAlchemy | 3.1.1 | Database abstraction |
| **Database** | SQLite (dev) / MySQL (prod) | - | Data persistence |
| **Scheduler** | APScheduler | 3.10.4 | Background job execution |
| **Auth** | Flask-JWT-Extended | 4.6.0 | JWT token authentication |
| **Password** | passlib (pbkdf2_sha256) | 1.7.4 | Secure password hashing |
| **Email** | Flask-Mail | 0.9.1 | SMTP email notifications |
| **CORS** | Flask-CORS | 4.0.0 | Cross-origin requests |
| **HTTP Client** | requests | 2.31.0 | GitHub API & webhooks |
| **Cron Parsing** | croniter | 2.0.1 | Cron expression validation |
| **Environment** | python-dotenv | 1.0.0 | Environment variables |

### Dependencies (requirements.txt)

```txt
Flask==3.0.0
Flask-SQLAlchemy==3.1.1
Flask-CORS==4.0.0
Flask-JWT-Extended==4.6.0
Flask-Mail==0.9.1
APScheduler==3.10.4
croniter==2.0.1
requests==2.31.0
python-dotenv==1.0.0
passlib==1.7.4
```

---

## Project Structure

```
src/
├── __init__.py                    # Package marker
├── __main__.py                    # Entry point for `python -m src`
├── app.py                         # Flask application factory
├── config.py                      # Configuration (Pydantic-style settings)
│
├── models/                        # SQLAlchemy ORM models
│   ├── __init__.py                # db instance + model imports
│   ├── user.py                    # User model (auth + roles)
│   ├── job.py                     # Job model (cron jobs)
│   ├── job_execution.py           # JobExecution model (history)
│   ├── job_category.py            # JobCategory model
│   ├── pic_team.py                # PicTeam model (ownership)
│   ├── notification.py            # Notification model (in-app)
│   ├── notification_preferences.py # UserNotificationPreferences
│   ├── ui_preferences.py          # UserUiPreferences
│   └── slack_settings.py          # SlackSettings (global)
│
├── routes/                        # Flask Blueprints (API endpoints)
│   ├── __init__.py
│   ├── auth.py                    # /api/auth/* endpoints
│   ├── jobs.py                    # /api/jobs/*, /api/executions/*, etc.
│   └── notifications.py           # /api/notifications/* endpoints
│
├── scheduler/                     # APScheduler integration
│   ├── __init__.py                # Scheduler instance
│   └── job_executor.py            # Job execution logic
│
├── services/                      # Business logic services
│   ├── __init__.py
│   └── end_date_maintenance.py    # Job expiration handling
│
├── utils/                         # Utility functions
│   ├── __init__.py
│   ├── auth.py                    # Auth decorators & helpers
│   ├── email.py                   # Email sending (Flask-Mail)
│   ├── slack.py                   # Slack webhook integration
│   ├── notifications.py           # In-app notification helpers
│   ├── api_errors.py              # Error message utilities
│   └── sqlite_schema.py           # Schema migration helpers
│
├── scripts/                       # Utility scripts
│   └── ...
│
└── instance/                      # Instance-specific data (SQLite DB)
    └── cron_jobs.db
```

---

## Database Schema

### Entity Relationship Diagram

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────────┐
│     users       │     │      jobs       │     │   job_executions    │
├─────────────────┤     ├─────────────────┤     ├─────────────────────┤
│ id (PK)         │◄────│ created_by (FK) │     │ id (PK)             │
│ username        │     │ id (PK)         │◄────│ job_id (FK)         │
│ email           │     │ name            │     │ status              │
│ password_hash   │     │ cron_expression │     │ trigger_type        │
│ role            │     │ target_url      │     │ started_at          │
│ is_active       │     │ github_owner    │     │ completed_at        │
│ created_at      │     │ github_repo     │     │ duration_seconds    │
│ updated_at      │     │ github_workflow │     │ execution_type      │
└────────┬────────┘     │ category        │     │ target              │
         │              │ pic_team        │     │ response_status     │
         │              │ end_date        │     │ error_message       │
         │              │ is_active       │     │ output              │
         │              │ enable_email_*  │     └─────────────────────┘
         │              │ notification_*  │
         │              └────────┬────────┘
         │                       │
         │              ┌────────▼────────┐
         │              │  notifications  │
         │              ├─────────────────┤
         └──────────────│ user_id (FK)    │
                        │ id (PK)         │
                        │ title           │
                        │ message         │
                        │ type            │
                        │ related_job_id  │
                        │ is_read         │
                        └─────────────────┘

┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  job_categories │     │   pic_teams     │     │ slack_settings  │
├─────────────────┤     ├─────────────────┤     ├─────────────────┤
│ id (PK)         │     │ id (PK)         │     │ id (PK)         │
│ slug (unique)   │     │ slug (unique)   │     │ is_enabled      │
│ name            │     │ name            │     │ webhook_url     │
│ is_active       │     │ slack_handle    │     │ channel         │
└─────────────────┘     │ is_active       │     └─────────────────┘
                        └─────────────────┘

┌─────────────────────────────┐     ┌─────────────────────────┐
│ user_notification_preferences│     │   user_ui_preferences   │
├─────────────────────────────┤     ├─────────────────────────┤
│ id (PK)                     │     │ id (PK)                 │
│ user_id (FK, unique)        │     │ user_id (FK, unique)    │
│ email_on_job_success        │     │ jobs_table_columns (JSON)│
│ email_on_job_failure        │     └─────────────────────────┘
│ email_on_job_disabled       │
│ browser_notifications       │
│ daily_digest                │
│ weekly_report               │
└─────────────────────────────┘
```

### Model Specifications

#### User Model
| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| id | UUID (String 36) | PK | Unique identifier |
| username | String(80) | Unique, Not Null, Indexed | Login username |
| email | String(120) | Unique, Not Null, Indexed | Email address |
| password_hash | String(255) | Not Null | PBKDF2-SHA256 hash |
| role | String(20) | Not Null, Default: 'viewer' | admin/user/viewer |
| is_active | Boolean | Not Null, Default: True | Account status |
| created_at | DateTime | UTC | Creation timestamp |
| updated_at | DateTime | UTC, Auto-update | Last modification |

#### Job Model
| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| id | UUID (String 36) | PK | Unique identifier |
| name | String(255) | Unique, Not Null | Display name |
| cron_expression | String(100) | Not Null | 5-field cron (minute hour day month dow) |
| target_url | String(500) | Nullable | Generic webhook URL |
| github_owner | String(255) | Nullable | GitHub org/user |
| github_repo | String(255) | Nullable | Repository name |
| github_workflow_name | String(255) | Nullable | Workflow filename |
| job_metadata | Text (JSON) | Nullable | Custom key-value data |
| category | String(100) | Not Null, Default: 'general' | Category slug |
| pic_team | String(100) | Nullable | Team slug (ownership) |
| end_date | Date | Nullable | Job expiration date |
| enable_email_notifications | Boolean | Default: False | Email alerts enabled |
| notification_emails | Text | Nullable | Comma-separated emails |
| notify_on_success | Boolean | Default: False | Notify on success |
| created_by | UUID (FK→users) | Nullable | Owner user ID |
| is_active | Boolean | Default: True | Job enabled status |
| created_at | DateTime | UTC | Creation timestamp |
| updated_at | DateTime | UTC, Auto-update | Last modification |

#### JobExecution Model
| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| id | UUID (String 36) | PK | Unique identifier |
| job_id | UUID (FK→jobs) | Not Null, Indexed, CASCADE | Parent job |
| status | String(20) | Not Null | success/failed/running |
| trigger_type | String(20) | Not Null | scheduled/manual |
| started_at | DateTime | Not Null, UTC | Execution start |
| completed_at | DateTime | Nullable | Execution end |
| duration_seconds | Float | Nullable | Total duration |
| execution_type | String(50) | Nullable | github_actions/webhook |
| target | String(500) | Nullable | URL or workflow path |
| response_status | Integer | Nullable | HTTP status code |
| error_message | Text | Nullable | Error details |
| output | Text | Nullable | Response body |

---

## API Endpoints Reference

### Base URL: `/api`

### Authentication Endpoints (`/api/auth`)

| Method | Endpoint | Auth | Role | Description |
|--------|----------|------|------|-------------|
| POST | `/auth/login` | None | - | Login with username/email + password |
| POST | `/auth/register` | JWT | Admin | Create new user account |
| POST | `/auth/refresh` | Refresh Token | - | Refresh access token |
| GET | `/auth/me` | JWT | Any | Get current user info |
| GET | `/auth/users` | JWT | Admin | List all users |
| GET | `/auth/users/{id}` | JWT | Self/Admin | Get user by ID |
| PUT | `/auth/users/{id}` | JWT | Self/Admin | Update user |
| DELETE | `/auth/users/{id}` | JWT | Admin | Delete user |
| GET | `/auth/users/{id}/preferences` | JWT | Self/Admin | Get notification preferences |
| PUT | `/auth/users/{id}/preferences` | JWT | Self/Admin | Update notification preferences |
| GET | `/auth/users/{id}/ui-preferences` | JWT | Self/Admin | Get UI preferences |
| PUT | `/auth/users/{id}/ui-preferences` | JWT | Self/Admin | Update UI preferences |

### Jobs Endpoints (`/api/jobs`)

| Method | Endpoint | Auth | Role | Description |
|--------|----------|------|------|-------------|
| GET | `/jobs` | JWT | Any | List all jobs (with filters) |
| POST | `/jobs` | JWT | Admin/User | Create new job |
| GET | `/jobs/{id}` | JWT | Any | Get job by ID |
| PUT | `/jobs/{id}` | JWT | Owner/Admin | Update job |
| DELETE | `/jobs/{id}` | JWT | Owner/Admin | Delete job |
| POST | `/jobs/{id}/execute` | JWT | Owner/Admin | Manual trigger |
| POST | `/jobs/bulk-upload` | JWT | Admin/User | CSV bulk upload |
| GET | `/jobs/{id}/executions` | JWT | Any | Get job's execution history |
| GET | `/jobs/{id}/executions/{exec_id}` | JWT | Any | Get specific execution |
| GET | `/jobs/{id}/executions/stats` | JWT | Any | Get job execution statistics |

### Cron Utilities (`/api/jobs`)

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/jobs/validate-cron` | JWT | Validate cron expression |
| POST | `/jobs/cron-preview` | JWT | Preview next N run times |
| POST | `/jobs/test-run` | JWT | Dry-run job (no persistence) |

### Executions Endpoints (`/api/executions`)

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/executions` | JWT | List all executions (paginated) |
| GET | `/executions/{id}` | JWT | Get execution details |
| GET | `/executions/statistics` | JWT | Global execution statistics |

### Category Endpoints (`/api/job-categories`)

| Method | Endpoint | Auth | Role | Description |
|--------|----------|------|------|-------------|
| GET | `/job-categories` | JWT | Any | List categories |
| POST | `/job-categories` | JWT | Admin | Create category |
| PUT | `/job-categories/{id}` | JWT | Admin | Update category |
| DELETE | `/job-categories/{id}` | JWT | Admin | Delete category |

### PIC Team Endpoints (`/api/pic-teams`)

| Method | Endpoint | Auth | Role | Description |
|--------|----------|------|------|-------------|
| GET | `/pic-teams` | JWT | Any | List teams |
| POST | `/pic-teams` | JWT | Admin | Create team |
| PUT | `/pic-teams/{id}` | JWT | Admin | Update team |
| DELETE | `/pic-teams/{id}` | JWT | Admin | Delete team |

### Settings Endpoints (`/api/settings`)

| Method | Endpoint | Auth | Role | Description |
|--------|----------|------|------|-------------|
| GET | `/settings/slack` | JWT | Admin | Get Slack config |
| PUT | `/settings/slack` | JWT | Admin | Update Slack config |

### Notifications Endpoints (`/api/notifications`)

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/notifications` | JWT | List user's notifications |
| GET | `/notifications/unread-count` | JWT | Get unread count |
| PUT | `/notifications/{id}/read` | JWT | Mark as read |
| PUT | `/notifications/read-all` | JWT | Mark all as read |
| DELETE | `/notifications/{id}` | JWT | Delete notification |
| DELETE | `/notifications/delete-read` | JWT | Delete all read |

### Health Check

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/health` | None | API health status |

---

## Authentication & Authorization

### JWT Token Structure

```json
{
  "sub": "<user_id>",
  "role": "admin|user|viewer",
  "email": "user@example.com",
  "exp": 1703000000,
  "iat": 1702996400
}
```

### Role Permissions Matrix

| Action | Admin | User | Viewer |
|--------|-------|------|--------|
| View all jobs | ✅ | ✅ | ✅ |
| Create jobs | ✅ | ✅ (own) | ❌ |
| Update any job | ✅ | ❌ | ❌ |
| Update own job | ✅ | ✅ | ❌ |
| Delete any job | ✅ | ❌ | ❌ |
| Delete own job | ✅ | ✅ | ❌ |
| Trigger any job | ✅ | ❌ | ❌ |
| Trigger own job | ✅ | ✅ | ❌ |
| Manage users | ✅ | ❌ | ❌ |
| Manage categories | ✅ | ❌ | ❌ |
| Manage teams | ✅ | ❌ | ❌ |
| Configure Slack | ✅ | ❌ | ❌ |

### Auth Utility Decorators

```python
@jwt_required()                    # Require valid JWT
@role_required('admin')            # Require admin role
@role_required('admin', 'user')    # Require admin OR user role
```

---

## Scheduler Architecture

### APScheduler Configuration

```python
SCHEDULER_JOBSTORES = {
    'default': {
        'type': 'sqlalchemy',
        'url': SQLALCHEMY_DATABASE_URI
    }
}

SCHEDULER_EXECUTORS = {
    'default': {
        'type': 'threadpool',
        'max_workers': 20
    }
}

SCHEDULER_JOB_DEFAULTS = {
    'coalesce': False,
    'max_instances': 3,
    'misfire_grace_time': 30
}
```

### Job Execution Flow

```
┌─────────────────┐
│  APScheduler    │
│  (Background)   │
└────────┬────────┘
         │ Cron trigger fires
         ▼
┌─────────────────────────────────┐
│ execute_job_with_app_context()  │
│ - Wraps in Flask app context    │
└────────────────┬────────────────┘
                 │
                 ▼
┌─────────────────────────────────┐
│       execute_job()             │
│ 1. Check job is_active          │
│ 2. Check end_date not passed    │
│ 3. Create JobExecution record   │
│ 4. Execute (GitHub or Webhook)  │
│ 5. Update execution status      │
│ 6. Send notifications if failed │
└─────────────────────────────────┘
```

### Execution Types

1. **GitHub Actions** (Priority 1):
   - POST to `https://api.github.com/repos/{owner}/{repo}/actions/workflows/{workflow}/dispatches`
   - Requires `GITHUB_TOKEN` environment variable

2. **Webhook** (Priority 2):
   - POST to `target_url` with job metadata as JSON body

### Auto-Pause on End Date

Jobs automatically pause when `end_date` passes:
- Checked at execution time
- Sets `is_active = False`
- Removes from APScheduler
- Creates warning notification

---

## Notification System

### Notification Types

| Type | Color | Use Case |
|------|-------|----------|
| `success` | Green | Job executed successfully |
| `error` | Red | Job execution failed |
| `warning` | Yellow | Job auto-paused, approaching end date |
| `info` | Blue | Job created, updated, configuration changes |

### Notification Channels

1. **In-App**: Stored in `notifications` table, displayed in UI
2. **Email**: Sent via SMTP (Flask-Mail) for failures/success based on job config
3. **Slack**: Posted to webhook for team visibility

### Broadcast Events

- `broadcast_job_created()` - New job added
- `broadcast_job_updated()` - Job configuration changed
- `broadcast_job_deleted()` - Job removed
- `broadcast_job_enabled()` - Job activated
- `broadcast_job_disabled()` - Job paused
- `broadcast_job_success()` - Execution succeeded
- `broadcast_job_failure()` - Execution failed

---

## Configuration Management

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `SECRET_KEY` | dev-secret-key | Flask secret key |
| `JWT_SECRET_KEY` | SECRET_KEY | JWT signing key |
| `JWT_ACCESS_TOKEN_EXPIRES` | 3600 | Access token TTL (seconds) |
| `JWT_REFRESH_TOKEN_EXPIRES` | 2592000 | Refresh token TTL (30 days) |
| `DATABASE_URL` | sqlite:///instance/cron_jobs.db | Database connection string |
| `CORS_ORIGINS` | * | Allowed origins (comma-separated) |
| `SCHEDULER_TIMEZONE` | Asia/Tokyo | Cron expression timezone |
| `GITHUB_TOKEN` | - | GitHub API personal access token |
| `MAIL_SERVER` | smtp.gmail.com | SMTP server |
| `MAIL_PORT` | 587 | SMTP port |
| `MAIL_USERNAME` | - | SMTP username |
| `MAIL_PASSWORD` | - | SMTP password |
| `MAIL_ENABLED` | True | Enable email notifications |
| `FRONTEND_BASE_URL` | http://localhost:5173 | Frontend URL for links |
| `EXPOSE_ERROR_DETAILS` | True (dev) / False (prod) | Show error details in responses |
| `ALLOW_DEFAULT_ADMIN` | True (dev) / False (prod) | Create default admin on startup |

---

## Development Philosophy

### Core Principles

1. **API-First Design**: All functionality exposed via REST API
2. **Clean Architecture**: Separation of concerns between layers
3. **Modular Structure**: One responsibility per file
4. **Testability**: Pure functions, dependency injection
5. **Enterprise Conventions**: Consistent patterns across codebase

### Copilot Instructions

**ALWAYS DO:**
- Follow folder boundaries strictly
- Generate code in the smallest units (one file at a time)
- Write clean Python with type hints
- Add proper docstrings and comments
- Make functions pure where possible
- Ensure routes/controllers never contain business logic
- Keep all orchestration in services/use cases
- Use existing utilities instead of duplicating code
- Ask for clarification when context is missing

**NEVER DO:**
- ❌ Never collapse multiple modules into one file
- ❌ Never mix infrastructure logic in controllers
- ❌ Never skip type hints/interfaces
- ❌ Never break the folder structure
- ❌ **Never create intermediate markdown files** (no `SUMMARY.md`, `CHANGES.md`, `UPDATE_LOG.md`, etc.)
- ❌ **Never create documentation files unless explicitly requested**
- ❌ Never generate files outside the defined project structure
- ❌ Never create backup files or temporary files

**FILE CREATION RULES:**
- Only create files that are part of the project structure defined above
- Code files only: `.py`, `.sql`, `.sh`, `.json`, `.txt` (requirements)
- No markdown files unless user explicitly asks for documentation
- No log files, summary files, or change tracking files
- If you need to explain changes, do so in the chat response, not in new files

### Layer Responsibilities

| Layer | Location | Responsibility |
|-------|----------|----------------|
| **Routes** | `routes/` | Request validation, response formatting |
| **Services** | `services/` | Business logic orchestration |
| **Models** | `models/` | Data entities, validation methods |
| **Utils** | `utils/` | Reusable helper functions |
| **Scheduler** | `scheduler/` | Background job execution |

### Coding Standards

```python
# DO: Use type hints
def get_user(user_id: str) -> Optional[User]:
    ...

# DO: Return dictionaries from models
def to_dict(self) -> dict:
    return {'id': self.id, 'name': self.name}

# DO: Use descriptive error messages
return jsonify({'error': 'Job not found'}), 404

# DON'T: Put business logic in routes
@jobs_bp.route('/jobs', methods=['POST'])
def create_job():
    # ✓ Validate input
    # ✓ Call service/model
    # ✓ Return response
    # ✗ Don't do complex calculations here
```

---

## Incremental Development Plan

This section provides a **phase-by-phase implementation guide** for recreating this system from scratch. Each phase is self-contained and can be completed independently before moving to the next.

---

### Phase 1: Project Setup & Configuration

**Objective**: Establish project foundation with proper structure and configuration.

**Deliverables**:
- [ ] Project folder structure created
- [ ] Virtual environment with dependencies
- [ ] Configuration management (`.env` + Config class)
- [ ] Flask application factory pattern
- [ ] Health check endpoint working

**Files to Create**:
```
src/
├── __init__.py
├── __main__.py
├── app.py              # Application factory
├── config.py           # Configuration class
requirements.txt
.env.example
```

**Validation**: `GET /api/health` returns `{"status": "healthy"}`

---

### Phase 2: Database & User Model

**Objective**: Set up database with User model for authentication.

**Deliverables**:
- [ ] SQLAlchemy integration
- [ ] User model with password hashing
- [ ] Database initialization script
- [ ] Default admin user creation

**Files to Create**:
```
src/models/
├── __init__.py         # db instance
└── user.py             # User model
```

**Validation**: Can create user via Python shell, password hashes correctly

---

### Phase 3: Authentication System

**Objective**: Implement JWT-based authentication.

**Deliverables**:
- [ ] Login endpoint (username/email + password)
- [ ] Token refresh endpoint
- [ ] Auth utility decorators
- [ ] Role-based access control

**Files to Create**:
```
src/routes/
├── __init__.py
└── auth.py             # Auth blueprint
src/utils/
├── __init__.py
└── auth.py             # Auth decorators
```

**Endpoints**:
- POST `/api/auth/login`
- POST `/api/auth/refresh`
- GET `/api/auth/me`

**Validation**: Login returns valid JWT, protected routes reject invalid tokens

---

### Phase 4: User Management

**Objective**: Complete user CRUD operations.

**Deliverables**:
- [ ] User registration (admin only)
- [ ] User listing (admin only)
- [ ] User update (self or admin)
- [ ] User deletion (admin only)

**Endpoints**:
- POST `/api/auth/register`
- GET `/api/auth/users`
- GET `/api/auth/users/{id}`
- PUT `/api/auth/users/{id}`
- DELETE `/api/auth/users/{id}`

**Validation**: Admin can manage users, users can update own profile

---

### Phase 5: Job Model & Basic CRUD

**Objective**: Create Job model with basic operations.

**Deliverables**:
- [ ] Job model with all fields
- [ ] List jobs with pagination
- [ ] Get single job
- [ ] Create job (with validation)
- [ ] Update job
- [ ] Delete job

**Files to Create**:
```
src/models/
└── job.py              # Job model
src/routes/
└── jobs.py             # Jobs blueprint (partial)
```

**Endpoints**:
- GET `/api/jobs`
- POST `/api/jobs`
- GET `/api/jobs/{id}`
- PUT `/api/jobs/{id}`
- DELETE `/api/jobs/{id}`

**Validation**: Full CRUD operations work with proper authorization

---

### Phase 6: APScheduler Integration

**Objective**: Schedule jobs to run automatically.

**Deliverables**:
- [ ] APScheduler initialization on app startup
- [ ] Cron expression parsing and validation
- [ ] Jobs added to scheduler on create
- [ ] Jobs updated in scheduler on update
- [ ] Jobs removed from scheduler on delete/pause

**Files to Create**:
```
src/scheduler/
├── __init__.py         # Scheduler instance
└── job_executor.py     # Execution logic
```

**Validation**: Jobs execute at scheduled times (test with `*/1 * * * *`)

---

### Phase 7: Job Execution & History

**Objective**: Track execution history and implement execution types.

**Deliverables**:
- [ ] JobExecution model
- [ ] GitHub Actions workflow dispatch
- [ ] Generic webhook calls
- [ ] Execution history endpoints
- [ ] Manual trigger endpoint

**Files to Create**:
```
src/models/
└── job_execution.py    # JobExecution model
```

**Endpoints**:
- POST `/api/jobs/{id}/execute`
- GET `/api/jobs/{id}/executions`
- GET `/api/executions`
- GET `/api/executions/{id}`
- GET `/api/executions/statistics`

**Validation**: Executions recorded with status, duration, errors

---

### Phase 8: Cron Utilities

**Objective**: Provide cron expression helpers.

**Deliverables**:
- [ ] Cron validation endpoint
- [ ] Next runs preview endpoint
- [ ] Test run (dry-run) endpoint

**Endpoints**:
- POST `/api/jobs/validate-cron`
- POST `/api/jobs/cron-preview`
- POST `/api/jobs/test-run`

**Validation**: Can validate expressions and preview schedules

---

### Phase 9: Categories & Teams

**Objective**: Organize jobs with categories and team ownership.

**Deliverables**:
- [ ] JobCategory model
- [ ] PicTeam model
- [ ] CRUD endpoints for both
- [ ] Jobs linked to categories/teams

**Files to Create**:
```
src/models/
├── job_category.py
└── pic_team.py
```

**Endpoints**:
- GET/POST `/api/job-categories`
- PUT/DELETE `/api/job-categories/{id}`
- GET/POST `/api/pic-teams`
- PUT/DELETE `/api/pic-teams/{id}`

**Validation**: Can create categories/teams and assign to jobs

---

### Phase 10: Bulk Upload

**Objective**: Support CSV bulk job creation.

**Deliverables**:
- [ ] CSV parsing with validation
- [ ] Create multiple jobs from CSV
- [ ] Update existing jobs from CSV
- [ ] Detailed error reporting

**Endpoint**:
- POST `/api/jobs/bulk-upload` (multipart/form-data)

**Validation**: Upload CSV with 10+ jobs, all created correctly

---

### Phase 11: In-App Notifications

**Objective**: Implement notification system.

**Deliverables**:
- [ ] Notification model
- [ ] Broadcast functions for events
- [ ] User notification endpoints
- [ ] Read/unread management

**Files to Create**:
```
src/models/
└── notification.py
src/utils/
└── notifications.py
src/routes/
└── notifications.py
```

**Endpoints**:
- GET `/api/notifications`
- GET `/api/notifications/unread-count`
- PUT `/api/notifications/{id}/read`
- PUT `/api/notifications/read-all`
- DELETE `/api/notifications/{id}`

**Validation**: Notifications created on job events, can be marked read

---

### Phase 12: Email Notifications

**Objective**: Send email alerts for job events.

**Deliverables**:
- [ ] Flask-Mail integration
- [ ] Failure notification emails
- [ ] Success notification emails (optional)
- [ ] Job-level email configuration

**Files to Create**:
```
src/utils/
└── email.py
```

**Validation**: Receive email on job failure (configure SMTP)

---

### Phase 13: Slack Integration

**Objective**: Post notifications to Slack.

**Deliverables**:
- [ ] SlackSettings model
- [ ] Slack webhook posting
- [ ] Admin settings endpoints
- [ ] Team-specific mentions

**Files to Create**:
```
src/models/
└── slack_settings.py
src/utils/
└── slack.py
```

**Endpoints**:
- GET `/api/settings/slack`
- PUT `/api/settings/slack`

**Validation**: Failure notifications appear in Slack channel

---

### Phase 14: User Preferences

**Objective**: Allow users to customize notification and UI settings.

**Deliverables**:
- [ ] UserNotificationPreferences model
- [ ] UserUiPreferences model
- [ ] Preferences endpoints

**Files to Create**:
```
src/models/
├── notification_preferences.py
└── ui_preferences.py
```

**Endpoints**:
- GET/PUT `/api/auth/users/{id}/preferences`
- GET/PUT `/api/auth/users/{id}/ui-preferences`

**Validation**: User preferences persist and affect behavior

---

### Phase 15: End Date Maintenance

**Objective**: Handle job expiration and reminders.

**Deliverables**:
- [ ] Auto-pause expired jobs
- [ ] Warning notifications before expiration
- [ ] Scheduled maintenance task

**Files to Create**:
```
src/services/
└── end_date_maintenance.py
```

**Validation**: Jobs auto-pause when end_date passes

---

### Phase 16: Testing & Documentation

**Objective**: Ensure quality and maintainability.

**Deliverables**:
- [ ] pytest test suite
- [ ] API documentation (OpenAPI/Swagger)
- [ ] README with setup instructions
- [ ] Postman collection

**Files to Create**:
```
test/
├── conftest.py
├── test_auth/
├── test_jobs/
└── test_notifications/
pytest.ini
Postman_Collection.json
```

**Validation**: All tests pass, documentation is complete

---

## Appendix: Quick Reference Commands

```bash
# Start development server
cd src && python -m flask run --port 5000

# Or use start script
./start_server.sh

# Run tests
pytest test/ -v

# Create admin user
python create_admin.py
```

---

*This architecture document serves as the single source of truth for the Cron Job Scheduler backend system.*

