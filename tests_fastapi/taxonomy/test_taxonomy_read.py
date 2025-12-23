import pytest


@pytest.fixture
def seed_taxonomy(app, setup_test_db):
    with app.app_context():
        from src.models import db
        from src.models.job_category import JobCategory
        from src.models.pic_team import PicTeam

        cat_active = JobCategory(slug="active", name="Active Category", is_active=True)
        cat_inactive = JobCategory(slug="inactive", name="Inactive Category", is_active=False)
        db.session.add_all([cat_active, cat_inactive])

        team_active = PicTeam(slug="team-a", name="Team A", slack_handle="@team-a", is_active=True)
        team_inactive = PicTeam(slug="team-b", name="Team B", slack_handle="@team-b", is_active=False)
        db.session.add_all([team_active, team_inactive])

        db.session.commit()

        return {
            "cat_active_id": cat_active.id,
            "cat_inactive_id": cat_inactive.id,
            "team_active_id": team_active.id,
            "team_inactive_id": team_inactive.id,
        }


@pytest.mark.asyncio
async def test_job_categories_requires_auth(async_client, seed_taxonomy):
    resp = await async_client.get("/api/v2/job-categories")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_job_categories_non_admin_sees_only_active(async_client, user_access_token, seed_taxonomy):
    resp = await async_client.get(
        "/api/v2/job-categories",
        params={"include_inactive": "true"},
        headers={"Authorization": f"Bearer {user_access_token}"},
    )
    assert resp.status_code == 200
    payload = resp.json()
    assert [c["slug"] for c in payload["categories"]] == ["active"]


@pytest.mark.asyncio
async def test_job_categories_admin_can_include_inactive(async_client, admin_access_token, seed_taxonomy):
    resp = await async_client.get(
        "/api/v2/job-categories",
        params={"include_inactive": "true"},
        headers={"Authorization": f"Bearer {admin_access_token}"},
    )
    assert resp.status_code == 200
    payload = resp.json()
    assert {c["slug"] for c in payload["categories"]} == {"active", "inactive"}


@pytest.mark.asyncio
async def test_pic_teams_non_admin_sees_only_active(async_client, viewer_access_token, seed_taxonomy):
    resp = await async_client.get(
        "/api/v2/pic-teams",
        params={"include_inactive": "true"},
        headers={"Authorization": f"Bearer {viewer_access_token}"},
    )
    assert resp.status_code == 200
    payload = resp.json()
    assert [t["slug"] for t in payload["pic_teams"]] == ["team-a"]


@pytest.mark.asyncio
async def test_pic_teams_admin_can_include_inactive(async_client, admin_access_token, seed_taxonomy):
    resp = await async_client.get(
        "/api/v2/pic-teams",
        params={"include_inactive": "true"},
        headers={"Authorization": f"Bearer {admin_access_token}"},
    )
    assert resp.status_code == 200
    payload = resp.json()
    assert {t["slug"] for t in payload["pic_teams"]} == {"team-a", "team-b"}

