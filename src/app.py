import logging
import os
import atexit
import threading
import time
from typing import Optional
from flask import Flask
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from datetime import datetime, timedelta
from apscheduler.triggers.cron import CronTrigger
from zoneinfo import ZoneInfo
from .config import Config, DB_PATH
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
_SCHEDULER_LOCK_PATH: Optional[str] = None
_SCHEDULER_LOCK_HELD = False


def _is_process_alive(pid: int) -> bool:
    try:
        if pid <= 0:
            return False
        # Works on Unix/macOS. On Windows, this may raise.
        os.kill(pid, 0)
        return True
    except Exception:
        return False


def _acquire_scheduler_lock() -> bool:
    """
    Prevent multiple backend processes from running the scheduler concurrently.
    Uses a lock file under src/instance with stale-PID detection.
    """
    global _SCHEDULER_LOCK_PATH, _SCHEDULER_LOCK_HELD

    lock_dir = os.path.dirname(DB_PATH)
    os.makedirs(lock_dir, exist_ok=True)
    lock_path = os.path.join(lock_dir, "scheduler.lock")
    _SCHEDULER_LOCK_PATH = lock_path

    # If lock exists, check whether it's stale.
    try:
        if os.path.exists(lock_path):
            try:
                with open(lock_path, "r", encoding="utf-8") as f:
                    first_line = (f.readline() or "").strip()
                existing_pid = int(first_line) if first_line.isdigit() else None
            except Exception:
                existing_pid = None

            if existing_pid and _is_process_alive(existing_pid):
                return False

            # Stale lock: best-effort remove.
            try:
                os.remove(lock_path)
            except Exception:
                return False

        fd = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(f"{os.getpid()}\n{datetime.utcnow().isoformat()}Z\n")
        _SCHEDULER_LOCK_HELD = True
        return True
    except FileExistsError:
        return False
    except Exception:
        return False


def _release_scheduler_lock():
    global _SCHEDULER_LOCK_HELD
    if not _SCHEDULER_LOCK_HELD:
        return
    _SCHEDULER_LOCK_HELD = False
    try:
        if _SCHEDULER_LOCK_PATH and os.path.exists(_SCHEDULER_LOCK_PATH):
            os.remove(_SCHEDULER_LOCK_PATH)
    except Exception:
        pass


atexit.register(_release_scheduler_lock)


def _get_scheduler_timezone(app: Flask):
    tz_name = app.config.get('SCHEDULER_TIMEZONE', 'Asia/Tokyo')
    try:
        return ZoneInfo(tz_name)
    except Exception:
        logger.warning(f"Invalid SCHEDULER_TIMEZONE '{tz_name}', falling back to UTC")
        return ZoneInfo('UTC')


def _job_signature(job: Job) -> str:
    updated_at = job.updated_at.isoformat() if getattr(job, "updated_at", None) else ""
    return "|".join(
        [
            job.id or "",
            job.name or "",
            job.cron_expression or "",
            str(bool(job.is_active)),
            job.end_date.isoformat() if job.end_date else "",
            job.target_url or "",
            job.github_owner or "",
            job.github_repo or "",
            job.github_workflow_name or "",
            str(bool(job.enable_email_notifications)),
            ",".join(job.get_notification_emails() or []),
            str(bool(job.notify_on_success)),
            updated_at,
        ]
    )


def _sync_jobs_to_scheduler(app: Flask, scheduler_tz: ZoneInfo, signatures: dict[str, str]):
    """
    Periodically reconcile jobs table -> APScheduler state.
    This keeps the system correct even if API requests hit a non-scheduler process
    (e.g., multiple gunicorn workers/instances).
    """
    with app.app_context():
        today_jst = datetime.now(scheduler_tz).date()
        all_jobs = Job.query.all()
        current_ids = {j.id for j in all_jobs if j.id}

        # Remove deleted jobs
        for job_id in list(signatures.keys()):
            if job_id not in current_ids:
                try:
                    if scheduler.get_job(job_id):
                        scheduler.remove_job(job_id)
                except Exception:
                    pass
                signatures.pop(job_id, None)

        for job in all_jobs:
            if not job.id:
                continue

            # Auto-pause expired jobs
            if job.is_active and job.end_date and job.end_date < today_jst:
                job.is_active = False
                db.session.add(job)
                db.session.commit()

            should_schedule = bool(job.is_active) and not (job.end_date and job.end_date < today_jst)
            sig = _job_signature(job)
            prev = signatures.get(job.id)

            if not should_schedule:
                if prev is not None:
                    try:
                        if scheduler.get_job(job.id):
                            scheduler.remove_job(job.id)
                    except Exception:
                        pass
                    signatures.pop(job.id, None)
                continue

            if prev == sig and scheduler.get_job(job.id):
                continue

            # Replace existing schedule
            try:
                if scheduler.get_job(job.id):
                    scheduler.remove_job(job.id)
            except Exception:
                pass

            try:
                trigger = CronTrigger.from_crontab(job.cron_expression, timezone=scheduler_tz)
            except Exception as e:
                logger.error(f"Invalid cron for job '{job.name}' (ID: {job.id}): {e}")
                continue

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

            try:
                scheduler.add_job(
                    func=execute_job_with_app_context,
                    trigger=trigger,
                    args=[job.id, job.name, job_config],
                    id=job.id,
                    name=job.name,
                    replace_existing=True
                )
                signatures[job.id] = sig
            except Exception as e:
                logger.error(f"Failed to schedule job '{job.name}' (ID: {job.id}): {e}")


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
        if not _acquire_scheduler_lock():
            logger.warning("Scheduler lock is held by another process; skipping APScheduler startup in this process.")
            scheduler_enabled = False

    if scheduler_enabled:
        scheduler_tz = _get_scheduler_timezone(app)
        scheduler.configure(
            jobstores=app.config['SCHEDULER_JOBSTORES'],
            executors=app.config['SCHEDULER_EXECUTORS'],
            job_defaults=app.config['SCHEDULER_JOB_DEFAULTS'],
            timezone=scheduler_tz
        )

        # Initial load + periodic sync from DB -> scheduler
        signatures: dict[str, str] = {}
        _sync_jobs_to_scheduler(app, scheduler_tz, signatures)

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

        poll_seconds = int(os.getenv("SCHEDULER_POLL_SECONDS", "60"))
        poll_seconds = max(10, min(poll_seconds, 300))

        def _sync_loop():
            while True:
                time.sleep(poll_seconds)
                try:
                    _sync_jobs_to_scheduler(app, scheduler_tz, signatures)
                except Exception as e:
                    logger.error(f"Scheduler sync loop error: {e}")

        t = threading.Thread(target=_sync_loop, name="scheduler-sync", daemon=True)
        t.start()

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
