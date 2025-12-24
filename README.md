# Cron Job Scheduler Backend

A production-ready FastAPI-based REST API for scheduling and managing cron jobs with APScheduler, featuring GitHub Actions integration, CORS support, and comprehensive validation.

## Features

- ✅ **JWT Authentication** - Secure token-based authentication with access and refresh tokens
- ✅ **Role-Based Authorization** - Three user roles (Admin, User, Viewer) with granular permissions
- ✅ **User Management** - Admin-controlled user registration and management
- ✅ **Job Ownership** - Track job creators and enforce ownership-based access control
- ✅ **Complete CRUD Operations** - Create, read, update, and delete scheduled jobs
- ✅ **Job Categories** - Admin-managed categories used to group jobs (defaults to `general`)
- ✅ **PIC Teams** - Admin-managed PIC teams for job ownership routing
- ✅ **Job End Date (JST)** - Required end date; expired jobs are auto-paused to prevent unnecessary runs
- ✅ **Weekly Reminders (JST)** - Monday reminders for jobs ending within 30 days (in-app + optional Slack)
- ✅ **Slack Integration** - Admin-configured Slack webhook + per-team Slack handle for mentions
- ✅ **Cron Expression Validation** - Validates cron syntax before saving
- ✅ **Dual Execution Modes** - Support for both GitHub Actions workflows and webhook URLs
- ✅ **Flexible Metadata** - Store custom JSON metadata with each job
- ✅ **Email Notifications** - Send alerts on job failure with detailed error information
- ✅ **Job Execution History** - Track execution results, status, and duration
- ✅ **Execution Statistics** - Analyze job performance with success rates and metrics
- ✅ **Date Range Filtering** - Filter executions, statistics, and notifications using `from`/`to` query params
- ✅ **Persistent Storage** - SQLite database (production-ready for MySQL migration)
- ✅ **Background Scheduler** - APScheduler (leader-only via lock) with DB → scheduler reconciliation
- ✅ **CORS Enabled** - Ready for frontend integration with proper auth headers
- ✅ **Unique Job Names** - Prevents duplicate job names
- ✅ **Active/Inactive Toggle** - Enable or disable jobs without deletion
- ✅ **Per-User UI Preferences** - Persist UI settings (e.g., Jobs table columns) across devices

## Project Structure

```
cron-job-backend/
├── src/                    # Source code directory
│   ├── __init__.py        # Package marker
│   ├── __main__.py        # Module entry point (python -m src)
│   ├── database/          # SQLAlchemy engines + session factories
│   ├── fastapi_app/       # FastAPI v2 app + routers (/api/v2/*)
│   ├── models/
│   │   ├── __init__.py
│   │   ├── user.py        # User model with authentication
│   │   ├── job.py         # Job model with ownership tracking
│   │   ├── job_category.py # Job category model (admin-managed)
│   │   ├── pic_team.py    # PIC team model (admin-managed)
│   │   ├── slack_settings.py # Global Slack integration settings
│   │   ├── job_execution.py # Job execution history model
│   │   └── notification.py # Notification model (in-app inbox)
│   │   └── ui_preferences.py # Per-user UI preferences
│   ├── utils/
│   │   ├── __init__.py    # Utilities package
│   │   ├── email.py       # Email notification utilities
│   │   └── sqlite_schema.py # Lightweight SQLite schema guard (no Alembic)
│   │   └── slack.py       # Slack incoming webhook helper
│   ├── services/
│   │   └── end_date_maintenance.py # Weekly end-date reminders + auto-pause
│   └── scheduler/
│       ├── __init__.py    # Scheduler initialization
│       └── job_executor.py # Job execution functions
│   └── instance/          # SQLite database directory (default)
│       └── cron_jobs.db
├── test/          # FastAPI test suite
├── venv/                  # Python virtual environment
├── scripts/create_admin.py # Script to create initial admin user
├── requirements.txt       # Python dependencies
├── pytest.ini             # Pytest configuration
├── .env                   # Environment variables (git-ignored)
├── .env.example           # Example environment variables
├── README.md              # This file
├── FOLDER_STRUCTURE.md    # Detailed folder structure documentation
├── TESTING_GUIDE.md       # Comprehensive testing guide
├── REORGANIZATION_SUMMARY.md # Project reorganization details
├── docs/database/DATABASE_SCHEMA_MYSQL.sql # MySQL database schema
├── MYSQL_SETUP_GUIDE.md   # MySQL setup and configuration
├── MYSQL_CONFIG_REFERENCE.md # MySQL configuration examples
├── MYSQL_DATABASE_SETUP.md   # MySQL database setup overview
├── architecture.md        # Architecture documentation
└── test_api.sh            # API testing script
```

**Directory Organization:**
- **src/** - All application source code
- **test/** - FastAPI pytest suite
- **src/instance/** - Runtime data and databases
- **venv/** - Python virtual environment

## Setup Instructions

### 1. Create Virtual Environment

```bash
# Create virtual environment
python3.12 -m venv venv

# Activate virtual environment
# On macOS/Linux:
source venv/bin/activate
# On Windows:
# venv\Scripts\activate
```

### 2. Install Dependencies
 
```bash
pip install -r requirements.txt
```

**Environment Variables:**
- `DEBUG` - Debug mode (default: False)
- `SECRET_KEY` - App secret key (used for JWT signing when `JWT_SECRET_KEY` is unset)
- `JWT_SECRET_KEY` - JWT token signing key (defaults to SECRET_KEY)
- `JWT_ACCESS_TOKEN_EXPIRES` - Access token expiration in seconds (default: 3600 = 1 hour)
- `JWT_REFRESH_TOKEN_EXPIRES` - Refresh token expiration in seconds (default: 2592000 = 30 days)
- `DATABASE_URL` - Optional database connection string override (by default uses an absolute SQLite path at `src/instance/cron_jobs.db`)
- `CORS_ORIGINS` - Comma-separated list of allowed origins (default: *)
- `GITHUB_TOKEN` - GitHub personal access token (optional, for GitHub Actions)
- `SCHEDULER_TIMEZONE` - Scheduler timezone (default: Asia/Tokyo)
- `SCHEDULER_ENABLED` - Set to `false` to disable APScheduler startup (useful for scripts/tests)
- `SCHEDULER_POLL_SECONDS` - How often the scheduler syncs jobs from DB (default: 60)
- `FRONTEND_BASE_URL` - Used to generate job links in Slack messages (default: http://localhost:5173)
- `EXPOSE_ERROR_DETAILS` - When `true`, API error responses include exception details (default: true in dev, false in production)
- `ALLOW_DEFAULT_ADMIN` - When `true`, auto-creates default `admin/admin123` if missing (default: true in dev, false in production)

## Notes / Behavior

- **Scheduler safety (single runner):**
  - The backend uses a lock file at `src/instance/scheduler.lock` so only one process runs APScheduler (prevents duplicate executions if multiple workers are started).
  - If another process holds the lock, that process will still serve APIs but will not run schedules.
- **SQLite schema updates (no Alembic):**
  - The app uses a lightweight SQLite schema guard on startup (`src/utils/sqlite_schema.py`) to add new columns when needed.
- **End date enforcement:**
  - Jobs require an `end_date` (date-only) and comparisons are done in **JST**.
  - If a job is triggered after its `end_date`, it is **auto-paused** and removed from the scheduler.
- **Weekly reminders:**
  - A Monday (JST) scheduler job creates in-app reminders for jobs ending in ≤ 30 days.
  - If Slack is enabled in Settings, the same reminders are also sent to Slack.

## Key APIs

- **PIC Teams**
  - `GET /api/v2/pic-teams`
  - `POST /api/v2/pic-teams` (admin)
  - `PUT /api/v2/pic-teams/<id>` (admin)
  - `DELETE /api/v2/pic-teams/<id>` (admin, disables)
- **Slack Settings (admin)**
  - `GET /api/v2/settings/slack`
  - `PUT /api/v2/settings/slack`
- **UI Preferences (per user)**
  - `GET /api/v2/auth/users/<user_id>/ui-preferences`
  - `PUT /api/v2/auth/users/<user_id>/ui-preferences`

## Scripts

- `./start_fastapi.sh` starts the backend on `http://localhost:5001` (Swagger at `/docs`).
### 3. Configure Environment Variables

```bash
# Copy example environment file
cp .env.example .env

# Edit .env file with your settings (optional for development)
# The defaults will work for local development
```

### 4. Create Initial Admin User

```bash
# Create the default admin account
python scripts/create_admin.py

# Default credentials (CHANGE THESE IN PRODUCTION):
# Username: admin
# Password: admin123
# Role: admin
```

### 5. Run the Application

```bash
# Run as Python module
python -m src
# Server will start on http://localhost:5001
```

---

## Testing

### Comprehensive Test Suite
The project includes a full pytest test suite with 94 tests covering all functionality:

```bash
# Run all tests
pytest test/ -v

# Run specific test module
pytest test/test_auth/ -v
pytest test/test_jobs/ -v
pytest test/test_notifications/ -v

# Run with coverage report
pytest test/ --cov=src --cov-report=html

# Run specific test file
pytest test/test_auth/test_login.py -v

# Run tests matching pattern
pytest test/ -k "test_create" -v
```

**Test Organization:**
- `test/test_auth/` - Authentication and authorization (16 tests)
- `test/test_jobs/` - Job CRUD operations (69 tests)
- `test/test_notifications/` - Email notification features (21 tests)
- `test/conftest.py` - Shared fixtures and configuration

**Test Coverage:** 61% of source code

**Test Duration:** ~3.3 seconds for full suite

See [TESTING_GUIDE.md](TESTING_GUIDE.md) for detailed testing documentation.

---

## Database Configuration

### SQLite (Development - Default)
SQLite database is used by default and created automatically in `src/instance/cron_jobs.db`.

### MySQL (Production)
To use MySQL in production:

1. **Install Dependencies:**
   ```bash
   pip install PyMySQL
   # or
   pip install mysql-connector-python
   ```

2. **Create Database:**
   See [`docs/database/DATABASE_SCHEMA_MYSQL.sql`](docs/database/DATABASE_SCHEMA_MYSQL.sql) for complete schema.
   ```bash
   mysql -u root -p < docs/database/DATABASE_SCHEMA_MYSQL.sql
   ```

3. **Configure Connection:**
   ```bash
   # Update .env file with your MySQL connection string
   # Example for PyMySQL:
   DATABASE_URL=mysql+pymysql://user:password@localhost:3306/cron_jobs_db
   
   # Example for mysql-connector-python:
   DATABASE_URL=mysql+mysqlconnector://user:password@localhost:3306/cron_jobs_db
   ```

4. **Additional MySQL Resources:**
   - [MYSQL_SETUP_GUIDE.md](MYSQL_SETUP_GUIDE.md) - Complete setup instructions
   - [MYSQL_CONFIG_REFERENCE.md](MYSQL_CONFIG_REFERENCE.md) - Configuration examples
   - [MYSQL_DATABASE_SETUP.md](MYSQL_DATABASE_SETUP.md) - Database overview

---

## Authentication & Authorization

### Overview

The API uses **JWT (JSON Web Token)** based authentication with role-based access control (RBAC). All endpoints except `/api/health` require authentication.

### User Roles & Permissions

| Role | Permissions |
|------|-------------|
| **Admin** | • Full access to all operations<br>• Can register new users<br>• Can create, read, update, delete any job<br>• Can view all users |
| **User** | • Can create new jobs<br>• Can read all jobs<br>• Can update/delete only their own jobs<br>• Cannot manage users |
| **Viewer** | • Read-only access<br>• Can view all jobs<br>• Cannot create, update, or delete jobs<br>• Cannot manage users |

### Authentication Flow

1. **Login** → Receive `access_token` and `refresh_token`
2. **Use access_token** in `Authorization: Bearer <token>` header for API calls
3. **Refresh token** when access_token expires using refresh_token
4. **Logout** → Simply discard tokens (client-side)

### Token Expiration

- **Access Token**: 1 hour (default, configurable via `JWT_ACCESS_TOKEN_EXPIRES`)
- **Refresh Token**: 30 days (default, configurable via `JWT_REFRESH_TOKEN_EXPIRES`)

---

## Authentication Endpoints

### 1. Login

**Endpoint:** `POST /api/auth/login`

**Description:** Authenticate user and receive JWT tokens

**Request Body:**
```json
{
  "username": "admin",
  "password": "admin123"
}
```

**Response (200 OK):**
```json
{
  "message": "Login successful",
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "user": {
    "id": "e05ce2d8-ea6b-4965-b0d0-25a44ac65625",
    "username": "admin",
    "email": "admin@example.com",
    "role": "admin",
    "is_active": true,
    "created_at": "2025-12-13T06:08:15.786388",
    "updated_at": "2025-12-13T06:08:15.786391"
  }
}
```

**Error Responses:**
- `400 Bad Request` - Missing username or password
- `401 Unauthorized` - Invalid credentials or inactive account

**Example:**
```bash
curl -X POST http://localhost:5001/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "admin123"}'
```

---

### 2. Register User (Admin Only)

**Endpoint:** `POST /api/auth/register`

**Description:** Register a new user (requires admin authentication)

**Headers:**
```
Authorization: Bearer <admin_access_token>
Content-Type: application/json
```

**Request Body:**
```json
{
  "username": "john_doe",
  "email": "john@example.com",
  "password": "secure_password",
  "role": "user"
}
```

**Validation Rules:**
- `username`: Required, min 3 characters, must be unique
- `email`: Required, must be unique
- `password`: Required, min 6 characters
- `role`: Optional, defaults to "viewer", must be one of: admin, user, viewer

**Response (201 Created):**
```json
{
  "message": "User registered successfully",
  "user": {
    "id": "uuid",
    "username": "john_doe",
    "email": "john@example.com",
    "role": "user",
    "is_active": true,
    "created_at": "2025-12-13T10:30:00",
    "updated_at": "2025-12-13T10:30:00"
  }
}
```

**Error Responses:**
- `400 Bad Request` - Validation errors (missing fields, weak password, invalid role)
- `401 Unauthorized` - Invalid or expired token
- `403 Forbidden` - Non-admin trying to register users
- `409 Conflict` - Username or email already exists

**Example:**
```bash
curl -X POST http://localhost:5001/api/auth/register \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <admin_token>" \
  -d '{
    "username": "john_doe",
    "email": "john@example.com",
    "password": "secure123",
    "role": "user"
  }'
```

---

### 3. Refresh Token

**Endpoint:** `POST /api/auth/refresh`

**Description:** Get a new access token using refresh token

**Headers:**
```
Authorization: Bearer <refresh_token>
```

**Response (200 OK):**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

**Error Responses:**
- `401 Unauthorized` - Invalid or expired refresh token

**Example:**
```bash
curl -X POST http://localhost:5001/api/auth/refresh \
  -H "Authorization: Bearer <refresh_token>"
```

---

### 4. Get Current User

**Endpoint:** `GET /api/auth/me`

**Description:** Get current authenticated user information

**Headers:**
```
Authorization: Bearer <access_token>
```

**Response (200 OK):**
```json
{
  "user": {
    "id": "uuid",
    "username": "admin",
    "email": "admin@example.com",
    "role": "admin",
    "is_active": true,
    "created_at": "2025-12-13T06:08:15",
    "updated_at": "2025-12-13T06:08:15"
  }
}
```

**Example:**
```bash
curl http://localhost:5001/api/auth/me \
  -H "Authorization: Bearer <access_token>"
```

---

### 5. List All Users (Admin Only)

**Endpoint:** `GET /api/auth/users`

**Description:** Get list of all users (admin only)

**Headers:**
```
Authorization: Bearer <admin_access_token>
```

**Response (200 OK):**
```json
{
  "count": 3,
  "users": [
    {
      "id": "uuid-1",
      "username": "admin",
      "email": "admin@example.com",
      "role": "admin",
      "is_active": true,
      "created_at": "2025-12-13T06:08:15",
      "updated_at": "2025-12-13T06:08:15"
    },
    ...
  ]
}
```

**Error Responses:**
- `401 Unauthorized` - Invalid or expired token
- `403 Forbidden` - Non-admin user

**Example:**
```bash
curl http://localhost:5001/api/auth/users \
  -H "Authorization: Bearer <admin_token>"
```

---

### 6. Get User by ID

**Endpoint:** `GET /api/auth/users/<user_id>`

**Description:** Get specific user details by ID

**Authorization:**
- Admins can view any user
- Regular users can only view their own profile

**Headers:**
```
Authorization: Bearer <access_token>
```

**Response (200 OK):**
```json
{
  "user": {
    "id": "uuid",
    "username": "john_doe",
    "email": "john@example.com",
    "role": "user",
    "is_active": true,
    "created_at": "2025-12-13T10:30:00",
    "updated_at": "2025-12-13T10:30:00"
  }
}
```

**Error Responses:**
- `401 Unauthorized` - Invalid or expired token
- `403 Forbidden` - Non-admin trying to view another user's profile
- `404 Not Found` - User not found

**Example:**
```bash
curl http://localhost:5001/api/auth/users/<user_id> \
  -H "Authorization: Bearer <access_token>"
```

---

### 7. Update User

**Endpoint:** `PUT /api/auth/users/<user_id>`

**Description:** Update user information

**Authorization:**
- All users can update their own email and password
- Only admins can update role and is_active status
- Only admins can update other users

**Headers:**
```
Authorization: Bearer <access_token>
Content-Type: application/json
```

**Request Body (all fields optional):**
```json
{
  "email": "newemail@example.com",   // Any authenticated user (for self)
  "password": "newpassword123",      // Any authenticated user (for self)
  "role": "admin",                   // Admin only
  "is_active": false                 // Admin only
}
```

**Validation Rules:**
- `email`: Must be unique, validated format
- `password`: Minimum 6 characters
- `role`: Must be one of: admin, user, viewer
- `is_active`: Boolean value

**Response (200 OK):**
```json
{
  "message": "User updated successfully",
  "updated_fields": ["email", "password"],
  "user": {
    "id": "uuid",
    "username": "john_doe",
    "email": "newemail@example.com",
    "role": "user",
    "is_active": true,
    "created_at": "2025-12-13T10:30:00",
    "updated_at": "2025-12-13T11:45:00"
  }
}
```

**Error Responses:**
- `400 Bad Request` - Validation errors (weak password, no fields to update)
- `401 Unauthorized` - Invalid or expired token
- `403 Forbidden` - Insufficient permissions (non-admin trying to change role, or update another user)
- `404 Not Found` - User not found
- `409 Conflict` - Email already exists

**Example:**
```bash
# User updating own email
curl -X PUT http://localhost:5001/api/auth/users/<user_id> \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <access_token>" \
  -d '{"email": "newemail@example.com"}'

# Admin updating user role
curl -X PUT http://localhost:5001/api/auth/users/<user_id> \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <admin_token>" \
  -d '{"role": "admin", "is_active": true}'
```

---

### 8. Delete User

**Endpoint:** `DELETE /api/auth/users/<user_id>`

**Description:** Delete a user (Admin only)

**Authorization:** Admin only

**Restrictions:**
- Admins cannot delete themselves (safety check)

**Headers:**
```
Authorization: Bearer <admin_access_token>
```

**Response (200 OK):**
```json
{
  "message": "User deleted successfully",
  "deleted_user": {
    "id": "uuid",
    "username": "john_doe"
  }
}
```

**Error Responses:**
- `400 Bad Request` - Trying to delete own account
- `401 Unauthorized` - Invalid or expired token
- `403 Forbidden` - Non-admin user
- `404 Not Found` - User not found

**Example:**
```bash
curl -X DELETE http://localhost:5001/api/auth/users/<user_id> \
  -H "Authorization: Bearer <admin_token>"
```

---

## Job Management Endpoints

### 1. Health Check

**Endpoint:** `GET /api/health`

**Description:** Check API and scheduler status (No authentication required)

**Response:**
```json
{
  "status": "healthy",
  "scheduler_running": true,
  "scheduled_jobs_count": 5
}
```

**Example:**
```bash
curl http://localhost:5001/api/health
```

---

### 2. Create a Job

**Endpoint:** `POST /api/jobs`

**Description:** Create a new scheduled job

**Required Role:** Admin or User

**Headers:**
```
Authorization: Bearer <access_token>
Content-Type: application/json
```

**Request Body (required fields):**
```json
{
  "name": "Job Name",                    // Required, must be unique
  "cron_expression": "*/5 * * * *"      // Required, valid cron syntax
}
```

**Request Body (optional fields):**
```json
{
  "target_url": "https://example.com",           // Optional: webhook URL
  "github_owner": "myorg",                       // Optional: GitHub org/user
  "github_repo": "myrepo",                       // Optional: GitHub repo
  "github_workflow_name": "workflow.yml",        // Optional: workflow file
  "metadata": {                                   // Optional: custom JSON
    "environment": "production",
    "branch": "main"
  }
}
```

**Validations:**
- ✅ `name` must be provided and non-empty
- ✅ `name` must be unique (no duplicates allowed)
- ✅ `cron_expression` must be valid cron syntax
---

## Cron Expression Reference

| Expression | Description | Use Case |
|------------|-------------|----------|
| `*/5 * * * *` | Every 5 minutes | Frequent monitoring |
| `*/10 * * * *` | Every 10 minutes | Regular checks |
| `*/30 * * * *` | Every 30 minutes | Moderate frequency |
| `0 * * * *` | Every hour (on the hour) | Hourly tasks |
| `0 */2 * * *` | Every 2 hours | Periodic sync |
| `0 0 * * *` | Daily at midnight | Daily reports |
| `0 2 * * *` | Daily at 2:00 AM | Nightly backups |
| `0 9 * * 1-5` | Weekdays at 9:00 AM | Business hours tasks |
| `0 0 * * 0` | Weekly on Sunday at midnight | Weekly cleanup |
| `0 0 1 * *` | Monthly on the 1st at midnight | Monthly reports |
| `0 0 1 1 *` | Annually on January 1st | Yearly tasks |

**Cron Format:** `minute hour day month day_of_week`
- minute: 0-59
- hour: 0-23
- day: 1-31
- month: 1-12
- day_of_week: 0-6 (0 = Sunday)

---

## Using Authentication in Practice

### Complete Workflow Example

```bash
# Step 1: Login and save token
TOKEN=$(curl -s -X POST http://localhost:5001/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "admin123"}' \
  | python3 -c "import sys, json; print(json.load(sys.stdin)['access_token'])")

# Step 2: Create a job with authentication
curl -X POST http://localhost:5001/api/jobs \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "name": "Nightly Backup",
    "cron_expression": "0 2 * * *",
    "target_url": "https://example.com/backup"
  }'

# Step 3: List all jobs
curl http://localhost:5001/api/jobs \
  -H "Authorization: Bearer $TOKEN"

# Step 4: Update a job (if you own it or are admin)
curl -X PUT http://localhost:5001/api/jobs/<job_id> \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"is_active": false}'

# Step 5: When token expires, refresh it
NEW_TOKEN=$(curl -s -X POST http://localhost:5001/api/auth/refresh \
  -H "Authorization: Bearer $REFRESH_TOKEN" \
  | python3 -c "import sys, json; print(json.load(sys.stdin)['access_token'])")
```

### Frontend Integration (JavaScript)

```javascript
// Login and store tokens
async function login(username, password) {
  const response = await fetch('http://localhost:5001/api/auth/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username, password })
  });
  
  const data = await response.json();
  localStorage.setItem('access_token', data.access_token);
  localStorage.setItem('refresh_token', data.refresh_token);
  return data;
}

// Make authenticated API call
async function createJob(jobData) {
  const token = localStorage.getItem('access_token');
  
  const response = await fetch('http://localhost:5001/api/jobs', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`
    },
    body: JSON.stringify(jobData)
  });
  
  if (response.status === 401) {
    // Token expired, refresh it
    await refreshToken();
    return createJob(jobData); // Retry
  }
  
  return response.json();
}

// Refresh access token
async function refreshToken() {
  const refreshToken = localStorage.getItem('refresh_token');
  
  const response = await fetch('http://localhost:5001/api/auth/refresh', {
    method: 'POST',
    headers: { 'Authorization': `Bearer ${refreshToken}` }
  });
  
  const data = await response.json();
  localStorage.setItem('access_token', data.access_token);
}
```

---

## CORS Configuration

The API supports Cross-Origin Resource Sharing (CORS) for frontend integration.

**Configured Settings:**
- **Allowed Origins:** Configurable via `CORS_ORIGINS` env variable (default: `*`)
- **Allowed Methods:** GET, POST, PUT, DELETE, OPTIONS
- **Allowed Headers:** Content-Type, Authorization
- **Credentials:** Supported
- **Max Age:** 3600 seconds

**Example CORS Test:**
```bash
curl -i -X OPTIONS http://localhost:5001/api/v2/jobs \
  -H "Origin: http://localhost:3000" \
  -H "Access-Control-Request-Method: POST" \
  -H "Access-Control-Request-Headers: Authorization, Content-Type"
```

---

## Architecture & Design

### Technology Stack
- **Framework:** FastAPI
- **Authentication:** JWT (PyJWT) with access/refresh tokens
- **Password Hashing:** passlib 1.7.4 with PBKDF2-SHA256
- **Scheduler:** APScheduler 3.10.4 (leader-only via lock + DB reconciliation)
- **Database:** SQLAlchemy + SQLite (MySQL-ready)
- **Validation:** croniter 2.0.1 for cron expression validation
- **HTTP Client:** requests 2.31.0 for GitHub API and webhooks
- **CORS:** Starlette `CORSMiddleware`

### Key Features

**1. Application Factory Pattern**
- Initialization via `src/fastapi_app/main.py:create_app()`
- Easy testing and configuration management

**2. JWT Authentication & Authorization**
- Token-based authentication with access and refresh tokens
- Role-based access control (Admin, User, Viewer)
- Secure password hashing with PBKDF2-SHA256
- Job ownership tracking and enforcement

**3. Router-Based Architecture**
- Routers organized under `src/fastapi_app/routers/`
- Dependency-injected auth + role checks
- Better code organization

**4. Scheduler Integration**
- Background scheduler starts under FastAPI lifespan (leader-only)
- DB → scheduler reconciliation keeps APScheduler aligned with stored jobs
- CronTrigger for reliable scheduling

**5. Database Design**
- **User Model:** UUID primary keys, role-based fields, password hashing
- **Job Model:** UUID primary keys, ownership tracking (created_by)
- JSON metadata support
- Timestamps for audit trail
- Boolean active flags for soft disable
- Foreign key relationships between users and jobs

**6. Execution Modes**
- **GitHub Actions:** Dispatches workflow via GitHub API
- **Webhook:** Simple GET request to target URL
- Metadata passed as workflow inputs for GitHub Actions

### Error Handling
- Graceful shutdown on SIGINT/SIGTERM
- Scheduler shutdown on app exit
- Database rollback on failures
- Detailed logging for debugging

---

## Development Notes

### Database
- **Storage:** `src/instance/cron_jobs.db` (SQLite, default)
- **Schema:** Managed by SQLAlchemy ORM
- **Migration:** Tables auto-created on first run
- **Production:** Can switch to MySQL by changing `DATABASE_URL`

### Job IDs
- Auto-generated UUIDs via Python's `uuid.uuid4()`
- Stored as 36-character strings
- Used for job identification and scheduler IDs

### Logging
- Console output with INFO level
- Includes timestamps, logger name, and level
- Scheduler events logged separately by APScheduler

### Security Considerations

**Authentication & Authorization:**
- JWT tokens with configurable expiration (1 hour access, 30 days refresh)
- Passwords hashed with PBKDF2-SHA256 (passlib)
- Role-based access control enforced at endpoint level
- Job ownership validation for non-admin users
- Token refresh mechanism for long-lived sessions

**API Security:**
- All endpoints (except health) require authentication
- CORS origins should be restricted in production
- GitHub token stored securely in environment variable
- Sensitive data (passwords) never returned in API responses

**Best Practices:**
- Change default admin password immediately after deployment
- Use strong JWT_SECRET_KEY in production (32+ random characters)
- Enable HTTPS in production (reverse proxy with SSL/TLS)
- Restrict CORS_ORIGINS to specific domains
- Regularly rotate JWT secret keys
- Implement rate limiting for authentication endpoints
- Store tokens securely on client side (httpOnly cookies preferred)

---

## Production Deployment

### Recommended Changes for Production

1. **Use Production WSGI Server**
   ```bash
   pip install gunicorn
   gunicorn -w 4 -b 0.0.0.0:5001 app:app
   ```

2. **Switch to MySQL/PostgreSQL**
   ```bash
   # .env
   DATABASE_URL=mysql://user:password@localhost/cron_jobs
   ```

3. **Configure Security Settings**
   ```bash
   # .env
   SECRET_KEY=your-super-secret-key-32-chars-minimum
   JWT_SECRET_KEY=different-jwt-secret-key-for-tokens
   CORS_ORIGINS=https://yourfrontend.com,https://app.yourfrontend.com
   ```

4. **Change Default Admin Password**
   ```bash
   # After first deployment, login as admin and change password
   # Or create a new admin and delete the default one
   ```

5. **Enable HTTPS**
   - Use reverse proxy (nginx/Apache)
   - SSL/TLS certificates

6. **Environment Variables**
   - Never commit `.env` file
   - Use secret management (AWS Secrets Manager, etc.)

7. **Monitoring**
   - Add application monitoring (Sentry, DataDog)
   - Set up health check endpoint monitoring
   - Configure alerts for scheduler failures

---

## Troubleshooting

### Port Already in Use
```bash
# Find and kill process on port 5001
lsof -ti :5001 | xargs kill -9
```

### Database Locked
```bash
# Remove lock file
rm src/instance/cron_jobs.db-journal
```

### Scheduler Not Starting
- Check logs for APScheduler errors
- Verify database connection
- Ensure no duplicate job IDs

### Jobs Not Executing
- Verify `is_active` is `true`
- Check cron expression is valid
- Verify GitHub token (if using GitHub Actions)
- Check scheduler is running: `GET /api/health`

### CORS Errors
- Verify `CORS_ORIGINS` includes your frontend domain
- Check browser console for specific CORS error
- Ensure OPTIONS preflight request succeeds

---

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Write tests
5. Submit a pull request

---

## Future Enhancements

### Manual Execute Endpoint (Implemented)
- [x] **POST /api/jobs/<job_id>/execute** - Manual job execution (optionally with runtime overrides; not persisted)

### Other Planned Features
- [x] ~~Authentication & authorization~~ **COMPLETED**
- [x] ~~User profile management (update email, change password)~~ **COMPLETED**
- [x] ~~Job execution history/logs~~ **COMPLETED**
- [x] ~~Email notifications on job failure~~ **COMPLETED**
- [ ] Password reset functionality *(Not needed for internal QA team application)*
- [ ] Webhook retry logic with exponential backoff
- [ ] Job dependency management
- [ ] Web UI dashboard
- [ ] Docker containerization
- [ ] Kubernetes deployment configs
**Error Responses:**
- `400 Bad Request` - Invalid JSON, missing fields, invalid cron, duplicate name, or missing target
- `500 Internal Server Error` - Scheduler or database failure

**Example - GitHub Actions Job:**
```bash
curl -X POST http://localhost:5001/api/jobs \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <access_token>" \
  -d '{
    "name": "QA Backend Tests",
    "cron_expression": "0 3 * * *",
    "github_owner": "myorg",
    "github_repo": "test-automation",
    "github_workflow_name": "qa-tests.yml",
    "metadata": {
      "environment": "QA",
      "branch": "master",
      "parallelContainers": "5"
    }
  }'
```

**Example - Webhook Job:**
```bash
curl -X POST http://localhost:5001/api/jobs \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <access_token>" \
  -d '{
    "name": "Hourly Health Check",
    "cron_expression": "0 * * * *",
    "target_url": "https://api.example.com/health"
  }'
```

---

### 3. List All Jobs

**Endpoint:** `GET /api/jobs`

**Description:** Retrieve all scheduled jobs

**Required Role:** All authenticated users (Admin, User, Viewer)

**Headers:**
```
Authorization: Bearer <access_token>
```

**Response (200 OK):**
```json
{
  "count": 2,
  "jobs": [
    {
      "id": "uuid-1",
      "name": "Job 1",
      "cron_expression": "*/5 * * * *",
      "category": "general",
      "is_active": true,
      "last_execution_at": "2025-12-18T06:49:31.105845",
      "next_execution_at": "2025-12-18T07:49:00+09:00",
      ...
    },
    {
      "id": "uuid-2",
      "name": "Job 2",
      "cron_expression": "0 * * * *",
      "category": "dr-testing",
      "is_active": false,
      "last_execution_at": null,
      "next_execution_at": null,
      ...
    }
  ]
}
```

**Example:**
```bash
curl http://localhost:5001/api/jobs \
  -H "Authorization: Bearer <access_token>"
```

---

### 4. Get Specific Job

**Endpoint:** `GET /api/jobs/<job_id>`

**Description:** Retrieve details of a specific job by ID

**Required Role:** All authenticated users (Admin, User, Viewer)

**Headers:**
```
Authorization: Bearer <access_token>
```

**Response (200 OK):**
```json
{
  "job": {
    "id": "8c19f741-1a44-4d4b-b71e-638bb614d184",
    "name": "Daily Backup",
    "cron_expression": "0 2 * * *",
    "target_url": null,
    "github_owner": "myorg",
    "github_repo": "myrepo",
    "github_workflow_name": "backup.yml",
    "metadata": {...},
    "is_active": true,
    "created_at": "2025-12-13T10:30:00",
    "updated_at": "2025-12-13T10:30:00"
  }
}
```

**Error Responses:**
- `404 Not Found` - Job ID does not exist

**Example:**
```bash
curl http://localhost:5001/api/jobs/8c19f741-1a44-4d4b-b71e-638bb614d184 \
  -H "Authorization: Bearer <access_token>"
```

---

### 5. Update a Job

**Endpoint:** `PUT /api/jobs/<job_id>`

**Description:** Update an existing job (all fields optional)

**Required Role:** 
- **Admin**: Can update any job
- **User**: Can update only their own jobs
- **Viewer**: Cannot update jobs (403 Forbidden)

**Headers:**
```
Authorization: Bearer <access_token>
Content-Type: application/json
```

**Request Body (all optional):**
```json
{
  "name": "Updated Job Name",
  "cron_expression": "*/10 * * * *",
  "target_url": "https://new-url.com",
  "github_owner": "neworg",
  "github_repo": "newrepo",
  "github_workflow_name": "new-workflow.yml",
  "metadata": {
    "new_key": "new_value"
  },
  "is_active": false
}
```

**Validations:**
- ✅ If `name` provided, must be non-empty and unique (excluding current job)
- ✅ If `cron_expression` provided, must be valid cron syntax
- ✅ Job must have at least one target (either `target_url` or complete GitHub config)
- ✅ Request must have `Content-Type: application/json`
- ✅ Scheduler automatically updated when job properties change
- ✅ Setting `is_active: false` removes job from scheduler but keeps it in database

**Response (200 OK):**
```json
{
  "message": "Job updated successfully",
  "job": {
    "id": "8c19f741-1a44-4d4b-b71e-638bb614d184",
    "name": "Updated Job Name",
    ...
  }
}
```

**Error Responses:**
- `400 Bad Request` - Invalid JSON, empty name, invalid cron, duplicate name, or missing target
- `404 Not Found` - Job ID does not exist
- `500 Internal Server Error` - Scheduler update failed

**Example - Update cron expression:**
```bash
curl -X PUT http://localhost:5001/api/jobs/8c19f741-1a44-4d4b-b71e-638bb614d184 \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <access_token>" \
  -d '{
    "cron_expression": "*/15 * * * *"
  }'
```

**Example - Disable job:**
```bash
curl -X PUT http://localhost:5001/api/jobs/8c19f741-1a44-4d4b-b71e-638bb614d184 \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <access_token>" \
  -d '{
    "is_active": false
  }'
```

---

### 6. Delete a Job

**Endpoint:** `DELETE /api/jobs/<job_id>`

**Description:** Permanently delete a job from database and scheduler

**Required Role:**
- **Admin**: Can delete any job
- **User**: Can delete only their own jobs
- **Viewer**: Cannot delete jobs (403 Forbidden)

**Headers:**
```
Authorization: Bearer <access_token>
```

**Response (200 OK):
```json
{
  "message": "Job deleted successfully",
  "deleted_job": {
    "id": "8c19f741-1a44-4d4b-b71e-638bb614d184",
    "name": "Daily Backup"
  }
}
```

**Error Responses:**
- `404 Not Found` - Job ID does not exist
- `500 Internal Server Error` - Database deletion failed

**Example:**
```bash
curl -X DELETE http://localhost:5001/api/jobs/8c19f741-1a44-4d4b-b71e-638bb614d184 \
  -H "Authorization: Bearer <access_token>"
```

---

### 7. View Job Execution History

**Endpoint:** `GET /api/jobs/<job_id>/executions`

**Description:** Get complete execution history for a specific job

**Required Role:** All authenticated users

**Headers:**
```
Authorization: Bearer <access_token>
```

**Query Parameters:**
- `status` (optional) - Filter by status: `success`, `failed`, `running`
- `trigger_type` (optional) - Filter by trigger type: `scheduled`, `manual`
- `limit` (optional) - Limit results (default: 50)
- `from` (optional) - ISO date/datetime (inclusive, based on `started_at`)
- `to` (optional) - ISO date/datetime (exclusive, based on `started_at`). Date-only treated as inclusive day.

**Response (200 OK):**
```json
{
  "job_id": "9d4c2282-9b95-4f79-823b-43c73fc3f7c7",
  "job_name": "Daily Test Job",
  "total_executions": 5,
  "executions": [
    {
      "id": "exec-uuid-1",
      "job_id": "9d4c2282-9b95-4f79-823b-43c73fc3f7c7",
      "status": "success",
      "trigger_type": "scheduled",
      "started_at": "2025-12-13T10:00:00+00:00",
      "completed_at": "2025-12-13T10:00:15+00:00",
      "duration_seconds": 15.234,
      "execution_type": "webhook",
      "target": "https://example.com/webhook",
      "response_status": 200,
      "error_message": null,
      "output": "Success response body"
    }
  ]
}
```

**Example:**
```bash
curl http://localhost:5001/api/jobs/<job_id>/executions \
  -H "Authorization: Bearer <access_token>" | jq .
```

---

### 8. Get Specific Execution Details

**Endpoint:** `GET /api/jobs/<job_id>/executions/<execution_id>`

**Description:** Get detailed information about a specific job execution

**Required Role:** All authenticated users

**Headers:**
```
Authorization: Bearer <access_token>
```

**Response (200 OK):**
```json
{
  "execution": {
    "id": "exec-uuid-1",
    "job_id": "9d4c2282-9b95-4f79-823b-43c73fc3f7c7",
    "job_name": "Daily Test Job",
    "status": "success",
    "trigger_type": "scheduled",
    "started_at": "2025-12-13T10:00:00+00:00",
    "completed_at": "2025-12-13T10:00:15+00:00",
    "duration_seconds": 15.234,
    "execution_type": "webhook",
    "target": "https://example.com/webhook",
    "response_status": 200,
    "error_message": null,
    "output": "Success response body"
  }
}
```

**Error Responses:**
- `404 Not Found` - Job or execution not found

**Example:**
```bash
curl http://localhost:5001/api/jobs/<job_id>/executions/<execution_id> \
  -H "Authorization: Bearer <access_token>" | jq .
```

---

### 9. Get Execution Statistics

**Endpoint:** `GET /api/jobs/<job_id>/executions/stats`

**Description:** Get summary statistics for all executions of a job

**Required Role:** All authenticated users

**Headers:**
```
Authorization: Bearer <access_token>
```

**Response (200 OK):**
```json
{
  "job_id": "9d4c2282-9b95-4f79-823b-43c73fc3f7c7",
  "job_name": "Daily Test Job",
  "latest_execution": {
    "status": "success",
    "completed_at": "2025-12-13T10:00:15+00:00"
  },
  "statistics": {
    "total_executions": 25,
    "success_count": 23,
    "failed_count": 2,
    "running_count": 0,
    "success_rate": 92.0,
    "average_duration_seconds": 12.5
  }
}
```

**Example:**
```bash
curl http://localhost:5001/api/jobs/<job_id>/executions/stats \
  -H "Authorization: Bearer <access_token>" | jq .
```

---

## Email Notifications

### Overview

The job scheduler supports **optional email notifications** when jobs fail. Email notifications are **disabled by default** - you must explicitly enable them for each job.

When enabled, you can:
- Send email alerts on job failure with detailed error information
- Optionally receive success confirmations for critical jobs
- Configure different email recipients per job
- Use HTML or plain text email format

### Features

- **Explicit Toggle**: Email notifications disabled by default, must be explicitly enabled per job
- **Failure Alerts**: Automatically send emails when a job fails
- **Success Notifications**: Optional email confirmations for critical jobs (when enabled)
- **HTML & Text Emails**: Rich HTML emails with fallback plain text
- **Error Details**: Emails include job name, ID, error message, and execution details
- **Multiple Recipients**: Configure different email addresses per job
- **SMTP Support**: Works with Gmail, Outlook, custom SMTP servers

### Configuration

Email notifications are configured via environment variables in your `.env` file:

```bash
# Enable/disable email notifications globally
MAIL_ENABLED=True

# SMTP Server Settings (Gmail example)
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USE_TLS=True
MAIL_USERNAME=your-email@gmail.com
MAIL_PASSWORD=your-app-password  # Use app-specific password for Gmail
MAIL_DEFAULT_SENDER=noreply@cronjobscheduler.local

# Alternative: Custom SMTP Server
MAIL_SERVER=smtp.company.com
MAIL_PORT=587
MAIL_USERNAME=user@company.com
MAIL_PASSWORD=your-password
```

### Gmail Setup

To use Gmail for email notifications:

1. **Enable 2-Step Verification** in your Google Account
2. **Generate App Password**:
   - Go to [Google Account Security](https://myaccount.google.com/security)
   - Create an **App Password** for "Mail" and "Windows Computer"
   - Copy the generated 16-character password
3. **Update .env file**:
   ```bash
   MAIL_USERNAME=your-email@gmail.com
   MAIL_PASSWORD=your-16-character-app-password
   ```

### Job Configuration

When creating or updating a job, include the email notification settings:

**Create Job WITH Email Notifications (Enabled):**

```json
{
  "name": "Critical Data Sync Job",
  "cron_expression": "0 2 * * *",
  "target_url": "https://api.example.com/sync",
  "enable_email_notifications": true,
  "notification_emails": ["admin@example.com", "devops@example.com"],
  "notify_on_success": false
}
```

**Create Job WITHOUT Email Notifications (Disabled - Default):**

```json
{
  "name": "Regular Sync Job",
  "cron_expression": "0 3 * * *",
  "target_url": "https://api.example.com/sync"
}
```
Note: `enable_email_notifications` defaults to `false`. No email fields needed if disabled.

**Update Job to Enable Notifications:**

```json
{
  "enable_email_notifications": true,
  "notification_emails": ["alerts@example.com"],
  "notify_on_success": false
}
```

**Update Job to Disable Notifications:**

```json
{
  "enable_email_notifications": false
}
```
Note: When disabling, email addresses are cleared automatically.

### Email Recipients

When `enable_email_notifications` is `true`, you can specify one or more recipients:

```json
{
  "enable_email_notifications": true,
  "notification_emails": [
    "admin@example.com",
    "devops@example.com",
    "alerts@example.com"
  ]
}
```

### Email Content

**Failure Email Example:**

Subject: `🔴 Job Failure Alert: Critical Data Sync Job`

```
Job Execution Failed
====================

Job Name: Critical Data Sync Job
Job ID: 9d4c2282-9b95-4f79-823b-43c73fc3f7c7
Error: Webhook returned status 500

Please review your job configuration and logs to identify and resolve the issue.
```

**Success Email Example:**

Subject: `✅ Job Success: Critical Data Sync Job`

```
Job Completed Successfully
==========================

Job Name: Critical Data Sync Job
Job ID: 9d4c2282-9b95-4f79-823b-43c73fc3f7c7
Duration: 45.23 seconds

No action is required. This is an informational notification.
```

### Best Practices

1. **Use Distribution Lists**: Use email groups/lists instead of individual addresses for better team communication
2. **Production Setup**: Use dedicated SMTP accounts, not personal emails
3. **Error Monitoring**: Enable success notifications only for critical jobs to avoid email fatigue
4. **Test Configuration**: Send a test email by intentionally failing a job after setup
5. **Log Monitoring**: Check application logs to confirm email delivery attempts

### Troubleshooting

**No emails being sent?**

1. Verify `MAIL_ENABLED=True` in your `.env` file
2. Check `MAIL_USERNAME` and `MAIL_PASSWORD` are correct
3. Ensure job has `notification_emails` configured
4. Check application logs for SMTP errors: `grep -i "mail\|email" app.log`
5. Verify firewall/network allows outbound SMTP connections on `MAIL_PORT`

**Gmail shows "Less secure app" error?**

- Use **App Passwords** instead of your regular Gmail password
- Enable 2-Step Verification first, then create an App Password

**Custom SMTP not working?**

- Verify SMTP server address and port
- Test credentials with `telnet MAIL_SERVER MAIL_PORT`
- Check if authentication is required and certificate validation is needed

---

## Job Execution History

## Validation Summary

### Global Validations (All Endpoints)
- ✅ **Content-Type Check** - Rejects requests without `application/json` header (POST/PUT only)
- ✅ **JSON Parsing** - Validates request body is valid JSON

### Field-Specific Validations


| Field | Validations |
|-------|------------|
| `name` | • Required on creation<br>• Must be non-empty string<br>• Must be unique across all jobs<br>• Uniqueness checked excluding current job on update |
| `cron_expression` | • Required on creation<br>• Must be valid cron syntax (validated using croniter)<br>• Examples: `*/5 * * * *`, `0 2 * * *` |
| `target_url` | • Optional<br>• Can be null or valid URL string<br>• Required if GitHub config not provided |
| `github_owner` | • Optional<br>• Part of GitHub Actions trio<br>• Must provide all three (owner, repo, workflow) or none |
| `github_repo` | • Optional<br>• Part of GitHub Actions trio |
| `github_workflow_name` | • Optional<br>• Part of GitHub Actions trio<br>• Should be workflow file name (e.g., `test.yml`) |
| `metadata` | • Optional<br>• Must be valid JSON object<br>• Stored as JSON text in database |
| `is_active` | • Optional (defaults to `true` on creation)<br>• Boolean value<br>• `false` removes from scheduler without deletion |

### Business Logic Validations
- ✅ **Dual Target Validation** - Job must have EITHER `target_url` OR complete GitHub Actions configuration
- ✅ **Scheduler Sync** - Changes to cron, targets, or metadata trigger automatic scheduler re-registration
- ✅ **Active State Management** - Inactive jobs exist in database but not in scheduler

---

---

## Cron Expression Examples

- `*/5 * * * *` - Every 5 minutes
- `0 * * * *` - Every hour
- `0 0 * * *` - Daily at midnight
- `0 2 * * *` - Daily at 2:00 AM
- `0 0 * * 0` - Weekly on Sunday at midnight
- `0 0 1 * *` - Monthly on the 1st at midnight

## Development Notes

### Database
- SQLite database stored in `src/instance/cron_jobs.db` (default)
- Key tables: `users`, `jobs`, `job_executions`, `notifications`, `user_notification_preferences`
- Jobs track ownership via `created_by` foreign key to users
- All IDs are auto-generated UUIDs

### Authentication
- Default admin account: username=`admin`, password=`admin123`
- Access tokens expire after 1 hour
- Refresh tokens expire after 30 days
- Passwords hashed with PBKDF2-SHA256

### Scheduler
- Runs in background and persists jobs across restarts
- Only loads active jobs (`is_active=true`)
- Automatically syncs with database changes

### Logging
- Console output with INFO level
- Includes authentication events (login, registration)
- Job execution and scheduler events logged

---

## Quick Reference: Authentication

### Default Admin Credentials
```
Username: admin
Password: admin123
Email: admin@example.com
Role: admin
```
**⚠️ CHANGE THESE IN PRODUCTION!**

### User Roles Summary

| Action | Admin | User | Viewer |
|--------|:-----:|:----:|:------:|
| View all jobs | ✅ | ✅ | ✅ |
| Create jobs | ✅ | ✅ | ❌ |
| Update own jobs | ✅ | ✅ | ❌ |
| Update any job | ✅ | ❌ | ❌ |
| Delete own jobs | ✅ | ✅ | ❌ |
| Delete any job | ✅ | ❌ | ❌ |
| Register users | ✅ | ❌ | ❌ |
| List all users | ✅ | ❌ | ❌ |

### Common Error Codes
- **401 Unauthorized**: Missing, invalid, or expired token
- **403 Forbidden**: Valid token but insufficient permissions (wrong role or not owner)
- **409 Conflict**: Username or email already exists (registration)

---

## API Endpoints Summary

### Authentication Endpoints
| Method | Endpoint | Auth Required | Role Required | Description |
|--------|----------|---------------|---------------|-------------|
| POST | `/api/auth/login` | No | - | Login and get tokens |
| POST | `/api/auth/register` | Yes | Admin | Register new user |
| POST | `/api/auth/refresh` | Yes (refresh token) | - | Refresh access token |
| GET | `/api/auth/me` | Yes | - | Get current user info |
| GET | `/api/auth/users` | Yes | Admin | List all users |
| GET | `/api/auth/users/<user_id>` | Yes | Admin or Self | Get user by ID |
| PUT | `/api/auth/users/<user_id>` | Yes | Admin or Self | Update user |
| DELETE | `/api/auth/users/<user_id>` | Yes | Admin | Delete user |

### Job Management Endpoints
| Method | Endpoint | Auth Required | Role Required | Description |
|--------|----------|---------------|---------------|-------------|
| GET | `/api/health` | No | - | Health check |
| POST | `/api/jobs` | Yes | Admin, User | Create job |
| GET | `/api/jobs` | Yes | All | List all jobs |
| GET | `/api/jobs/<id>` | Yes | All | Get job details |
| PUT | `/api/jobs/<id>` | Yes | Admin, Owner | Update job |
| DELETE | `/api/jobs/<id>` | Yes | Admin, Owner | Delete job |

### Job Category Endpoints
| Method | Endpoint | Auth Required | Role Required | Description |
|--------|----------|---------------|---------------|-------------|
| GET | `/api/job-categories` | Yes | All | List categories |
| POST | `/api/job-categories` | Yes | Admin | Create category |
| PUT | `/api/job-categories/<id>` | Yes | Admin | Update category (slug derived from name) |
| DELETE | `/api/job-categories/<id>` | Yes | Admin | Disable category |

### Job Execution History Endpoints
| Method | Endpoint | Auth Required | Role Required | Description |
|--------|----------|---------------|---------------|-------------|
| GET | `/api/jobs/<id>/executions` | Yes | All | View execution history |
| GET | `/api/jobs/<id>/executions/<exec_id>` | Yes | All | Get execution details |
| GET | `/api/jobs/<id>/executions/stats` | Yes | All | Get execution statistics |

### Global Execution Endpoints
| Method | Endpoint | Auth Required | Role Required | Description |
|--------|----------|---------------|---------------|-------------|
| GET | `/api/executions` | Yes | All | List executions (supports `page`/`limit` and `from`/`to`) |
| GET | `/api/executions/<exec_id>` | Yes | All | Get execution by ID |
| GET | `/api/executions/statistics` | Yes | All | Aggregated stats (supports `from`/`to`) |

### Notification Endpoints
| Method | Endpoint | Auth Required | Role Required | Description |
|--------|----------|---------------|---------------|-------------|
| GET | `/api/notifications` | Yes | All | List notifications (supports `unread_only` and `from`/`to`) |
| GET | `/api/notifications/unread-count` | Yes | All | Unread count (supports `from`/`to`) |
| PUT | `/api/notifications/<id>/read` | Yes | All | Mark notification as read |
| PUT | `/api/notifications/read-all` | Yes | All | Mark all notifications as read |
| DELETE | `/api/notifications/<id>` | Yes | All | Delete notification |

## License

MIT
