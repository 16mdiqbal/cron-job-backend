import pytest
from sqlalchemy import select

from src.database.session import get_async_db_session
from src.fastapi_app.utils.notifications import create_notification
from src.models.notification import Notification


@pytest.mark.asyncio
async def test_create_notification_inserts_row(setup_test_db):
    user_id = setup_test_db["user"].id

    async with get_async_db_session() as session:
        created = await create_notification(
            session,
            user_id=user_id,
            title="Test",
            message="Hello",
            type="info",
        )

        assert created.id is not None
        assert created.user_id == user_id
        assert created.is_read is False
        assert created.read_at is None

        result = await session.execute(select(Notification).where(Notification.id == created.id))
        row = result.scalar_one_or_none()
        assert row is not None
        assert row.title == "Test"

