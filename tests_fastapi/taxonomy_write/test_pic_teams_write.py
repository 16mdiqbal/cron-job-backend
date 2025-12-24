import pytest


@pytest.fixture
def seed_teams_and_jobs(db_session, setup_test_db):
    from src.models.job import Job
    from src.models.pic_team import PicTeam

    old_team = PicTeam(slug="old-team", name="Old Team", slack_handle="@old-team", is_active=True)
    other_team = PicTeam(slug="other-team", name="Other Team", slack_handle="@other-team", is_active=True)
    db_session.add_all([old_team, other_team])

    job1 = Job(name="team-job-1", cron_expression="0 0 * * *", pic_team="old-team", category="general")
    job2 = Job(name="team-job-2", cron_expression="0 0 * * *", pic_team="old-team", category="general")
    job3 = Job(name="team-job-3", cron_expression="0 0 * * *", pic_team="other-team", category="general")
    db_session.add_all([job1, job2, job3])

    db_session.commit()

    return {
        "old_team_id": old_team.id,
        "other_team_id": other_team.id,
        "job1_id": job1.id,
        "job2_id": job2.id,
        "job3_id": job3.id,
    }


@pytest.mark.asyncio
async def test_create_pic_team_admin_only(async_client, user_access_token):
    resp = await async_client.post(
        "/api/v2/pic-teams",
        headers={"Authorization": f"Bearer {user_access_token}"},
        json={"name": "X", "slack_handle": "@x"},
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_create_pic_team_requires_json(async_client, admin_access_token):
    resp = await async_client.post(
        "/api/v2/pic-teams",
        headers={"Authorization": f"Bearer {admin_access_token}"},
        content="x",
    )
    assert resp.status_code == 400
    assert resp.json()["error"] == "Content-Type must be application/json"


@pytest.mark.asyncio
async def test_create_pic_team_requires_name(async_client, admin_access_token):
    resp = await async_client.post(
        "/api/v2/pic-teams",
        headers={"Authorization": f"Bearer {admin_access_token}"},
        json={"slack_handle": "@x"},
    )
    assert resp.status_code == 400
    assert resp.json() == {"error": "Missing required fields", "message": '"name" is required.'}


@pytest.mark.asyncio
async def test_create_pic_team_requires_slack_handle(async_client, admin_access_token):
    resp = await async_client.post(
        "/api/v2/pic-teams",
        headers={"Authorization": f"Bearer {admin_access_token}"},
        json={"name": "QA Team"},
    )
    assert resp.status_code == 400
    assert resp.json() == {"error": "Missing required fields", "message": '"slack_handle" is required.'}


@pytest.mark.asyncio
async def test_create_pic_team_slug_generated_from_name(async_client, admin_access_token):
    resp = await async_client.post(
        "/api/v2/pic-teams",
        headers={"Authorization": f"Bearer {admin_access_token}"},
        json={"name": "QA Team", "slack_handle": "@qa"},
    )
    assert resp.status_code == 201
    payload = resp.json()
    assert payload["message"] == "PIC team created"
    assert payload["pic_team"]["slug"] == "qa-team"
    assert payload["pic_team"]["slack_handle"] == "@qa"


@pytest.mark.asyncio
async def test_create_pic_team_duplicate_slug(async_client, admin_access_token, seed_teams_and_jobs):
    resp = await async_client.post(
        "/api/v2/pic-teams",
        headers={"Authorization": f"Bearer {admin_access_token}"},
        json={"name": "Old Team", "slack_handle": "@new"},
    )
    assert resp.status_code == 409
    assert resp.json() == {
        "error": "Duplicate slug",
        "message": 'PIC team slug "old-team" already exists.',
    }


@pytest.mark.asyncio
async def test_update_pic_team_not_found(async_client, admin_access_token):
    resp = await async_client.put(
        "/api/v2/pic-teams/does-not-exist",
        headers={"Authorization": f"Bearer {admin_access_token}"},
        json={"name": "New"},
    )
    assert resp.status_code == 404
    assert resp.json()["error"] == "Not found"


@pytest.mark.asyncio
async def test_update_pic_team_rejects_slug_key(async_client, admin_access_token, seed_teams_and_jobs):
    resp = await async_client.put(
        f"/api/v2/pic-teams/{seed_teams_and_jobs['old_team_id']}",
        headers={"Authorization": f"Bearer {admin_access_token}"},
        json={"slug": "nope"},
    )
    assert resp.status_code == 400
    assert resp.json() == {
        "error": "Invalid payload",
        "message": "Slug cannot be edited directly; it is derived from name.",
    }


@pytest.mark.asyncio
async def test_update_pic_team_slack_handle_cannot_be_empty(async_client, admin_access_token, seed_teams_and_jobs):
    resp = await async_client.put(
        f"/api/v2/pic-teams/{seed_teams_and_jobs['old_team_id']}",
        headers={"Authorization": f"Bearer {admin_access_token}"},
        json={"slack_handle": "   "},
    )
    assert resp.status_code == 400
    assert resp.json() == {"error": "Invalid slack_handle", "message": "slack_handle cannot be empty."}


@pytest.mark.asyncio
async def test_update_pic_team_renames_slug_and_updates_jobs(async_client, admin_access_token, seed_teams_and_jobs):
    resp = await async_client.put(
        f"/api/v2/pic-teams/{seed_teams_and_jobs['old_team_id']}",
        headers={"Authorization": f"Bearer {admin_access_token}"},
        json={"name": "New Team Name"},
    )
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["message"] == "PIC team updated"
    assert payload["pic_team"]["slug"] == "new-team-name"
    assert payload["jobs_updated"] == 2

    from src.database.session import get_db_session
    from src.models.job import Job

    with get_db_session() as session:
        job1 = session.get(Job, seed_teams_and_jobs["job1_id"])
        job2 = session.get(Job, seed_teams_and_jobs["job2_id"])
        job3 = session.get(Job, seed_teams_and_jobs["job3_id"])
        assert job1.pic_team == "new-team-name"
        assert job2.pic_team == "new-team-name"
        assert job3.pic_team == "other-team"


@pytest.mark.asyncio
async def test_update_pic_team_can_toggle_is_active(async_client, admin_access_token, seed_teams_and_jobs):
    resp = await async_client.put(
        f"/api/v2/pic-teams/{seed_teams_and_jobs['old_team_id']}",
        headers={"Authorization": f"Bearer {admin_access_token}"},
        json={"is_active": False},
    )
    assert resp.status_code == 200
    assert resp.json()["pic_team"]["is_active"] is False

    from src.database.session import get_db_session
    from src.models.pic_team import PicTeam

    with get_db_session() as session:
        team = session.get(PicTeam, seed_teams_and_jobs["old_team_id"])
        assert team.is_active is False


@pytest.mark.asyncio
async def test_delete_pic_team_disables(async_client, admin_access_token, seed_teams_and_jobs):
    resp = await async_client.delete(
        f"/api/v2/pic-teams/{seed_teams_and_jobs['old_team_id']}",
        headers={"Authorization": f"Bearer {admin_access_token}"},
    )
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["message"] == "PIC team disabled"
    assert payload["pic_team"]["is_active"] is False

    from src.database.session import get_db_session
    from src.models.pic_team import PicTeam

    with get_db_session() as session:
        team = session.get(PicTeam, seed_teams_and_jobs["old_team_id"])
        assert team.is_active is False
