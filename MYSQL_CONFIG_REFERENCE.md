# MySQL Configuration Example for src/config.py

## Option 1: Using PyMySQL (Recommended)

```python
import os
from datetime import timedelta

class Config:
    """Base configuration"""
    
    # MySQL Database Configuration with PyMySQL
    SQLALCHEMY_DATABASE_URI = os.getenv(
        'DATABASE_URL',
        'mysql+pymysql://cron_job_user:secure_password@localhost/cron_job_backend'
    )
    
    # Connection pool configuration
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_size': 10,              # Number of connections to maintain
        'pool_recycle': 3600,         # Recycle connections every 1 hour
        'pool_pre_ping': True,        # Test connections before using (prevents "connection lost" errors)
        'connect_args': {
            'charset': 'utf8mb4',     # Use UTF-8 encoding
            'use_unicode': True,
        }
    }
    
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ECHO = False           # Set to True to log SQL queries
    
    # JWT Configuration
    JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', 'dev-secret-key-change-in-production')
    JWT_ACCESS_TOKEN_EXPIRES = int(os.getenv('JWT_ACCESS_TOKEN_EXPIRES', 3600))  # 1 hour
    JWT_REFRESH_TOKEN_EXPIRES = int(os.getenv('JWT_REFRESH_TOKEN_EXPIRES', 2592000))  # 30 days
    
    # CORS Configuration
    CORS_ORIGINS = os.getenv('CORS_ORIGINS', 'http://localhost:3000,http://localhost:5173').split(',')
    
    # Email Configuration
    MAIL_SERVER = os.getenv('MAIL_SERVER', 'smtp.gmail.com')
    MAIL_PORT = int(os.getenv('MAIL_PORT', 587))
    MAIL_USE_TLS = os.getenv('MAIL_USE_TLS', True)
    MAIL_USERNAME = os.getenv('MAIL_USERNAME', 'your-email@gmail.com')
    MAIL_PASSWORD = os.getenv('MAIL_PASSWORD', 'your-app-password')
    MAIL_DEFAULT_SENDER = os.getenv('MAIL_DEFAULT_SENDER', 'noreply@cronjobs.com')
    
    # Scheduler Configuration
    SCHEDULER_JOBSTORES = {
        'default': {
            'type': 'sqlalchemy',
            'url': SQLALCHEMY_DATABASE_URI.replace('+pymysql', '+mysqldb') if '+pymysql' in SQLALCHEMY_DATABASE_URI else SQLALCHEMY_DATABASE_URI
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
        'max_instances': 1
    }
    
    SCHEDULER_TIMEZONE = os.getenv('SCHEDULER_TIMEZONE', 'UTC')
    
    # Debug and logging
    DEBUG = os.getenv('DEBUG', 'False').lower() == 'true'
    TESTING = False


class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True
    SQLALCHEMY_ECHO = True  # Log SQL queries in development


class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False
    SQLALCHEMY_ECHO = False


class TestingConfig(Config):
    """Testing configuration - uses SQLite for speed"""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    # Disable scheduler in tests
    SCHEDULER_ENABLED = False
```

## Option 2: Using mysql-connector-python

```python
import os

class Config:
    """Base configuration"""
    
    # MySQL Database Configuration with mysql-connector-python
    SQLALCHEMY_DATABASE_URI = os.getenv(
        'DATABASE_URL',
        'mysql+mysqlconnector://cron_job_user:secure_password@localhost:3306/cron_job_backend'
    )
    
    # Connection pool configuration
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_size': 10,
        'pool_recycle': 3600,
        'pool_pre_ping': True,
        'connect_args': {
            'charset': 'utf8mb4',
            'use_unicode': True,
            'autocommit': False,
        }
    }
    
    SQLALCHEMY_TRACK_MODIFICATIONS = False
```

## Option 3: Remote MySQL Server

```python
# For connecting to a remote MySQL server (AWS RDS, etc.)
SQLALCHEMY_DATABASE_URI = os.getenv(
    'DATABASE_URL',
    'mysql+pymysql://cron_job_user:password@db.example.com:3306/cron_job_backend'
)

# SSL configuration for secure connections
SQLALCHEMY_ENGINE_OPTIONS = {
    'pool_size': 10,
    'pool_recycle': 3600,
    'pool_pre_ping': True,
    'connect_args': {
        'charset': 'utf8mb4',
        'ssl_disabled': False,  # Enable SSL
        'ssl_verify_cert': True,
        'ssl_verify_identity': True,
    }
}
```

## Environment Variables (.env file)

```bash
# Database
DATABASE_URL=mysql+pymysql://cron_job_user:secure_password@localhost/cron_job_backend

# JWT
JWT_SECRET_KEY=your-super-secret-key-min-32-chars
JWT_ACCESS_TOKEN_EXPIRES=3600
JWT_REFRESH_TOKEN_EXPIRES=2592000

# Email
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USE_TLS=true
MAIL_USERNAME=your-email@gmail.com
MAIL_PASSWORD=your-app-password
MAIL_DEFAULT_SENDER=noreply@cronjobs.com

# Scheduler
SCHEDULER_TIMEZONE=UTC
SCHEDULER_ENABLED=true

# Debug
DEBUG=false
```

## Connection String Format Reference

### PyMySQL
```
mysql+pymysql://[username]:[password]@[hostname]:[port]/[database]
```

### mysql-connector-python
```
mysql+mysqlconnector://[username]:[password]@[hostname]:[port]/[database]
```

### mysqlclient
```
mysql://[username]:[password]@[hostname]:[port]/[database]
```

### With Special Characters in Password
URL-encode special characters:
- `@` → `%40`
- `:` → `%3A`
- `/` → `%2F`
- `#` → `%23`

Example: Password `pass@word:123`
```
mysql+pymysql://user:pass%40word%3A123@localhost/database
```

## Connection Pool Settings Explanation

| Setting | Purpose | Default | Recommendation |
|---------|---------|---------|-----------------|
| `pool_size` | Number of connections to maintain | 5 | 10-20 for production |
| `pool_recycle` | Seconds before recycling connection | -1 | 3600 (1 hour) |
| `pool_pre_ping` | Test connection before using | False | True (prevents stale connections) |
| `max_overflow` | Connections beyond pool_size | 10 | 20-50 for production |

## Performance Tuning

### For High Traffic
```python
SQLALCHEMY_ENGINE_OPTIONS = {
    'pool_size': 20,
    'max_overflow': 50,
    'pool_recycle': 1800,
    'pool_pre_ping': True,
}
```

### For Low Traffic/Development
```python
SQLALCHEMY_ENGINE_OPTIONS = {
    'pool_size': 5,
    'max_overflow': 10,
    'pool_recycle': 3600,
    'pool_pre_ping': True,
}
```

## SSL/TLS Configuration

For remote MySQL servers (AWS RDS, CloudSQL, etc.):

```python
SQLALCHEMY_ENGINE_OPTIONS = {
    'pool_size': 10,
    'pool_recycle': 3600,
    'pool_pre_ping': True,
    'connect_args': {
        'charset': 'utf8mb4',
        'ssl_disabled': False,
        'ssl_verify_cert': True,
        'ssl_verify_identity': True,
        'ssl_ca': '/path/to/ca-bundle.crt',  # For custom CA certificates
    }
}
```

## Testing Connection

```bash
# Test connection from command line
mysql -u cron_job_user -p -h localhost cron_job_backend -e "SELECT 1;"

# From Python
python -c "from src.app import create_app; app = create_app(); print('Connected to MySQL')"
```
