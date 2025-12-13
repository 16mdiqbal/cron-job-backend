"""
Create initial admin user for the application.
Run this script once to create the first admin user.

Usage:
    python create_admin.py
"""
import sys
from app import app
from models import db
from models.user import User

def create_admin():
    with app.app_context():
        # Check if admin already exists
        admin = User.query.filter_by(username='admin').first()
        
        if admin:
            print("Admin user already exists!")
            print(f"Username: admin")
            return
        
        # Create admin user
        admin = User(
            username='admin',
            email='admin@example.com',
            role='admin',
            is_active=True
        )
        admin.set_password('admin123')  # Change this password!
        
        db.session.add(admin)
        db.session.commit()
        
        print("✅ Admin user created successfully!")
        print(f"Username: admin")
        print(f"Password: admin123")
        print(f"Email: admin@example.com")
        print(f"Role: admin")
        print("\n⚠️  IMPORTANT: Change the admin password after first login!")

if __name__ == '__main__':
    create_admin()
