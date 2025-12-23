import pytest


@pytest.mark.asyncio
async def test_get_ui_preferences_self_creates_defaults(async_client, viewer_access_token, setup_test_db):
    viewer = setup_test_db["viewer"]
    resp = await async_client.get(
        f"/api/v2/auth/users/{viewer.id}/ui-preferences",
        headers={"Authorization": f"Bearer {viewer_access_token}"},
    )
    assert resp.status_code == 200
    payload = resp.json()
    cols = payload["preferences"]["jobs_table_columns"]
    assert cols["pic_team"] is True
    assert cols["end_date"] is True
    assert cols["cron_expression"] is False
    assert cols["target_url"] is False
    assert cols["last_execution_at"] is False


@pytest.mark.asyncio
async def test_get_ui_preferences_other_forbidden_for_non_admin(async_client, user_access_token, setup_test_db):
    admin = setup_test_db["admin"]
    resp = await async_client.get(
        f"/api/v2/auth/users/{admin.id}/ui-preferences",
        headers={"Authorization": f"Bearer {user_access_token}"},
    )
    assert resp.status_code == 403
    assert resp.json()["error"] == "Forbidden: Cannot access other users preferences"


@pytest.mark.asyncio
async def test_get_ui_preferences_admin_can_access_any(async_client, admin_access_token, setup_test_db):
    user = setup_test_db["user"]
    resp = await async_client.get(
        f"/api/v2/auth/users/{user.id}/ui-preferences",
        headers={"Authorization": f"Bearer {admin_access_token}"},
    )
    assert resp.status_code == 200
    assert "jobs_table_columns" in resp.json()["preferences"]


@pytest.mark.asyncio
async def test_update_ui_preferences_requires_json(async_client, user_access_token, setup_test_db):
    user = setup_test_db["user"]
    resp = await async_client.put(
        f"/api/v2/auth/users/{user.id}/ui-preferences",
        headers={"Authorization": f"Bearer {user_access_token}"},
        content="x",
    )
    assert resp.status_code == 400
    assert resp.json()["error"] == "Content-Type must be application/json"


@pytest.mark.asyncio
async def test_update_ui_preferences_requires_jobs_table_columns(async_client, user_access_token, setup_test_db):
    user = setup_test_db["user"]
    resp = await async_client.put(
        f"/api/v2/auth/users/{user.id}/ui-preferences",
        headers={"Authorization": f"Bearer {user_access_token}"},
        json={},
    )
    assert resp.status_code == 400
    payload = resp.json()
    assert payload["error"] == "Missing required fields"


@pytest.mark.asyncio
async def test_update_ui_preferences_jobs_table_columns_must_be_object(async_client, user_access_token, setup_test_db):
    user = setup_test_db["user"]
    resp = await async_client.put(
        f"/api/v2/auth/users/{user.id}/ui-preferences",
        headers={"Authorization": f"Bearer {user_access_token}"},
        json={"jobs_table_columns": ["nope"]},
    )
    assert resp.status_code == 400
    payload = resp.json()
    assert payload["error"] == "Invalid payload"


@pytest.mark.asyncio
async def test_update_ui_preferences_self_normalizes_keys(async_client, user_access_token, setup_test_db):
    user = setup_test_db["user"]
    resp = await async_client.put(
        f"/api/v2/auth/users/{user.id}/ui-preferences",
        headers={"Authorization": f"Bearer {user_access_token}"},
        json={"jobs_table_columns": {"pic_team": False, "unknown": True, "target_url": True}},
    )
    assert resp.status_code == 200
    payload = resp.json()
    cols = payload["preferences"]["jobs_table_columns"]
    assert cols["pic_team"] is False
    assert cols["target_url"] is True
    assert "unknown" not in cols

    check = await async_client.get(
        f"/api/v2/auth/users/{user.id}/ui-preferences",
        headers={"Authorization": f"Bearer {user_access_token}"},
    )
    assert check.status_code == 200
    assert check.json()["preferences"]["jobs_table_columns"]["target_url"] is True


@pytest.mark.asyncio
async def test_update_ui_preferences_other_forbidden_for_non_admin(async_client, user_access_token, setup_test_db):
    admin = setup_test_db["admin"]
    resp = await async_client.put(
        f"/api/v2/auth/users/{admin.id}/ui-preferences",
        headers={"Authorization": f"Bearer {user_access_token}"},
        json={"jobs_table_columns": {"pic_team": False}},
    )
    assert resp.status_code == 403
    assert resp.json()["error"] == "Forbidden: Cannot update other users preferences"


@pytest.mark.asyncio
async def test_update_ui_preferences_not_found(async_client, admin_access_token):
    resp = await async_client.put(
        "/api/v2/auth/users/does-not-exist/ui-preferences",
        headers={"Authorization": f"Bearer {admin_access_token}"},
        json={"jobs_table_columns": {"pic_team": False}},
    )
    assert resp.status_code == 404
    assert resp.json()["error"] == "User not found"

