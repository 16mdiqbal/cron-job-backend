import pytest


@pytest.mark.asyncio
async def test_register_user_as_admin(async_client, admin_access_token, setup_test_db):
    response = await async_client.post(
        "/api/v2/auth/register",
        headers={"Authorization": f"Bearer {admin_access_token}"},
        json={
            "username": "newuser",
            "email": "newuser@example.com",
            "password": "newpass123",
            "role": "user",
        },
    )

    assert response.status_code == 201
    data = response.json()
    assert data["success"] is True
    assert data["message"] == "User created successfully"
    assert data["user"]["username"] == "newuser"
    assert data["user"]["email"] == "newuser@example.com"
    assert data["user"]["role"] == "user"
    assert data["user"]["is_active"] is True


@pytest.mark.asyncio
async def test_register_user_as_regular_user_forbidden(async_client, user_access_token, setup_test_db):
    response = await async_client.post(
        "/api/v2/auth/register",
        headers={"Authorization": f"Bearer {user_access_token}"},
        json={
            "username": "anotheruser",
            "email": "anotheruser@example.com",
            "password": "pass123",
            "role": "user",
        },
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_register_user_as_viewer_forbidden(async_client, viewer_access_token, setup_test_db):
    response = await async_client.post(
        "/api/v2/auth/register",
        headers={"Authorization": f"Bearer {viewer_access_token}"},
        json={
            "username": "vieweruser",
            "email": "vieweruser@example.com",
            "password": "pass123",
            "role": "viewer",
        },
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_register_duplicate_username(async_client, admin_access_token, setup_test_db):
    response = await async_client.post(
        "/api/v2/auth/register",
        headers={"Authorization": f"Bearer {admin_access_token}"},
        json={
            "username": "testadmin",
            "email": "new@example.com",
            "password": "pass123",
            "role": "user",
        },
    )

    assert response.status_code == 409
    assert "already exists" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_register_duplicate_email(async_client, admin_access_token, setup_test_db):
    response = await async_client.post(
        "/api/v2/auth/register",
        headers={"Authorization": f"Bearer {admin_access_token}"},
        json={
            "username": "uniqueuser",
            "email": "testadmin@example.com",
            "password": "pass123",
            "role": "user",
        },
    )

    assert response.status_code == 409
    assert "already exists" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_register_with_short_password(async_client, admin_access_token, setup_test_db):
    response = await async_client.post(
        "/api/v2/auth/register",
        headers={"Authorization": f"Bearer {admin_access_token}"},
        json={
            "username": "shortpass",
            "email": "short@example.com",
            "password": "12345",
            "role": "user",
        },
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_register_with_invalid_email(async_client, admin_access_token, setup_test_db):
    response = await async_client.post(
        "/api/v2/auth/register",
        headers={"Authorization": f"Bearer {admin_access_token}"},
        json={
            "username": "invalidemail",
            "email": "not-an-email",
            "password": "pass123",
            "role": "user",
        },
    )
    assert response.status_code == 422

