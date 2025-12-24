import pytest
from sqlalchemy import select

from src.database.session import get_async_db_session
from src.models.user import User


@pytest.mark.asyncio
async def test_phase2_async_session_can_read_models(db_session):
    user = User(username="phase2user", email="phase2@example.com", role="admin", is_active=True)
    user.set_password("pass123")
    db_session.add(user)
    db_session.commit()
    user_id = user.id

    async with get_async_db_session() as session:
        result = await session.execute(select(User).where(User.id == user_id))
        fetched = result.scalar_one()
        assert fetched.username == "phase2user"
