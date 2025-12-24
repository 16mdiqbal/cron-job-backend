import pytest


@pytest.mark.asyncio
async def test_delete_user_admin_only(async_client, user_access_token, setup_test_db):
    viewer = setup_test_db["viewer"]
    resp = await async_client.delete(
        f"/api/v2/auth/users/{viewer.id}",
        headers={"Authorization": f"Bearer {user_access_token}"},
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_delete_user_cannot_delete_self(async_client, admin_access_token, setup_test_db):
    admin = setup_test_db["admin"]
    resp = await async_client.delete(
        f"/api/v2/auth/users/{admin.id}",
        headers={"Authorization": f"Bearer {admin_access_token}"},
    )
    assert resp.status_code == 400
    payload = resp.json()
    assert payload["error"] == "Cannot delete your own account"


@pytest.mark.asyncio
async def test_delete_user_not_found(async_client, admin_access_token):
    resp = await async_client.delete(
        "/api/v2/auth/users/does-not-exist",
        headers={"Authorization": f"Bearer {admin_access_token}"},
    )
    assert resp.status_code == 404
    payload = resp.json()
    assert payload["error"] == "User not found"


@pytest.mark.asyncio
async def test_delete_user_success(async_client, admin_access_token, setup_test_db):
    viewer = setup_test_db["viewer"]
    resp = await async_client.delete(
        f"/api/v2/auth/users/{viewer.id}",
        headers={"Authorization": f"Bearer {admin_access_token}"},
    )
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["message"] == "User deleted successfully"
    assert payload["deleted_user"]["id"] == viewer.id
    assert payload["deleted_user"]["username"] == viewer.username

    check = await async_client.get(
        f"/api/v2/auth/users/{viewer.id}",
        headers={"Authorization": f"Bearer {admin_access_token}"},
    )
    assert check.status_code == 404

