import pytest


@pytest.mark.asyncio
async def test_get_slack_settings_admin_only(async_client, user_access_token):
    resp = await async_client.get(
        "/api/v2/settings/slack",
        headers={"Authorization": f"Bearer {user_access_token}"},
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_get_slack_settings_creates_defaults(async_client, admin_access_token):
    resp = await async_client.get(
        "/api/v2/settings/slack",
        headers={"Authorization": f"Bearer {admin_access_token}"},
    )
    assert resp.status_code == 200
    payload = resp.json()
    settings = payload["slack_settings"]
    assert settings["is_enabled"] is False
    assert settings["webhook_url"] is None
    assert settings["channel"] is None


@pytest.mark.asyncio
async def test_update_slack_settings_requires_json(async_client, admin_access_token):
    resp = await async_client.put(
        "/api/v2/settings/slack",
        headers={"Authorization": f"Bearer {admin_access_token}"},
        content="x",
    )
    assert resp.status_code == 400
    assert resp.json()["error"] == "Content-Type must be application/json"


@pytest.mark.asyncio
async def test_update_slack_settings_admin_only(async_client, user_access_token):
    resp = await async_client.put(
        "/api/v2/settings/slack",
        headers={"Authorization": f"Bearer {user_access_token}"},
        json={"is_enabled": False},
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_update_slack_settings_requires_webhook_when_enabled(async_client, admin_access_token):
    resp = await async_client.put(
        "/api/v2/settings/slack",
        headers={"Authorization": f"Bearer {admin_access_token}"},
        json={"is_enabled": True},
    )
    assert resp.status_code == 400
    assert resp.json() == {
        "error": "Invalid settings",
        "message": "webhook_url is required when Slack is enabled.",
    }


@pytest.mark.asyncio
async def test_update_slack_settings_trims_and_persists(async_client, admin_access_token):
    resp = await async_client.put(
        "/api/v2/settings/slack",
        headers={"Authorization": f"Bearer {admin_access_token}"},
        json={
            "is_enabled": True,
            "webhook_url": "  https://hooks.slack.com/services/T123/B456/XYZ  ",
            "channel": "  #cron-alerts  ",
        },
    )
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["message"] == "Slack settings updated"
    settings = payload["slack_settings"]
    assert settings["is_enabled"] is True
    assert settings["webhook_url"] == "https://hooks.slack.com/services/T123/B456/XYZ"
    assert settings["channel"] == "#cron-alerts"

    get_resp = await async_client.get(
        "/api/v2/settings/slack",
        headers={"Authorization": f"Bearer {admin_access_token}"},
    )
    assert get_resp.status_code == 200
    persisted = get_resp.json()["slack_settings"]
    assert persisted["is_enabled"] is True
    assert persisted["webhook_url"] == "https://hooks.slack.com/services/T123/B456/XYZ"
    assert persisted["channel"] == "#cron-alerts"


@pytest.mark.asyncio
async def test_update_slack_settings_empty_strings_become_null(async_client, admin_access_token):
    # Start with enabled settings.
    await async_client.put(
        "/api/v2/settings/slack",
        headers={"Authorization": f"Bearer {admin_access_token}"},
        json={
            "is_enabled": True,
            "webhook_url": "https://hooks.slack.com/services/T123/B456/XYZ",
            "channel": "#cron-alerts",
        },
    )

    # Disable and clear values via empty strings.
    resp = await async_client.put(
        "/api/v2/settings/slack",
        headers={"Authorization": f"Bearer {admin_access_token}"},
        json={"is_enabled": False, "webhook_url": "   ", "channel": ""},
    )
    assert resp.status_code == 200
    settings = resp.json()["slack_settings"]
    assert settings["is_enabled"] is False
    assert settings["webhook_url"] is None
    assert settings["channel"] is None

