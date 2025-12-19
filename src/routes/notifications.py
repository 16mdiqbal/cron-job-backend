import logging
from datetime import datetime, date, time, timedelta, timezone
from typing import Optional
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from sqlalchemy import func
from ..models import db
from ..models.notification import Notification
from ..models.user import User
from ..utils.api_errors import safe_error_message

logger = logging.getLogger(__name__)

# Create Blueprint
notifications_bp = Blueprint('notifications', __name__, url_prefix='/api/notifications')

def _parse_iso_date_or_datetime_utc_naive(value: Optional[str]) -> Optional[datetime]:
    """
    Parse an ISO date/datetime and normalize to UTC naive datetime for DB comparisons.
    Accepts:
      - YYYY-MM-DD
      - YYYY-MM-DDTHH:MM:SS[.ffffff][Z|+HH:MM]
    """
    if not value:
        return None

    raw = (value or '').strip()
    if not raw:
        return None

    # Date-only inputs like "2025-12-18"
    try:
        if len(raw) == 10 and raw[4] == '-' and raw[7] == '-':
            d = date.fromisoformat(raw)
            return datetime.combine(d, time.min)
    except Exception:
        pass

    normalized = raw.replace('Z', '+00:00')
    try:
        dt = datetime.fromisoformat(normalized)
    except ValueError as e:
        raise ValueError('Invalid date format. Use YYYY-MM-DD or ISO datetime.') from e
    if dt.tzinfo is None:
        # Assume UTC if naive
        dt = dt.replace(tzinfo=timezone.utc)
    dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt


@notifications_bp.route('', methods=['GET'])
@jwt_required()
def get_notifications():
    """
    Get notifications for the current user.
    Supports pagination and filtering by read status.
    
    Query Parameters:
        page: Page number (default: 1)
        per_page: Items per page (default: 20, max: 100)
        unread_only: Filter to show only unread notifications (default: false)
        from: ISO date/datetime (inclusive, based on created_at)
        to: ISO date/datetime (exclusive, based on created_at). Date-only treated as inclusive day.
    
    Headers:
        Authorization: Bearer <access_token>
    
    Returns:
        200: Notifications retrieved successfully
        401: Unauthorized (invalid token)
        500: Internal server error
    """
    try:
        current_user_id = get_jwt_identity()
        
        # Get query parameters
        page = request.args.get('page', 1, type=int)
        per_page = min(request.args.get('per_page', 20, type=int), 100)
        unread_only = request.args.get('unread_only', 'false').lower() == 'true'
        from_raw = request.args.get('from')
        to_raw = request.args.get('to')
        try:
            from_dt = _parse_iso_date_or_datetime_utc_naive(from_raw)
            to_dt = _parse_iso_date_or_datetime_utc_naive(to_raw)
        except ValueError as e:
            return jsonify({'error': 'Invalid date', 'message': safe_error_message(e, 'Invalid date')}), 400
        if to_raw and to_dt and len(to_raw.strip()) == 10:
            to_dt = to_dt + timedelta(days=1)
        if from_dt and to_dt and from_dt >= to_dt:
            return jsonify({'error': 'Invalid date range', 'message': '"from" must be earlier than "to".'}), 400
        
        # Build query
        query = Notification.query.filter_by(user_id=current_user_id)
        
        if unread_only:
            query = query.filter_by(is_read=False)

        if from_dt:
            query = query.filter(Notification.created_at >= from_dt)
        if to_dt:
            query = query.filter(Notification.created_at < to_dt)
        
        # Order by created_at descending (newest first)
        query = query.order_by(Notification.created_at.desc())
        
        # Paginate
        paginated = query.paginate(page=page, per_page=per_page, error_out=False)
        
        return jsonify({
            'notifications': [n.to_dict() for n in paginated.items],
            'total': paginated.total,
            'page': page,
            'per_page': per_page,
            'total_pages': paginated.pages,
            'range': {
                'from': from_dt.isoformat() if from_dt else None,
                'to': to_dt.isoformat() if to_dt else None,
            },
        }), 200
        
    except Exception as e:
        logger.error(f"Error retrieving notifications: {str(e)}")
        return jsonify({
            'error': 'Internal server error',
            'message': safe_error_message(e)
        }), 500


@notifications_bp.route('/unread-count', methods=['GET'])
@jwt_required()
def get_unread_count():
    """
    Get count of unread notifications for the current user.

    Optional query params:
      - from: ISO date/datetime (inclusive, based on created_at)
      - to: ISO date/datetime (exclusive, based on created_at). Date-only treated as inclusive day.
    
    Headers:
        Authorization: Bearer <access_token>
    
    Returns:
        200: Unread count retrieved successfully
        401: Unauthorized (invalid token)
        500: Internal server error
    """
    try:
        current_user_id = get_jwt_identity()

        from_raw = request.args.get('from')
        to_raw = request.args.get('to')
        try:
            from_dt = _parse_iso_date_or_datetime_utc_naive(from_raw)
            to_dt = _parse_iso_date_or_datetime_utc_naive(to_raw)
        except ValueError as e:
            return jsonify({'error': 'Invalid date', 'message': safe_error_message(e, 'Invalid date')}), 400
        if to_raw and to_dt and len(to_raw.strip()) == 10:
            to_dt = to_dt + timedelta(days=1)
        if from_dt and to_dt and from_dt >= to_dt:
            return jsonify({'error': 'Invalid date range', 'message': '"from" must be earlier than "to".'}), 400
        
        query = Notification.query.filter_by(user_id=current_user_id, is_read=False)
        if from_dt:
            query = query.filter(Notification.created_at >= from_dt)
        if to_dt:
            query = query.filter(Notification.created_at < to_dt)
        count = query.count()
        
        return jsonify({
            'unread_count': count,
            'range': {
                'from': from_dt.isoformat() if from_dt else None,
                'to': to_dt.isoformat() if to_dt else None,
            },
        }), 200
        
    except Exception as e:
        logger.error(f"Error retrieving unread count: {str(e)}")
        return jsonify({
            'error': 'Internal server error',
            'message': safe_error_message(e)
        }), 500


@notifications_bp.route('/<notification_id>/read', methods=['PUT'])
@jwt_required()
def mark_as_read(notification_id):
    """
    Mark a specific notification as read.
    
    Args:
        notification_id: The notification ID
    
    Headers:
        Authorization: Bearer <access_token>
    
    Returns:
        200: Notification marked as read
        401: Unauthorized (invalid token)
        403: Forbidden (not your notification)
        404: Notification not found
        500: Internal server error
    """
    try:
        current_user_id = get_jwt_identity()
        
        notification = Notification.query.filter_by(id=notification_id).first()
        
        if not notification:
            return jsonify({'error': 'Notification not found'}), 404
        
        # Check if notification belongs to current user
        if notification.user_id != current_user_id:
            return jsonify({'error': 'Forbidden: Cannot access other users notifications'}), 403
        
        notification.mark_as_read()
        
        return jsonify({
            'message': 'Notification marked as read',
            'notification': notification.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error marking notification as read: {str(e)}")
        return jsonify({
            'error': 'Internal server error',
            'message': safe_error_message(e)
        }), 500


@notifications_bp.route('/read-all', methods=['PUT'])
@jwt_required()
def mark_all_as_read():
    """
    Mark all notifications as read for the current user.
    
    Headers:
        Authorization: Bearer <access_token>
    
    Returns:
        200: All notifications marked as read
        401: Unauthorized (invalid token)
        500: Internal server error
    """
    try:
        current_user_id = get_jwt_identity()
        
        # Update all unread notifications
        from datetime import datetime
        updated_count = Notification.query.filter_by(
            user_id=current_user_id,
            is_read=False
        ).update({
            'is_read': True,
            'read_at': datetime.utcnow()
        })
        
        db.session.commit()
        
        return jsonify({
            'message': 'All notifications marked as read',
            'updated_count': updated_count
        }), 200
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error marking all notifications as read: {str(e)}")
        return jsonify({
            'error': 'Internal server error',
            'message': safe_error_message(e)
        }), 500


@notifications_bp.route('/<notification_id>', methods=['DELETE'])
@jwt_required()
def delete_notification(notification_id):
    """
    Delete a specific notification.
    
    Args:
        notification_id: The notification ID
    
    Headers:
        Authorization: Bearer <access_token>
    
    Returns:
        200: Notification deleted successfully
        401: Unauthorized (invalid token)
        403: Forbidden (not your notification)
        404: Notification not found
        500: Internal server error
    """
    try:
        current_user_id = get_jwt_identity()
        
        notification = Notification.query.filter_by(id=notification_id).first()
        
        if not notification:
            return jsonify({'error': 'Notification not found'}), 404
        
        # Check if notification belongs to current user
        if notification.user_id != current_user_id:
            return jsonify({'error': 'Forbidden: Cannot delete other users notifications'}), 403
        
        db.session.delete(notification)
        db.session.commit()
        
        return jsonify({
            'message': 'Notification deleted successfully'
        }), 200
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error deleting notification: {str(e)}")
        return jsonify({
            'error': 'Internal server error',
            'message': safe_error_message(e)
        }), 500


@notifications_bp.route('/delete-read', methods=['DELETE'])
@jwt_required()
def delete_read_notifications():
    """
    Delete all read notifications for the current user (optionally within date range).

    Optional query params:
      - from: ISO date/datetime (inclusive, based on created_at)
      - to: ISO date/datetime (exclusive, based on created_at). Date-only treated as inclusive day.

    Returns:
      200: { deleted_count }
    """
    try:
        current_user_id = get_jwt_identity()

        from_raw = request.args.get('from')
        to_raw = request.args.get('to')
        try:
            from_dt = _parse_iso_date_or_datetime_utc_naive(from_raw)
            to_dt = _parse_iso_date_or_datetime_utc_naive(to_raw)
        except ValueError as e:
            return jsonify({'error': 'Invalid date', 'message': safe_error_message(e, 'Invalid date')}), 400
        if to_raw and to_dt and len(to_raw.strip()) == 10:
            to_dt = to_dt + timedelta(days=1)
        if from_dt and to_dt and from_dt >= to_dt:
            return jsonify({'error': 'Invalid date range', 'message': '"from" must be earlier than "to".'}), 400

        query = Notification.query.filter_by(user_id=current_user_id, is_read=True)
        if from_dt:
            query = query.filter(Notification.created_at >= from_dt)
        if to_dt:
            query = query.filter(Notification.created_at < to_dt)

        deleted_count = query.delete(synchronize_session=False)
        db.session.commit()

        return jsonify({'deleted_count': deleted_count}), 200
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error deleting read notifications: {str(e)}")
        return jsonify({'error': 'Internal server error', 'message': safe_error_message(e)}), 500
