import os

import pytest


@pytest.mark.asyncio
async def test_test_run_requires_user_or_admin(async_client, viewer_access_token):
    resp = await async_client.post(
        "/api/v2/jobs/test-run",
        headers={"Authorization": f"Bearer {viewer_access_token}"},
        json={"target_url": "https://example.com/hook"},
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_test_run_missing_target_configuration(async_client, user_access_token):
    resp = await async_client.post(
        "/api/v2/jobs/test-run",
        headers={"Authorization": f"Bearer {user_access_token}"},
        json={"metadata": {}},
    )
    assert resp.status_code == 400
    payload = resp.json()
    assert payload["error"] == "Missing target configuration"


@pytest.mark.asyncio
async def test_test_run_invalid_metadata(async_client, user_access_token):
    resp = await async_client.post(
        "/api/v2/jobs/test-run",
        headers={"Authorization": f"Bearer {user_access_token}"},
        json={"target_url": "https://example.com/hook", "metadata": ["nope"]},
    )
    assert resp.status_code == 400
    payload = resp.json()
    assert payload["error"] == "Invalid metadata"


@pytest.mark.asyncio
async def test_test_run_webhook_invalid_scheme(async_client, user_access_token):
    resp = await async_client.post(
        "/api/v2/jobs/test-run",
        headers={"Authorization": f"Bearer {user_access_token}"},
        json={"target_url": "ftp://example.com/hook"},
    )
    assert resp.status_code == 400
    payload = resp.json()
    assert payload["error"] == "Invalid target_url"


@pytest.mark.asyncio
async def test_test_run_webhook_success(async_client, user_access_token, monkeypatch):
    async def fake_http_request(method, url, *, headers=None, json_payload=None, timeout=10.0):
        assert method == "POST"
        assert url == "https://example.com/hook"
        assert json_payload == {"k": "v"}
        assert timeout == 3.0
        return 200, "ok"

    monkeypatch.setattr("src.fastapi_app.routers.jobs._http_request", fake_http_request)

    resp = await async_client.post(
        "/api/v2/jobs/test-run",
        headers={"Authorization": f"Bearer {user_access_token}"},
        json={"target_url": "https://example.com/hook", "metadata": {"k": "v"}, "timeout_seconds": 3},
    )
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["ok"] is True
    assert payload["type"] == "webhook"
    assert payload["status_code"] == 200


@pytest.mark.asyncio
async def test_test_run_github_missing_token_returns_200(async_client, user_access_token, monkeypatch):
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    resp = await async_client.post(
        "/api/v2/jobs/test-run",
        headers={"Authorization": f"Bearer {user_access_token}"},
        json={"github_owner": "octo", "github_repo": "repo", "github_workflow_name": "workflow.yml", "metadata": {"ref": "main"}},
    )
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["ok"] is False
    assert payload["type"] == "github"
    assert payload["error"] == "GitHub token not configured"


@pytest.mark.asyncio
async def test_test_run_github_success(async_client, user_access_token, monkeypatch):
    monkeypatch.setenv("GITHUB_TOKEN", "token")
    captured = {"url": None, "json": None, "headers": None}

    async def fake_http_request(method, url, *, headers=None, json_payload=None, timeout=10.0):
        captured["url"] = url
        captured["json"] = json_payload
        captured["headers"] = headers
        return 204, ""

    monkeypatch.setattr("src.fastapi_app.routers.jobs._http_request", fake_http_request)

    resp = await async_client.post(
        "/api/v2/jobs/test-run",
        headers={"Authorization": f"Bearer {user_access_token}"},
        json={
            "github_owner": "octo",
            "github_repo": "repo",
            "github_workflow_name": "workflow.yml",
            "metadata": {"branch": "dev", "x": 1},
        },
    )
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["ok"] is True
    assert payload["type"] == "github"
    assert payload["status_code"] == 204
    assert captured["url"].endswith("/repos/octo/repo/actions/workflows/workflow.yml/dispatches")
    assert captured["json"]["ref"] == "dev"
    assert captured["json"]["inputs"]["x"] == 1
    assert "Authorization" in (captured["headers"] or {})

