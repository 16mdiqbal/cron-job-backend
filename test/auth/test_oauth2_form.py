import pytest


@pytest.mark.asyncio
async def test_form_login(async_client, setup_test_db):
    response = await async_client.post(
        "/api/v2/auth/login/form",
        data={"username": "testadmin", "password": "admin123"},
    )

    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["user"]["username"] == "testadmin"


@pytest.mark.asyncio
async def test_form_login_with_email_as_username(async_client, setup_test_db):
    response = await async_client.post(
        "/api/v2/auth/login/form",
        data={"username": "testuser@example.com", "password": "user123"},
    )

    assert response.status_code == 200
    assert response.json()["user"]["email"] == "testuser@example.com"

