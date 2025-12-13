"""
Pytest configuration and shared fixtures for all tests.
"""
import os
import sys
import pytest
from datetime import timedelta

# Add src directory to path to import app modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from app import create_app
from models import db
from models.user import User
from models.job import Job


@pytest.fixture(scope='function')
def app():
    """Create and configure a test application instance."""
    # Disable scheduler before creating app
    os.environ['SCHEDULER_ENABLED'] = 'false'
    
    app = create_app()
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
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
    
    # Re-enable scheduler after test
    os.environ['SCHEDULER_ENABLED'] = 'true'


@pytest.fixture(scope='function')
def client(app):
    """Create a test client."""
    return app.test_client()


@pytest.fixture(scope='function')
def admin_user(app):
    """Create an admin user for testing."""
    with app.app_context():
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
