from datetime import datetime, timezone

import pytest


@pytest.fixture
def seed_notifications_for_mark_read(db_session, setup_test_db):
    from src.models.notification import Notification

    user = setup_test_db["user"]
    admin = setup_test_db["admin"]

    user_unread = Notification(
        user_id=user.id,
        title="Unread",
        message="Unread message",
        type="info",
        is_read=False,
        created_at=datetime(2025, 1, 1, 9, 0, 0, tzinfo=timezone.utc),
    )
    user_read = Notification(
        user_id=user.id,
        title="Already Read",
        message="Already read message",
        type="success",
        is_read=True,
        read_at=datetime(2025, 1, 1, 10, 0, 0, tzinfo=timezone.utc),
        created_at=datetime(2025, 1, 1, 9, 30, 0, tzinfo=timezone.utc),
    )
    admin_unread = Notification(
        user_id=admin.id,
        title="Admin Unread",
        message="Admin unread message",
        type="warning",
        is_read=False,
        created_at=datetime(2025, 1, 1, 9, 0, 0, tzinfo=timezone.utc),
    )

    db_session.add_all([user_unread, user_read, admin_unread])
    db_session.commit()

    return {
        "user_unread_id": user_unread.id,
        "user_read_id": user_read.id,
        "admin_unread_id": admin_unread.id,
    }


@pytest.mark.asyncio
async def test_mark_notification_read_requires_auth(async_client, seed_notifications_for_mark_read):
    resp = await async_client.put(f"/api/v2/notifications/{seed_notifications_for_mark_read['user_unread_id']}/read")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_mark_notification_read_not_found(async_client, user_access_token, seed_notifications_for_mark_read):
    resp = await async_client.put(
        "/api/v2/notifications/does-not-exist/read",
        headers={"Authorization": f"Bearer {user_access_token}"},
    )
    assert resp.status_code == 404
    assert resp.json() == {"error": "Notification not found"}


@pytest.mark.asyncio
async def test_mark_notification_read_forbidden_other_user(async_client, user_access_token, seed_notifications_for_mark_read):
    resp = await async_client.put(
        f"/api/v2/notifications/{seed_notifications_for_mark_read['admin_unread_id']}/read",
        headers={"Authorization": f"Bearer {user_access_token}"},
    )
    assert resp.status_code == 403
    assert resp.json() == {"error": "Forbidden: Cannot access other users notifications"}


@pytest.mark.asyncio
async def test_mark_notification_read_marks_as_read(async_client, user_access_token, seed_notifications_for_mark_read):
    resp = await async_client.put(
        f"/api/v2/notifications/{seed_notifications_for_mark_read['user_unread_id']}/read",
        headers={"Authorization": f"Bearer {user_access_token}"},
    )
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["message"] == "Notification marked as read"
    assert payload["notification"]["id"] == seed_notifications_for_mark_read["user_unread_id"]
    assert payload["notification"]["is_read"] is True
    assert payload["notification"]["read_at"] is not None


@pytest.mark.asyncio
async def test_mark_all_notifications_read(async_client, user_access_token, seed_notifications_for_mark_read):
    resp = await async_client.put(
        "/api/v2/notifications/read-all",
        headers={"Authorization": f"Bearer {user_access_token}"},
    )
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["message"] == "All notifications marked as read"
    assert payload["updated_count"] == 1

    count_resp = await async_client.get(
        "/api/v2/notifications/unread-count",
        headers={"Authorization": f"Bearer {user_access_token}"},
    )
    assert count_resp.status_code == 200
    assert count_resp.json()["unread_count"] == 0
