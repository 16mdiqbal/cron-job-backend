"""
Create an initial admin user for the application (FastAPI-only).

Usage:
  venv/bin/python scripts/create_admin.py
  ADMIN_USERNAME=admin ADMIN_PASSWORD=admin123 venv/bin/python scripts/create_admin.py
"""

import os

from sqlalchemy import select

from src.database.bootstrap import init_db
from src.database.session import get_db_session
from src.models.user import User


def create_admin() -> bool:
    init_db()

    username = (os.getenv("ADMIN_USERNAME") or "admin").strip()
    password = os.getenv("ADMIN_PASSWORD") or "admin123"
    email = (os.getenv("ADMIN_EMAIL") or "admin@example.com").strip()

    with get_db_session() as session:
        existing = session.execute(select(User).where(User.username == username)).scalars().first()
        if existing:
            print("✓ Admin user already exists!")
            print(f"  Username: {existing.username}")
            print(f"  Email: {existing.email}")
            print(f"  Role: {existing.role}")
            return False

        admin = User(username=username, email=email, role="admin", is_active=True)
        admin.set_password(password)
        session.add(admin)
        session.commit()

    print("✅ Admin user created successfully!")
    print(f"  Username: {username}")
    print(f"  Password: {password}")
    print(f"  Email: {email}")
    print("  Role: admin")
    print("\n⚠️  IMPORTANT: Change the admin password after first login!")
    return True


if __name__ == "__main__":
    create_admin()
