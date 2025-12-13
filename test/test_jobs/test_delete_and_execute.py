"""
Tests for job deletion and execution retrieval functionality.
"""
import pytest


class TestJobDeletion:
    """Test job deletion endpoint."""
    
    def test_delete_job_succeeds(self, client, admin_token, sample_job_data):
        """Test successful job deletion."""
        # Create job
        create_response = client.post('/api/jobs',
            headers={'Authorization': f'Bearer {admin_token}'},
            json=sample_job_data
        )
        job_id = create_response.get_json()['job']['id']
        
        # Delete job
        response = client.delete(f'/api/jobs/{job_id}',
            headers={'Authorization': f'Bearer {admin_token}'}
        )
        
        assert response.status_code == 200
        data = response.get_json()
        assert 'deleted_job' in data
        assert data['deleted_job']['id'] == job_id
    
    def test_delete_nonexistent_job_returns_404(self, client, admin_token):
        """Test that deleting nonexistent job returns 404."""
        response = client.delete('/api/jobs/nonexistent',
            headers={'Authorization': f'Bearer {admin_token}'}
        )
        
        assert response.status_code == 404
    
    def test_deleted_job_no_longer_accessible(self, client, admin_token, sample_job_data):
        """Test that deleted job cannot be retrieved."""
        # Create job
        create_response = client.post('/api/jobs',
            headers={'Authorization': f'Bearer {admin_token}'},
            json=sample_job_data
        )
        job_id = create_response.get_json()['job']['id']
        
        # Delete job
        client.delete(f'/api/jobs/{job_id}',
            headers={'Authorization': f'Bearer {admin_token}'}
        )
        
        # Try to get deleted job
        response = client.get(f'/api/jobs/{job_id}',
            headers={'Authorization': f'Bearer {admin_token}'}
        )
        
        assert response.status_code == 404
    
    def test_delete_job_without_authentication_fails(self, client):
        """Test that deleting without auth fails."""
        response = client.delete('/api/jobs/someid')
        
        assert response.status_code == 401
    
    def test_delete_job_viewer_role_fails(self, client, viewer_token, 
                                          admin_token, sample_job_data):
        """Test that viewer cannot delete jobs."""
        # Create job as admin
        create_response = client.post('/api/jobs',
            headers={'Authorization': f'Bearer {admin_token}'},
            json=sample_job_data
        )
        job_id = create_response.get_json()['job']['id']
        
        # Try to delete as viewer
        response = client.delete(f'/api/jobs/{job_id}',
            headers={'Authorization': f'Bearer {viewer_token}'}
        )
        
        assert response.status_code == 403
    
    def test_delete_own_job_as_user_succeeds(self, client, user_token):
        """Test that user can delete their own jobs."""
        # Create job as user
        job_data = {
            'name': 'User Job To Delete',
            'cron_expression': '0 * * * *',
            'target_url': 'https://httpbin.org/status/200'
        }
        create_response = client.post('/api/jobs',
            headers={'Authorization': f'Bearer {user_token}'},
            json=job_data
        )
        assert create_response.status_code == 201
        job_id = create_response.get_json()['job']['id']
        
        # Delete own job
        response = client.delete(f'/api/jobs/{job_id}',
            headers={'Authorization': f'Bearer {user_token}'}
        )
        
        assert response.status_code == 200
    
    def test_delete_job_response_includes_message(self, client, admin_token, sample_job_data):
        """Test that delete response includes success message."""
        # Create job
        create_response = client.post('/api/jobs',
            headers={'Authorization': f'Bearer {admin_token}'},
            json=sample_job_data
        )
        job_id = create_response.get_json()['job']['id']
        
        # Delete
        response = client.delete(f'/api/jobs/{job_id}',
            headers={'Authorization': f'Bearer {admin_token}'}
        )
        
        assert response.status_code == 200
        data = response.get_json()
        assert 'message' in data
        assert 'Job deleted successfully' in data['message']


class TestJobExecutions:
    """Test job execution retrieval endpoints."""
    
    def test_get_job_executions(self, client, admin_token, sample_github_job):
        """Test retrieving executions for a job."""
        # Create job
        create_response = client.post('/api/jobs',
            headers={'Authorization': f'Bearer {admin_token}'},
            json=sample_github_job
        )
        job_id = create_response.get_json()['job']['id']
        
        # Get executions
        response = client.get(f'/api/jobs/{job_id}/executions',
            headers={'Authorization': f'Bearer {admin_token}'}
        )
        
        assert response.status_code == 200
        data = response.get_json()
        assert 'job_id' in data
        assert 'job_name' in data
        assert 'total_executions' in data
        assert 'executions' in data
    
    def test_get_executions_nonexistent_job_returns_404(self, client, admin_token):
        """Test that getting executions for nonexistent job returns 404."""
        response = client.get('/api/jobs/nonexistent/executions',
            headers={'Authorization': f'Bearer {admin_token}'}
        )
        
        assert response.status_code == 404
    
    def test_get_execution_stats(self, client, admin_token, sample_github_job):
        """Test retrieving execution statistics."""
        # Create job
        create_response = client.post('/api/jobs',
            headers={'Authorization': f'Bearer {admin_token}'},
            json=sample_github_job
        )
        job_id = create_response.get_json()['job']['id']
        
        # Get stats
        response = client.get(f'/api/jobs/{job_id}/executions/stats',
            headers={'Authorization': f'Bearer {admin_token}'}
        )
        
        assert response.status_code == 200
        data = response.get_json()
        assert 'job_id' in data
        assert 'job_name' in data
        assert 'statistics' in data
        
        stats = data['statistics']
        assert 'total_executions' in stats
        assert 'success_count' in stats
        assert 'failed_count' in stats
        assert 'success_rate' in stats
    
    def test_get_execution_stats_nonexistent_job_returns_404(self, client, admin_token):
        """Test that getting stats for nonexistent job returns 404."""
        response = client.get('/api/jobs/nonexistent/executions/stats',
            headers={'Authorization': f'Bearer {admin_token}'}
        )
        
        assert response.status_code == 404
    
    def test_get_executions_without_authentication_fails(self, client):
        """Test that getting executions without auth fails."""
        response = client.get('/api/jobs/someid/executions')
        
        assert response.status_code == 401
    
    def test_get_execution_stats_without_authentication_fails(self, client):
        """Test that getting stats without auth fails."""
        response = client.get('/api/jobs/someid/executions/stats')
        
        assert response.status_code == 401
    
    def test_viewer_can_get_executions(self, client, viewer_token, 
                                       admin_token, sample_github_job):
        """Test that viewer can get job executions."""
        # Create job as admin
        create_response = client.post('/api/jobs',
            headers={'Authorization': f'Bearer {admin_token}'},
            json=sample_github_job
        )
        job_id = create_response.get_json()['job']['id']
        
        # Get executions as viewer
        response = client.get(f'/api/jobs/{job_id}/executions',
            headers={'Authorization': f'Bearer {viewer_token}'}
        )
        
        assert response.status_code == 200
    
    def test_viewer_can_get_execution_stats(self, client, viewer_token, 
                                            admin_token, sample_github_job):
        """Test that viewer can get execution stats."""
        # Create job as admin
        create_response = client.post('/api/jobs',
            headers={'Authorization': f'Bearer {admin_token}'},
            json=sample_github_job
        )
        job_id = create_response.get_json()['job']['id']
        
        # Get stats as viewer
        response = client.get(f'/api/jobs/{job_id}/executions/stats',
            headers={'Authorization': f'Bearer {viewer_token}'}
        )
        
        assert response.status_code == 200
