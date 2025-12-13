#!/bin/bash

# Stop any existing server
echo "Stopping any existing Flask server..."
pkill -f "python app.py" 2>/dev/null || true
sleep 1

# Start the server
echo "Starting Flask server..."
cd /Users/mohammadiqbal/Documents/Workspace/cron-job-backend
source venv/bin/activate
python app.py &
SERVER_PID=$!

echo "Server started with PID: $SERVER_PID"
echo "Waiting 3 seconds for server to initialize..."
sleep 3

# Test if server is running
if curl -s http://localhost:5001/api/health > /dev/null 2>&1; then
    echo "✓ Server is running successfully on http://localhost:5001"
    echo ""
    echo "To stop the server later, run: kill $SERVER_PID"
else
    echo "✗ Server failed to start. Check server.log for errors"
fi
