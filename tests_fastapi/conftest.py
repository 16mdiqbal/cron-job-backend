import os

import pytest
from httpx import ASGITransport, AsyncClient


@pytest.fixture(scope="function")
def db_urls(tmp_path, monkeypatch):
    db_path = tmp_path / "test.db"
    database_url = f"sqlite:///{db_path}"

    # Set environment before importing app modules (src/app.py creates a module-level app).
    monkeypatch.setenv("SCHEDULER_ENABLED", "false")
    monkeypatch.setenv("TESTING", "true")
    monkeypatch.setenv("ALLOW_DEFAULT_ADMIN", "false")
    monkeypatch.setenv("SECRET_KEY", "test-secret")
    monkeypatch.setenv("JWT_SECRET_KEY", "test-secret")
    monkeypatch.setenv("DATABASE_URL", database_url)
    monkeypatch.setenv("FASTAPI_DATABASE_URL", database_url)

    # Flask Config is evaluated at import-time, so patch it explicitly per test.
    import src.config as flask_config

    flask_config.Config.SQLALCHEMY_DATABASE_URI = database_url
    flask_config.Config.SECRET_KEY = "test-secret"
    flask_config.Config.JWT_SECRET_KEY = "test-secret"
    flask_config.Config.ALLOW_DEFAULT_ADMIN = False

    from src.fastapi_app.config import get_settings
    from src.database import engine as db_engine
    from src.database import session as db_session

    get_settings.cache_clear()
    db_engine.get_engine.cache_clear()
    db_engine.get_async_engine.cache_clear()
    db_session._sync_session_factory = None
    db_session._async_session_factory = None

    return database_url


@pytest.fixture(scope="function")
def app(db_urls):
    from src.app import create_app as create_flask_app
    from src.models import db

    app = create_flask_app()
    app.config["TESTING"] = True
    app.config["SQLALCHEMY_DATABASE_URI"] = db_urls

    with app.app_context():
        db.drop_all()
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture(scope="function")
def fastapi_app(db_urls):
    assert os.environ.get("DATABASE_URL") == db_urls
    from src.fastapi_app.main import create_app as create_fastapi_app

    return create_fastapi_app()


@pytest.fixture(scope="function")
async def async_client(fastapi_app):
    transport = ASGITransport(app=fastapi_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


@pytest.fixture(scope="function")
def setup_test_db(app):
    with app.app_context():
        os.environ["TESTING"] = "true"

        from src.models import db
        from src.models.user import User

        User.query.delete()
        db.session.commit()

        admin = User(username="testadmin", email="testadmin@example.com", role="admin", is_active=True)
        admin.set_password("admin123")
        db.session.add(admin)

        user = User(username="testuser", email="testuser@example.com", role="user", is_active=True)
        user.set_password("user123")
        db.session.add(user)

        inactive = User(username="inactiveuser", email="inactive@example.com", role="user", is_active=False)
        inactive.set_password("inactive123")
        db.session.add(inactive)

        viewer = User(username="testviewer", email="testviewer@example.com", role="viewer", is_active=True)
        viewer.set_password("viewer123")
        db.session.add(viewer)

        db.session.commit()

        yield {
            "admin": admin,
            "user": user,
            "inactive": inactive,
            "viewer": viewer,
        }


@pytest.fixture
def admin_access_token(setup_test_db):
    admin = setup_test_db["admin"]
    from src.fastapi_app.dependencies.auth import create_access_token

    return create_access_token(user_id=admin.id, role=admin.role, email=admin.email)


@pytest.fixture
def user_access_token(setup_test_db):
    user = setup_test_db["user"]
    from src.fastapi_app.dependencies.auth import create_access_token

    return create_access_token(user_id=user.id, role=user.role, email=user.email)


@pytest.fixture
def viewer_access_token(setup_test_db):
    viewer = setup_test_db["viewer"]
    from src.fastapi_app.dependencies.auth import create_access_token

    return create_access_token(user_id=viewer.id, role=viewer.role, email=viewer.email)


@pytest.fixture
def admin_refresh_token(setup_test_db):
    admin = setup_test_db["admin"]
    from src.fastapi_app.dependencies.auth import create_refresh_token

    return create_refresh_token(user_id=admin.id, role=admin.role, email=admin.email)
