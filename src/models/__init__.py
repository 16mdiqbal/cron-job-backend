from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

# Import models after db is defined to avoid circular imports
from .user import User
from .job import Job
from .job_category import JobCategory
from .pic_team import PicTeam
from .job_execution import JobExecution
from .notification_preferences import UserNotificationPreferences
from .ui_preferences import UserUiPreferences
from .slack_settings import SlackSettings
from .notification import Notification
