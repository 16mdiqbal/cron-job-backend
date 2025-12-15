#!/bin/bash

# Database Initialization Script
# This script initializes the database and creates the default admin user
# Usage: ./initialize_db.sh

echo "=========================================="
echo "Initializing Database and Admin User"
echo "=========================================="
echo ""

cd /Users/mohammadiqbal/Documents/Workspace/cron-job-backend

# Activate virtual environment
source venv/bin/activate

# Clean up old database files
echo "Cleaning up old database files..."
rm -f cron_jobs.db 2>/dev/null || true
rm -f instance/cron_jobs.db 2>/dev/null || true

# Ensure the correct database directory exists
mkdir -p src/instance

echo "✓ Cleaned up old database files"
echo ""

# Run the initialization script
echo "Running initialization script..."
python create_admin.py

echo ""
echo "=========================================="
echo "✅ Database initialization complete!"
echo "=========================================="
