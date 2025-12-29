import pytest


@pytest.mark.asyncio
async def test_update_user_requires_auth(async_client):
    resp = await async_client.put("/api/v2/auth/users/any", json={"email": "x@example.com"})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_update_user_self_email_allowed_for_viewer(async_client, viewer_access_token, setup_test_db):
    viewer = setup_test_db["viewer"]
    resp = await async_client.put(
        f"/api/v2/auth/users/{viewer.id}",
        headers={"Authorization": f"Bearer {viewer_access_token}"},
        json={"email": "newviewer@example.com"},
    )
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["message"] == "User updated successfully"
    assert "email" in payload["updated_fields"]
    assert payload["user"]["email"] == "newviewer@example.com"


@pytest.mark.asyncio
async def test_update_user_other_forbidden_for_non_admin(async_client, user_access_token, setup_test_db):
    admin = setup_test_db["admin"]
    resp = await async_client.put(
        f"/api/v2/auth/users/{admin.id}",
        headers={"Authorization": f"Bearer {user_access_token}"},
        json={"email": "nope@example.com"},
    )
    assert resp.status_code == 403
    payload = resp.json()
    assert payload["error"] == "Forbidden. You can only update your own profile."


@pytest.mark.asyncio
async def test_update_user_non_admin_cannot_change_role(async_client, user_access_token, setup_test_db):
    user = setup_test_db["user"]
    resp = await async_client.put(
        f"/api/v2/auth/users/{user.id}",
        headers={"Authorization": f"Bearer {user_access_token}"},
        json={"role": "admin"},
    )
    assert resp.status_code == 403
    payload = resp.json()
    assert payload["error"] == "Only admins can change user roles"


@pytest.mark.asyncio
async def test_update_user_non_admin_cannot_change_is_active(async_client, user_access_token, setup_test_db):
    user = setup_test_db["user"]
    resp = await async_client.put(
        f"/api/v2/auth/users/{user.id}",
        headers={"Authorization": f"Bearer {user_access_token}"},
        json={"is_active": False},
    )
    assert resp.status_code == 403
    payload = resp.json()
    assert payload["error"] == "Only admins can change user active status"


@pytest.mark.asyncio
async def test_update_user_admin_can_change_role_and_is_active(async_client, admin_access_token, setup_test_db):
    user = setup_test_db["user"]
    resp = await async_client.put(
        f"/api/v2/auth/users/{user.id}",
        headers={"Authorization": f"Bearer {admin_access_token}"},
        json={"role": "viewer", "is_active": False},
    )
    assert resp.status_code == 200
    payload = resp.json()
    assert set(payload["updated_fields"]) >= {"role", "is_active"}
    assert payload["user"]["role"] == "viewer"
    assert payload["user"]["is_active"] is False


@pytest.mark.asyncio
async def test_update_user_email_conflict_returns_409(async_client, admin_access_token, setup_test_db):
    user = setup_test_db["user"]
    viewer = setup_test_db["viewer"]
    resp = await async_client.put(
        f"/api/v2/auth/users/{user.id}",
        headers={"Authorization": f"Bearer {admin_access_token}"},
        json={"email": viewer.email},
    )
    assert resp.status_code == 409
    payload = resp.json()
    assert payload["error"] == "Email already exists"


@pytest.mark.asyncio
async def test_update_user_password_too_short(async_client, user_access_token, setup_test_db):
    user = setup_test_db["user"]
    resp = await async_client.put(
        f"/api/v2/auth/users/{user.id}",
        headers={"Authorization": f"Bearer {user_access_token}"},
        json={"password": "123"},
    )
    assert resp.status_code == 400
    payload = resp.json()
    assert payload["error"] == "Password must be at least 6 characters long"


@pytest.mark.asyncio
async def test_update_user_invalid_role(async_client, admin_access_token, setup_test_db):
    user = setup_test_db["user"]
    resp = await async_client.put(
        f"/api/v2/auth/users/{user.id}",
        headers={"Authorization": f"Bearer {admin_access_token}"},
        json={"role": "superadmin"},
    )
    assert resp.status_code == 400
    payload = resp.json()
    assert payload["error"] == "Invalid role"


@pytest.mark.asyncio
async def test_update_user_no_valid_fields(async_client, user_access_token, setup_test_db):
    user = setup_test_db["user"]
    resp = await async_client.put(
        f"/api/v2/auth/users/{user.id}",
        headers={"Authorization": f"Bearer {user_access_token}"},
        json={"username": "ignored"},
    )
    assert resp.status_code == 400
    payload = resp.json()
    assert payload["error"] == "No valid fields to update"


@pytest.mark.asyncio
async def test_update_user_not_found(async_client, admin_access_token):
    resp = await async_client.put(
        "/api/v2/auth/users/does-not-exist",
        headers={"Authorization": f"Bearer {admin_access_token}"},
        json={"email": "x@example.com"},
    )
    assert resp.status_code == 404
    payload = resp.json()
    assert payload["error"] == "User not found"

