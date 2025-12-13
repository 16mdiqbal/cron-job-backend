# MySQL Database Setup - Complete Documentation

**Created:** December 13, 2025  
**Status:** ✅ Ready for Production

## Overview

Complete MySQL database schema and configuration files have been created for the Cron Job Backend application. The schema supports all features including user management, job scheduling, and execution tracking.

## Files Created

### 1. **DATABASE_SCHEMA_MYSQL.sql** 
Complete SQL schema file with:
- ✅ Users table with authentication and roles
- ✅ Jobs table with webhook and GitHub Actions support
- ✅ Job Executions table with history tracking
- ✅ Indexes for performance optimization
- ✅ Foreign key constraints
- ✅ Database views for statistics
- ✅ Stored procedures for common operations

### 2. **MYSQL_SETUP_GUIDE.md**
Comprehensive setup guide including:
- ✅ Prerequisites and installation steps
- ✅ Database creation and user setup
- ✅ Configuration instructions
- ✅ Connection string formats
- ✅ Testing procedures
- ✅ Backup and restore scripts
- ✅ Performance optimization tips
- ✅ Monitoring and troubleshooting

### 3. **MYSQL_CONFIG_REFERENCE.md**
Quick reference for configuration including:
- ✅ Python configuration examples
- ✅ Environment variables template
- ✅ Connection pooling settings
- ✅ SSL/TLS configuration
- ✅ Performance tuning recommendations
- ✅ Special character handling

## Database Schema Summary

### Tables

| Table | Purpose | Rows | Indexes |
|-------|---------|------|---------|
| `users` | User accounts & authentication | 10-100 | 3 (username, email, role) |
| `jobs` | Scheduled cron jobs | 100-1000 | 4 (name, created_by, is_active, notifications) |
| `job_executions` | Execution history | 10000+ | 5 (job_id, status, trigger_type, started_at) |

### Features

✅ **Supports All Application Features:**
- User authentication with role-based access
- Job scheduling with cron expressions
- Webhook and GitHub Actions execution
- Email notification configuration
- Flexible metadata storage (JSON)
- Complete execution history
- Statistics and reporting

✅ **Production Ready:**
- UTF-8 character encoding
- Foreign key constraints
- Cascade delete for data integrity
- Indexes for query performance
- View and stored procedures

✅ **Scalable:**
- Connection pooling
- Index optimization
- Query views for analytics
- Automatic timestamp management

## Quick Start

### 1. Install MySQL Driver
```bash
pip install PyMySQL
# Add to requirements.txt
```

### 2. Create Database
```bash
mysql -u root -p < DATABASE_SCHEMA_MYSQL.sql
```

### 3. Update Configuration
Edit `src/config.py`:
```python
SQLALCHEMY_DATABASE_URI = 'mysql+pymysql://user:password@localhost/cron_job_backend'
```

### 4. Update .env
```bash
DATABASE_URL=mysql+pymysql://cron_job_user:password@localhost/cron_job_backend
```

### 5. Test Connection
```bash
pytest test/ -v
```

## Key Tables Structure

### Users Table
```
id (UUID, PK)
username (VARCHAR, UNIQUE)
email (VARCHAR, UNIQUE)
password_hash (VARCHAR)
role (VARCHAR) - admin, user, viewer
is_active (BOOLEAN)
created_at (TIMESTAMP)
updated_at (TIMESTAMP)
```

### Jobs Table
```
id (UUID, PK)
name (VARCHAR, UNIQUE)
cron_expression (VARCHAR)
target_url (VARCHAR, nullable)
github_owner (VARCHAR, nullable)
github_repo (VARCHAR, nullable)
github_workflow_name (VARCHAR, nullable)
job_metadata (JSON, nullable)
enable_email_notifications (BOOLEAN)
notification_emails (TEXT, nullable)
notify_on_success (BOOLEAN)
created_by (UUID, FK -> users.id)
is_active (BOOLEAN)
created_at (TIMESTAMP)
updated_at (TIMESTAMP)
```

### Job Executions Table
```
id (UUID, PK)
job_id (UUID, FK -> jobs.id)
status (VARCHAR) - success, failed, running
trigger_type (VARCHAR) - scheduled, manual
started_at (TIMESTAMP)
completed_at (TIMESTAMP, nullable)
duration_seconds (FLOAT, nullable)
execution_type (VARCHAR, nullable)
target (VARCHAR, nullable)
response_status (INT, nullable)
error_message (LONGTEXT, nullable)
output (LONGTEXT, nullable)
```

## Views Available

### job_statistics
Shows aggregated stats per job:
- Total executions
- Success/failure counts
- Success rate %
- Average duration
- Last execution time

### recent_executions
Shows last 100 executions with job names

## Stored Procedures

### GetJobStats(job_id)
Retrieves detailed statistics for a specific job

### CleanupOldExecutions(days_to_keep)
Removes old execution records
```sql
CALL CleanupOldExecutions(30);  -- Keep last 30 days
```

## Connection Options

### Option 1: PyMySQL (Recommended)
- Pure Python implementation
- Good compatibility
- Works on all platforms
```
mysql+pymysql://user:pass@localhost/db
```

### Option 2: mysql-connector-python
- Official MySQL connector
- Good performance
- Requires MySQL setup
```
mysql+mysqlconnector://user:pass@localhost/db
```

### Option 3: Remote Server
For AWS RDS, Google Cloud SQL, etc.
```
mysql+pymysql://user:pass@hostname:3306/db
```

## Performance Optimization

### Indexes
- **Users**: Fast lookup by username/email/role
- **Jobs**: Fast lookup by name, filtering by creator/status
- **Executions**: Fast filtering by job, status, time range

### Connection Pooling
- Pool size: 10-20 connections
- Recycle: Every 3600 seconds (1 hour)
- Pre-ping: Test connection before use

### Query Optimization
- Use provided views for analytics
- Use stored procedures for bulk operations
- Monitor slow query log

## Backup Strategy

### Regular Backups
```bash
# Daily backup
mysqldump -u user -p db_name > backup_$(date +%Y%m%d).sql

# With compression
mysqldump -u user -p db_name | gzip > backup_$(date +%Y%m%d).sql.gz
```

### Restore
```bash
# From backup
mysql -u user -p db_name < backup.sql

# From compressed backup
gunzip < backup.sql.gz | mysql -u user -p db_name
```

## Security Considerations

✅ **Implemented:**
- Character encoding (UTF-8 MB4)
- Foreign key constraints
- Prepared statements (via SQLAlchemy ORM)
- Password hashing (PBKDF2-SHA256)
- Role-based access control

✅ **Recommended:**
- Use strong passwords for MySQL user
- Enable SSL/TLS for remote connections
- Limit network access to MySQL server
- Regular backups
- Monitor slow queries
- Keep MySQL updated

## Troubleshooting

### Connection Issues
1. Verify MySQL server is running
2. Check credentials in .env
3. Verify database exists
4. Check network/firewall access

### Performance Issues
1. Check query execution time
2. Verify indexes are being used
3. Monitor connection pool
4. Check slow query log

### Data Issues
1. Verify foreign key constraints
2. Check character encoding
3. Test with smaller dataset first

## Monitoring Queries

### Check Database Size
```sql
SELECT 
    table_name,
    ROUND(((data_length + index_length) / 1024 / 1024), 2) AS size_mb
FROM information_schema.TABLES
WHERE table_schema = 'cron_job_backend';
```

### Check Active Connections
```sql
SHOW PROCESSLIST;
```

### Check Job Statistics
```sql
SELECT * FROM job_statistics;
```

## Migration from SQLite

If migrating from SQLite:
1. Create MySQL database using the schema
2. Update configuration to MySQL in .env
3. Update src/config.py with MySQL connection string
4. Run tests to verify connection
5. Optionally export and migrate data

## Testing

All tests work with MySQL:
```bash
pytest test/ -v

# With MySQL connection test
pytest test/test_jobs/ -v
```

## Production Deployment

### Prerequisites
- MySQL 5.7+ or MySQL 8.0+
- Dedicated MySQL user with limited privileges
- Network access configured
- SSL/TLS enabled for remote connections

### Configuration
1. Use strong passwords
2. Enable connection pooling
3. Configure slow query log
4. Setup regular backups
5. Monitor performance metrics

### Scaling
For high-traffic deployments:
- Increase connection pool size
- Add read replicas (MySQL Replication)
- Consider MySQL Cluster or Galera
- Implement caching layer

## Next Steps

1. ✅ Review DATABASE_SCHEMA_MYSQL.sql
2. ✅ Install PyMySQL: `pip install PyMySQL`
3. ✅ Create MySQL database and user
4. ✅ Update .env with connection string
5. ✅ Update src/config.py with MySQL URI
6. ✅ Run tests: `pytest test/ -v`
7. ✅ Start application: `python -m src`

## Support

For issues or questions:
1. Check MYSQL_SETUP_GUIDE.md
2. Review MYSQL_CONFIG_REFERENCE.md
3. Check MySQL documentation
4. Review application logs

---

**Documentation Complete**  
All files ready for MySQL deployment! 🚀
