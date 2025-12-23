#!/usr/bin/env python3
"""
Initialize FastAPI database with the same schema as Flask.

This creates a separate database for FastAPI during migration to avoid
Flask scheduler interference during tests.
"""

import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.models import db
from src.app import create_app

# Set testing mode
os.environ['TESTING'] = 'true'
os.environ['SCHEDULER_ENABLED'] = 'false'


def init_fastapi_database():
    """Initialize FastAPI database with the same schema."""
    # Create Flask app to get database models
    app = create_app()
    
    # Override database path for FastAPI
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    fastapi_db_path = os.path.join(base_dir, 'src', 'instance', 'fastapi_cron_jobs.db')
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{fastapi_db_path}'
    
    print(f"Initializing FastAPI database at: {fastapi_db_path}")
    
    with app.app_context():
        # Drop existing tables
        db.drop_all()
        print("  Dropped existing tables")
        
        # Create all tables
        db.create_all()
        print("  Created all tables")
        
        # Verify tables created
        from sqlalchemy import inspect
        inspector = inspect(db.engine)
        tables = inspector.get_table_names()
        print(f"  Tables created: {', '.join(tables)}")
    
    print("\n✅ FastAPI database initialized successfully!")
    print(f"   Location: {fastapi_db_path}")
    print("\nNote: This database is separate from Flask's database during migration.")


def init_test_database():
    """Initialize test database for FastAPI tests."""
    # Create Flask app to get database models
    app = create_app()
    
    # Override database path for FastAPI tests
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    test_db_path = os.path.join(base_dir, 'src', 'instance', 'fastapi_test.db')
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{test_db_path}'
    
    print(f"\nInitializing FastAPI test database at: {test_db_path}")
    
    with app.app_context():
        # Drop existing tables
        db.drop_all()
        
        # Create all tables
        db.create_all()
        print("  ✅ Test database initialized")
    
    return test_db_path


if __name__ == '__main__':
    print("=" * 70)
    print("FastAPI Database Initialization")
    print("=" * 70)
    
    # Initialize main FastAPI database
    init_fastapi_database()
    
    # Initialize test database
    init_test_database()
    
    print("\n" + "=" * 70)
    print("Both databases are now ready for FastAPI migration!")
    print("=" * 70)
