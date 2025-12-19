"""
Tests for deleting read notifications.
"""

from datetime import datetime, timedelta, time

import pytest

from src.models import db
from src.models.notification import Notification
from src.models.user import User
from src.utils.notifications import create_notification


class TestDeleteReadNotifications:
    def test_deletes_only_read_for_current_user(self, app, client, admin_token, admin_user, regular_user):
        with app.app_context():
            admin_id = User.query.filter_by(username='admin').first().id
            regular_id = User.query.filter_by(username='user').first().id
            unread = create_notification(
                user_id=admin_id,
                title='Unread',
                message='unread message',
                notification_type='info',
            )
            read_one = create_notification(
                user_id=admin_id,
                title='Read 1',
                message='read message',
                notification_type='warning',
            )
            read_two = create_notification(
                user_id=admin_id,
                title='Read 2',
                message='read message',
                notification_type='error',
            )
            other_user_read = create_notification(
                user_id=regular_id,
                title='Other user read',
                message='read message',
                notification_type='info',
            )

            now = datetime.utcnow()
            for n in (read_one, read_two, other_user_read):
                n.is_read = True
                n.read_at = now
            db.session.commit()

            unread_id = unread.id
            read_one_id = read_one.id
            read_two_id = read_two.id
            other_user_read_id = other_user_read.id

        response = client.delete(
            '/api/notifications/delete-read',
            headers={'Authorization': f'Bearer {admin_token}'},
        )
        assert response.status_code == 200
        assert response.get_json()['deleted_count'] == 2

        with app.app_context():
            remaining_ids = {n.id for n in Notification.query.all()}
            assert unread_id in remaining_ids
            assert other_user_read_id in remaining_ids
            assert read_one_id not in remaining_ids
            assert read_two_id not in remaining_ids

    def test_deletes_read_within_date_range(self, app, client, admin_token, admin_user):
        now = datetime.utcnow()
        today = now.date()
        yesterday = today - timedelta(days=1)

        with app.app_context():
            admin_id = User.query.filter_by(username='admin').first().id
            old_read = create_notification(
                user_id=admin_id,
                title='Old read',
                message='old',
                notification_type='info',
            )
            old_read.created_at = datetime.combine(yesterday, time(12, 0, 0))
            old_read.is_read = True
            old_read.read_at = now

            today_read = create_notification(
                user_id=admin_id,
                title='Today read',
                message='today',
                notification_type='info',
            )
            today_read.created_at = datetime.combine(today, time(12, 0, 0))
            today_read.is_read = True
            today_read.read_at = now

            db.session.commit()

            old_read_id = old_read.id
            today_read_id = today_read.id

        response = client.delete(
            f'/api/notifications/delete-read?from={today.isoformat()}&to={today.isoformat()}',
            headers={'Authorization': f'Bearer {admin_token}'},
        )
        assert response.status_code == 200
        assert response.get_json()['deleted_count'] == 1

        with app.app_context():
            remaining_ids = {n.id for n in Notification.query.all()}
            assert old_read_id in remaining_ids
            assert today_read_id not in remaining_ids
