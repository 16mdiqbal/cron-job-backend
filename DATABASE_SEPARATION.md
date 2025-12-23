# Database Configuration Strategy for FastAPI Migration

## Overview

During the Flask-to-FastAPI migration, FastAPI supports running on either:
- a **shared database** (default, keeps users/auth in sync across Flask + FastAPI), or
- a **separate database** (optional, useful for isolated migration work).

For tests, FastAPI defaults to an isolated database to avoid interference from background threads/components.

## Database Structure

### 1. Flask Database (Original)
- **Path**: `src/instance/cron_jobs.db`
- **Used by**: Flask application
- **Purpose**: Production database for existing Flask endpoints

### 2. FastAPI Database (Default = Shared)
- **Path**: Same as Flask by default (`DATABASE_URL` / `src/instance/cron_jobs.db`)
- **Used by**: FastAPI application
- **Purpose**: Keeps user/auth and data parity simple during side-by-side migration

### 3. FastAPI Database (Optional = Separate)
- **Example Path**: `src/instance/fastapi_cron_jobs.db`
- **Used by**: FastAPI application (development/migration)
- **Purpose**: Optional isolation during migration (enable via `FASTAPI_DATABASE_URL`)

### 4. FastAPI Test Database (Default when `TESTING=true`)
- **Path**: `src/instance/fastapi_test.db`
- **Used by**: FastAPI pytest tests
- **Purpose**: Isolated test database to prevent Flask scheduler interference

## Why Use a Separate Database?

### Problem
During tests, Flask's background scheduler thread continues running and tries to access the database. When FastAPI tests tear down their database, Flask's scheduler throws errors:
```
sqlite3.OperationalError: no such table: jobs
```

### Solution
Use a separate FastAPI database (especially for tests) to isolate from Flask components:
- ✅ **Clean isolation**: Each stack manages its own database
- ✅ **No interference**: Flask scheduler doesn't affect FastAPI tests
- ✅ **Safe migration**: Both systems can run independently
- ✅ **Easy rollback**: Flask continues using original database

## Database Initialization

### Initialize Optional FastAPI Databases
```bash
# Run initialization script
python scripts/init_fastapi_db.py

# Or manually:
python -c "from scripts.init_fastapi_db import init_fastapi_database; init_fastapi_database()"
```

This creates databases that can be used when you opt into separation:
1. `fastapi_cron_jobs.db` - Optional migration DB
2. `fastapi_test.db` - Default test DB (when `TESTING=true`)

### Schema Synchronization
Both databases use the **same SQLAlchemy models** from `src/models/`, ensuring identical schema:
- Users
- Jobs
- Job Executions
- Notifications
- Job Categories
- PIC Teams
- Slack Settings
- User Preferences

## Configuration

### Environment Variables
```bash
# Enable testing mode (uses fastapi_test.db)
export TESTING=true

# Disable Flask scheduler during tests
export SCHEDULER_ENABLED=false

# (Optional) Run FastAPI on a separate DB during migration
export FASTAPI_DATABASE_URL="sqlite:///src/instance/fastapi_cron_jobs.db"
```

### FastAPI Settings
The `Settings` class:
1. Detects `TESTING=true` and defaults FastAPI to `src/instance/fastapi_test.db`
2. Uses the shared Flask database by default when not testing
3. Lets you override FastAPI's database via `FASTAPI_DATABASE_URL`
4. Uses async SQLite driver (`sqlite+aiosqlite://`) for async connections

```python
# src/fastapi_app/config.py
if self.testing:
    # Use separate test database
    test_db_path = 'src/instance/fastapi_test.db'
else:
    # Default to the shared Flask database (override via FASTAPI_DATABASE_URL)
    self.fastapi_database_url = self.database_url
```

## Running Tests

### FastAPI Tests (No Flask interference)
```bash
# Tests use fastapi_test.db automatically
pytest tests_fastapi -v
```

### Flask Tests (Original database)
```bash
# Tests use in-memory database
pytest test/test_auth/ -v
```

## Migration Timeline

### Phase 1-3 (Current)
- **Flask**: Uses `cron_jobs.db`
- **FastAPI**: Uses `cron_jobs.db` by default (optional `FASTAPI_DATABASE_URL` for separation)
- **Status**: Running side-by-side

### Phase 4-7 (Migration)
- Both databases maintained
- Data can be synced if needed
- Gradual endpoint migration

### Phase 8 (Cutover)
- Migrate to single shared database
- Options:
  - **Option A**: FastAPI takes over `cron_jobs.db`
  - **Option B**: Merge both into new database
  - **Option C**: Keep FastAPI database, migrate Flask data

## Data Migration (When Needed)

If you need to sync data between databases:

```python
# Copy data from Flask DB to FastAPI DB
python scripts/migrate_data_to_fastapi.py

# Or copy specific tables
python scripts/migrate_data_to_fastapi.py --tables users,jobs
```

## Troubleshooting

### Issue: Tests freeze or hang
**Cause**: Flask scheduler trying to access torn-down database

**Solution**: ✅ Already fixed with separate databases

### Issue: Database not found
**Cause**: FastAPI database not initialized

**Solution**:
```bash
python scripts/init_fastapi_db.py
```

### Issue: Schema mismatch
**Cause**: Models updated but database not recreated

**Solution**:
```bash
# Reinitialize databases
python scripts/init_fastapi_db.py
```

## Best Practices

1. **Always initialize** FastAPI databases after pulling changes
2. **Don't modify** Flask database directly during migration
3. **Run init script** after model changes
4. **Use environment variables** to control which database
5. **Test in isolation** - don't mix Flask and FastAPI tests

## Future: Single Database

After migration completes (Phase 8), we'll consolidate to a single database:

```python
# Both Flask and FastAPI use same database
database_url = "sqlite:///src/instance/cron_jobs.db"
```

Until then, **separation = stability**! 🎯
