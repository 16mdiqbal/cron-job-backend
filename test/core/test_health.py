import pytest


@pytest.mark.asyncio
async def test_phase1_health_endpoint(async_client):
    resp = await async_client.get("/api/v2/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "healthy"
    assert data["api"] == "v2"
    assert data["service"] == "cron-job-scheduler-fastapi"
    assert "timestamp" in data


@pytest.mark.asyncio
async def test_phase1_openapi_endpoint(async_client):
    resp = await async_client.get("/api/v2/openapi.json")
    assert resp.status_code == 200
    data = resp.json()
    assert "openapi" in data
    assert "/api/v2/health" in data.get("paths", {})

