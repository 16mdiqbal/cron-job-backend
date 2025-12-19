"""
Regression tests: job updates should create in-app notifications.
"""


class TestJobUpdateNotification:
    def test_updating_cron_creates_job_updated_notification(self, client, admin_token):
        create_response = client.post(
            '/api/jobs',
            headers={'Authorization': f'Bearer {admin_token}'},
            json={
                'name': 'Cron Update Notif Job',
                'cron_expression': '0 * * * *',
                'target_url': 'https://httpbin.org/status/200',
            },
        )
        assert create_response.status_code == 201
        job_id = create_response.get_json()['job']['id']

        update_response = client.put(
            f'/api/jobs/{job_id}',
            headers={'Authorization': f'Bearer {admin_token}'},
            json={'cron_expression': '5 * * * *'},
        )
        assert update_response.status_code == 200

        notifications_response = client.get(
            '/api/notifications?page=1&per_page=20',
            headers={'Authorization': f'Bearer {admin_token}'},
        )
        assert notifications_response.status_code == 200
        titles = [n['title'] for n in notifications_response.get_json()['notifications']]
        assert 'Job Updated' in titles

