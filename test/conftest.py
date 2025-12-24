"""
Pytest configuration and shared fixtures for all tests.
"""
import os
import sys
import pytest
from datetime import timedelta

# Add parent directory to path to import src modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

def _configure_test_db(*, database_url: str) -> None:
    """
    Ensure legacy Flask tests never touch the real dev SQLite DB.

    This must run BEFORE create_app(), because create_app() calls db.create_all()
    using the URI from src.config.Config (evaluated at import-time).
    """
    os.environ["SCHEDULER_ENABLED"] = "false"
    os.environ["TESTING"] = "true"
    os.environ["ALLOW_DEFAULT_ADMIN"] = "false"
    os.environ["DATABASE_URL"] = database_url

    import src.config as flask_config

    flask_config.Config.SQLALCHEMY_DATABASE_URI = database_url
    flask_config.Config.ALLOW_DEFAULT_ADMIN = False
    flask_config.Config.DEBUG = False


@pytest.fixture(scope='function')
def db_url(tmp_path):
    db_path = tmp_path / "legacy_flask_test.db"
    return f"sqlite:///{db_path}"


@pytest.fixture(scope='function')
def app(db_url):
    """Create and configure a test application instance."""
    _configure_test_db(database_url=db_url)

    from src.app import create_app
    from src.models import db

    app = create_app()
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = db_url
    app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(hours=1)
    
    # Create fresh database for each test
    with app.app_context():
        # Drop all tables first (in case they exist)
        db.drop_all()
        # Create all tables
        db.create_all()
        yield app
        # Clean up after test
        db.session.remove()
        db.drop_all()


@pytest.fixture(scope='function')
def client(app):
    """Create a test client."""
    return app.test_client()


@pytest.fixture(scope='function')
def admin_user(app):
    """Create an admin user for testing."""
    with app.app_context():
        from src.models import db
        from src.models.user import User

        admin = User(
            username='admin',
            email='admin@example.com',
            role='admin'
        )
        admin.set_password('admin123')
        db.session.add(admin)
        db.session.commit()
        return admin


@pytest.fixture(scope='function')
def regular_user(app):
    """Create a regular user for testing."""
    with app.app_context():
        from src.models import db
        from src.models.user import User

        user = User(
            username='user',
            email='user@example.com',
            role='user'
        )
        user.set_password('user123')
        db.session.add(user)
        db.session.commit()
        return user


@pytest.fixture(scope='function')
def viewer_user(app):
    """Create a viewer user for testing."""
    with app.app_context():
        from src.models import db
        from src.models.user import User

        user = User(
            username='viewer',
            email='viewer@example.com',
            role='viewer'
        )
        user.set_password('viewer123')
        db.session.add(user)
        db.session.commit()
        return user


@pytest.fixture(scope='function')
def admin_token(client, admin_user):
    """Get authentication token for admin user."""
    response = client.post('/api/auth/login', json={
        'username': 'admin',
        'password': 'admin123'
    })
    assert response.status_code == 200
    return response.get_json()['access_token']


@pytest.fixture(scope='function')
def user_token(client, regular_user):
    """Get authentication token for regular user."""
    response = client.post('/api/auth/login', json={
        'username': 'user',
        'password': 'user123'
    })
    assert response.status_code == 200
    return response.get_json()['access_token']


@pytest.fixture(scope='function')
def viewer_token(client, viewer_user):
    """Get authentication token for viewer user."""
    response = client.post('/api/auth/login', json={
        'username': 'viewer',
        'password': 'viewer123'
    })
    assert response.status_code == 200
    return response.get_json()['access_token']


@pytest.fixture(scope='function')
def sample_job_data():
    """Sample job data for testing."""
    return {
        'name': 'Test Job',
        'cron_expression': '0 * * * *',
        'target_url': 'https://httpbin.org/status/200'
    }


@pytest.fixture(scope='function')
def sample_job_with_notifications():
    """Sample job data with notifications enabled."""
    return {
        'name': 'Notify Job',
        'cron_expression': '0 12 * * *',
        'target_url': 'https://httpbin.org/status/200',
        'enable_email_notifications': True,
        'notification_emails': ['admin@example.com', 'team@example.com'],
        'notify_on_success': True
    }


@pytest.fixture(scope='function')
def sample_github_job():
    """Sample GitHub Actions job data for testing."""
    return {
        'name': 'GitHub Job',
        'cron_expression': '0 0 * * *',
        'github_owner': 'myorg',
        'github_repo': 'myrepo',
        'github_workflow_name': 'deploy.yml'
    }
