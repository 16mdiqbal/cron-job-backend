import logging
from flask import Blueprint, request, jsonify
from flask_jwt_extended import create_access_token, create_refresh_token, jwt_required, get_jwt_identity
from models import db
from models.user import User
from utils.auth import role_required

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
            'message': str(e)
        }), 500


@auth_bp.route('/login', methods=['POST'])
def login():
    """
    Login and receive JWT tokens.
    
    Expected JSON payload:
    {
        "username": "john_doe",
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
        if not data.get('username') or not data.get('password'):
            return jsonify({'error': 'Username and password are required'}), 400
        
        username = data['username'].strip()
        password = data['password']
        
        # Find user
        user = User.query.filter_by(username=username).first()
        
        if not user:
            logger.warning(f"Login attempt with non-existent username: {username}")
            return jsonify({'error': 'Invalid username or password'}), 401
        
        # Check if user is active
        if not user.is_active:
            logger.warning(f"Login attempt for inactive user: {username}")
            return jsonify({'error': 'Account is inactive. Contact administrator.'}), 401
        
        # Verify password
        if not user.check_password(password):
            logger.warning(f"Failed login attempt for user: {username}")
            return jsonify({'error': 'Invalid username or password'}), 401
        
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
        
        logger.info(f"User logged in successfully: {username}")
        
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
            'message': str(e)
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
            'message': str(e)
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
            'message': str(e)
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
            'message': str(e)
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
            'message': str(e)
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
            'message': str(e)
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
            'message': str(e)
        }), 500
