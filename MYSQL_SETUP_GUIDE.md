# MySQL Database Setup Guide

This guide explains how to set up and configure the Cron Job Backend with MySQL database.

## Prerequisites

- MySQL 5.7+ or MySQL 8.0+
- Python 3.8+
- PyMySQL or mysql-connector-python package

## Installation Steps

### 1. Install MySQL Database Driver

```bash
pip install PyMySQL
# OR
pip install mysql-connector-python
```

Add the dependency to `requirements.txt`:
```
PyMySQL==1.1.0
```

Or update the requirements:
```bash
pip install -r requirements.txt
```

### 2. Create MySQL Database

#### Option A: Using MySQL Command Line

```bash
# Connect to MySQL server
mysql -u root -p

# Create database
CREATE DATABASE IF NOT EXISTS cron_job_backend;

# Exit MySQL
exit
```

#### Option B: Run the SQL Schema File

```bash
# Run the complete schema
mysql -u root -p cron_job_backend < DATABASE_SCHEMA_MYSQL.sql

# Or without password prompt (less secure)
mysql -u root cron_job_backend < DATABASE_SCHEMA_MYSQL.sql
```

### 3. Create MySQL User (Recommended)

```bash
mysql -u root -p

# Create dedicated user for the application
CREATE USER 'cron_job_user'@'localhost' IDENTIFIED BY 'secure_password_here';

# Grant all privileges on the database
GRANT ALL PRIVILEGES ON cron_job_backend.* TO 'cron_job_user'@'localhost';

# Apply the changes
FLUSH PRIVILEGES;

exit
```

### 4. Update Application Configuration

Edit `src/config.py` to use MySQL:

```python
import os

class Config:
    """Base configuration"""
    
    # MySQL Database Configuration
    SQLALCHEMY_DATABASE_URI = os.getenv(
        'DATABASE_URL',
        'mysql+pymysql://cron_job_user:secure_password_here@localhost/cron_job_backend'
    )
    
    # For mysql-connector-python:
    # SQLALCHEMY_DATABASE_URI = os.getenv(
    #     'DATABASE_URL',
    #     'mysql+mysqlconnector://cron_job_user:secure_password_here@localhost/cron_job_backend'
    # )
    
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_size': 10,
        'pool_recycle': 3600,
        'pool_pre_ping': True,
    }
    
    # Other configurations...
```

### 5. Update .env File

Create or update `.env` file with MySQL connection string:

```bash
# Database Configuration
DATABASE_URL=mysql+pymysql://cron_job_user:secure_password_here@localhost/cron_job_backend

# JWT Configuration
JWT_SECRET_KEY=your-secret-key-here
JWT_ACCESS_TOKEN_EXPIRES=3600

# Email Configuration (if using email notifications)
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USERNAME=your-email@gmail.com
MAIL_PASSWORD=your-app-password
```

## Database Connection Strings

### PyMySQL (Recommended for development)
```
mysql+pymysql://user:password@localhost/database_name
mysql+pymysql://user:password@localhost:3306/database_name
```

### mysql-connector-python
```
mysql+mysqlconnector://user:password@localhost/database_name
mysql+mysqlconnector://user:password@localhost:3306/database_name
```

### mysqlclient (fastest, requires additional setup)
```
mysql://user:password@localhost/database_name
```

## Database Schema Overview

### Users Table
- Stores user accounts
- Supports role-based access control (admin, user, viewer)
- Fields: id, username, email, password_hash, role, is_active, created_at, updated_at
- Indexes: username, email, role

### Jobs Table
- Stores cron job configurations
- Supports both webhook and GitHub Actions targets
- Stores metadata and notification settings as JSON
- Fields: id, name, cron_expression, target_url, github_*, notification_*, created_by, is_active, created_at, updated_at
- Indexes: name, created_by, is_active, enable_email_notifications

### Job Executions Table
- Tracks execution history
- Records status, timing, and error information
- Automatically deletes with parent job
- Fields: id, job_id, status, trigger_type, started_at, completed_at, duration_seconds, execution_type, target, response_status, error_message, output
- Indexes: job_id, status, trigger_type, started_at

## Database Views

### job_statistics
Provides aggregated statistics for each job:
- Total executions
- Successful/failed counts
- Success rate percentage
- Average execution duration
- Last execution time

### recent_executions
Shows the 100 most recent job executions with job names

## Stored Procedures

### GetJobStats(p_job_id)
Retrieves detailed statistics for a specific job

### CleanupOldExecutions(p_days_to_keep)
Removes execution records older than specified days

Usage:
```sql
CALL CleanupOldExecutions(30);  -- Keep last 30 days
```

## Testing Database Connection

After configuration, test the connection:

```python
# Test connection script
from src.app import create_app

app = create_app()

with app.app_context():
    from src.models import db
    
    try:
        # Test database connection
        db.engine.execute('SELECT 1')
        print("✓ Database connection successful!")
    except Exception as e:
        print(f"✗ Database connection failed: {e}")
```

Or run:
```bash
python -c "from src.app import create_app; app = create_app(); print('✓ Connected to MySQL')"
```

## Backup and Restore

### Backup Database
```bash
# Backup entire database
mysqldump -u cron_job_user -p cron_job_backend > backup.sql

# Backup with time stamp
mysqldump -u cron_job_user -p cron_job_backend > backup_$(date +%Y%m%d_%H%M%S).sql
```

### Restore Database
```bash
# Restore from backup
mysql -u cron_job_user -p cron_job_backend < backup.sql

# Restore to a different database
mysql -u cron_job_user -p new_database_name < backup.sql
```

## Performance Optimization

### 1. Enable Query Caching
Add to MySQL configuration (`my.cnf` or `my.ini`):
```ini
[mysqld]
query_cache_size = 256M
query_cache_type = 1
```

### 2. Connection Pooling
Already configured in `src/config.py`:
```python
SQLALCHEMY_ENGINE_OPTIONS = {
    'pool_size': 10,           # Number of connections to maintain
    'pool_recycle': 3600,      # Recycle connections every hour
    'pool_pre_ping': True,     # Test connections before using
}
```

### 3. Index Usage
All important columns are indexed:
- **Users**: username, email, role lookups
- **Jobs**: name, created_by, is_active filtering
- **Executions**: job_id, status, time-based queries

### 4. JSON Field Optimization
`metadata` and `notification_emails` fields use TEXT:
- If querying JSON content frequently, consider MySQL 5.7.8+ JSON type
- Current approach keeps compatibility and is suitable for most use cases

## Monitoring

### Check Database Size
```sql
SELECT 
    table_name,
    ROUND(((data_length + index_length) / 1024 / 1024), 2) AS size_mb
FROM information_schema.TABLES
WHERE table_schema = 'cron_job_backend'
ORDER BY (data_length + index_length) DESC;
```

### Monitor Connections
```sql
SHOW PROCESSLIST;
SHOW STATUS WHERE variable_name IN ('Threads_connected', 'Threads_running');
```

### Check Slow Queries
Enable slow query log:
```sql
SET GLOBAL slow_query_log = 'ON';
SET GLOBAL long_query_time = 2;  -- Queries taking more than 2 seconds
```

## Troubleshooting

### Connection Refused
```
Error: Can't connect to MySQL server on 'localhost'
```
**Solution**: Ensure MySQL server is running
```bash
# macOS
brew services start mysql

# Linux
sudo systemctl start mysql

# Windows
net start MySQL80
```

### Authentication Failed
```
Error: Access denied for user 'cron_job_user'@'localhost'
```
**Solution**: Verify credentials in `.env` and MySQL user privileges

### Table Already Exists
```
Error: Table 'users' already exists
```
**Solution**: Drop existing tables or use a different database name

### Character Encoding Issues
Ensure utf8mb4 is used:
```sql
ALTER DATABASE cron_job_backend CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

## Migration from SQLite to MySQL

If migrating from SQLite:

```bash
# 1. Backup SQLite database
cp instance/cron_jobs.db instance/cron_jobs.db.backup

# 2. Export data from SQLite (if needed)
sqlite3 instance/cron_jobs.db ".dump" > sqlite_backup.sql

# 3. Update configuration to MySQL
# (Update .env and src/config.py)

# 4. Create MySQL database and tables
mysql -u root -p < DATABASE_SCHEMA_MYSQL.sql

# 5. Re-initialize Flask app to create tables
# (The app will use the new MySQL database)

# 6. Verify connection
pytest test/ -v
```

## References

- [SQLAlchemy MySQL Documentation](https://docs.sqlalchemy.org/en/20/dialects/mysql.html)
- [PyMySQL Documentation](https://pymysql.readthedocs.io/)
- [MySQL Documentation](https://dev.mysql.com/doc/)
- [MySQL Performance Optimization](https://dev.mysql.com/doc/refman/8.0/en/optimization.html)
