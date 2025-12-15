import logging
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from ..models import db
from ..models.notification import Notification
from ..models.user import User

logger = logging.getLogger(__name__)

# Create Blueprint
notifications_bp = Blueprint('notifications', __name__, url_prefix='/api/notifications')


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
        
        # Build query
        query = Notification.query.filter_by(user_id=current_user_id)
        
        if unread_only:
            query = query.filter_by(is_read=False)
        
        # Order by created_at descending (newest first)
        query = query.order_by(Notification.created_at.desc())
        
        # Paginate
        paginated = query.paginate(page=page, per_page=per_page, error_out=False)
        
        return jsonify({
            'notifications': [n.to_dict() for n in paginated.items],
            'total': paginated.total,
            'page': page,
            'per_page': per_page,
            'total_pages': paginated.pages
        }), 200
        
    except Exception as e:
        logger.error(f"Error retrieving notifications: {str(e)}")
        return jsonify({
            'error': 'Internal server error',
            'message': str(e)
        }), 500


@notifications_bp.route('/unread-count', methods=['GET'])
@jwt_required()
def get_unread_count():
    """
    Get count of unread notifications for the current user.
    
    Headers:
        Authorization: Bearer <access_token>
    
    Returns:
        200: Unread count retrieved successfully
        401: Unauthorized (invalid token)
        500: Internal server error
    """
    try:
        current_user_id = get_jwt_identity()
        
        count = Notification.query.filter_by(
            user_id=current_user_id,
            is_read=False
        ).count()
        
        return jsonify({
            'unread_count': count
        }), 200
        
    except Exception as e:
        logger.error(f"Error retrieving unread count: {str(e)}")
        return jsonify({
            'error': 'Internal server error',
            'message': str(e)
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
            'message': str(e)
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
            'message': str(e)
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
            'message': str(e)
        }), 500
