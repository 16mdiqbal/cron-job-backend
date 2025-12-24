#!/bin/bash

# Database Initialization Script
# This script initializes the DB schema and creates a default admin user (FastAPI-only).
# Usage: ./initialize_db.sh

echo "=========================================="
echo "Initializing Database and Admin User"
echo "=========================================="
echo ""

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

# Activate virtual environment
if [[ -f "$ROOT_DIR/venv/bin/activate" ]]; then
  source "$ROOT_DIR/venv/bin/activate"
fi

# Run the initialization script
echo "Running initialization script..."
python create_admin.py

echo ""
echo "=========================================="
echo "✅ Database initialization complete!"
echo "=========================================="
