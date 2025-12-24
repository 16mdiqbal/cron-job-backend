import pytest


@pytest.mark.asyncio
async def test_login_with_username(async_client, setup_test_db):
    response = await async_client.post(
        "/api/v2/auth/login",
        json={"username": "testadmin", "password": "admin123"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["message"] == "Login successful"
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["username"] == "testadmin"
    assert data["user"]["role"] == "admin"
    assert "password" not in data["user"]
    assert "password_hash" not in data["user"]


@pytest.mark.asyncio
async def test_login_with_email(async_client, setup_test_db):
    response = await async_client.post(
        "/api/v2/auth/login",
        json={"email": "testuser@example.com", "password": "user123"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["user"]["email"] == "testuser@example.com"
    assert data["user"]["role"] == "user"


@pytest.mark.asyncio
async def test_login_with_invalid_username(async_client, setup_test_db):
    response = await async_client.post(
        "/api/v2/auth/login",
        json={"username": "nonexistent", "password": "password123"},
    )

    assert response.status_code == 401
    assert "Invalid email/username or password" in response.json()["detail"]


@pytest.mark.asyncio
async def test_login_with_invalid_password(async_client, setup_test_db):
    response = await async_client.post(
        "/api/v2/auth/login",
        json={"username": "testadmin", "password": "wrongpassword"},
    )

    assert response.status_code == 401
    assert "Invalid email/username or password" in response.json()["detail"]


@pytest.mark.asyncio
async def test_login_inactive_user(async_client, setup_test_db):
    response = await async_client.post(
        "/api/v2/auth/login",
        json={"username": "inactiveuser", "password": "inactive123"},
    )

    assert response.status_code == 401
    assert "inactive" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_login_missing_password(async_client, setup_test_db):
    response = await async_client.post(
        "/api/v2/auth/login",
        json={"username": "testadmin"},
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_login_missing_credentials(async_client, setup_test_db):
    response = await async_client.post(
        "/api/v2/auth/login",
        json={"password": "password123"},
    )

    assert response.status_code == 422

