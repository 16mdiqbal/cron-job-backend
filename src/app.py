import logging
import os
from flask import Flask
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from datetime import datetime, timedelta
from apscheduler.triggers.cron import CronTrigger
from zoneinfo import ZoneInfo
from .config import Config
from .models import db
from .models.job import Job
from .utils.email import mail
from .scheduler import scheduler
from .scheduler.job_executor import (
    execute_job,
    execute_job_with_app_context,
    run_end_date_maintenance_with_app_context,
    set_flask_app,
)
from .routes.jobs import jobs_bp
from .routes.auth import auth_bp
from .routes.notifications import notifications_bp
from .models.user import User
from .models.job_category import JobCategory
from .utils.sqlite_schema import ensure_sqlite_schema

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def _get_scheduler_timezone(app: Flask):
    tz_name = app.config.get('SCHEDULER_TIMEZONE', 'Asia/Tokyo')
    try:
        return ZoneInfo(tz_name)
    except Exception:
        logger.warning(f"Invalid SCHEDULER_TIMEZONE '{tz_name}', falling back to UTC")
        return ZoneInfo('UTC')


def _validate_production_config(app: Flask):
    """
    Fail fast on unsafe production defaults.
    Keep dev experience flexible, but make production explicit and safe.
    """
    if app.config.get('FLASK_ENV') != 'production':
        return

    secret_key = (app.config.get('SECRET_KEY') or '').strip()
    jwt_secret = (app.config.get('JWT_SECRET_KEY') or '').strip()
    cors_origins = [o.strip() for o in (app.config.get('CORS_ORIGINS') or []) if o and o.strip()]

    if not secret_key or secret_key == 'dev-secret-key-please-change-in-production':
        raise RuntimeError('Invalid production config: set a strong SECRET_KEY (do not use the default dev value).')

    if not jwt_secret or jwt_secret in ['dev-secret-key-please-change-in-production', secret_key]:
        # Allow JWT_SECRET_KEY == SECRET_KEY in dev, but require explicit and distinct in prod.
        raise RuntimeError('Invalid production config: set a strong, distinct JWT_SECRET_KEY.')

    if not cors_origins or '*' in cors_origins:
        raise RuntimeError('Invalid production config: set CORS_ORIGINS to explicit frontend origin(s); "*" is not allowed.')


def create_app():
    """
    Application factory pattern for creating and configuring the Flask app.
    """
    app = Flask(__name__)
    app.config.from_object(Config)
    set_flask_app(app)
    _validate_production_config(app)

    # Initialize CORS
    CORS(app, resources={
        r"/api/*": {
            "origins": app.config['CORS_ORIGINS'],
            "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            "allow_headers": ["Content-Type", "Authorization"],
            "expose_headers": ["Content-Type"],
            "supports_credentials": True,
            "max_age": 3600
        }
    })

    # Initialize JWT
    jwt = JWTManager(app)
    app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(seconds=app.config['JWT_ACCESS_TOKEN_EXPIRES'])
    app.config['JWT_REFRESH_TOKEN_EXPIRES'] = timedelta(seconds=app.config['JWT_REFRESH_TOKEN_EXPIRES'])

    # Initialize SQLAlchemy
    db.init_app(app)

    # Initialize Flask-Mail
    mail.init_app(app)

    # Create database tables and initialize default admin user
    with app.app_context():
        db.create_all()
        ensure_sqlite_schema(db)
        logger.info("Database tables created successfully")

        # Seed default job categories (admin-managed)
        try:
            if JobCategory.query.count() == 0:
                seed = [
                    ('general', 'General'),
                    ('regression', 'Regression'),
                    ('dr-testing', 'DR Testing'),
                    ('feature-testing', 'Feature Testing'),
                    ('prod-canary', 'Prod/Canary'),
                    ('refund', 'Refund'),
                    ('backward-compatibility', 'Backward Compatibility'),
                ]
                for slug, name in seed:
                    db.session.add(JobCategory(slug=slug, name=name, is_active=True))
                db.session.commit()
                logger.info("✅ Default job categories seeded successfully")
        except Exception as e:
            logger.error(f"Error seeding job categories: {str(e)}")
            db.session.rollback()
        
        # Create default admin user if it doesn't exist (dev-only by default)
        if app.config.get('ALLOW_DEFAULT_ADMIN', False):
            admin = User.query.filter_by(username='admin').first()
            if not admin:
                try:
                    admin = User(
                        username='admin',
                        email='admin@example.com',
                        role='admin',
                        is_active=True
                    )
                    admin.set_password('admin123')
                    db.session.add(admin)
                    db.session.commit()
                    logger.info("✅ Default admin user created successfully")
                    logger.warning("⚠️  Default admin password is 'admin123'. Change it immediately!")
                except Exception as e:
                    logger.error(f"Error creating default admin user: {str(e)}")
                    db.session.rollback()
        else:
            logger.info("Default admin auto-creation is disabled (ALLOW_DEFAULT_ADMIN=false).")

    # Configure and start APScheduler (unless disabled for testing)
    scheduler_enabled = os.getenv('SCHEDULER_ENABLED', 'true').lower() != 'false'
    
    if scheduler_enabled:
        scheduler_tz = _get_scheduler_timezone(app)
        scheduler.configure(
            jobstores=app.config['SCHEDULER_JOBSTORES'],
            executors=app.config['SCHEDULER_EXECUTORS'],
            job_defaults=app.config['SCHEDULER_JOB_DEFAULTS'],
            timezone=scheduler_tz
        )

        # Load existing jobs from database into scheduler
        with app.app_context():
            today_jst = datetime.now(scheduler_tz).date()
            existing_jobs = Job.query.filter_by(is_active=True).all()
            for job in existing_jobs:
                try:
                    # Auto-pause expired jobs (quietly) to prevent unexpected executions
                    if job.end_date and job.end_date < today_jst:
                        job.is_active = False
                        db.session.commit()
                        logger.info(f"Auto-paused expired job '{job.name}' (ID: {job.id}) due to end_date")
                        continue

                    trigger = CronTrigger.from_crontab(job.cron_expression, timezone=scheduler_tz)
                    job_config = {
                        'target_url': job.target_url,
                        'github_owner': job.github_owner,
                        'github_repo': job.github_repo,
                        'github_workflow_name': job.github_workflow_name,
                        'metadata': job.get_metadata(),
                        'enable_email_notifications': job.enable_email_notifications,
                        'notification_emails': job.get_notification_emails(),
                        'notify_on_success': job.notify_on_success
                    }
                    scheduler.add_job(
                        func=execute_job_with_app_context,
                        trigger=trigger,
                        args=[job.id, job.name, job_config],
                        id=job.id,
                        name=job.name,
                        replace_existing=True
                    )
                    logger.info(f"Loaded job '{job.name}' (ID: {job.id}) into scheduler")
                except Exception as e:
                    logger.error(f"Failed to load job '{job.name}': {str(e)}")

        # Weekly maintenance: end_date reminders + auto-pause (Mondays, JST)
        try:
            scheduler.add_job(
                func=run_end_date_maintenance_with_app_context,
                trigger=CronTrigger(day_of_week='mon', hour=9, minute=0, timezone=scheduler_tz),
                id='end_date_maintenance',
                name='End date maintenance',
                replace_existing=True,
            )
        except Exception as e:
            logger.error(f"Failed to schedule end_date maintenance job: {e}")

        if not scheduler.running:
            scheduler.start()
            logger.info("APScheduler started successfully")

    # Register Blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(jobs_bp)
    app.register_blueprint(notifications_bp)

    return app


# Create app instance
app = create_app()


if __name__ == '__main__':
    try:
        app.run(host='0.0.0.0', port=5001, debug=app.config['DEBUG'])
    except (KeyboardInterrupt, SystemExit):
        # Gracefully shut down scheduler on exit
        if scheduler.running:
            scheduler.shutdown()
            logger.info("APScheduler shut down successfully")
        raise
