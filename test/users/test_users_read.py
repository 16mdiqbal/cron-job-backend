import pytest


@pytest.mark.asyncio
async def test_list_users_admin_only(async_client, admin_access_token):
    resp = await async_client.get(
        "/api/v2/auth/users",
        headers={"Authorization": f"Bearer {admin_access_token}"},
    )
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["count"] >= 4
    assert isinstance(payload["users"], list)
    assert {u["role"] for u in payload["users"]} >= {"admin", "user", "viewer"}


@pytest.mark.asyncio
async def test_list_users_forbidden_for_non_admin(async_client, user_access_token):
    resp = await async_client.get(
        "/api/v2/auth/users",
        headers={"Authorization": f"Bearer {user_access_token}"},
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_get_user_self_allowed(async_client, viewer_access_token, setup_test_db):
    viewer = setup_test_db["viewer"]
    resp = await async_client.get(
        f"/api/v2/auth/users/{viewer.id}",
        headers={"Authorization": f"Bearer {viewer_access_token}"},
    )
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["user"]["id"] == viewer.id
    assert payload["user"]["role"] == "viewer"


@pytest.mark.asyncio
async def test_get_user_other_forbidden_for_non_admin(async_client, user_access_token, setup_test_db):
    admin = setup_test_db["admin"]
    resp = await async_client.get(
        f"/api/v2/auth/users/{admin.id}",
        headers={"Authorization": f"Bearer {user_access_token}"},
    )
    assert resp.status_code == 403
    payload = resp.json()
    assert payload["error"] == "Forbidden. You can only view your own profile."


@pytest.mark.asyncio
async def test_get_user_admin_can_view_any(async_client, admin_access_token, setup_test_db):
    user = setup_test_db["user"]
    resp = await async_client.get(
        f"/api/v2/auth/users/{user.id}",
        headers={"Authorization": f"Bearer {admin_access_token}"},
    )
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["user"]["id"] == user.id


@pytest.mark.asyncio
async def test_get_user_not_found(async_client, admin_access_token):
    resp = await async_client.get(
        "/api/v2/auth/users/does-not-exist",
        headers={"Authorization": f"Bearer {admin_access_token}"},
    )
    assert resp.status_code == 404
    payload = resp.json()
    assert payload["error"] == "User not found"

