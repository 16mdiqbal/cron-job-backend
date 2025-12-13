"""
Tests for job update functionality.
"""
import pytest


class TestJobUpdate:
    """Test job update endpoint."""
    
    def test_update_job_name(self, client, admin_token, sample_job_data):
        """Test updating job name."""
        # Create job
        create_response = client.post('/api/jobs',
            headers={'Authorization': f'Bearer {admin_token}'},
            json=sample_job_data
        )
        job_id = create_response.get_json()['job']['id']
        
        # Update name
        response = client.put(f'/api/jobs/{job_id}',
            headers={'Authorization': f'Bearer {admin_token}'},
            json={'name': 'Updated Job Name'}
        )
        
        assert response.status_code == 200
        assert response.get_json()['job']['name'] == 'Updated Job Name'
    
    def test_update_job_cron_expression(self, client, admin_token, sample_job_data):
        """Test updating cron expression."""
        # Create job
        create_response = client.post('/api/jobs',
            headers={'Authorization': f'Bearer {admin_token}'},
            json=sample_job_data
        )
        job_id = create_response.get_json()['job']['id']
        
        # Update cron
        response = client.put(f'/api/jobs/{job_id}',
            headers={'Authorization': f'Bearer {admin_token}'},
            json={'cron_expression': '*/30 * * * *'}
        )
        
        assert response.status_code == 200
        assert response.get_json()['job']['cron_expression'] == '*/30 * * * *'
    
    def test_update_job_target_url(self, client, admin_token, sample_job_data):
        """Test updating target URL."""
        # Create job
        create_response = client.post('/api/jobs',
            headers={'Authorization': f'Bearer {admin_token}'},
            json=sample_job_data
        )
        job_id = create_response.get_json()['job']['id']
        
        # Update URL
        new_url = 'https://httpbin.org/status/201'
        response = client.put(f'/api/jobs/{job_id}',
            headers={'Authorization': f'Bearer {admin_token}'},
            json={'target_url': new_url}
        )
        
        assert response.status_code == 200
        assert response.get_json()['job']['target_url'] == new_url
    
    def test_update_job_enable_notifications(self, client, admin_token, sample_job_data):
        """Test enabling notifications on a job."""
        # Create job (notifications disabled)
        create_response = client.post('/api/jobs',
            headers={'Authorization': f'Bearer {admin_token}'},
            json=sample_job_data
        )
        job_id = create_response.get_json()['job']['id']
        assert create_response.get_json()['job']['enable_email_notifications'] == False
        
        # Enable notifications
        response = client.put(f'/api/jobs/{job_id}',
            headers={'Authorization': f'Bearer {admin_token}'},
            json={
                'enable_email_notifications': True,
                'notification_emails': ['admin@example.com']
            }
        )
        
        assert response.status_code == 200
        job = response.get_json()['job']
        assert job['enable_email_notifications'] == True
        assert 'admin@example.com' in job['notification_emails']
    
    def test_update_job_disable_notifications(self, client, admin_token, 
                                              sample_job_with_notifications):
        """Test disabling notifications clears emails."""
        # Create job with notifications
        create_response = client.post('/api/jobs',
            headers={'Authorization': f'Bearer {admin_token}'},
            json=sample_job_with_notifications
        )
        job_id = create_response.get_json()['job']['id']
        assert create_response.get_json()['job']['enable_email_notifications'] == True
        
        # Disable notifications
        response = client.put(f'/api/jobs/{job_id}',
            headers={'Authorization': f'Bearer {admin_token}'},
            json={'enable_email_notifications': False}
        )
        
        assert response.status_code == 200
        job = response.get_json()['job']
        assert job['enable_email_notifications'] == False
        assert job['notification_emails'] == []
    
    def test_update_job_notification_emails(self, client, admin_token, 
                                            sample_job_with_notifications):
        """Test updating notification emails."""
        # Create job
        create_response = client.post('/api/jobs',
            headers={'Authorization': f'Bearer {admin_token}'},
            json=sample_job_with_notifications
        )
        job_id = create_response.get_json()['job']['id']
        
        # Update emails
        new_emails = ['newemail@example.com', 'another@example.com']
        response = client.put(f'/api/jobs/{job_id}',
            headers={'Authorization': f'Bearer {admin_token}'},
            json={'notification_emails': new_emails}
        )
        
        assert response.status_code == 200
        assert response.get_json()['job']['notification_emails'] == new_emails
    
    def test_update_job_enable_success_notifications(self, client, admin_token, 
                                                      sample_job_with_notifications):
        """Test enabling success notifications."""
        # Create job
        create_response = client.post('/api/jobs',
            headers={'Authorization': f'Bearer {admin_token}'},
            json=sample_job_with_notifications
        )
        job_id = create_response.get_json()['job']['id']
        
        # Verify initial state
        job = create_response.get_json()['job']
        original_notify_on_success = job['notify_on_success']
        
        # Update success notification
        response = client.put(f'/api/jobs/{job_id}',
            headers={'Authorization': f'Bearer {admin_token}'},
            json={'notify_on_success': not original_notify_on_success}
        )
        
        assert response.status_code == 200
        assert response.get_json()['job']['notify_on_success'] == (not original_notify_on_success)
    
    def test_update_job_is_active(self, client, admin_token, sample_job_data):
        """Test disabling and re-enabling a job."""
        # Create job
        create_response = client.post('/api/jobs',
            headers={'Authorization': f'Bearer {admin_token}'},
            json=sample_job_data
        )
        job_id = create_response.get_json()['job']['id']
        
        # Disable job
        response = client.put(f'/api/jobs/{job_id}',
            headers={'Authorization': f'Bearer {admin_token}'},
            json={'is_active': False}
        )
        assert response.status_code == 200
        assert response.get_json()['job']['is_active'] == False
        
        # Re-enable job
        response = client.put(f'/api/jobs/{job_id}',
            headers={'Authorization': f'Bearer {admin_token}'},
            json={'is_active': True}
        )
        assert response.status_code == 200
        assert response.get_json()['job']['is_active'] == True
    
    def test_update_job_metadata(self, client, admin_token, sample_job_data):
        """Test updating job metadata."""
        # Create job
        create_response = client.post('/api/jobs',
            headers={'Authorization': f'Bearer {admin_token}'},
            json=sample_job_data
        )
        job_id = create_response.get_json()['job']['id']
        
        # Update metadata
        new_metadata = {'environment': 'staging', 'retry_count': 5}
        response = client.put(f'/api/jobs/{job_id}',
            headers={'Authorization': f'Bearer {admin_token}'},
            json={'metadata': new_metadata}
        )
        
        assert response.status_code == 200
        assert response.get_json()['job']['metadata']['environment'] == 'staging'
    
    def test_update_job_invalid_cron_fails(self, client, admin_token, sample_job_data):
        """Test that invalid cron fails update."""
        # Create job
        create_response = client.post('/api/jobs',
            headers={'Authorization': f'Bearer {admin_token}'},
            json=sample_job_data
        )
        job_id = create_response.get_json()['job']['id']
        
        # Try invalid cron
        response = client.put(f'/api/jobs/{job_id}',
            headers={'Authorization': f'Bearer {admin_token}'},
            json={'cron_expression': 'invalid'}
        )
        
        assert response.status_code == 400
    
    def test_update_nonexistent_job_returns_404(self, client, admin_token):
        """Test that updating nonexistent job returns 404."""
        response = client.put('/api/jobs/nonexistent',
            headers={'Authorization': f'Bearer {admin_token}'},
            json={'name': 'New Name'}
        )
        
        assert response.status_code == 404
    
    def test_update_job_without_authentication_fails(self, client):
        """Test that updating job without auth fails."""
        response = client.put('/api/jobs/someid',
            json={'name': 'New Name'}
        )
        
        assert response.status_code == 401
    
    def test_update_job_viewer_role_fails(self, client, viewer_token, 
                                          admin_token, sample_job_data):
        """Test that viewer cannot update jobs."""
        # Create job as admin
        create_response = client.post('/api/jobs',
            headers={'Authorization': f'Bearer {admin_token}'},
            json=sample_job_data
        )
        job_id = create_response.get_json()['job']['id']
        
        # Try to update as viewer
        response = client.put(f'/api/jobs/{job_id}',
            headers={'Authorization': f'Bearer {viewer_token}'},
            json={'name': 'Updated Name'}
        )
        
        assert response.status_code == 403
    
    def test_update_own_job_as_user_succeeds(self, client, admin_token, 
                                             user_token, regular_user):
        """Test that user can update their own jobs."""
        # Create job as user
        job_data = {
            'name': 'User Job',
            'cron_expression': '0 * * * *',
            'target_url': 'https://httpbin.org/status/200'
        }
        create_response = client.post('/api/jobs',
            headers={'Authorization': f'Bearer {user_token}'},
            json=job_data
        )
        assert create_response.status_code == 201
        job_id = create_response.get_json()['job']['id']
        
        # Update own job
        response = client.put(f'/api/jobs/{job_id}',
            headers={'Authorization': f'Bearer {user_token}'},
            json={'name': 'Updated User Job'}
        )
        
        assert response.status_code == 200
    
    def test_update_job_response_includes_message(self, client, admin_token, sample_job_data):
        """Test that update response includes message."""
        # Create job
        create_response = client.post('/api/jobs',
            headers={'Authorization': f'Bearer {admin_token}'},
            json=sample_job_data
        )
        job_id = create_response.get_json()['job']['id']
        
        # Update
        response = client.put(f'/api/jobs/{job_id}',
            headers={'Authorization': f'Bearer {admin_token}'},
            json={'name': 'Updated'}
        )
        
        assert response.status_code == 200
        assert 'message' in response.get_json()
        assert 'Job updated successfully' in response.get_json()['message']
