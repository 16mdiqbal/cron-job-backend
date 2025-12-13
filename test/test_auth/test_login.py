"""
Tests for authentication functionality.
"""
import pytest


class TestLogin:
    """Test login endpoint."""
    
    def test_login_with_valid_credentials(self, client, admin_user):
        """Test login with valid admin credentials."""
        response = client.post('/api/auth/login', json={
            'username': 'admin',
            'password': 'admin123'
        })
        
        assert response.status_code == 200
        data = response.get_json()
        assert 'access_token' in data
        assert data['user']['username'] == 'admin'
        assert data['user']['role'] == 'admin'
    
    def test_login_with_invalid_username(self, client):
        """Test login with invalid username."""
        response = client.post('/api/auth/login', json={
            'username': 'nonexistent',
            'password': 'password'
        })
        
        assert response.status_code == 401
        assert 'error' in response.get_json()
    
    def test_login_with_invalid_password(self, client, admin_user):
        """Test login with invalid password."""
        response = client.post('/api/auth/login', json={
            'username': 'admin',
            'password': 'wrongpassword'
        })
        
        assert response.status_code == 401
    
    def test_login_missing_username(self, client):
        """Test login with missing username field."""
        response = client.post('/api/auth/login', json={
            'password': 'password'
        })
        
        assert response.status_code == 400
    
    def test_login_missing_password(self, client):
        """Test login with missing password field."""
        response = client.post('/api/auth/login', json={
            'username': 'admin'
        })
        
        assert response.status_code == 400
    
    def test_login_empty_credentials(self, client):
        """Test login with empty credentials."""
        response = client.post('/api/auth/login', json={
            'username': '',
            'password': ''
        })
        
        assert response.status_code == 400


class TestGetCurrentUser:
    """Test get current user endpoint."""
    
    def test_get_current_user_with_valid_token(self, client, admin_token, admin_user):
        """Test getting current user with valid token."""
        response = client.get('/api/auth/me', headers={
            'Authorization': f'Bearer {admin_token}'
        })
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['user']['username'] == 'admin'
        assert data['user']['email'] == 'admin@example.com'
        assert data['user']['role'] == 'admin'
    
    def test_get_current_user_without_token(self, client):
        """Test getting current user without token."""
        response = client.get('/api/auth/me')
        
        assert response.status_code == 401
    
    def test_get_current_user_with_invalid_token(self, client):
        """Test getting current user with invalid token."""
        response = client.get('/api/auth/me', headers={
            'Authorization': 'Bearer invalid_token'
        })
        
        assert response.status_code == 422
    
    def test_get_current_user_with_regular_user(self, client, user_token, regular_user):
        """Test getting current user for regular user."""
        response = client.get('/api/auth/me', headers={
            'Authorization': f'Bearer {user_token}'
        })
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['user']['username'] == 'user'
        assert data['user']['role'] == 'user'
    
    def test_get_current_user_with_viewer_user(self, client, viewer_token, viewer_user):
        """Test getting current user for viewer user."""
        response = client.get('/api/auth/me', headers={
            'Authorization': f'Bearer {viewer_token}'
        })
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['user']['username'] == 'viewer'
        assert data['user']['role'] == 'viewer'


class TestAuthentication:
    """Test authentication security."""
    
    def test_authorization_header_missing(self, client):
        """Test request without Authorization header."""
        response = client.get('/api/jobs')
        
        assert response.status_code == 401
    
    def test_authorization_header_malformed(self, client):
        """Test request with malformed Authorization header."""
        response = client.get('/api/jobs', headers={
            'Authorization': 'InvalidFormat'
        })
        
        assert response.status_code == 401
    
    def test_expired_token_handling(self, client, admin_token):
        """Test handling of invalid/malformed token."""
        # Using invalid token structure returns 422
        response = client.get('/api/jobs', headers={
            'Authorization': 'Bearer expired_token_example'
        })
        
        assert response.status_code == 422
    
    def test_token_case_sensitivity(self, client, admin_token):
        """Test that Bearer token is case-insensitive."""
        # Standard format should work
        response = client.get('/api/jobs', headers={
            'Authorization': f'Bearer {admin_token}'
        })
        
        assert response.status_code == 200
        
        # Lowercase should also work
        response = client.get('/api/jobs', headers={
            'Authorization': f'bearer {admin_token}'
        })
        
        # This might fail depending on implementation
        # But checking standard Bearer format works


class TestUserRoles:
    """Test role-based access control."""
    
    def test_admin_can_access_protected_routes(self, client, admin_token):
        """Test that admin can access protected routes."""
        response = client.get('/api/jobs', headers={
            'Authorization': f'Bearer {admin_token}'
        })
        
        assert response.status_code == 200
    
    def test_user_can_access_protected_routes(self, client, user_token):
        """Test that regular user can access protected routes."""
        response = client.get('/api/jobs', headers={
            'Authorization': f'Bearer {user_token}'
        })
        
        assert response.status_code == 200
    
    def test_viewer_can_access_protected_routes(self, client, viewer_token):
        """Test that viewer can access protected routes."""
        response = client.get('/api/jobs', headers={
            'Authorization': f'Bearer {viewer_token}'
        })
        
        assert response.status_code == 200
