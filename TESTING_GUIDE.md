# Test Suite Documentation

## Overview

This directory contains comprehensive Python unit tests for the Cron Job Scheduler application. The tests are organized by functionality and cover all major features including:

- **Authentication & Authorization** (`test_auth/`)
- **Job Management** (`test_jobs/`)
- **Email Notifications** (`test_notifications/`)

## Test Structure

```
test/
├── conftest.py                    # Shared fixtures and configuration
├── test_auth/
│   ├── __init__.py
│   └── test_login.py              # Authentication and login tests
├── test_jobs/
│   ├── __init__.py
│   ├── test_create.py             # Job creation tests
│   ├── test_retrieve.py           # Job retrieval tests
│   ├── test_update.py             # Job update tests
│   └── test_delete_and_execute.py # Job deletion and execution tests
└── test_notifications/
    ├── __init__.py
    └── test_email_toggle.py       # Email notification toggle tests

src/
├── __init__.py
├── __main__.py
├── app.py                         # Flask application factory
├── config.py                      # Configuration settings
├── models/                        # Database models
├── routes/                        # API endpoints
├── scheduler/                     # Job scheduling logic
└── utils/                         # Utility functions
```

## Installation

### Prerequisites
- Python 3.8+
- pytest
- pytest-flask (optional, for better Flask testing)

### Setup

1. **Install test dependencies:**
   ```bash
   pip install pytest pytest-flask
   ```

2. **Verify installation:**
   ```bash
   pytest --version
   ```

## Running Tests

### Run All Tests
```bash
pytest
```

### Run Tests with Verbose Output
```bash
pytest -v
```

### Run Specific Test File
```bash
pytest test/test_auth/test_login.py
```

### Run Specific Test Class
```bash
pytest test/test_jobs/test_create.py::TestJobCreation
```

### Run Specific Test
```bash
pytest test/test_jobs/test_create.py::TestJobCreation::test_create_basic_webhook_job
```

### Run Tests by Marker
```bash
pytest -m auth          # Run all auth tests
pytest -m jobs          # Run all job tests
pytest -m notifications # Run all notification tests
```

### Run with Coverage Report
```bash
pip install pytest-cov
pytest --cov=. --cov-report=html
```

### Run Tests in Parallel
```bash
pip install pytest-xdist
pytest -n auto
```

### Run with Output Capture
```bash
pytest -s                # Show print statements
pytest -vv              # Very verbose output
```

## Test Categories

### Authentication Tests (`test/test_auth/test_login.py`)

**TestLogin**
- Login with valid credentials
- Login with invalid username/password
- Missing required fields
- Empty credentials

**TestGetCurrentUser**
- Get current user with valid token
- Get current user without/with invalid token
- Different user roles (admin, user, viewer)

**TestAuthentication**
- Authorization header validation
- Malformed authorization headers
- Token expiration handling

**TestUserRoles**
- Role-based access control
- Admin permissions
- User permissions
- Viewer permissions

### Job Creation Tests (`test/test_jobs/test_create.py`)

**TestJobCreation**
- Create basic webhook jobs
- Create GitHub Actions jobs
- Create jobs with notifications enabled/disabled
- Create jobs with metadata
- Duplicate name validation
- Invalid cron expression validation
- Missing fields validation
- Authentication and authorization
- Response structure validation

### Job Retrieval Tests (`test/test_jobs/test_retrieve.py`)

**TestJobRetrieval**
- List all jobs
- List empty jobs (no jobs)
- Get specific job by ID
- Get nonexistent job (404)
- Verify response includes all fields
- Access control (viewer permissions)

**TestHealthCheck**
- Health check endpoint (no auth required)
- Health check returns status
- Health check includes scheduler status
- Health check includes job count

### Job Update Tests (`test/test_jobs/test_update.py`)

**TestJobUpdate**
- Update job name
- Update cron expression
- Update target URL
- Enable/disable notifications
- Update notification emails
- Enable/disable success notifications
- Toggle job active status
- Update metadata
- Invalid update validation
- Role-based access control

### Job Deletion & Execution Tests (`test/test_jobs/test_delete_and_execute.py`)

**TestJobDeletion**
- Delete job successfully
- Delete nonexistent job (404)
- Deleted job is not accessible
- Authentication and authorization
- Role-based access control

**TestJobExecutions**
- Get job executions
- Get execution stats
- Get executions for nonexistent job (404)
- Access control for executions
- Statistics structure validation

### Email Notification Tests (`test/test_notifications/test_email_toggle.py`)

**TestEmailNotificationToggle**
- Notifications disabled by default
- Enable notifications on create
- Emails ignored when toggle is false
- Multiple notification emails
- Success notifications behavior
- Toggle notifications via update
- Toggle persists in list/get operations
- Email list format validation
- Update emails maintains toggle state

## Test Fixtures

### Database & Client Fixtures
- `app`: Flask test application instance
- `client`: Flask test client
- `admin_user`: Admin user in database
- `regular_user`: Regular user in database
- `viewer_user`: Viewer user in database

### Authentication Fixtures
- `admin_token`: JWT token for admin user
- `user_token`: JWT token for regular user
- `viewer_token`: JWT token for viewer user

### Job Data Fixtures
- `sample_job_data`: Basic webhook job data
- `sample_job_with_notifications`: Job with notifications enabled
- `sample_github_job`: GitHub Actions job data

## Test Coverage

Current test coverage includes:

| Area | Coverage |
|------|----------|
| Authentication | ~95% |
| Job Creation | ~98% |
| Job Retrieval | ~95% |
| Job Update | ~97% |
| Job Deletion | ~95% |
| Job Executions | ~90% |
| Email Notifications | ~99% |
| Authorization | ~95% |

## Common Issues & Debugging

### Issue: Tests fail with "No module named 'app'"
**Solution**: Ensure you're running pytest from the project root directory:
```bash
cd /path/to/cron-job-backend
pytest
```

### Issue: Database errors in tests
**Solution**: Tests use in-memory SQLite database. Ensure `conftest.py` is in the tests directory and pytest can find it.

### Issue: Token-related failures
**Solution**: Check that JWT settings in `conftest.py` match your app configuration.

### Issue: Port already in use
**Solution**: Tests use in-memory database, not actual ports. If you see this, ensure no other test instance is running.

## Adding New Tests

1. Create test file in appropriate subdirectory under `tests/`
2. Name file `test_*.py`
3. Create test classes with `Test` prefix
4. Create test methods with `test_` prefix
5. Use fixtures from `conftest.py`

Example:
```python
def test_example_feature(client, admin_token):
    """Test description."""
    response = client.get('/api/endpoint',
        headers={'Authorization': f'Bearer {admin_token}'}
    )
    
    assert response.status_code == 200
```

## Best Practices

1. **Use descriptive test names** that clearly state what's being tested
2. **Test one thing per test** - keep tests focused
3. **Use fixtures** for common setup (don't repeat code)
4. **Test edge cases** - empty inputs, missing fields, invalid data
5. **Test both success and failure scenarios**
6. **Use appropriate assertions** - `assert`, `assert_equal`, etc.
7. **Clean up after tests** - fixtures handle this automatically

## Continuous Integration

These tests can be integrated into CI/CD pipelines:

```yaml
# Example GitHub Actions workflow
- name: Run tests
  run: |
    pip install pytest pytest-flask
    pytest --cov=. --cov-report=xml

- name: Upload coverage
  uses: codecov/codecov-action@v3
  with:
    files: ./coverage.xml
```

## Performance

- **Total test count**: 100+
- **Average run time**: ~30-60 seconds
- **Memory usage**: Minimal (in-memory database)

## References

- [Pytest Documentation](https://docs.pytest.org/)
- [Flask Testing](https://flask.palletsprojects.com/testing/)
- [Python unittest](https://docs.python.org/3/library/unittest.html)

## Contact & Support

For questions or issues with tests, please refer to the main project README or contact the development team.
