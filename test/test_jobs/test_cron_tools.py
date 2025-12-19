"""
Tests for cron validation/preview and test-run helpers.
"""

from types import SimpleNamespace


class TestCronTools:
    def test_validate_cron_returns_explanatory_message(self, client, admin_token):
        resp = client.post(
            '/api/jobs/validate-cron',
            headers={'Authorization': f'Bearer {admin_token}'},
            json={'expression': '*/5 * *'},
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['valid'] is False
        assert '5 fields' in (data.get('message') or '').lower()

    def test_cron_preview_returns_next_runs(self, client, admin_token):
        resp = client.post(
            '/api/jobs/cron-preview',
            headers={'Authorization': f'Bearer {admin_token}'},
            json={'expression': '*/5 * * * *', 'count': 5},
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['timezone']
        assert len(data['next_runs']) == 5

    def test_test_run_webhook_is_quiet_and_returns_status(self, client, admin_token, monkeypatch):
        from src.routes import jobs as jobs_routes

        def fake_post(url, json=None, timeout=None, headers=None):
            return SimpleNamespace(status_code=200)

        monkeypatch.setattr(jobs_routes.requests, 'post', fake_post)

        resp = client.post(
            '/api/jobs/test-run',
            headers={'Authorization': f'Bearer {admin_token}'},
            json={'target_url': 'https://example.com', 'metadata': {'hello': 'world'}},
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['type'] == 'webhook'
        assert data['status_code'] == 200
        assert data['ok'] is True

