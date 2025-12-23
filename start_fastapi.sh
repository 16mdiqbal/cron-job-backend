#!/bin/bash

# FastAPI Server Startup Script
# Cutover default: run FastAPI on port 5001 (Flask replacement).
# To run alongside Flask, set FASTAPI_PORT=8001 (or any free port).

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}🚀 Starting FastAPI Server...${NC}"

# Get the directory where the script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Activate virtual environment if it exists
if [ -d "$SCRIPT_DIR/venv" ]; then
    echo -e "${YELLOW}📦 Activating virtual environment...${NC}"
    source "$SCRIPT_DIR/venv/bin/activate"
elif [ -d "$SCRIPT_DIR/../venv" ]; then
    echo -e "${YELLOW}📦 Activating virtual environment...${NC}"
    source "$SCRIPT_DIR/../venv/bin/activate"
fi

# Set default port
PORT=${FASTAPI_PORT:-5001}
HOST=${FASTAPI_HOST:-0.0.0.0}

# Scheduler ownership (Phase 8 cutover): enable scheduler by default for FastAPI.
export SCHEDULER_ENABLED=${SCHEDULER_ENABLED:-true}
export TESTING=${TESTING:-false}
mkdir -p "$SCRIPT_DIR/src/instance"
export SCHEDULER_LOCK_PATH=${SCHEDULER_LOCK_PATH:-"$SCRIPT_DIR/src/instance/scheduler.lock"}

# Check if port is already in use
if lsof -Pi :$PORT -sTCP:LISTEN -t >/dev/null 2>&1; then
    echo -e "${RED}❌ Port $PORT is already in use${NC}"
    echo -e "${YELLOW}To kill the process using port $PORT, run:${NC}"
    echo "  lsof -ti :$PORT | xargs kill -9"
    exit 1
fi

echo -e "${GREEN}📚 API Documentation will be available at:${NC}"
echo -e "   Swagger UI: http://localhost:$PORT/docs"
echo -e "   ReDoc:      http://localhost:$PORT/redoc"
echo -e "   Health:     http://localhost:$PORT/api/v2/health"
echo ""

# Run uvicorn
echo -e "${GREEN}▶️  Starting uvicorn on port $PORT...${NC}"
cd "$SCRIPT_DIR"

# Development mode with hot reload
uvicorn src.fastapi_app.main:app \
    --host $HOST \
    --port $PORT \
    --reload \
    --reload-dir src \
    --log-level info
