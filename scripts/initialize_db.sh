#!/bin/bash

# Database Initialization Script
# This script initializes the DB schema and creates a default admin user (FastAPI-only).
# Usage: ./scripts/initialize_db.sh

echo "=========================================="
echo "Initializing Database and Admin User"
echo "=========================================="
echo ""

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$REPO_ROOT"

# Activate virtual environment
if [[ -f "$REPO_ROOT/venv/bin/activate" ]]; then
  source "$REPO_ROOT/venv/bin/activate"
fi

# Run the initialization script
echo "Running initialization script..."
python create_admin.py

echo ""
echo "=========================================="
echo "✅ Database initialization complete!"
echo "=========================================="
