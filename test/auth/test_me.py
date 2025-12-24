from datetime import datetime, timedelta, timezone

import jwt
import pytest

from src.app.config import get_settings


@pytest.mark.asyncio
async def test_get_current_user_with_valid_token(async_client, admin_access_token, setup_test_db):
    response = await async_client.get(
        "/api/v2/auth/me",
        headers={"Authorization": f"Bearer {admin_access_token}"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["username"] == "testadmin"
    assert data["email"] == "testadmin@example.com"
    assert data["role"] == "admin"
    assert data["is_active"] is True


@pytest.mark.asyncio
async def test_get_current_user_without_token(async_client, setup_test_db):
    response = await async_client.get("/api/v2/auth/me")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_current_user_with_invalid_token(async_client, setup_test_db):
    response = await async_client.get(
        "/api/v2/auth/me",
        headers={"Authorization": "Bearer invalid_token_here"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_current_user_with_expired_token(async_client, setup_test_db):
    admin = setup_test_db["admin"]
    settings = get_settings()

    expired_payload = {
        "sub": admin.id,
        "role": admin.role,
        "email": admin.email,
        "exp": datetime.now(timezone.utc) - timedelta(hours=1),
        "iat": datetime.now(timezone.utc) - timedelta(hours=2),
        "type": "access",
        "fresh": True,
    }
    expired_token = jwt.encode(expired_payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)

    response = await async_client.get(
        "/api/v2/auth/me",
        headers={"Authorization": f"Bearer {expired_token}"},
    )

    assert response.status_code == 401
    assert "expired" in response.json()["detail"].lower()

