import pytest


@pytest.mark.asyncio
async def test_verify_valid_token(async_client, admin_access_token, setup_test_db):
    response = await async_client.get(
        "/api/v2/auth/verify",
        headers={"Authorization": f"Bearer {admin_access_token}"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["valid"] is True
    assert data["username"] == "testadmin"
    assert data["role"] == "admin"


@pytest.mark.asyncio
async def test_verify_invalid_token(async_client, setup_test_db):
    response = await async_client.get(
        "/api/v2/auth/verify",
        headers={"Authorization": "Bearer invalid_token"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_logout(async_client, admin_access_token, setup_test_db):
    response = await async_client.post(
        "/api/v2/auth/logout",
        headers={"Authorization": f"Bearer {admin_access_token}"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["message"] == "Logout successful"

