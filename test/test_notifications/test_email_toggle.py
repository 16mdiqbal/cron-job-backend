"""
Tests for email notification toggle functionality.
"""
import pytest


class TestEmailNotificationToggle:
    """Test email notification toggle feature."""
    
    def test_email_notifications_disabled_by_default(self, client, admin_token):
        """Test that email notifications are disabled by default."""
        response = client.post('/api/jobs',
            headers={'Authorization': f'Bearer {admin_token}'},
            json={
                'name': 'Default Notify Job',
                'cron_expression': '0 * * * *',
                'target_url': 'https://httpbin.org/status/200'
            }
        )
        
        assert response.status_code == 201
        job = response.get_json()['job']
        assert job['enable_email_notifications'] == False
        assert job['notification_emails'] == []
    
    def test_enable_notifications_on_create(self, client, admin_token):
        """Test enabling notifications when creating job."""
        response = client.post('/api/jobs',
            headers={'Authorization': f'Bearer {admin_token}'},
            json={
                'name': 'Enabled Notify Job',
                'cron_expression': '0 * * * *',
                'target_url': 'https://httpbin.org/status/200',
                'enable_email_notifications': True,
                'notification_emails': ['admin@example.com']
            }
        )
        
        assert response.status_code == 201
        job = response.get_json()['job']
        assert job['enable_email_notifications'] == True
        assert 'admin@example.com' in job['notification_emails']
    
    def test_emails_ignored_when_toggle_false(self, client, admin_token):
        """Test that emails are ignored when toggle is false."""
        response = client.post('/api/jobs',
            headers={'Authorization': f'Bearer {admin_token}'},
            json={
                'name': 'Ignored Emails Job',
                'cron_expression': '0 * * * *',
                'target_url': 'https://httpbin.org/status/200',
                'enable_email_notifications': False,
                'notification_emails': ['should@be.ignored.com']
            }
        )
        
        assert response.status_code == 201
        job = response.get_json()['job']
        assert job['enable_email_notifications'] == False
        assert job['notification_emails'] == []
    
    def test_multiple_notification_emails(self, client, admin_token):
        """Test that multiple emails can be set."""
        emails = ['admin@example.com', 'team@example.com', 'ops@example.com']
        response = client.post('/api/jobs',
            headers={'Authorization': f'Bearer {admin_token}'},
            json={
                'name': 'Multiple Emails Job',
                'cron_expression': '0 * * * *',
                'target_url': 'https://httpbin.org/status/200',
                'enable_email_notifications': True,
                'notification_emails': emails
            }
        )
        
        assert response.status_code == 201
        job = response.get_json()['job']
        assert len(job['notification_emails']) == 3
        for email in emails:
            assert email in job['notification_emails']
    
    def test_notify_on_success_disabled_when_notifications_off(self, client, admin_token):
        """Test that success notifications are disabled when main toggle is off."""
        response = client.post('/api/jobs',
            headers={'Authorization': f'Bearer {admin_token}'},
            json={
                'name': 'Success Notify Disabled Job',
                'cron_expression': '0 * * * *',
                'target_url': 'https://httpbin.org/status/200',
                'enable_email_notifications': False,
                'notify_on_success': True
            }
        )
        
        assert response.status_code == 201
        job = response.get_json()['job']
        assert job['enable_email_notifications'] == False
        assert job['notify_on_success'] == False
    
    def test_notify_on_success_enabled_when_notifications_on(self, client, admin_token):
        """Test that success notifications work when main toggle is on."""
        response = client.post('/api/jobs',
            headers={'Authorization': f'Bearer {admin_token}'},
            json={
                'name': 'Success Notify Enabled Job',
                'cron_expression': '0 * * * *',
                'target_url': 'https://httpbin.org/status/200',
                'enable_email_notifications': True,
                'notify_on_success': True,
                'notification_emails': ['admin@example.com']
            }
        )
        
        assert response.status_code == 201
        job = response.get_json()['job']
        assert job['enable_email_notifications'] == True
        assert job['notify_on_success'] == True
    
    def test_toggle_notifications_on_via_update(self, client, admin_token, sample_job_data):
        """Test toggling notifications on via update."""
        # Create job with notifications off
        create_response = client.post('/api/jobs',
            headers={'Authorization': f'Bearer {admin_token}'},
            json=sample_job_data
        )
        job_id = create_response.get_json()['job']['id']
        
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
    
    def test_toggle_notifications_off_via_update(self, client, admin_token, 
                                                 sample_job_with_notifications):
        """Test toggling notifications off via update clears emails."""
        # Create job with notifications on
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
    
    def test_toggle_persists_in_list(self, client, admin_token):
        """Test that toggle setting persists when listing jobs."""
        # Create enabled job
        create_response = client.post('/api/jobs',
            headers={'Authorization': f'Bearer {admin_token}'},
            json={
                'name': 'List Toggle Job',
                'cron_expression': '0 * * * *',
                'target_url': 'https://httpbin.org/status/200',
                'enable_email_notifications': True,
                'notification_emails': ['admin@example.com']
            }
        )
        job_id = create_response.get_json()['job']['id']
        
        # List jobs
        list_response = client.get('/api/jobs',
            headers={'Authorization': f'Bearer {admin_token}'}
        )
        
        assert list_response.status_code == 200
        jobs = list_response.get_json()['jobs']
        job = next((j for j in jobs if j['id'] == job_id), None)
        assert job is not None
        assert job['enable_email_notifications'] == True
    
    def test_toggle_persists_in_get(self, client, admin_token):
        """Test that toggle setting persists when getting single job."""
        # Create enabled job
        create_response = client.post('/api/jobs',
            headers={'Authorization': f'Bearer {admin_token}'},
            json={
                'name': 'Get Toggle Job',
                'cron_expression': '0 * * * *',
                'target_url': 'https://httpbin.org/status/200',
                'enable_email_notifications': True,
                'notification_emails': ['admin@example.com']
            }
        )
        job_id = create_response.get_json()['job']['id']
        
        # Get job
        get_response = client.get(f'/api/jobs/{job_id}',
            headers={'Authorization': f'Bearer {admin_token}'}
        )
        
        assert get_response.status_code == 200
        job = get_response.get_json()['job']
        assert job['enable_email_notifications'] == True
    
    def test_success_notifications_independent_of_emails(self, client, admin_token):
        """Test that success notifications flag works without emails."""
        response = client.post('/api/jobs',
            headers={'Authorization': f'Bearer {admin_token}'},
            json={
                'name': 'Success No Emails Job',
                'cron_expression': '0 * * * *',
                'target_url': 'https://httpbin.org/status/200',
                'enable_email_notifications': True,
                'notify_on_success': True,
                'notification_emails': []
            }
        )
        
        assert response.status_code == 201
        job = response.get_json()['job']
        assert job['notify_on_success'] == True
    
    def test_email_list_format_in_response(self, client, admin_token):
        """Test that email list is returned as array."""
        response = client.post('/api/jobs',
            headers={'Authorization': f'Bearer {admin_token}'},
            json={
                'name': 'Email Format Job',
                'cron_expression': '0 * * * *',
                'target_url': 'https://httpbin.org/status/200',
                'enable_email_notifications': True,
                'notification_emails': ['admin@example.com', 'team@example.com']
            }
        )
        
        assert response.status_code == 201
        job = response.get_json()['job']
        assert isinstance(job['notification_emails'], list)
        assert all(isinstance(email, str) for email in job['notification_emails'])
    
    def test_update_emails_maintains_toggle_state(self, client, admin_token, 
                                                  sample_job_with_notifications):
        """Test that updating emails doesn't change toggle state."""
        # Create job
        create_response = client.post('/api/jobs',
            headers={'Authorization': f'Bearer {admin_token}'},
            json=sample_job_with_notifications
        )
        job_id = create_response.get_json()['job']['id']
        original_toggle = create_response.get_json()['job']['enable_email_notifications']
        
        # Update emails
        response = client.put(f'/api/jobs/{job_id}',
            headers={'Authorization': f'Bearer {admin_token}'},
            json={'notification_emails': ['newemail@example.com']}
        )
        
        assert response.status_code == 200
        assert response.get_json()['job']['enable_email_notifications'] == original_toggle
