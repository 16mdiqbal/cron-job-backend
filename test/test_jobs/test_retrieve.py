"""
Tests for job retrieval functionality.
"""
import pytest


class TestJobRetrieval:
    """Test job retrieval endpoints."""
    
    def test_list_all_jobs(self, client, admin_token, sample_job_data):
        """Test listing all jobs."""
        # Create a job first
        create_response = client.post('/api/jobs',
            headers={'Authorization': f'Bearer {admin_token}'},
            json=sample_job_data
        )
        assert create_response.status_code == 201
        
        # List jobs
        response = client.get('/api/jobs',
            headers={'Authorization': f'Bearer {admin_token}'}
        )
        
        assert response.status_code == 200
        data = response.get_json()
        assert 'jobs' in data
        assert 'count' in data
        assert data['count'] >= 1
    
    def test_list_empty_jobs(self, client, admin_token):
        """Test listing jobs when none exist."""
        response = client.get('/api/jobs',
            headers={'Authorization': f'Bearer {admin_token}'}
        )
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['count'] == 0
        assert data['jobs'] == []
    
    def test_get_specific_job_by_id(self, client, admin_token, sample_job_data):
        """Test retrieving a specific job by ID."""
        # Create a job
        create_response = client.post('/api/jobs',
            headers={'Authorization': f'Bearer {admin_token}'},
            json=sample_job_data
        )
        job_id = create_response.get_json()['job']['id']
        
        # Get the job
        response = client.get(f'/api/jobs/{job_id}',
            headers={'Authorization': f'Bearer {admin_token}'}
        )
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['job']['id'] == job_id
        assert data['job']['name'] == sample_job_data['name']
    
    def test_get_nonexistent_job_returns_404(self, client, admin_token):
        """Test that getting nonexistent job returns 404."""
        response = client.get('/api/jobs/nonexistent_id',
            headers={'Authorization': f'Bearer {admin_token}'}
        )
        
        assert response.status_code == 404
    
    def test_list_jobs_includes_all_fields(self, client, admin_token, 
                                          sample_job_with_notifications):
        """Test that list includes all job fields."""
        # Create job
        create_response = client.post('/api/jobs',
            headers={'Authorization': f'Bearer {admin_token}'},
            json=sample_job_with_notifications
        )
        assert create_response.status_code == 201
        
        # List jobs
        response = client.get('/api/jobs',
            headers={'Authorization': f'Bearer {admin_token}'}
        )
        
        assert response.status_code == 200
        jobs = response.get_json()['jobs']
        job = jobs[0]
        
        # Check all expected fields
        assert 'id' in job
        assert 'name' in job
        assert 'cron_expression' in job
        assert 'target_url' in job
        assert 'is_active' in job
        assert 'created_at' in job
        assert 'enable_email_notifications' in job
        assert 'notification_emails' in job
        assert 'notify_on_success' in job
    
    def test_get_job_includes_all_fields(self, client, admin_token, 
                                         sample_job_with_notifications):
        """Test that get job response includes all fields."""
        # Create job
        create_response = client.post('/api/jobs',
            headers={'Authorization': f'Bearer {admin_token}'},
            json=sample_job_with_notifications
        )
        job_id = create_response.get_json()['job']['id']
        
        # Get job
        response = client.get(f'/api/jobs/{job_id}',
            headers={'Authorization': f'Bearer {admin_token}'}
        )
        
        assert response.status_code == 200
        job = response.get_json()['job']
        
        # Check notification fields
        assert job['enable_email_notifications'] == True
        assert isinstance(job['notification_emails'], list)
        assert job['notify_on_success'] == True
    
    def test_list_jobs_without_authentication_fails(self, client):
        """Test that listing jobs without auth fails."""
        response = client.get('/api/jobs')
        
        assert response.status_code == 401
    
    def test_get_job_without_authentication_fails(self, client):
        """Test that getting job without auth fails."""
        response = client.get('/api/jobs/someid')
        
        assert response.status_code == 401
    
    def test_list_jobs_viewer_can_access(self, client, viewer_token, 
                                         admin_token, sample_job_data):
        """Test that viewer can list jobs."""
        # Create job as admin
        client.post('/api/jobs',
            headers={'Authorization': f'Bearer {admin_token}'},
            json=sample_job_data
        )
        
        # List as viewer
        response = client.get('/api/jobs',
            headers={'Authorization': f'Bearer {viewer_token}'}
        )
        
        assert response.status_code == 200
    
    def test_get_job_viewer_can_access(self, client, viewer_token, 
                                       admin_token, sample_job_data):
        """Test that viewer can get specific job."""
        # Create job as admin
        create_response = client.post('/api/jobs',
            headers={'Authorization': f'Bearer {admin_token}'},
            json=sample_job_data
        )
        job_id = create_response.get_json()['job']['id']
        
        # Get as viewer
        response = client.get(f'/api/jobs/{job_id}',
            headers={'Authorization': f'Bearer {viewer_token}'}
        )
        
        assert response.status_code == 200


class TestHealthCheck:
    """Test health check endpoint."""
    
    def test_health_check_no_auth_required(self, client):
        """Test that health check doesn't require authentication."""
        response = client.get('/api/health')
        
        assert response.status_code == 200
    
    def test_health_check_returns_status(self, client):
        """Test that health check returns status."""
        response = client.get('/api/health')
        
        data = response.get_json()
        assert 'status' in data
        assert data['status'] == 'healthy'
    
    def test_health_check_returns_scheduler_running(self, client):
        """Test that health check includes scheduler status."""
        response = client.get('/api/health')
        
        data = response.get_json()
        assert 'scheduler_running' in data
        assert isinstance(data['scheduler_running'], bool)
    
    def test_health_check_returns_job_count(self, client):
        """Test that health check includes scheduled jobs count."""
        response = client.get('/api/health')
        
        data = response.get_json()
        assert 'scheduled_jobs_count' in data
        assert isinstance(data['scheduled_jobs_count'], int)
