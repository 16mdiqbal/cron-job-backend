import pytest


@pytest.mark.asyncio
async def test_cron_preview_returns_next_runs(async_client, viewer_access_token):
    resp = await async_client.post(
        "/api/v2/jobs/cron-preview",
        headers={"Authorization": f"Bearer {viewer_access_token}"},
        json={"expression": "*/5 * * * *", "count": 3},
    )
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["count"] == 3
    assert len(payload["next_runs"]) == 3
    assert "timezone" in payload


@pytest.mark.asyncio
async def test_cron_preview_invalid_cron_returns_400(async_client, viewer_access_token):
    resp = await async_client.post(
        "/api/v2/jobs/cron-preview",
        headers={"Authorization": f"Bearer {viewer_access_token}"},
        json={"expression": "*/5 * *"},
    )
    assert resp.status_code == 400
    payload = resp.json()
    assert payload["error"] == "Invalid cron expression"

