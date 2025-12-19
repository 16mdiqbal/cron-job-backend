#!/bin/bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Stop any existing server (optional)
if [[ "${STOP_EXISTING:-true}" == "true" ]]; then
  echo "Stopping any existing Flask server..."
  pkill -f "python -m src.app" 2>/dev/null || true
  sleep 1
fi

# IMPORTANT: do not wipe DB by default.
# If you really want to wipe, run:
#   WIPE_DB=true ./start_server.sh
if [[ "${WIPE_DB:-false}" == "true" ]]; then
  echo "WIPE_DB=true: removing legacy DB files (not src/instance)"
  rm -f "$ROOT_DIR/cron_jobs.db" 2>/dev/null || true
  rm -f "$ROOT_DIR/instance/cron_jobs.db" 2>/dev/null || true
fi

# Ensure the correct database directory exists
mkdir -p "$ROOT_DIR/src/instance"

# Start the server
echo "Starting Flask server..."
cd "$ROOT_DIR"
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
