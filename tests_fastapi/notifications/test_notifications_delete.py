from datetime import datetime, timezone

import pytest


@pytest.fixture
def seed_notifications_for_delete(app, setup_test_db):
    with app.app_context():
        from src.models import db
        from src.models.notification import Notification

        user = setup_test_db["user"]
        admin = setup_test_db["admin"]

        user_read_old = Notification(
            user_id=user.id,
            title="Read Old",
            message="Read old message",
            type="info",
            is_read=True,
            read_at=datetime(2025, 1, 1, 10, 0, 0, tzinfo=timezone.utc),
            created_at=datetime(2025, 1, 1, 9, 0, 0, tzinfo=timezone.utc),
        )
        user_read_new = Notification(
            user_id=user.id,
            title="Read New",
            message="Read new message",
            type="success",
            is_read=True,
            read_at=datetime(2025, 1, 3, 10, 0, 0, tzinfo=timezone.utc),
            created_at=datetime(2025, 1, 3, 9, 0, 0, tzinfo=timezone.utc),
        )
        user_unread = Notification(
            user_id=user.id,
            title="Unread",
            message="Unread message",
            type="warning",
            is_read=False,
            created_at=datetime(2025, 1, 2, 9, 0, 0, tzinfo=timezone.utc),
        )
        admin_read = Notification(
            user_id=admin.id,
            title="Admin Read",
            message="Admin read message",
            type="info",
            is_read=True,
            read_at=datetime(2025, 1, 2, 10, 0, 0, tzinfo=timezone.utc),
            created_at=datetime(2025, 1, 2, 9, 0, 0, tzinfo=timezone.utc),
        )

        db.session.add_all([user_read_old, user_read_new, user_unread, admin_read])
        db.session.commit()

        return {
            "user_read_old_id": user_read_old.id,
            "user_read_new_id": user_read_new.id,
            "user_unread_id": user_unread.id,
            "admin_read_id": admin_read.id,
        }


@pytest.mark.asyncio
async def test_delete_notification_requires_auth(async_client, seed_notifications_for_delete):
    resp = await async_client.delete(f"/api/v2/notifications/{seed_notifications_for_delete['user_unread_id']}")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_delete_notification_not_found(async_client, user_access_token, seed_notifications_for_delete):
    resp = await async_client.delete(
        "/api/v2/notifications/does-not-exist",
        headers={"Authorization": f"Bearer {user_access_token}"},
    )
    assert resp.status_code == 404
    assert resp.json() == {"error": "Notification not found"}


@pytest.mark.asyncio
async def test_delete_notification_forbidden_other_user(async_client, user_access_token, seed_notifications_for_delete):
    resp = await async_client.delete(
        f"/api/v2/notifications/{seed_notifications_for_delete['admin_read_id']}",
        headers={"Authorization": f"Bearer {user_access_token}"},
    )
    assert resp.status_code == 403
    assert resp.json() == {"error": "Forbidden: Cannot delete other users notifications"}


@pytest.mark.asyncio
async def test_delete_notification_success(async_client, user_access_token, seed_notifications_for_delete):
    resp = await async_client.delete(
        f"/api/v2/notifications/{seed_notifications_for_delete['user_unread_id']}",
        headers={"Authorization": f"Bearer {user_access_token}"},
    )
    assert resp.status_code == 200
    assert resp.json() == {"message": "Notification deleted successfully"}

    list_resp = await async_client.get(
        "/api/v2/notifications",
        headers={"Authorization": f"Bearer {user_access_token}"},
    )
    assert list_resp.status_code == 200
    ids = [n["id"] for n in list_resp.json()["notifications"]]
    assert seed_notifications_for_delete["user_unread_id"] not in ids


@pytest.mark.asyncio
async def test_delete_read_notifications_requires_auth(async_client, seed_notifications_for_delete):
    resp = await async_client.delete("/api/v2/notifications/delete-read")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_delete_read_notifications_invalid_date(async_client, user_access_token, seed_notifications_for_delete):
    resp = await async_client.delete(
        "/api/v2/notifications/delete-read",
        params={"from": "bad-date"},
        headers={"Authorization": f"Bearer {user_access_token}"},
    )
    assert resp.status_code == 400
    assert resp.json() == {"error": "Invalid date", "message": "Invalid date"}


@pytest.mark.asyncio
async def test_delete_read_notifications_invalid_range(async_client, user_access_token, seed_notifications_for_delete):
    resp = await async_client.delete(
        "/api/v2/notifications/delete-read",
        params={"from": "2025-01-02T00:00:00", "to": "2025-01-02T00:00:00"},
        headers={"Authorization": f"Bearer {user_access_token}"},
    )
    assert resp.status_code == 400
    assert resp.json() == {"error": "Invalid date range", "message": '"from" must be earlier than "to".'}


@pytest.mark.asyncio
async def test_delete_read_notifications_deletes_only_read_for_user(async_client, user_access_token, seed_notifications_for_delete):
    resp = await async_client.delete(
        "/api/v2/notifications/delete-read",
        headers={"Authorization": f"Bearer {user_access_token}"},
    )
    assert resp.status_code == 200
    assert resp.json() == {"deleted_count": 2}

    list_resp = await async_client.get(
        "/api/v2/notifications",
        headers={"Authorization": f"Bearer {user_access_token}"},
    )
    assert list_resp.status_code == 200
    ids = [n["id"] for n in list_resp.json()["notifications"]]
    assert seed_notifications_for_delete["user_read_old_id"] not in ids
    assert seed_notifications_for_delete["user_read_new_id"] not in ids
    assert seed_notifications_for_delete["user_unread_id"] in ids


@pytest.mark.asyncio
async def test_delete_read_notifications_date_range_inclusive_to_day(
    async_client, user_access_token, seed_notifications_for_delete
):
    resp = await async_client.delete(
        "/api/v2/notifications/delete-read",
        params={"from": "2025-01-01", "to": "2025-01-01"},
        headers={"Authorization": f"Bearer {user_access_token}"},
    )
    assert resp.status_code == 200
    assert resp.json() == {"deleted_count": 1}

    list_resp = await async_client.get(
        "/api/v2/notifications",
        headers={"Authorization": f"Bearer {user_access_token}"},
    )
    ids = [n["id"] for n in list_resp.json()["notifications"]]
    assert seed_notifications_for_delete["user_read_old_id"] not in ids
    assert seed_notifications_for_delete["user_read_new_id"] in ids

