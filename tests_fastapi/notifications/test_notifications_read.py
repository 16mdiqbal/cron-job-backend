from datetime import datetime, timezone

import pytest


@pytest.fixture
def seed_notifications(app, setup_test_db):
    with app.app_context():
        from src.models import db
        from src.models.notification import Notification

        user = setup_test_db["user"]
        admin = setup_test_db["admin"]

        user_old_unread = Notification(
            user_id=user.id,
            title="Old Unread",
            message="Old unread message",
            type="info",
            is_read=False,
            created_at=datetime(2025, 1, 1, 9, 0, 0, tzinfo=timezone.utc),
        )
        user_new_read = Notification(
            user_id=user.id,
            title="New Read",
            message="New read message",
            type="success",
            is_read=True,
            read_at=datetime(2025, 1, 2, 10, 0, 0, tzinfo=timezone.utc),
            created_at=datetime(2025, 1, 2, 9, 0, 0, tzinfo=timezone.utc),
        )
        admin_unread = Notification(
            user_id=admin.id,
            title="Admin Unread",
            message="Admin unread message",
            type="warning",
            is_read=False,
            created_at=datetime(2025, 1, 3, 9, 0, 0, tzinfo=timezone.utc),
        )

        db.session.add_all([user_old_unread, user_new_read, admin_unread])
        db.session.commit()

        return {
            "user_old_unread_id": user_old_unread.id,
            "user_new_read_id": user_new_read.id,
            "admin_unread_id": admin_unread.id,
        }


@pytest.mark.asyncio
async def test_notifications_requires_auth(async_client, seed_notifications):
    resp = await async_client.get("/api/v2/notifications")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_notifications_lists_only_current_user_sorted_desc(async_client, user_access_token, seed_notifications):
    resp = await async_client.get(
        "/api/v2/notifications",
        headers={"Authorization": f"Bearer {user_access_token}"},
    )
    assert resp.status_code == 200
    payload = resp.json()

    assert payload["total"] == 2
    assert payload["page"] == 1
    assert payload["per_page"] == 20
    assert payload["total_pages"] == 1
    assert payload["range"] == {"from": None, "to": None}

    ids = [n["id"] for n in payload["notifications"]]
    assert ids == [seed_notifications["user_new_read_id"], seed_notifications["user_old_unread_id"]]
    assert seed_notifications["admin_unread_id"] not in ids


@pytest.mark.asyncio
async def test_notifications_unread_only(async_client, user_access_token, seed_notifications):
    resp = await async_client.get(
        "/api/v2/notifications",
        params={"unread_only": "true"},
        headers={"Authorization": f"Bearer {user_access_token}"},
    )
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["total"] == 1
    assert [n["id"] for n in payload["notifications"]] == [seed_notifications["user_old_unread_id"]]


@pytest.mark.asyncio
async def test_notifications_per_page_is_capped(async_client, user_access_token, seed_notifications):
    resp = await async_client.get(
        "/api/v2/notifications",
        params={"per_page": "1000"},
        headers={"Authorization": f"Bearer {user_access_token}"},
    )
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["per_page"] == 100
    assert payload["total_pages"] == 1


@pytest.mark.asyncio
async def test_notifications_invalid_date(async_client, user_access_token, seed_notifications):
    resp = await async_client.get(
        "/api/v2/notifications",
        params={"from": "not-a-date"},
        headers={"Authorization": f"Bearer {user_access_token}"},
    )
    assert resp.status_code == 400
    assert resp.json() == {"error": "Invalid date", "message": "Invalid date"}


@pytest.mark.asyncio
async def test_notifications_invalid_date_range(async_client, user_access_token, seed_notifications):
    resp = await async_client.get(
        "/api/v2/notifications",
        params={"from": "2025-01-03T00:00:00", "to": "2025-01-03T00:00:00"},
        headers={"Authorization": f"Bearer {user_access_token}"},
    )
    assert resp.status_code == 400
    assert resp.json() == {"error": "Invalid date range", "message": '"from" must be earlier than "to".'}


@pytest.mark.asyncio
async def test_notifications_date_only_to_is_inclusive_day(async_client, user_access_token, seed_notifications):
    resp = await async_client.get(
        "/api/v2/notifications",
        params={"from": "2025-01-01", "to": "2025-01-01"},
        headers={"Authorization": f"Bearer {user_access_token}"},
    )
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["total"] == 1
    assert [n["id"] for n in payload["notifications"]] == [seed_notifications["user_old_unread_id"]]
    assert payload["range"] == {"from": "2025-01-01T00:00:00", "to": "2025-01-02T00:00:00"}


@pytest.mark.asyncio
async def test_unread_count_requires_auth(async_client, seed_notifications):
    resp = await async_client.get("/api/v2/notifications/unread-count")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_unread_count_counts_only_unread_for_user(async_client, user_access_token, seed_notifications):
    resp = await async_client.get(
        "/api/v2/notifications/unread-count",
        headers={"Authorization": f"Bearer {user_access_token}"},
    )
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["unread_count"] == 1
    assert payload["range"] == {"from": None, "to": None}


@pytest.mark.asyncio
async def test_unread_count_date_filter(async_client, user_access_token, seed_notifications):
    resp = await async_client.get(
        "/api/v2/notifications/unread-count",
        params={"from": "2025-01-01", "to": "2025-01-01"},
        headers={"Authorization": f"Bearer {user_access_token}"},
    )
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["unread_count"] == 1
    assert payload["range"] == {"from": "2025-01-01T00:00:00", "to": "2025-01-02T00:00:00"}
