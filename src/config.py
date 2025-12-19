import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Get the absolute path to the project root directory
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
# Database will be stored in src/instance/cron_jobs.db
DB_PATH = os.path.join(BASE_DIR, 'src', 'instance', 'cron_jobs.db')


class Config:
    """
    Configuration class for Flask application and APScheduler.
    """
    # Flask Configuration
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-please-change-in-production')
    FLASK_ENV = os.getenv('FLASK_ENV', 'development')
    DEBUG = os.getenv('FLASK_DEBUG', 'False').lower() in ['true', '1', 'yes']

    # In production, avoid leaking internal exception details to clients.
    _DEFAULT_EXPOSE_ERRORS = 'true' if FLASK_ENV != 'production' else 'false'
    EXPOSE_ERROR_DETAILS = os.getenv('EXPOSE_ERROR_DETAILS', _DEFAULT_EXPOSE_ERRORS).lower() in ['true', '1', 'yes']

    # In production, do not auto-create the default admin user at startup.
    _DEFAULT_ALLOW_DEFAULT_ADMIN = 'true' if FLASK_ENV != 'production' else 'false'
    ALLOW_DEFAULT_ADMIN = os.getenv('ALLOW_DEFAULT_ADMIN', _DEFAULT_ALLOW_DEFAULT_ADMIN).lower() in ['true', '1', 'yes']

    # JWT Configuration
    JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', SECRET_KEY)
    JWT_ACCESS_TOKEN_EXPIRES = int(os.getenv('JWT_ACCESS_TOKEN_EXPIRES', 3600))  # 1 hour default
    JWT_REFRESH_TOKEN_EXPIRES = int(os.getenv('JWT_REFRESH_TOKEN_EXPIRES', 2592000))  # 30 days default

    # CORS Configuration
    CORS_ORIGINS = os.getenv('CORS_ORIGINS', '*').split(',')

    # Frontend base URL used to generate deep links in Slack notifications
    FRONTEND_BASE_URL = os.getenv('FRONTEND_BASE_URL', 'http://localhost:5173')

    # Database Configuration - Using absolute path to prevent multiple database files
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL', f'sqlite:///{DB_PATH}')
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # APScheduler Configuration
    SCHEDULER_API_ENABLED = True
    # Cron expressions in the UI/CSV are specified in JST by convention.
    # You can override this via env var if needed.
    SCHEDULER_TIMEZONE = os.getenv('SCHEDULER_TIMEZONE', 'Asia/Tokyo')
    
    # APScheduler Job Store Configuration
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

    # GitHub API Configuration (for future use)
    GITHUB_TOKEN = os.getenv('GITHUB_TOKEN', '')

    # Email Configuration for Notifications
    MAIL_SERVER = os.getenv('MAIL_SERVER', 'smtp.gmail.com')
    MAIL_PORT = int(os.getenv('MAIL_PORT', 587))
    MAIL_USE_TLS = os.getenv('MAIL_USE_TLS', 'True').lower() in ['true', '1', 'yes']
    MAIL_USERNAME = os.getenv('MAIL_USERNAME', '')
    MAIL_PASSWORD = os.getenv('MAIL_PASSWORD', '')
    MAIL_DEFAULT_SENDER = os.getenv('MAIL_DEFAULT_SENDER', 'noreply@cronjobscheduler.local')
    
    # Enable/Disable email notifications
    MAIL_ENABLED = os.getenv('MAIL_ENABLED', 'True').lower() in ['true', '1', 'yes']
