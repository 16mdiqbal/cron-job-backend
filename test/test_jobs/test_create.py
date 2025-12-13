"""
Tests for job creation functionality.
"""
import pytest


class TestJobCreation:
    """Test job creation endpoint."""
    
    def test_create_basic_webhook_job(self, client, admin_token, sample_job_data):
        """Test creating a basic webhook job."""
        response = client.post('/api/jobs', 
            headers={'Authorization': f'Bearer {admin_token}'},
            json=sample_job_data
        )
        
        assert response.status_code == 201
        data = response.get_json()
        assert data['job']['name'] == 'Test Job'
        assert data['job']['cron_expression'] == '0 * * * *'
        assert data['job']['target_url'] == 'https://httpbin.org/status/200'
        assert data['job']['enable_email_notifications'] == False
    
    def test_create_github_actions_job(self, client, admin_token, sample_github_job):
        """Test creating a GitHub Actions job."""
        response = client.post('/api/jobs',
            headers={'Authorization': f'Bearer {admin_token}'},
            json=sample_github_job
        )
        
        assert response.status_code == 201
        data = response.get_json()
        assert data['job']['name'] == 'GitHub Job'
        assert data['job']['github_owner'] == 'myorg'
        assert data['job']['github_repo'] == 'myrepo'
        assert data['job']['github_workflow_name'] == 'deploy.yml'
    
    def test_create_job_with_notifications_enabled(self, client, admin_token, 
                                                   sample_job_with_notifications):
        """Test creating a job with email notifications enabled."""
        response = client.post('/api/jobs',
            headers={'Authorization': f'Bearer {admin_token}'},
            json=sample_job_with_notifications
        )
        
        assert response.status_code == 201
        data = response.get_json()
        assert data['job']['enable_email_notifications'] == True
        assert len(data['job']['notification_emails']) == 2
        assert 'admin@example.com' in data['job']['notification_emails']
        assert data['job']['notify_on_success'] == True
    
    def test_create_job_with_notifications_disabled_default(self, client, admin_token):
        """Test that notifications are disabled by default."""
        response = client.post('/api/jobs',
            headers={'Authorization': f'Bearer {admin_token}'},
            json={
                'name': 'No Notify Job',
                'cron_expression': '0 * * * *',
                'target_url': 'https://httpbin.org/status/200'
            }
        )
        
        assert response.status_code == 201
        data = response.get_json()
        assert data['job']['enable_email_notifications'] == False
        assert data['job']['notification_emails'] == []
    
    def test_create_job_with_metadata(self, client, admin_token):
        """Test creating a job with metadata."""
        response = client.post('/api/jobs',
            headers={'Authorization': f'Bearer {admin_token}'},
            json={
                'name': 'Job With Metadata',
                'cron_expression': '0 * * * *',
                'target_url': 'https://httpbin.org/status/200',
                'metadata': {
                    'environment': 'production',
                    'retry_count': 3,
                    'timeout': 30
                }
            }
        )
        
        assert response.status_code == 201
        data = response.get_json()
        assert data['job']['metadata']['environment'] == 'production'
        assert data['job']['metadata']['retry_count'] == 3
    
    def test_create_job_with_emails_but_notifications_disabled(self, client, admin_token):
        """Test that emails are ignored when notifications are disabled."""
        response = client.post('/api/jobs',
            headers={'Authorization': f'Bearer {admin_token}'},
            json={
                'name': 'Ignored Emails Job',
                'cron_expression': '0 * * * *',
                'target_url': 'https://httpbin.org/status/200',
                'enable_email_notifications': False,
                'notification_emails': ['should@be.ignored']
            }
        )
        
        assert response.status_code == 201
        data = response.get_json()
        assert data['job']['notification_emails'] == []
    
    def test_create_duplicate_job_name_fails(self, client, admin_token, sample_job_data):
        """Test that duplicate job names are rejected."""
        # Create first job
        response1 = client.post('/api/jobs',
            headers={'Authorization': f'Bearer {admin_token}'},
            json=sample_job_data
        )
        assert response1.status_code == 201
        
        # Try to create duplicate
        response2 = client.post('/api/jobs',
            headers={'Authorization': f'Bearer {admin_token}'},
            json=sample_job_data
        )
        
        assert response2.status_code == 400
        assert 'Duplicate job name' in response2.get_json()['error']
    
    def test_create_job_invalid_cron_fails(self, client, admin_token):
        """Test that invalid cron expression fails."""
        response = client.post('/api/jobs',
            headers={'Authorization': f'Bearer {admin_token}'},
            json={
                'name': 'Invalid Cron Job',
                'cron_expression': 'invalid cron expression',
                'target_url': 'https://httpbin.org/status/200'
            }
        )
        
        assert response.status_code == 400
        assert 'Invalid cron expression' in response.get_json()['error']
    
    def test_create_job_missing_name_fails(self, client, admin_token):
        """Test that missing job name fails."""
        response = client.post('/api/jobs',
            headers={'Authorization': f'Bearer {admin_token}'},
            json={
                'cron_expression': '0 * * * *',
                'target_url': 'https://httpbin.org/status/200'
            }
        )
        
        assert response.status_code == 400
    
    def test_create_job_missing_cron_fails(self, client, admin_token):
        """Test that missing cron expression fails."""
        response = client.post('/api/jobs',
            headers={'Authorization': f'Bearer {admin_token}'},
            json={
                'name': 'No Cron Job',
                'target_url': 'https://httpbin.org/status/200'
            }
        )
        
        assert response.status_code == 400
    
    def test_create_job_no_target_fails(self, client, admin_token):
        """Test that job without target fails."""
        response = client.post('/api/jobs',
            headers={'Authorization': f'Bearer {admin_token}'},
            json={
                'name': 'No Target Job',
                'cron_expression': '0 * * * *'
            }
        )
        
        assert response.status_code == 400
        assert 'Missing target configuration' in response.get_json()['error']
    
    def test_create_job_empty_name_fails(self, client, admin_token):
        """Test that empty job name fails."""
        response = client.post('/api/jobs',
            headers={'Authorization': f'Bearer {admin_token}'},
            json={
                'name': '',
                'cron_expression': '0 * * * *',
                'target_url': 'https://httpbin.org/status/200'
            }
        )
        
        assert response.status_code == 400
    
    def test_create_job_without_authentication(self, client, sample_job_data):
        """Test that creating job without auth token fails."""
        response = client.post('/api/jobs', json=sample_job_data)
        
        assert response.status_code == 401
    
    def test_create_job_viewer_role_fails(self, client, viewer_token, sample_job_data):
        """Test that viewer cannot create jobs."""
        response = client.post('/api/jobs',
            headers={'Authorization': f'Bearer {viewer_token}'},
            json=sample_job_data
        )
        
        assert response.status_code == 403
    
    def test_create_job_user_role_succeeds(self, client, user_token, sample_job_data):
        """Test that regular user can create jobs."""
        response = client.post('/api/jobs',
            headers={'Authorization': f'Bearer {user_token}'},
            json=sample_job_data
        )
        
        assert response.status_code == 201
    
    def test_create_job_invalid_content_type(self, client, admin_token):
        """Test that request with wrong content type fails."""
        response = client.post('/api/jobs',
            headers={'Authorization': f'Bearer {admin_token}'},
            data='invalid data',
            content_type='text/plain'
        )
        
        assert response.status_code == 400
    
    def test_create_job_response_has_message(self, client, admin_token, sample_job_data):
        """Test that response includes success message."""
        response = client.post('/api/jobs',
            headers={'Authorization': f'Bearer {admin_token}'},
            json=sample_job_data
        )
        
        assert response.status_code == 201
        data = response.get_json()
        assert 'message' in data
        assert 'Job created successfully' in data['message']
    
    def test_create_job_response_includes_id(self, client, admin_token, sample_job_data):
        """Test that response includes job ID."""
        response = client.post('/api/jobs',
            headers={'Authorization': f'Bearer {admin_token}'},
            json=sample_job_data
        )
        
        assert response.status_code == 201
        data = response.get_json()
        assert 'id' in data['job']
        assert data['job']['id'] is not None
    
    def test_create_multiple_jobs_all_active_by_default(self, client, admin_token):
        """Test that multiple jobs are created with is_active=True by default."""
        jobs_data = [
            {'name': f'Job {i}', 'cron_expression': '0 * * * *', 
             'target_url': 'https://httpbin.org/status/200'}
            for i in range(3)
        ]
        
        for job_data in jobs_data:
            response = client.post('/api/jobs',
                headers={'Authorization': f'Bearer {admin_token}'},
                json=job_data
            )
            assert response.status_code == 201
            assert response.get_json()['job']['is_active'] == True
