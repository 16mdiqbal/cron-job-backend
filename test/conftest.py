import os

import pytest
from httpx import ASGITransport, AsyncClient


@pytest.fixture(scope="function")
def db_url(tmp_path, monkeypatch):
    db_path = tmp_path / "test.db"
    database_url = f"sqlite:///{db_path}"

    monkeypatch.setenv("SCHEDULER_ENABLED", "false")
    monkeypatch.setenv("TESTING", "true")
    monkeypatch.setenv("ALLOW_DEFAULT_ADMIN", "false")
    monkeypatch.setenv("SECRET_KEY", "test-secret")
    monkeypatch.setenv("JWT_SECRET_KEY", "test-secret")
    monkeypatch.setenv("DATABASE_URL", database_url)
    monkeypatch.setenv("FASTAPI_DATABASE_URL", database_url)

    # Clear cached settings/engines/session factories so each test uses its own temp DB.
    from src.app.config import get_settings
    from src.database import engine as db_engine
    from src.database import session as db_session

    get_settings.cache_clear()
    db_engine.get_engine.cache_clear()
    db_engine.get_async_engine.cache_clear()
    db_session._sync_session_factory = None
    db_session._async_session_factory = None

    return database_url


@pytest.fixture(scope="function")
def setup_db(db_url):
    assert os.environ.get("DATABASE_URL") == db_url
    from src.database.bootstrap import init_db

    init_db()
    yield


@pytest.fixture(scope="function")
def db_session(setup_db):
    from src.database.session import get_db_session

    with get_db_session() as session:
        yield session


@pytest.fixture(scope="function")
def fastapi_app(db_url):
    assert os.environ.get("DATABASE_URL") == db_url
    from src.app.main import create_app as create_fastapi_app

    return create_fastapi_app()


@pytest.fixture(scope="function")
async def async_client(fastapi_app):
    transport = ASGITransport(app=fastapi_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


@pytest.fixture(scope="function")
def setup_test_db(db_session):
    from src.models.user import User

    # Clear users (tests depend on deterministic identities).
    db_session.query(User).delete()

    admin = User(username="testadmin", email="testadmin@example.com", role="admin", is_active=True)
    admin.set_password("admin123")
    db_session.add(admin)

    user = User(username="testuser", email="testuser@example.com", role="user", is_active=True)
    user.set_password("user123")
    db_session.add(user)

    inactive = User(username="inactiveuser", email="inactive@example.com", role="user", is_active=False)
    inactive.set_password("inactive123")
    db_session.add(inactive)

    viewer = User(username="testviewer", email="testviewer@example.com", role="viewer", is_active=True)
    viewer.set_password("viewer123")
    db_session.add(viewer)

    db_session.commit()

    return {
        "admin": admin,
        "user": user,
        "inactive": inactive,
        "viewer": viewer,
    }


@pytest.fixture
def admin_access_token(setup_test_db):
    admin = setup_test_db["admin"]
    from src.app.dependencies.auth import create_access_token

    return create_access_token(user_id=admin.id, role=admin.role, email=admin.email)


@pytest.fixture
def user_access_token(setup_test_db):
    user = setup_test_db["user"]
    from src.app.dependencies.auth import create_access_token

    return create_access_token(user_id=user.id, role=user.role, email=user.email)


@pytest.fixture
def viewer_access_token(setup_test_db):
    viewer = setup_test_db["viewer"]
    from src.app.dependencies.auth import create_access_token

    return create_access_token(user_id=viewer.id, role=viewer.role, email=viewer.email)


@pytest.fixture
def admin_refresh_token(setup_test_db):
    admin = setup_test_db["admin"]
    from src.app.dependencies.auth import create_refresh_token

    return create_refresh_token(user_id=admin.id, role=admin.role, email=admin.email)

