"""
Authentication utilities for JWT token management and authorization checks.
"""
import logging
from functools import wraps
from flask import jsonify
from flask_jwt_extended import verify_jwt_in_request, get_jwt_identity, get_jwt
from models import db
from models.user import User

logger = logging.getLogger(__name__)


def token_required(fn):
    """
    Decorator to require valid JWT token for endpoint access.
    Automatically verifies token and makes user identity available.
    """
    @wraps(fn)
    def wrapper(*args, **kwargs):
        try:
            verify_jwt_in_request()
            return fn(*args, **kwargs)
        except Exception as e:
            logger.error(f"Token verification failed: {str(e)}")
            return jsonify({'error': 'Invalid or expired token'}), 401
    return wrapper


def role_required(*allowed_roles):
    """
    Decorator to require specific roles for endpoint access.
    Usage: @role_required('admin', 'user')
    
    Args:
        allowed_roles: Variable number of role strings (e.g., 'admin', 'user', 'viewer')
    """
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            try:
                verify_jwt_in_request()
                claims = get_jwt()
                user_role = claims.get('role')
                
                if user_role not in allowed_roles:
                    logger.warning(f"Access denied for role '{user_role}'. Required: {allowed_roles}")
                    return jsonify({
                        'error': 'Insufficient permissions',
                        'message': f'This endpoint requires one of the following roles: {", ".join(allowed_roles)}'
                    }), 403
                
                return fn(*args, **kwargs)
            except Exception as e:
                logger.error(f"Role verification failed: {str(e)}")
                return jsonify({'error': 'Invalid or expired token'}), 401
        return wrapper
    return decorator


def get_current_user():
    """
    Get the current authenticated user from the JWT token.
    Returns User object or None if not found.
    """
    try:
        user_id = get_jwt_identity()
        return User.query.filter_by(id=user_id, is_active=True).first()
    except Exception as e:
        logger.error(f"Failed to get current user: {str(e)}")
        return None


def is_admin():
    """Check if current user has admin role."""
    claims = get_jwt()
    return claims.get('role') == 'admin'


def is_job_owner(job):
    """
    Check if current user owns the given job.
    Admins always return True.
    """
    if is_admin():
        return True
    
    user = get_current_user()
    if not user:
        return False
    
    return job.created_by == user.id


def can_modify_job(job):
    """
    Check if current user can modify (update/delete) the given job.
    - Admin: Can modify any job
    - User: Can modify only their own jobs
    - Viewer: Cannot modify any job
    """
    claims = get_jwt()
    user_role = claims.get('role')
    
    if user_role == 'admin':
        return True
    
    if user_role == 'viewer':
        return False
    
    if user_role == 'user':
        return is_job_owner(job)
    
    return False
