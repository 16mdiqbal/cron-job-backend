import pytest


@pytest.mark.asyncio
async def test_refresh_with_valid_token(async_client, admin_refresh_token, setup_test_db):
    response = await async_client.post(
        "/api/v2/auth/refresh",
        headers={"Authorization": f"Bearer {admin_refresh_token}"},
    )

    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["expires_in"] == 3600

    new_token = data["access_token"]
    verify_response = await async_client.get(
        "/api/v2/auth/me",
        headers={"Authorization": f"Bearer {new_token}"},
    )
    assert verify_response.status_code == 200


@pytest.mark.asyncio
async def test_refresh_without_token(async_client, setup_test_db):
    response = await async_client.post("/api/v2/auth/refresh")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_refresh_with_access_token_rejected(async_client, admin_access_token, setup_test_db):
    response = await async_client.post(
        "/api/v2/auth/refresh",
        headers={"Authorization": f"Bearer {admin_access_token}"},
    )
    assert response.status_code == 401

