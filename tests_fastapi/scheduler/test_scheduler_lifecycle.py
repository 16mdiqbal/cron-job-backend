import os

import pytest


@pytest.fixture
def fastapi_app_scheduler_enabled(db_url, setup_db, tmp_path, monkeypatch):
    # db_url fixture sets SCHEDULER_ENABLED=false/TESTING=true; override for this specific app instance.
    monkeypatch.setenv("TESTING", "false")
    monkeypatch.setenv("SCHEDULER_ENABLED", "true")
    monkeypatch.setenv("SCHEDULER_LOCK_PATH", str(tmp_path / "scheduler.lock"))

    from src.fastapi_app.config import get_settings
    from src.fastapi_app import scheduler_runtime

    get_settings.cache_clear()
    scheduler_runtime._reset_for_tests()

    from src.fastapi_app.main import create_app as create_fastapi_app

    return create_fastapi_app()


@pytest.mark.asyncio
async def test_scheduler_does_not_start_in_tests_by_default(async_client):
    resp = await async_client.get("/api/v2/health")
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["scheduler_running"] is False
    assert payload["scheduled_jobs_count"] == 0


@pytest.mark.asyncio
async def test_scheduler_starts_when_enabled_and_reports_health(fastapi_app_scheduler_enabled):
    # httpx.ASGITransport (0.28+) does not run ASGI lifespan hooks; start/stop explicitly here.
    from src.fastapi_app import scheduler_runtime

    started = scheduler_runtime.start_scheduler()
    assert started is True
    try:
        # Use the existing async_client fixture pattern to hit the health endpoint directly.
        from httpx import ASGITransport, AsyncClient

        transport = ASGITransport(app=fastapi_app_scheduler_enabled)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/api/v2/health")
            assert resp.status_code == 200
            payload = resp.json()
            assert payload["scheduler_running"] is True
            assert payload["scheduled_jobs_count"] == 0
    finally:
        scheduler_runtime.stop_scheduler()

    lock_path = os.environ.get("SCHEDULER_LOCK_PATH")
    assert lock_path
    assert os.path.exists(lock_path) is False
