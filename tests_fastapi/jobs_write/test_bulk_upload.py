from datetime import datetime
from zoneinfo import ZoneInfo

import pytest


def _today_jst():
    return datetime.now(ZoneInfo("Asia/Tokyo")).date()


@pytest.fixture
def seed_bulk_upload_refs(app, setup_test_db):
    with app.app_context():
        from src.models import db
        from src.models.job import Job
        from src.models.job_category import JobCategory
        from src.models.pic_team import PicTeam

        category = JobCategory(slug="maintenance", name="Maintenance Jobs", is_active=True)
        team = PicTeam(slug="team-a", name="Team A", slack_handle="@team-a", is_active=True)
        db.session.add_all([category, team])
        db.session.flush()

        user = setup_test_db["user"]
        existing = Job(
            name="existing-job",
            cron_expression="0 * * * *",
            category=category.slug,
            end_date=_today_jst(),
            pic_team=team.slug,
            created_by=user.id,
            target_url="https://example.com/hook",
            is_active=True,
        )
        db.session.add(existing)
        db.session.commit()

        return {"category_slug": category.slug, "team_slug": team.slug}


def _csv_bytes(text: str) -> bytes:
    return text.encode("utf-8")


@pytest.mark.asyncio
async def test_bulk_upload_requires_user_or_admin(async_client, viewer_access_token, seed_bulk_upload_refs):
    csv_text = "Job Name,Cron Schedule (JST),Target URL,Category,End Date,PIC Team\nx,0 * * * *,https://example.com,maintenance,2099-01-01,team-a\n"
    resp = await async_client.post(
        "/api/v2/jobs/bulk-upload",
        headers={"Authorization": f"Bearer {viewer_access_token}"},
        files={"file": ("jobs.csv", _csv_bytes(csv_text), "text/csv")},
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_bulk_upload_missing_file(async_client, user_access_token):
    resp = await async_client.post(
        "/api/v2/jobs/bulk-upload",
        headers={"Authorization": f"Bearer {user_access_token}"},
        data={},
    )
    assert resp.status_code == 400
    payload = resp.json()
    assert payload["error"] == "Missing file"


@pytest.mark.asyncio
async def test_bulk_upload_invalid_csv_empty(async_client, user_access_token):
    resp = await async_client.post(
        "/api/v2/jobs/bulk-upload",
        headers={"Authorization": f"Bearer {user_access_token}"},
        files={"file": ("jobs.csv", b"", "text/csv")},
    )
    assert resp.status_code == 400
    payload = resp.json()
    assert payload["error"] == "Invalid CSV"


@pytest.mark.asyncio
async def test_bulk_upload_dry_run_validates_without_writing(async_client, user_access_token, seed_bulk_upload_refs):
    end_date = _today_jst().isoformat()
    csv_text = (
        "Job Name,Cron Schedule (JST),Status,Target URL,Category,End Date,PIC Team\n"
        f"bulk-job-1,0 * * * *,enabled,https://example.com/hook,maintenance,{end_date},Team A\n"
        f"existing-job,0 * * * *,enabled,https://example.com/hook,maintenance,{end_date},team-a\n"
    )
    resp = await async_client.post(
        "/api/v2/jobs/bulk-upload",
        headers={"Authorization": f"Bearer {user_access_token}"},
        data={"dry_run": "true"},
        files={"file": ("jobs.csv", _csv_bytes(csv_text), "text/csv")},
    )
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["dry_run"] is True
    assert payload["message"] == "CSV validated successfully"
    assert payload["created_count"] == 1
    assert payload["error_count"] == 1

    jobs = await async_client.get(
        "/api/v2/jobs",
        headers={"Authorization": f"Bearer {user_access_token}"},
    )
    assert jobs.status_code == 200
    names = {job["name"] for job in jobs.json()["jobs"]}
    assert "bulk-job-1" not in names
    assert "existing-job" in names


@pytest.mark.asyncio
async def test_bulk_upload_partial_success_and_normalizes_csv(async_client, user_access_token, seed_bulk_upload_refs):
    end_date = _today_jst().isoformat()
    csv_text = (
        "Job Name,Cron Schedule (JST),Status,Target URL,Repo,Workflow Name,Category,End Date,PIC Team,Request Body,Branch,\n"
        f'webhook-bulk,*/5 * * * *,enabled,https://example.com/hook,,,maintenance,{end_date},team-a,"{{\"\"k\"\": \"\"v\"\"}}",main,\n'
        f'github-bulk,0 * * * *,enabled,,octo/repo,workflow.yml,maintenance,{end_date},team-a,"{{\"\"x\"\": 1}}",,\n'
        f"bad-category,0 * * * *,enabled,https://example.com/hook,,,does-not-exist,{end_date},team-a,,,\n"
        ",,,,,,,,,,,\n"
    )

    resp = await async_client.post(
        "/api/v2/jobs/bulk-upload",
        headers={"Authorization": f"Bearer {user_access_token}"},
        data={"default_github_owner": "default-org"},
        files={"file": ("jobs.csv", _csv_bytes(csv_text), "text/csv")},
    )
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["dry_run"] is False
    assert payload["created_count"] == 2
    assert payload["error_count"] == 1
    assert payload["stats"]["removed_column_count"] == 1
    assert payload["stats"]["removed_empty_row_count"] == 1

    jobs_resp = await async_client.get(
        "/api/v2/jobs",
        headers={"Authorization": f"Bearer {user_access_token}"},
    )
    assert jobs_resp.status_code == 200
    jobs = {job["name"]: job for job in jobs_resp.json()["jobs"]}
    assert "webhook-bulk" in jobs
    assert "github-bulk" in jobs

    webhook_detail = await async_client.get(
        f"/api/v2/jobs/{jobs['webhook-bulk']['id']}",
        headers={"Authorization": f"Bearer {user_access_token}"},
    )
    assert webhook_detail.status_code == 200
    wjob = webhook_detail.json()["job"]
    assert wjob["target_url"] == "https://example.com/hook"
    assert wjob["metadata"]["k"] == "v"
    assert wjob["metadata"]["branchDetails"] == "main"

    github_detail = await async_client.get(
        f"/api/v2/jobs/{jobs['github-bulk']['id']}",
        headers={"Authorization": f"Bearer {user_access_token}"},
    )
    assert github_detail.status_code == 200
    gjob = github_detail.json()["job"]
    assert gjob["target_url"] is None
    assert gjob["github_owner"] == "octo"
    assert gjob["github_repo"] == "repo"
    assert gjob["github_workflow_name"] == "workflow.yml"


@pytest.mark.asyncio
async def test_bulk_upload_invalid_request_body_json(async_client, user_access_token, seed_bulk_upload_refs):
    end_date = _today_jst().isoformat()
    csv_text = (
        "Job Name,Cron Schedule (JST),Target URL,Category,End Date,PIC Team,Request Body\n"
        f'bad-json,0 * * * *,https://example.com/hook,maintenance,{end_date},team-a,"not-json"\n'
    )
    resp = await async_client.post(
        "/api/v2/jobs/bulk-upload",
        headers={"Authorization": f"Bearer {user_access_token}"},
        files={"file": ("jobs.csv", _csv_bytes(csv_text), "text/csv")},
    )
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["created_count"] == 0
    assert payload["error_count"] == 1
    assert payload["errors"][0]["error"] == "Invalid JSON in Request Body"

