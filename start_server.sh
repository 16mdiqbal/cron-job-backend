#!/bin/bash

# Stop any existing server
echo "Stopping any existing Flask server..."
pkill -f "python -m src.app" 2>/dev/null || true
sleep 1

# Clean up old database instances from different locations to avoid confusion
echo "Cleaning up old database files from root directory..."
rm -f /Users/mohammadiqbal/Documents/Workspace/cron-job-backend/cron_jobs.db 2>/dev/null || true
rm -f /Users/mohammadiqbal/Documents/Workspace/cron-job-backend/instance/cron_jobs.db 2>/dev/null || true

# Ensure the correct database directory exists
mkdir -p /Users/mohammadiqbal/Documents/Workspace/cron-job-backend/src/instance

# Start the server
echo "Starting Flask server..."
cd /Users/mohammadiqbal/Documents/Workspace/cron-job-backend
source venv/bin/activate
python -m src.app &
SERVER_PID=$!

echo "Server started with PID: $SERVER_PID"
echo "Waiting 3 seconds for server to initialize..."
sleep 3

# Test if server is running
if curl -s http://localhost:5001/api/health > /dev/null 2>&1; then
    echo "✓ Server is running successfully on http://localhost:5001"
    echo ""
    echo "Default credentials:"
    echo "  Username: admin"
    echo "  Password: admin123"
    echo ""
    echo "To stop the server later, run: kill $SERVER_PID"
else
    echo "✗ Server failed to start. Check server.log for errors"
fi
