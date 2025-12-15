"""
Create initial admin user for the application.
Run this script to create the first admin user.

Usage:
    python -m create_admin
    or: python -m src.create_admin
"""
from src.app import app
from src.models import db
from src.models.user import User

def create_admin():
    """Create admin user if it doesn't exist."""
    with app.app_context():
        # Create all tables first
        db.create_all()
        
        # Check if admin already exists
        admin = User.query.filter_by(username='admin').first()
        
        if admin:
            print("✓ Admin user already exists!")
            print(f"  Username: {admin.username}")
            print(f"  Email: {admin.email}")
            print(f"  Role: {admin.role}")
            return False
        
        # Create admin user
        admin = User(
            username='admin',
            email='admin@example.com',
            role='admin',
            is_active=True
        )
        admin.set_password('admin123')
        
        db.session.add(admin)
        db.session.commit()
        
        print("✅ Admin user created successfully!")
        print(f"  Username: admin")
        print(f"  Password: admin123")
        print(f"  Email: admin@example.com")
        print(f"  Role: admin")
        print("\n⚠️  IMPORTANT: Change the admin password after first login!")
        return True

if __name__ == '__main__':
    create_admin()
