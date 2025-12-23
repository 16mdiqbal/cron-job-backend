import pytest


@pytest.fixture
def seed_categories_and_jobs(app, setup_test_db):
    with app.app_context():
        from src.models import db
        from src.models.job import Job
        from src.models.job_category import JobCategory

        general = JobCategory(slug="general", name="General", is_active=True)
        old_cat = JobCategory(slug="old-cat", name="Old Cat", is_active=True)
        db.session.add_all([general, old_cat])

        job1 = Job(name="job-1", cron_expression="0 0 * * *", category="old-cat")
        job2 = Job(name="job-2", cron_expression="0 0 * * *", category="old-cat")
        job3 = Job(name="job-3", cron_expression="0 0 * * *", category="general")
        db.session.add_all([job1, job2, job3])

        db.session.commit()

        return {
            "general_id": general.id,
            "old_cat_id": old_cat.id,
            "job1_id": job1.id,
            "job2_id": job2.id,
            "job3_id": job3.id,
        }


@pytest.mark.asyncio
async def test_create_job_category_admin_only(async_client, user_access_token):
    resp = await async_client.post(
        "/api/v2/job-categories",
        headers={"Authorization": f"Bearer {user_access_token}"},
        json={"name": "X"},
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_create_job_category_requires_json(async_client, admin_access_token):
    resp = await async_client.post(
        "/api/v2/job-categories",
        headers={"Authorization": f"Bearer {admin_access_token}"},
        content="x",
    )
    assert resp.status_code == 400
    assert resp.json()["error"] == "Content-Type must be application/json"


@pytest.mark.asyncio
async def test_create_job_category_requires_name(async_client, admin_access_token):
    resp = await async_client.post(
        "/api/v2/job-categories",
        headers={"Authorization": f"Bearer {admin_access_token}"},
        json={},
    )
    assert resp.status_code == 400
    assert resp.json() == {"error": "Missing required fields", "message": '"name" is required.'}


@pytest.mark.asyncio
async def test_create_job_category_slug_generated_from_name(async_client, admin_access_token):
    resp = await async_client.post(
        "/api/v2/job-categories",
        headers={"Authorization": f"Bearer {admin_access_token}"},
        json={"name": "Analytics Jobs"},
    )
    assert resp.status_code == 201
    payload = resp.json()
    assert payload["message"] == "Category created"
    assert payload["category"]["slug"] == "analytics-jobs"
    assert payload["category"]["name"] == "Analytics Jobs"


@pytest.mark.asyncio
async def test_create_job_category_duplicate_slug(async_client, admin_access_token, seed_categories_and_jobs):
    resp = await async_client.post(
        "/api/v2/job-categories",
        headers={"Authorization": f"Bearer {admin_access_token}"},
        json={"name": "Old Cat"},
    )
    assert resp.status_code == 409
    assert resp.json() == {
        "error": "Duplicate slug",
        "message": 'Category slug "old-cat" already exists.',
    }


@pytest.mark.asyncio
async def test_update_job_category_not_found(async_client, admin_access_token):
    resp = await async_client.put(
        "/api/v2/job-categories/does-not-exist",
        headers={"Authorization": f"Bearer {admin_access_token}"},
        json={"name": "New"},
    )
    assert resp.status_code == 404
    assert resp.json()["error"] == "Not found"


@pytest.mark.asyncio
async def test_update_job_category_rejects_slug_key(async_client, admin_access_token, seed_categories_and_jobs):
    resp = await async_client.put(
        f"/api/v2/job-categories/{seed_categories_and_jobs['old_cat_id']}",
        headers={"Authorization": f"Bearer {admin_access_token}"},
        json={"slug": "nope"},
    )
    assert resp.status_code == 400
    assert resp.json() == {
        "error": "Invalid payload",
        "message": "Slug cannot be edited directly; it is derived from name.",
    }


@pytest.mark.asyncio
async def test_update_general_category_cannot_be_renamed(async_client, admin_access_token, seed_categories_and_jobs):
    resp = await async_client.put(
        f"/api/v2/job-categories/{seed_categories_and_jobs['general_id']}",
        headers={"Authorization": f"Bearer {admin_access_token}"},
        json={"name": "Not General"},
    )
    assert resp.status_code == 400
    assert resp.json() == {"error": "Invalid category", "message": 'The "General" category cannot be renamed.'}


@pytest.mark.asyncio
async def test_update_job_category_renames_slug_and_updates_jobs(async_client, admin_access_token, seed_categories_and_jobs, app):
    resp = await async_client.put(
        f"/api/v2/job-categories/{seed_categories_and_jobs['old_cat_id']}",
        headers={"Authorization": f"Bearer {admin_access_token}"},
        json={"name": "New Name"},
    )
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["message"] == "Category updated"
    assert payload["category"]["slug"] == "new-name"
    assert payload["jobs_updated"] == 2

    with app.app_context():
        from src.models.job import Job

        job1 = Job.query.get(seed_categories_and_jobs["job1_id"])
        job2 = Job.query.get(seed_categories_and_jobs["job2_id"])
        job3 = Job.query.get(seed_categories_and_jobs["job3_id"])
        assert job1.category == "new-name"
        assert job2.category == "new-name"
        assert job3.category == "general"


@pytest.mark.asyncio
async def test_delete_job_category_disables(async_client, admin_access_token, seed_categories_and_jobs, app):
    resp = await async_client.delete(
        f"/api/v2/job-categories/{seed_categories_and_jobs['old_cat_id']}",
        headers={"Authorization": f"Bearer {admin_access_token}"},
    )
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["message"] == "Category disabled"
    assert payload["category"]["is_active"] is False

    with app.app_context():
        from src.models.job_category import JobCategory

        cat = JobCategory.query.get(seed_categories_and_jobs["old_cat_id"])
        assert cat.is_active is False

