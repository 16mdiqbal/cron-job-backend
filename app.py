import logging
from flask import Flask
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from datetime import timedelta
from apscheduler.triggers.cron import CronTrigger
from config import Config
from models import db
from models.job import Job
from scheduler import scheduler
from scheduler.job_executor import execute_job
from routes.jobs import jobs_bp
from routes.auth import auth_bp

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def create_app():
    """
    Application factory pattern for creating and configuring the Flask app.
    """
    app = Flask(__name__)
    app.config.from_object(Config)

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

    # Create database tables
    with app.app_context():
        db.create_all()
        logger.info("Database tables created successfully")

    # Configure and start APScheduler
    scheduler.configure(
        jobstores=app.config['SCHEDULER_JOBSTORES'],
        executors=app.config['SCHEDULER_EXECUTORS'],
        job_defaults=app.config['SCHEDULER_JOB_DEFAULTS'],
        timezone=app.config['SCHEDULER_TIMEZONE']
    )

    # Load existing jobs from database into scheduler
    with app.app_context():
        existing_jobs = Job.query.filter_by(is_active=True).all()
        for job in existing_jobs:
            try:
                trigger = CronTrigger.from_crontab(job.cron_expression)
                job_config = {
                    'target_url': job.target_url,
                    'github_owner': job.github_owner,
                    'github_repo': job.github_repo,
                    'github_workflow_name': job.github_workflow_name,
                    'metadata': job.get_metadata()
                }
                scheduler.add_job(
                    func=execute_job,
                    trigger=trigger,
                    args=[job.id, job.name, job_config],
                    id=job.id,
                    name=job.name,
                    replace_existing=True
                )
                logger.info(f"Loaded job '{job.name}' (ID: {job.id}) into scheduler")
            except Exception as e:
                logger.error(f"Failed to load job '{job.name}': {str(e)}")

    if not scheduler.running:
        scheduler.start()
        logger.info("APScheduler started successfully")

    # Register Blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(jobs_bp)

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
