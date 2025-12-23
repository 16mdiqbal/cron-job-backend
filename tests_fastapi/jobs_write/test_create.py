from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pytest


@pytest.fixture
def seed_team_and_category(app, setup_test_db):
    with app.app_context():
        from src.models import db
        from src.models.job_category import JobCategory
        from src.models.pic_team import PicTeam

        team = PicTeam(slug="team-a", name="Team A", slack_handle="@team-a", is_active=True)
        disabled_team = PicTeam(slug="team-b", name="Team B", slack_handle="@team-b", is_active=False)

        category = JobCategory(slug="maintenance", name="Maintenance Jobs", is_active=True)

        db.session.add_all([team, disabled_team, category])
        db.session.commit()

        return {
            "team_slug": team.slug,
            "disabled_team_slug": disabled_team.slug,
            "category_slug": category.slug,
            "category_name": category.name,
        }


def _today_jst_str() -> str:
    today = datetime.now(ZoneInfo("Asia/Tokyo")).date()
    return today.isoformat()


def _yesterday_jst_str() -> str:
    today = datetime.now(ZoneInfo("Asia/Tokyo")).date()
    return (today - timedelta(days=1)).isoformat()


@pytest.mark.asyncio
async def test_create_job_requires_user_or_admin(async_client, viewer_access_token, seed_team_and_category):
    resp = await async_client.post(
        "/api/v2/jobs",
        headers={"Authorization": f"Bearer {viewer_access_token}"},
        json={
            "name": "job-1",
            "cron_expression": "0 * * * *",
            "end_date": _today_jst_str(),
            "pic_team": seed_team_and_category["team_slug"],
            "target_url": "https://example.com/hook",
        },
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_create_job_missing_required_fields(async_client, user_access_token, seed_team_and_category):
    resp = await async_client.post(
        "/api/v2/jobs",
        headers={"Authorization": f"Bearer {user_access_token}"},
        json={},
    )
    assert resp.status_code == 400
    payload = resp.json()
    assert payload["error"] == "Missing required fields"
    assert set(payload["missing_fields"]) == {"name", "cron_expression", "end_date"}


@pytest.mark.asyncio
async def test_create_job_empty_name(async_client, user_access_token, seed_team_and_category):
    resp = await async_client.post(
        "/api/v2/jobs",
        headers={"Authorization": f"Bearer {user_access_token}"},
        json={
            "name": "   ",
            "cron_expression": "0 * * * *",
            "end_date": _today_jst_str(),
            "pic_team": seed_team_and_category["team_slug"],
            "target_url": "https://example.com/hook",
        },
    )
    assert resp.status_code == 400
    assert resp.json()["error"] == "Job name cannot be empty"


@pytest.mark.asyncio
async def test_create_job_invalid_cron(async_client, user_access_token, seed_team_and_category):
    resp = await async_client.post(
        "/api/v2/jobs",
        headers={"Authorization": f"Bearer {user_access_token}"},
        json={
            "name": "job-bad-cron",
            "cron_expression": "0 * * *",
            "end_date": _today_jst_str(),
            "pic_team": seed_team_and_category["team_slug"],
            "target_url": "https://example.com/hook",
        },
    )
    assert resp.status_code == 400
    payload = resp.json()
    assert payload["error"] == "Invalid cron expression"


@pytest.mark.asyncio
async def test_create_job_invalid_end_date_format(async_client, user_access_token, seed_team_and_category):
    resp = await async_client.post(
        "/api/v2/jobs",
        headers={"Authorization": f"Bearer {user_access_token}"},
        json={
            "name": "job-bad-date",
            "cron_expression": "0 * * * *",
            "end_date": "2025/01/01",
            "pic_team": seed_team_and_category["team_slug"],
            "target_url": "https://example.com/hook",
        },
    )
    assert resp.status_code == 400
    payload = resp.json()
    assert payload["error"] == "Invalid end_date"


@pytest.mark.asyncio
async def test_create_job_end_date_in_past(async_client, user_access_token, seed_team_and_category):
    resp = await async_client.post(
        "/api/v2/jobs",
        headers={"Authorization": f"Bearer {user_access_token}"},
        json={
            "name": "job-past-date",
            "cron_expression": "0 * * * *",
            "end_date": _yesterday_jst_str(),
            "pic_team": seed_team_and_category["team_slug"],
            "target_url": "https://example.com/hook",
        },
    )
    assert resp.status_code == 400
    payload = resp.json()
    assert payload["error"] == "Invalid end_date"


@pytest.mark.asyncio
async def test_create_job_pic_team_required(async_client, user_access_token, seed_team_and_category):
    resp = await async_client.post(
        "/api/v2/jobs",
        headers={"Authorization": f"Bearer {user_access_token}"},
        json={
            "name": "job-no-team",
            "cron_expression": "0 * * * *",
            "end_date": _today_jst_str(),
            "target_url": "https://example.com/hook",
        },
    )
    assert resp.status_code == 400
    payload = resp.json()
    assert payload["error"] == "Invalid PIC team"


@pytest.mark.asyncio
async def test_create_job_pic_team_disabled(async_client, user_access_token, seed_team_and_category):
    resp = await async_client.post(
        "/api/v2/jobs",
        headers={"Authorization": f"Bearer {user_access_token}"},
        json={
            "name": "job-disabled-team",
            "cron_expression": "0 * * * *",
            "end_date": _today_jst_str(),
            "pic_team": seed_team_and_category["disabled_team_slug"],
            "target_url": "https://example.com/hook",
        },
    )
    assert resp.status_code == 400
    payload = resp.json()
    assert payload["error"] == "Invalid PIC team"


@pytest.mark.asyncio
async def test_create_job_missing_target_configuration(async_client, user_access_token, seed_team_and_category):
    resp = await async_client.post(
        "/api/v2/jobs",
        headers={"Authorization": f"Bearer {user_access_token}"},
        json={
            "name": "job-no-target",
            "cron_expression": "0 * * * *",
            "end_date": _today_jst_str(),
            "pic_team": seed_team_and_category["team_slug"],
        },
    )
    assert resp.status_code == 400
    payload = resp.json()
    assert payload["error"] == "Missing target configuration"


@pytest.mark.asyncio
async def test_create_job_defaults_category_to_general(async_client, user_access_token, seed_team_and_category):
    resp = await async_client.post(
        "/api/v2/jobs",
        headers={"Authorization": f"Bearer {user_access_token}"},
        json={
            "name": "job-general",
            "cron_expression": "0 * * * *",
            "end_date": _today_jst_str(),
            "pic_team": seed_team_and_category["team_slug"],
            "target_url": "https://example.com/hook",
        },
    )
    assert resp.status_code == 201
    payload = resp.json()
    assert payload["message"] == "Job created successfully"
    assert payload["job"]["category"] == "general"


@pytest.mark.asyncio
async def test_create_job_resolves_category_by_name(async_client, user_access_token, seed_team_and_category):
    resp = await async_client.post(
        "/api/v2/jobs",
        headers={"Authorization": f"Bearer {user_access_token}"},
        json={
            "name": "job-category-by-name",
            "cron_expression": "0 * * * *",
            "end_date": _today_jst_str(),
            "pic_team": seed_team_and_category["team_slug"],
            "category": seed_team_and_category["category_name"],
            "target_url": "https://example.com/hook",
        },
    )
    assert resp.status_code == 201
    payload = resp.json()
    assert payload["job"]["category"] == seed_team_and_category["category_slug"]


@pytest.mark.asyncio
async def test_create_job_unknown_category(async_client, user_access_token, seed_team_and_category):
    resp = await async_client.post(
        "/api/v2/jobs",
        headers={"Authorization": f"Bearer {user_access_token}"},
        json={
            "name": "job-unknown-category",
            "cron_expression": "0 * * * *",
            "end_date": _today_jst_str(),
            "pic_team": seed_team_and_category["team_slug"],
            "category": "Does Not Exist",
            "target_url": "https://example.com/hook",
        },
    )
    assert resp.status_code == 400
    payload = resp.json()
    assert payload["error"] == "Invalid category"


@pytest.mark.asyncio
async def test_create_job_github_defaults_owner(async_client, user_access_token, seed_team_and_category):
    resp = await async_client.post(
        "/api/v2/jobs",
        headers={"Authorization": f"Bearer {user_access_token}"},
        json={
            "name": "job-github-default-owner",
            "cron_expression": "0 * * * *",
            "end_date": _today_jst_str(),
            "pic_team": seed_team_and_category["team_slug"],
            "github_repo": "repo-1",
            "github_workflow_name": "workflow.yml",
        },
    )
    assert resp.status_code == 201
    payload = resp.json()
    assert payload["job"]["github_owner"] is not None
    assert payload["job"]["github_owner"] != ""


@pytest.mark.asyncio
async def test_create_job_email_notification_fields(async_client, user_access_token, seed_team_and_category):
    resp = await async_client.post(
        "/api/v2/jobs",
        headers={"Authorization": f"Bearer {user_access_token}"},
        json={
            "name": "job-email-notify",
            "cron_expression": "0 * * * *",
            "end_date": _today_jst_str(),
            "pic_team": seed_team_and_category["team_slug"],
            "target_url": "https://example.com/hook",
            "enable_email_notifications": True,
            "notification_emails": ["a@example.com", "b@example.com"],
            "notify_on_success": True,
        },
    )
    assert resp.status_code == 201
    payload = resp.json()
    assert payload["job"]["enable_email_notifications"] is True
    assert payload["job"]["notification_emails"] == ["a@example.com", "b@example.com"]
    assert payload["job"]["notify_on_success"] is True


@pytest.mark.asyncio
async def test_create_job_duplicate_name(async_client, user_access_token, seed_team_and_category):
    payload = {
        "name": "job-dup",
        "cron_expression": "0 * * * *",
        "end_date": _today_jst_str(),
        "pic_team": seed_team_and_category["team_slug"],
        "target_url": "https://example.com/hook",
    }
    resp = await async_client.post(
        "/api/v2/jobs",
        headers={"Authorization": f"Bearer {user_access_token}"},
        json=payload,
    )
    assert resp.status_code == 201

    resp = await async_client.post(
        "/api/v2/jobs",
        headers={"Authorization": f"Bearer {user_access_token}"},
        json=payload,
    )
    assert resp.status_code == 400
    assert resp.json()["error"] == "Duplicate job name"


@pytest.mark.asyncio
async def test_create_job_broadcasts_notification(async_client, user_access_token, seed_team_and_category, setup_test_db):
    resp = await async_client.post(
        "/api/v2/jobs",
        headers={"Authorization": f"Bearer {user_access_token}"},
        json={
            "name": "job-notify-created",
            "cron_expression": "0 * * * *",
            "end_date": _today_jst_str(),
            "pic_team": seed_team_and_category["team_slug"],
            "target_url": "https://example.com/hook",
        },
    )
    assert resp.status_code == 201
    job_id = resp.json()["job"]["id"]

    inbox = await async_client.get(
        "/api/v2/notifications",
        params={"per_page": 20},
        headers={"Authorization": f"Bearer {user_access_token}"},
    )
    assert inbox.status_code == 200
    notifications = inbox.json()["notifications"]
    assert any(
        n["title"] == "New Job Created"
        and n.get("related_job_id") == job_id
        and setup_test_db["user"].email in n["message"]
        for n in notifications
    )
