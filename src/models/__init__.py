from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

# Import models after db is defined to avoid circular imports
from .user import User
from .job import Job
from .job_category import JobCategory
from .job_execution import JobExecution
from .notification_preferences import UserNotificationPreferences
from .notification import Notification
