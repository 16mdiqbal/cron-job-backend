import pytest


@pytest.mark.asyncio
async def test_get_notification_preferences_self_creates_defaults(async_client, viewer_access_token, setup_test_db):
    viewer = setup_test_db["viewer"]
    resp = await async_client.get(
        f"/api/v2/auth/users/{viewer.id}/preferences",
        headers={"Authorization": f"Bearer {viewer_access_token}"},
    )
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["message"] == "Notification preferences retrieved successfully"
    prefs = payload["preferences"]
    assert prefs["user_id"] == viewer.id
    assert prefs["email_on_job_success"] is True
    assert prefs["email_on_job_failure"] is True
    assert prefs["email_on_job_disabled"] is False
    # Flask GET default values:
    assert prefs["browser_notifications"] is False
    assert prefs["daily_digest"] is False
    assert prefs["weekly_report"] is False


@pytest.mark.asyncio
async def test_get_notification_preferences_other_forbidden_for_non_admin(
    async_client, user_access_token, setup_test_db
):
    admin = setup_test_db["admin"]
    resp = await async_client.get(
        f"/api/v2/auth/users/{admin.id}/preferences",
        headers={"Authorization": f"Bearer {user_access_token}"},
    )
    assert resp.status_code == 403
    payload = resp.json()
    assert payload["error"] == "Forbidden: Cannot access other users preferences"


@pytest.mark.asyncio
async def test_get_notification_preferences_admin_can_access_any(async_client, admin_access_token, setup_test_db):
    user = setup_test_db["user"]
    resp = await async_client.get(
        f"/api/v2/auth/users/{user.id}/preferences",
        headers={"Authorization": f"Bearer {admin_access_token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["preferences"]["user_id"] == user.id


@pytest.mark.asyncio
async def test_get_notification_preferences_user_not_found(async_client, admin_access_token):
    resp = await async_client.get(
        "/api/v2/auth/users/does-not-exist/preferences",
        headers={"Authorization": f"Bearer {admin_access_token}"},
    )
    assert resp.status_code == 404
    assert resp.json()["error"] == "User not found"


@pytest.mark.asyncio
async def test_update_notification_preferences_requires_json(async_client, user_access_token, setup_test_db):
    user = setup_test_db["user"]
    resp = await async_client.put(
        f"/api/v2/auth/users/{user.id}/preferences",
        headers={"Authorization": f"Bearer {user_access_token}"},
        content="x",
    )
    assert resp.status_code == 400
    assert resp.json()["error"] == "Content-Type must be application/json"


@pytest.mark.asyncio
async def test_update_notification_preferences_self_partial_update(async_client, user_access_token, setup_test_db):
    user = setup_test_db["user"]

    # First GET creates Flask defaults.
    await async_client.get(
        f"/api/v2/auth/users/{user.id}/preferences",
        headers={"Authorization": f"Bearer {user_access_token}"},
    )

    resp = await async_client.put(
        f"/api/v2/auth/users/{user.id}/preferences",
        headers={"Authorization": f"Bearer {user_access_token}"},
        json={"browser_notifications": True, "weekly_report": True},
    )
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["message"] == "Notification preferences updated successfully"
    prefs = payload["preferences"]
    assert prefs["browser_notifications"] is True
    assert prefs["weekly_report"] is True
    # Unchanged from Flask GET defaults
    assert prefs["daily_digest"] is False


@pytest.mark.asyncio
async def test_update_notification_preferences_other_forbidden_for_non_admin(
    async_client, user_access_token, setup_test_db
):
    admin = setup_test_db["admin"]
    resp = await async_client.put(
        f"/api/v2/auth/users/{admin.id}/preferences",
        headers={"Authorization": f"Bearer {user_access_token}"},
        json={"daily_digest": True},
    )
    assert resp.status_code == 403
    payload = resp.json()
    assert payload["error"] == "Forbidden: Cannot update other users preferences"


@pytest.mark.asyncio
async def test_update_notification_preferences_admin_can_update_any(async_client, admin_access_token, setup_test_db):
    user = setup_test_db["user"]
    resp = await async_client.put(
        f"/api/v2/auth/users/{user.id}/preferences",
        headers={"Authorization": f"Bearer {admin_access_token}"},
        json={"daily_digest": True},
    )
    assert resp.status_code == 200
    assert resp.json()["preferences"]["daily_digest"] is True

