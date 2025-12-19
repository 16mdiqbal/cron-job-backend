import logging
from flask import Blueprint, request, jsonify
from flask_jwt_extended import create_access_token, create_refresh_token, jwt_required, get_jwt_identity
from ..models import db
from ..models.user import User
from ..models.notification_preferences import UserNotificationPreferences
from ..models.ui_preferences import UserUiPreferences
from ..utils.auth import role_required
from ..utils.api_errors import safe_error_message

logger = logging.getLogger(__name__)

# Create Blueprint
auth_bp = Blueprint('auth', __name__, url_prefix='/api/auth')


@auth_bp.route('/register', methods=['POST'])
@jwt_required()
@role_required('admin')
def register():
    """
    Register a new user (Admin only).
    
    Expected JSON payload:
    {
        "username": "john_doe",
        "email": "john@example.com",
        "password": "secure_password",
        "role": "user"  // Optional, defaults to 'viewer'
    }
    
    Returns:
        201: User created successfully
        400: Bad request (validation errors)
        403: Forbidden (non-admin trying to register)
        409: Conflict (username/email already exists)
        500: Internal server error
    """
    try:
        if not request.is_json:
            return jsonify({'error': 'Content-Type must be application/json'}), 400
        
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['username', 'email', 'password']
        missing_fields = [field for field in required_fields if field not in data or not data[field]]
        
        if missing_fields:
            return jsonify({
                'error': 'Missing required fields',
                'missing': missing_fields
            }), 400
        
        username = data['username'].strip()
        email = data['email'].strip().lower()
        password = data['password']
        role = data.get('role', 'viewer')
        
        # Validate username length
        if len(username) < 3:
            return jsonify({'error': 'Username must be at least 3 characters long'}), 400
        
        # Validate password length
        if len(password) < 6:
            return jsonify({'error': 'Password must be at least 6 characters long'}), 400
        
        # Validate role
        if not User.validate_role(role):
            return jsonify({
                'error': 'Invalid role',
                'message': 'Role must be one of: admin, user, viewer'
            }), 400
        
        # Check if username already exists
        if User.query.filter_by(username=username).first():
            return jsonify({'error': 'Username already exists'}), 409
        
        # Check if email already exists
        if User.query.filter_by(email=email).first():
            return jsonify({'error': 'Email already exists'}), 409
        
        # Create new user
        new_user = User(
            username=username,
            email=email,
            role=role,
            is_active=True
        )
        new_user.set_password(password)
        
        db.session.add(new_user)
        db.session.commit()
        
        logger.info(f"New user registered: {username} ({role})")
        
        return jsonify({
            'message': 'User registered successfully',
            'user': new_user.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error registering user: {str(e)}")
        return jsonify({
            'error': 'Internal server error',
            'message': safe_error_message(e)
        }), 500


@auth_bp.route('/login', methods=['POST'])
def login():
    """
    Login and receive JWT tokens.
    
    Supports login with either username or email.
    
    Expected JSON payload (choose one):
    {
        "username": "john_doe",
        "password": "secure_password"
    }
    OR
    {
        "email": "john@example.com",
        "password": "secure_password"
    }
    
    Returns:
        200: Login successful with access and refresh tokens
        400: Bad request (missing fields)
        401: Unauthorized (invalid credentials or inactive user)
        500: Internal server error
    """
    try:
        if not request.is_json:
            return jsonify({'error': 'Content-Type must be application/json'}), 400
        
        data = request.get_json()
        
        # Validate required fields
        username_or_email = data.get('username') or data.get('email')
        password = data.get('password')
        
        if not username_or_email or not password:
            return jsonify({'error': 'Email/Username and password are required'}), 400
        
        username_or_email = username_or_email.strip()
        
        # Find user by username OR email
        user = User.query.filter(
            (User.username == username_or_email) | (User.email == username_or_email)
        ).first()
        
        if not user:
            logger.warning(f"Login attempt with non-existent username/email: {username_or_email}")
            return jsonify({'error': 'Invalid email/username or password'}), 401
        
        # Check if user is active
        if not user.is_active:
            logger.warning(f"Login attempt for inactive user: {user.username}")
            return jsonify({'error': 'Account is inactive. Contact administrator.'}), 401
        
        # Verify password
        if not user.check_password(password):
            logger.warning(f"Failed login attempt for user: {user.username}")
            return jsonify({'error': 'Invalid email/username or password'}), 401
        
        # Create tokens with user claims
        additional_claims = {
            'role': user.role,
            'email': user.email
        }
        
        access_token = create_access_token(
            identity=user.id,
            additional_claims=additional_claims
        )
        
        refresh_token = create_refresh_token(
            identity=user.id,
            additional_claims=additional_claims
        )
        
        logger.info(f"User logged in successfully: {user.username}")
        
        return jsonify({
            'message': 'Login successful',
            'access_token': access_token,
            'refresh_token': refresh_token,
            'user': user.to_dict()
        }), 200
        
    except Exception as e:
        logger.error(f"Error during login: {str(e)}")
        return jsonify({
            'error': 'Internal server error',
            'message': safe_error_message(e)
        }), 500


@auth_bp.route('/refresh', methods=['POST'])
@jwt_required(refresh=True)
def refresh():
    """
    Refresh access token using refresh token.
    
    Headers:
        Authorization: Bearer <refresh_token>
    
    Returns:
        200: New access token
        401: Unauthorized (invalid refresh token)
        500: Internal server error
    """
    try:
        current_user_id = get_jwt_identity()
        
        # Get user to include latest role in new token
        user = User.query.filter_by(id=current_user_id, is_active=True).first()
        
        if not user:
            return jsonify({'error': 'User not found or inactive'}), 401
        
        additional_claims = {
            'role': user.role,
            'email': user.email
        }
        
        new_access_token = create_access_token(
            identity=current_user_id,
            additional_claims=additional_claims
        )
        
        return jsonify({
            'access_token': new_access_token
        }), 200
        
    except Exception as e:
        logger.error(f"Error refreshing token: {str(e)}")
        return jsonify({
            'error': 'Internal server error',
            'message': safe_error_message(e)
        }), 500


@auth_bp.route('/me', methods=['GET'])
@jwt_required()
def get_current_user():
    """
    Get current authenticated user information.
    
    Headers:
        Authorization: Bearer <access_token>
    
    Returns:
        200: User information
        401: Unauthorized (invalid token)
        404: User not found
        500: Internal server error
    """
    try:
        current_user_id = get_jwt_identity()
        user = User.query.filter_by(id=current_user_id).first()
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        return jsonify({
            'user': user.to_dict()
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting current user: {str(e)}")
        return jsonify({
            'error': 'Internal server error',
            'message': safe_error_message(e)
        }), 500


@auth_bp.route('/users', methods=['GET'])
@jwt_required()
@role_required('admin')
def list_users():
    """
    List all users (Admin only).
    
    Headers:
        Authorization: Bearer <access_token>
    
    Returns:
        200: List of all users
        401: Unauthorized (invalid token)
        403: Forbidden (non-admin)
        500: Internal server error
    """
    try:
        users = User.query.all()
        
        return jsonify({
            'count': len(users),
            'users': [user.to_dict() for user in users]
        }), 200
        
    except Exception as e:
        logger.error(f"Error listing users: {str(e)}")
        return jsonify({
            'error': 'Internal server error',
            'message': safe_error_message(e)
        }), 500


@auth_bp.route('/users/<user_id>', methods=['GET'])
@jwt_required()
def get_user(user_id):
    """
    Get specific user by ID.
    Admins can view any user. Regular users can only view their own profile.
    
    Headers:
        Authorization: Bearer <access_token>
    
    Returns:
        200: User information
        401: Unauthorized (invalid token)
        403: Forbidden (trying to view another user's profile)
        404: User not found
        500: Internal server error
    """
    try:
        current_user_id = get_jwt_identity()
        current_user = User.query.filter_by(id=current_user_id).first()
        
        if not current_user:
            return jsonify({'error': 'Current user not found'}), 401
        
        # Check authorization: admin can view any user, others can only view themselves
        if current_user.role != 'admin' and current_user_id != user_id:
            return jsonify({'error': 'Forbidden. You can only view your own profile.'}), 403
        
        user = User.query.filter_by(id=user_id).first()
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        return jsonify({
            'user': user.to_dict()
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting user: {str(e)}")
        return jsonify({
            'error': 'Internal server error',
            'message': safe_error_message(e)
        }), 500


@auth_bp.route('/users/<user_id>', methods=['PUT'])
@jwt_required()
def update_user(user_id):
    """
    Update user information.
    Admins can update any user's any field.
    Regular users can only update their own email and password.
    
    Expected JSON payload (all fields optional):
    {
        "email": "newemail@example.com",
        "password": "newpassword123",
        "role": "admin",  // Admin only
        "is_active": false  // Admin only
    }
    
    Headers:
        Authorization: Bearer <access_token>
    
    Returns:
        200: User updated successfully
        400: Bad request (validation errors)
        401: Unauthorized (invalid token)
        403: Forbidden (insufficient permissions)
        404: User not found
        409: Conflict (email already exists)
        500: Internal server error
    """
    try:
        if not request.is_json:
            return jsonify({'error': 'Content-Type must be application/json'}), 400
        
        current_user_id = get_jwt_identity()
        current_user = User.query.filter_by(id=current_user_id).first()
        
        if not current_user:
            return jsonify({'error': 'Current user not found'}), 401
        
        # Check if user is updating themselves or if they're admin
        is_self_update = current_user_id == user_id
        is_admin = current_user.role == 'admin'
        
        if not is_admin and not is_self_update:
            return jsonify({'error': 'Forbidden. You can only update your own profile.'}), 403
        
        # Find user to update
        user = User.query.filter_by(id=user_id).first()
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        data = request.get_json()
        updated_fields = []
        
        # Update email (allowed for self and admin)
        if 'email' in data and data['email']:
            new_email = data['email'].strip().lower()
            # Check if email already exists for another user
            existing_user = User.query.filter_by(email=new_email).first()
            if existing_user and existing_user.id != user_id:
                return jsonify({'error': 'Email already exists'}), 409
            user.email = new_email
            updated_fields.append('email')
        
        # Update password (allowed for self and admin)
        if 'password' in data and data['password']:
            new_password = data['password']
            if len(new_password) < 6:
                return jsonify({'error': 'Password must be at least 6 characters long'}), 400
            user.set_password(new_password)
            updated_fields.append('password')
        
        # Update role (admin only)
        if 'role' in data:
            if not is_admin:
                return jsonify({'error': 'Only admins can change user roles'}), 403
            new_role = data['role']
            if not User.validate_role(new_role):
                return jsonify({
                    'error': 'Invalid role',
                    'message': 'Role must be one of: admin, user, viewer'
                }), 400
            user.role = new_role
            updated_fields.append('role')
        
        # Update is_active (admin only)
        if 'is_active' in data:
            if not is_admin:
                return jsonify({'error': 'Only admins can change user active status'}), 403
            user.is_active = bool(data['is_active'])
            updated_fields.append('is_active')
        
        if not updated_fields:
            return jsonify({'error': 'No valid fields to update'}), 400
        
        db.session.commit()
        
        logger.info(f"User {user_id} updated by {current_user.username}. Fields: {', '.join(updated_fields)}")
        
        return jsonify({
            'message': 'User updated successfully',
            'updated_fields': updated_fields,
            'user': user.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error updating user: {str(e)}")
        return jsonify({
            'error': 'Internal server error',
            'message': safe_error_message(e)
        }), 500


@auth_bp.route('/users/<user_id>', methods=['DELETE'])
@jwt_required()
@role_required('admin')
def delete_user(user_id):
    """
    Delete user (Admin only).
    Cannot delete yourself.
    
    Headers:
        Authorization: Bearer <access_token>
    
    Returns:
        200: User deleted successfully
        400: Bad request (trying to delete yourself)
        401: Unauthorized (invalid token)
        403: Forbidden (non-admin)
        404: User not found
        500: Internal server error
    """
    try:
        current_user_id = get_jwt_identity()
        
        # Prevent self-deletion
        if current_user_id == user_id:
            return jsonify({'error': 'Cannot delete your own account'}), 400
        
        user = User.query.filter_by(id=user_id).first()
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        username = user.username
        
        # Delete user (cascade will handle related jobs)
        db.session.delete(user)
        db.session.commit()
        
        logger.info(f"User {username} (ID: {user_id}) deleted by admin {current_user_id}")
        
        return jsonify({
            'message': 'User deleted successfully',
            'deleted_user': {
                'id': user_id,
                'username': username
            }
        }), 200
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error deleting user: {str(e)}")
        return jsonify({
            'error': 'Internal server error',
            'message': safe_error_message(e)
        }), 500


@auth_bp.route('/users/<user_id>/preferences', methods=['GET'])
@jwt_required()
def get_notification_preferences(user_id):
    """
    Get user's notification preferences.
    Users can only access their own preferences unless they are admin.
    
    Headers:
        Authorization: Bearer <access_token>
    
    Returns:
        200: Preferences retrieved successfully
        401: Unauthorized (invalid token)
        403: Forbidden (non-admin accessing other user's preferences)
        404: User not found
        500: Internal server error
    """
    try:
        current_user_id = get_jwt_identity()
        current_user = User.query.filter_by(id=current_user_id).first()
        
        # Check permission: users can only access their own preferences, admins can access any
        if current_user_id != user_id and current_user.role != 'admin':
            return jsonify({'error': 'Forbidden: Cannot access other users preferences'}), 403
        
        user = User.query.filter_by(id=user_id).first()
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        # Get or create preferences
        preferences = UserNotificationPreferences.query.filter_by(user_id=user_id).first()
        
        if not preferences:
            # Create default preferences if they don't exist
            preferences = UserNotificationPreferences(
                user_id=user_id,
                email_on_job_success=True,
                email_on_job_failure=True,
                email_on_job_disabled=False,
                browser_notifications=False,
                daily_digest=False,
                weekly_report=False
            )
            db.session.add(preferences)
            db.session.commit()
            logger.info(f"Created default notification preferences for user {user_id}")
        
        return jsonify({
            'message': 'Notification preferences retrieved successfully',
            'preferences': preferences.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error retrieving notification preferences: {str(e)}")
        return jsonify({
            'error': 'Internal server error',
            'message': safe_error_message(e)
        }), 500


@auth_bp.route('/users/<user_id>/preferences', methods=['PUT'])
@jwt_required()
def update_notification_preferences(user_id):
    """
    Update user's notification preferences.
    Users can only update their own preferences unless they are admin.
    
    Headers:
        Authorization: Bearer <access_token>
    
    Expected JSON payload:
    {
        "email_on_job_success": true,
        "email_on_job_failure": true,
        "email_on_job_disabled": false,
        "browser_notifications": false,
        "daily_digest": false,
        "weekly_report": false
    }
    
    Returns:
        200: Preferences updated successfully
        400: Bad request (validation errors)
        401: Unauthorized (invalid token)
        403: Forbidden (non-admin updating other user's preferences)
        404: User not found
        500: Internal server error
    """
    try:
        current_user_id = get_jwt_identity()
        current_user = User.query.filter_by(id=current_user_id).first()
        
        # Check permission: users can only update their own preferences, admins can update any
        if current_user_id != user_id and current_user.role != 'admin':
            return jsonify({'error': 'Forbidden: Cannot update other users preferences'}), 403
        
        if not request.is_json:
            return jsonify({'error': 'Content-Type must be application/json'}), 400
        
        user = User.query.filter_by(id=user_id).first()
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        data = request.get_json()
        
        # Get or create preferences
        preferences = UserNotificationPreferences.query.filter_by(user_id=user_id).first()
        
        if not preferences:
            # Create new preferences if they don't exist
            preferences = UserNotificationPreferences(user_id=user_id)
            db.session.add(preferences)
        
        # Update only provided fields
        if 'email_on_job_success' in data:
            preferences.email_on_job_success = bool(data['email_on_job_success'])
        if 'email_on_job_failure' in data:
            preferences.email_on_job_failure = bool(data['email_on_job_failure'])
        if 'email_on_job_disabled' in data:
            preferences.email_on_job_disabled = bool(data['email_on_job_disabled'])
        if 'browser_notifications' in data:
            preferences.browser_notifications = bool(data['browser_notifications'])
        if 'daily_digest' in data:
            preferences.daily_digest = bool(data['daily_digest'])
        if 'weekly_report' in data:
            preferences.weekly_report = bool(data['weekly_report'])
        
        db.session.commit()
        
        logger.info(f"Notification preferences updated for user {user_id} by user {current_user_id}")
        
        return jsonify({
            'message': 'Notification preferences updated successfully',
            'preferences': preferences.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error updating notification preferences: {str(e)}")
        return jsonify({
            'error': 'Internal server error',
            'message': safe_error_message(e)
        }), 500


def _default_jobs_table_columns():
    # Keep the table quiet by default.
    return {
        'pic_team': True,
        'end_date': True,
        'cron_expression': False,
        'target_url': False,
        'last_execution_at': False,
    }


@auth_bp.route('/users/<user_id>/ui-preferences', methods=['GET'])
@jwt_required()
def get_ui_preferences(user_id):
    """
    Get user's UI preferences (e.g., Jobs table column visibility).
    Users can only access their own preferences unless they are admin.
    """
    try:
        current_user_id = get_jwt_identity()
        current_user = User.query.filter_by(id=current_user_id).first()
        if not current_user:
            return jsonify({'error': 'Unauthorized'}), 401

        if current_user_id != user_id and current_user.role != 'admin':
            return jsonify({'error': 'Forbidden: Cannot access other users preferences'}), 403

        user = User.query.filter_by(id=user_id).first()
        if not user:
            return jsonify({'error': 'User not found'}), 404

        prefs = UserUiPreferences.query.filter_by(user_id=user_id).first()
        if not prefs:
            prefs = UserUiPreferences(user_id=user_id)
            prefs.set_jobs_table_columns(_default_jobs_table_columns())
            db.session.add(prefs)
            db.session.commit()

        columns = prefs.get_jobs_table_columns() or _default_jobs_table_columns()
        return jsonify({'preferences': {'jobs_table_columns': columns}}), 200
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error retrieving UI preferences: {str(e)}")
        return jsonify({'error': 'Internal server error', 'message': safe_error_message(e)}), 500


@auth_bp.route('/users/<user_id>/ui-preferences', methods=['PUT'])
@jwt_required()
def update_ui_preferences(user_id):
    """
    Update user's UI preferences.
    Users can only update their own preferences unless they are admin.
    """
    try:
        current_user_id = get_jwt_identity()
        current_user = User.query.filter_by(id=current_user_id).first()
        if not current_user:
            return jsonify({'error': 'Unauthorized'}), 401

        if current_user_id != user_id and current_user.role != 'admin':
            return jsonify({'error': 'Forbidden: Cannot update other users preferences'}), 403

        if not request.is_json:
            return jsonify({'error': 'Content-Type must be application/json'}), 400

        user = User.query.filter_by(id=user_id).first()
        if not user:
            return jsonify({'error': 'User not found'}), 404

        data = request.get_json(silent=True) or {}
        if not isinstance(data, dict):
            return jsonify({'error': 'Invalid payload', 'message': 'JSON body must be an object.'}), 400

        incoming_cols = data.get('jobs_table_columns')
        if incoming_cols is None:
            return jsonify({'error': 'Missing required fields', 'message': '"jobs_table_columns" is required.'}), 400
        if not isinstance(incoming_cols, dict):
            return jsonify({'error': 'Invalid payload', 'message': '"jobs_table_columns" must be an object.'}), 400

        allowed_keys = set(_default_jobs_table_columns().keys())
        normalized = _default_jobs_table_columns()
        for k, v in incoming_cols.items():
            if k in allowed_keys:
                normalized[k] = bool(v)

        prefs = UserUiPreferences.query.filter_by(user_id=user_id).first()
        if not prefs:
            prefs = UserUiPreferences(user_id=user_id)
            db.session.add(prefs)

        prefs.set_jobs_table_columns(normalized)
        db.session.commit()

        return jsonify({'preferences': {'jobs_table_columns': normalized}}), 200
    except ValueError as e:
        db.session.rollback()
        return jsonify({'error': 'Invalid payload', 'message': safe_error_message(e, 'Invalid payload')}), 400
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error updating UI preferences: {str(e)}")
        return jsonify({'error': 'Internal server error', 'message': safe_error_message(e)}), 500
