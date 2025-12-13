#!/bin/bash

# ============================================================================
# VERIFICATION SCRIPT: Check Job Execution History
# ============================================================================
# Run this script AFTER the cron job has been triggered to verify execution
# ============================================================================

BASE_URL="http://localhost:5001"
JOB_ID="${1:-}"

if [ -z "$JOB_ID" ]; then
  echo "Usage: $0 <JOB_ID>"
  echo ""
  echo "Example: $0 uuid-1234-5678"
  echo ""
  echo "Or get the job ID from: curl -s http://localhost:5001/api/jobs -H 'Authorization: Bearer <token>' | jq '.jobs[] | select(.name == \"Demo-Every-10-Mins\") | .id'"
  exit 1
fi

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${BLUE}========================================================================${NC}"
echo -e "${BLUE}        VERIFYING CRON JOB EXECUTION${NC}"
echo -e "${BLUE}========================================================================${NC}"
echo ""

# Get admin token
echo -e "${YELLOW}Getting authentication token...${NC}"
LOGIN_RESPONSE=$(curl -s -X POST "$BASE_URL/api/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "admin",
    "password": "admin123"
  }')

TOKEN=$(echo $LOGIN_RESPONSE | grep -o '"access_token":"[^"]*' | cut -d'"' -f4)

if [ -z "$TOKEN" ]; then
  echo -e "${RED}Failed to get token${NC}"
  exit 1
fi

echo -e "${GREEN}✓ Authenticated${NC}"
echo ""

# ============================================================================
# Get job details
# ============================================================================
echo -e "${YELLOW}[1] Job Details:${NC}"
JOB_DETAILS=$(curl -s -X GET "$BASE_URL/api/jobs/$JOB_ID" \
  -H "Authorization: Bearer $TOKEN")

echo "$JOB_DETAILS" | jq '{
  id: .id,
  name: .name,
  cron_expression: .cron_expression,
  is_active: .is_active,
  created_at: .created_at,
  target_url: .target_url
}'
echo ""

# ============================================================================
# Get execution history
# ============================================================================
echo -e "${YELLOW}[2] Execution History:${NC}"
EXECUTIONS=$(curl -s -X GET "$BASE_URL/api/jobs/$JOB_ID/executions" \
  -H "Authorization: Bearer $TOKEN")

EXECUTION_COUNT=$(echo "$EXECUTIONS" | jq '.executions | length')

if [ "$EXECUTION_COUNT" -eq 0 ]; then
  echo -e "${YELLOW}No executions yet. Wait for the next 10-minute interval.${NC}"
else
  echo -e "${GREEN}✓ Found $EXECUTION_COUNT execution(s):${NC}"
  echo ""
  echo "$EXECUTIONS" | jq '.executions[] | {
    id: .id,
    status: .status,
    trigger_type: .trigger_type,
    duration_seconds: .duration_seconds,
    response_status_code: .response_status_code,
    created_at: .created_at
  }'
fi
echo ""

# ============================================================================
# Get execution statistics
# ============================================================================
echo -e "${YELLOW}[3] Execution Statistics:${NC}"
STATS=$(curl -s -X GET "$BASE_URL/api/jobs/$JOB_ID/execution-stats" \
  -H "Authorization: Bearer $TOKEN")

echo "$STATS" | jq '{
  total_executions: .total_executions,
  successful_executions: .successful_executions,
  failed_executions: .failed_executions,
  average_duration: .average_duration,
  last_execution: .last_execution
}'
echo ""

# ============================================================================
# Show database info
# ============================================================================
echo -e "${BLUE}========================================================================${NC}"
echo -e "${YELLOW}[4] Database Verification:${NC}"
echo -e "${BLUE}========================================================================${NC}"
echo ""

if [ -f "instance/cron_jobs.db" ]; then
  echo -e "${GREEN}SQLite Database Records:${NC}"
  echo ""
  
  echo -e "${BLUE}Job Record:${NC}"
  sqlite3 instance/cron_jobs.db "SELECT id, name, cron_expression, is_active, created_at FROM jobs WHERE id='$JOB_ID';" 2>/dev/null || echo "Could not query job"
  echo ""
  
  echo -e "${BLUE}Execution Records (All):${NC}"
  sqlite3 instance/cron_jobs.db "SELECT id, job_id, status, trigger_type, duration_seconds, response_status_code, created_at FROM job_executions WHERE job_id='$JOB_ID' ORDER BY created_at DESC;" 2>/dev/null || echo "No executions found"
  echo ""
  
  echo -e "${BLUE}Execution Count by Status:${NC}"
  sqlite3 instance/cron_jobs.db "SELECT status, COUNT(*) as count FROM job_executions WHERE job_id='$JOB_ID' GROUP BY status;" 2>/dev/null || echo "Could not count executions"
  echo ""
fi

echo -e "${BLUE}========================================================================${NC}"
echo -e "${GREEN}Verification Complete!${NC}"
echo -e "${BLUE}========================================================================${NC}"
