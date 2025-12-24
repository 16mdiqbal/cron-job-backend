import pytest


@pytest.mark.asyncio
async def test_validate_cron_requires_auth(async_client):
    resp = await async_client.post("/api/v2/jobs/validate-cron", json={"expression": "* * * * *"})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_validate_cron_allows_viewer(async_client, viewer_access_token):
    resp = await async_client.post(
        "/api/v2/jobs/validate-cron",
        headers={"Authorization": f"Bearer {viewer_access_token}"},
        json={"expression": "* * * * *"},
    )
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["valid"] is True


@pytest.mark.asyncio
async def test_validate_cron_invalid_returns_200(async_client, viewer_access_token):
    resp = await async_client.post(
        "/api/v2/jobs/validate-cron",
        headers={"Authorization": f"Bearer {viewer_access_token}"},
        json={"expression": "* * * *"},
    )
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["valid"] is False
    assert payload["error"] == "Invalid cron expression"

