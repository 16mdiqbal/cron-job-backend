# Project Folder Structure

This document describes the reorganized folder structure of the cron-job-backend project.

## Directory Layout

```
cron-job-backend/
├── src/                          # Source code directory
│   ├── __init__.py
│   ├── __main__.py               # Entry point for running as module
│   ├── app.py                    # Flask application factory
│   ├── config.py                 # Configuration settings
│   ├── models/                   # Database models
│   │   ├── __init__.py
│   │   ├── job.py                # Job model
│   │   ├── user.py               # User model
│   │   └── job_execution.py       # Job execution history
│   ├── routes/                   # API endpoint blueprints
│   │   ├── __init__.py
│   │   ├── auth.py               # Authentication endpoints
│   │   └── jobs.py               # Job management endpoints
│   ├── scheduler/                # Job scheduling logic
│   │   ├── __init__.py
│   │   └── job_executor.py       # Job execution handler
│   └── utils/                    # Utility functions
│       ├── __init__.py
│       ├── auth.py               # Authentication utilities
│       └── email.py              # Email notification handling
│
├── test/                         # Test directory
│   ├── conftest.py               # Pytest configuration and shared fixtures
│   ├── test_auth/                # Authentication tests
│   │   ├── __init__.py
│   │   └── test_login.py         # Login and token validation tests
│   ├── test_jobs/                # Job management tests
│   │   ├── __init__.py
│   │   ├── test_create.py        # Job creation tests
│   │   ├── test_retrieve.py      # Job retrieval tests
│   │   ├── test_update.py        # Job update tests
│   │   └── test_delete_and_execute.py  # Job deletion and execution tests
│   └── test_notifications/       # Notification tests
│       ├── __init__.py
│       └── test_email_toggle.py  # Email notification toggle tests
│
├── instance/                     # Flask instance folder (runtime data)
├── venv/                         # Python virtual environment
├── .env                          # Environment variables (not in git)
├── .env.example                  # Environment variables template
├── .gitignore                    # Git ignore file
├── .pytest_cache/                # Pytest cache directory
├── pytest.ini                    # Pytest configuration
├── requirements.txt              # Python dependencies
├── config.py                     # Project configuration
├── create_admin.py               # Script to create initial admin user
├── start_server.sh               # Shell script to start the server
├── README.md                     # Project documentation
├── TESTING_GUIDE.md              # Testing guide and instructions
├── TESTING.md                    # Testing overview
├── TEST_EXECUTION_SUMMARY.md     # Test execution results and summary
├── architecture.md               # Architecture documentation
└── architecture.md               # Architecture documentation
```

## Key Directories

### src/ - Source Code
Contains all application source code organized by functionality:
- **app.py** - Flask application factory and initialization
- **config.py** - Configuration settings and environment-specific settings
- **models/** - SQLAlchemy database models
- **routes/** - Flask blueprints for API endpoints
- **scheduler/** - APScheduler job scheduling logic
- **utils/** - Utility functions for auth, email, etc.

### test/ - Test Suite
Contains comprehensive pytest test suite:
- **conftest.py** - Shared fixtures, test database setup, and configuration
- **test_auth/** - Authentication and authorization tests
- **test_jobs/** - Job CRUD operation tests
- **test_notifications/** - Email notification feature tests

### Root Level Files
- **pytest.ini** - Pytest configuration (pythonpath set to src/)
- **requirements.txt** - Python package dependencies
- **start_server.sh** - Script to start the Flask development server
- **create_admin.py** - Utility script to create initial admin user
- **README.md** - Project documentation
- **TESTING_GUIDE.md** - Comprehensive testing guide

## Running the Application

### Development Server
```bash
# Option 1: Using start_server.sh
./start_server.sh

# Option 2: Direct Python execution
python -m src

# Option 3: Using Flask CLI
flask --app src.app run
```

### Create Admin User
```bash
python create_admin.py
```

## Running Tests

```bash
# Run all tests
pytest

# Run specific test directory
pytest test/test_auth/ -v

# Run with coverage
pytest --cov=src --cov-report=html

# Run specific test
pytest test/test_jobs/test_create.py::TestJobCreation::test_create_basic_webhook_job -v
```

## Import Structure

With the new folder structure, imports work as follows:

**From within src/**
```python
from models import db
from models.job import Job
from routes.jobs import jobs_bp
from scheduler import scheduler
from utils.email import mail
```

**From test/ (via conftest.py)**
```python
from app import create_app
from models import db
```

The pytest.ini file sets `pythonpath = src` so that pytest can properly resolve imports from the src directory.

## Migration Notes

- All source code has been moved to `src/` folder
- Test directory renamed from `tests/` to `test/`
- pytest.ini updated to set pythonpath to `src/`
- create_admin.py updated with path configuration
- start_server.sh updated to run module as `python -m src`
- conftest.py updated to import from src directory

## Benefits of This Structure

1. **Clear Separation**: Source code and tests are clearly separated
2. **Maintainability**: Organized by functionality (auth, jobs, notifications)
3. **Scalability**: Easy to add new modules or test categories
4. **Convention**: Follows Python package best practices
5. **Testing**: Easier to find and maintain tests for each feature
6. **CI/CD Ready**: Works well with continuous integration systems

## File Size Summary

| Directory | Purpose | Size |
|-----------|---------|------|
| src/ | All application source code | ~1,200 lines |
| test/ | Complete test suite | ~1,750 lines |
| venv/ | Python virtual environment | Not counted |
| instance/ | Runtime data and databases | Dynamic |

## Total Test Coverage

- **Test Count**: 94 tests
- **Passing**: 94 (100%)
- **Code Coverage**: 61%
- **Execution Time**: ~3.3 seconds
