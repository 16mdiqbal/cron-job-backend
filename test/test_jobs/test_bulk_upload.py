"""
Tests for job bulk upload functionality.
"""
import io


class TestJobBulkUpload:
    def test_bulk_upload_creates_github_job_with_default_owner_and_metadata(self, client, admin_token):
        csv_text = (
            "Job Name,Repo,Workflow Name,Branch,Cron schedule (JST),Status,Request Body,,\n"
            "My Bulk Job,myrepo,deploy.yml,main,0 * * * *,Enable,"
            "\"{\"\"branchDetails\"\": \"\"main\"\", \"\"foo\"\": \"\"bar\"\"}\",,\n"
        )

        response = client.post(
            '/api/jobs/bulk-upload',
            headers={'Authorization': f'Bearer {admin_token}'},
            data={
                'default_github_owner': 'myorg',
                'file': (io.BytesIO(csv_text.encode('utf-8')), 'jobs.csv'),
            },
            content_type='multipart/form-data',
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data['created_count'] == 1
        assert data['error_count'] == 0

        list_response = client.get(
            '/api/jobs',
            headers={'Authorization': f'Bearer {admin_token}'},
        )
        assert list_response.status_code == 200
        jobs = list_response.get_json()['jobs']
        assert len(jobs) == 1
        job = jobs[0]
        assert job['name'] == 'My Bulk Job'
        assert job['github_owner'] == 'myorg'
        assert job['github_repo'] == 'myrepo'
        assert job['github_workflow_name'] == 'deploy.yml'
        assert job['metadata']['foo'] == 'bar'
        assert job['metadata']['branchDetails'] == 'main'

    def test_bulk_upload_drops_empty_rows_and_empty_header_columns(self, client, admin_token):
        csv_text = (
            "Job Name,Repo,Workflow Name,Cron schedule (JST),Status,,\n"
            "Row 1,myrepo,deploy.yml,0 * * * *,Enable,,\n"
            ",,,,,,\n"
        )

        response = client.post(
            '/api/jobs/bulk-upload',
            headers={'Authorization': f'Bearer {admin_token}'},
            data={
                'default_github_owner': 'myorg',
                'file': (io.BytesIO(csv_text.encode('utf-8')), 'jobs.csv'),
            },
            content_type='multipart/form-data',
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data['stats']['removed_column_count'] == 2
        assert data['stats']['removed_empty_row_count'] == 1
        assert data['created_count'] == 1

    def test_bulk_upload_invalid_json_in_request_body_reports_error(self, client, admin_token):
        csv_text = (
            "Job Name,Repo,Workflow Name,Cron schedule (JST),Status,Request Body\n"
            "Bad JSON Job,myrepo,deploy.yml,0 * * * *,Enable,{not-json}\n"
        )

        response = client.post(
            '/api/jobs/bulk-upload',
            headers={'Authorization': f'Bearer {admin_token}'},
            data={
                'default_github_owner': 'myorg',
                'file': (io.BytesIO(csv_text.encode('utf-8')), 'jobs.csv'),
            },
            content_type='multipart/form-data',
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data['created_count'] == 0
        assert data['error_count'] == 1
        assert data['errors'][0]['error'] == 'Invalid JSON in Request Body'

    def test_bulk_upload_dry_run_does_not_create_jobs(self, client, admin_token):
        csv_text = (
            "Job Name,Repo,Workflow Name,Cron schedule (JST),Status\n"
            "Dry Run Job,myrepo,deploy.yml,0 * * * *,Enable\n"
        )

        response = client.post(
            '/api/jobs/bulk-upload',
            headers={'Authorization': f'Bearer {admin_token}'},
            data={
                'default_github_owner': 'myorg',
                'dry_run': 'true',
                'file': (io.BytesIO(csv_text.encode('utf-8')), 'jobs.csv'),
            },
            content_type='multipart/form-data',
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data['dry_run'] is True
        assert data['created_count'] == 1

        list_response = client.get(
            '/api/jobs',
            headers={'Authorization': f'Bearer {admin_token}'},
        )
        assert list_response.status_code == 200
        assert list_response.get_json()['jobs'] == []
