#!/bin/bash

# ============================================================================
# DEMONSTRATION: Automatic Cron Job Triggering with APScheduler
# ============================================================================
# This script demonstrates:
# 1. Creating a job with cron expression (every 10 minutes)
# 2. APScheduler automatically triggering it at the scheduled time
# 3. Verifying execution history via API endpoint
# ============================================================================

set -e

BASE_URL="http://localhost:5001"
ADMIN_TOKEN=""
JOB_ID=""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}========================================================================${NC}"
echo -e "${BLUE}        CRON JOB AUTOMATIC TRIGGER DEMONSTRATION${NC}"
echo -e "${BLUE}========================================================================${NC}"
echo ""

# ============================================================================
# STEP 1: Login and get admin token
# ============================================================================
echo -e "${YELLOW}[STEP 1]${NC} Getting admin authentication token..."
LOGIN_RESPONSE=$(curl -s -X POST "$BASE_URL/api/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "admin",
    "password": "admin123"
  }')

ADMIN_TOKEN=$(echo $LOGIN_RESPONSE | grep -o '"access_token":"[^"]*' | cut -d'"' -f4)

if [ -z "$ADMIN_TOKEN" ]; then
  echo -e "${RED}❌ Failed to get auth token${NC}"
  echo "Response: $LOGIN_RESPONSE"
  exit 1
fi

echo -e "${GREEN}✓ Admin token obtained${NC}"
echo ""

# ============================================================================
# STEP 2: Create a test job that triggers every 10 minutes
# ============================================================================
echo -e "${YELLOW}[STEP 2]${NC} Creating a test job with cron: '*/10 * * * *' (every 10 minutes)..."
CREATE_RESPONSE=$(curl -s -X POST "$BASE_URL/api/jobs" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -d '{
    "name": "Demo-Every-10-Mins",
    "cron_expression": "*/10 * * * *",
    "target_url": "https://webhook.site/unique-id-for-demo",
    "enable_email_notifications": false
  }')

JOB_ID=$(echo $CREATE_RESPONSE | grep -o '"id":"[^"]*' | head -1 | cut -d'"' -f4)

if [ -z "$JOB_ID" ]; then
  echo -e "${RED}❌ Failed to create job${NC}"
  echo "Response: $CREATE_RESPONSE"
  exit 1
fi

echo -e "${GREEN}✓ Job created successfully${NC}"
echo -e "  Job ID: ${BLUE}$JOB_ID${NC}"
echo -e "  Cron Expression: ${BLUE}*/10 * * * *${NC}"
echo ""

# ============================================================================
# STEP 3: Display job details
# ============================================================================
echo -e "${YELLOW}[STEP 3]${NC} Retrieving job details..."
JOB_DETAILS=$(curl -s -X GET "$BASE_URL/api/jobs/$JOB_ID" \
  -H "Authorization: Bearer $ADMIN_TOKEN")

echo -e "${GREEN}✓ Job Details:${NC}"
echo "$JOB_DETAILS" | grep -o '"name":"[^"]*\|"cron_expression":"[^"]*\|"is_active":[^,}]*\|"created_at":"[^"]*' | sed 's/^/  /'
echo ""

# ============================================================================
# STEP 4: Instructions for monitoring
# ============================================================================
echo -e "${BLUE}========================================================================${NC}"
echo -e "${YELLOW}⏱️  MONITORING INSTRUCTIONS${NC}"
echo -e "${BLUE}========================================================================${NC}"
echo ""
echo -e "${BLUE}Now the job is created and APScheduler will automatically trigger it:${NC}"
echo ""
echo -e "${GREEN}1. APP LOGS:${NC}"
echo "   The app will log when the trigger fires:"
echo -e "   ${BLUE}Executing job 'Demo-Every-10-Mins' (ID: $JOB_ID)${NC}"
echo ""
echo -e "${GREEN}2. TIMING:${NC}"
echo "   The job will trigger at times like:"
echo "   • 14:00, 14:10, 14:20, 14:30, 14:40, 14:50, 15:00, etc."
echo ""
echo "   Current time: $(date '+%H:%M:%S')"
CURRENT_MINUTES=$(($(date +%M) + 10))
if [ $CURRENT_MINUTES -ge 60 ]; then
  CURRENT_MINUTES=$((CURRENT_MINUTES - 60))
fi
echo "   Next trigger: Approximately XX:${printf "%02d" $CURRENT_MINUTES}:00"
echo ""
echo -e "${GREEN}3. VERIFY EXECUTION:${NC}"
echo "   After the job triggers (wait up to 10 minutes), run:"
echo ""
echo -e "   ${BLUE}curl -X GET '$BASE_URL/api/jobs/$JOB_ID/executions' \\${NC}"
echo -e "   ${BLUE}  -H 'Authorization: Bearer $ADMIN_TOKEN'${NC}"
echo ""
echo -e "${GREEN}4. CHECK EXECUTION STATISTICS:${NC}"
echo "   Or check execution stats:"
echo ""
echo -e "   ${BLUE}curl -X GET '$BASE_URL/api/jobs/$JOB_ID/execution-stats' \\${NC}"
echo -e "   ${BLUE}  -H 'Authorization: Bearer $ADMIN_TOKEN'${NC}"
echo ""
echo -e "${BLUE}========================================================================${NC}"
echo ""

# ============================================================================
# STEP 5: Show command for immediate verification
# ============================================================================
echo -e "${YELLOW}[OPTIONAL]${NC} Verify immediately (before first trigger):"
echo ""
echo -e "${BLUE}curl -X GET '$BASE_URL/api/jobs/$JOB_ID/executions' \\${NC}"
echo -e "${BLUE}  -H 'Authorization: Bearer $ADMIN_TOKEN' | jq .${NC}"
echo ""

# ============================================================================
# STEP 6: Call the endpoint to show current (empty) executions
# ============================================================================
echo -e "${YELLOW}[CHECKING]${NC} Current executions (should be empty initially)..."
EXECUTIONS=$(curl -s -X GET "$BASE_URL/api/jobs/$JOB_ID/executions" \
  -H "Authorization: Bearer $ADMIN_TOKEN")

echo "$EXECUTIONS" | grep -o '"executions":\[\]' > /dev/null && echo -e "${GREEN}✓ No executions yet (as expected)${NC}" || echo -e "${YELLOW}! Some executions exist${NC}"
echo ""

# ============================================================================
# STEP 7: Display what happens when job triggers
# ============================================================================
echo -e "${BLUE}========================================================================${NC}"
echo -e "${YELLOW}📊 WHAT WILL HAPPEN WHEN JOB TRIGGERS${NC}"
echo -e "${BLUE}========================================================================${NC}"
echo ""
echo -e "${GREEN}1. APScheduler Background Thread:${NC}"
echo "   - Checks every second if current time matches cron (*/10)"
echo "   - At 14:10:00, 14:20:00, 14:30:00, etc. → MATCH!"
echo "   - Calls execute_job() function"
echo ""
echo -e "${GREEN}2. Job Execution:${NC}"
echo "   - Creates JobExecution record in database"
echo "   - Sends HTTP POST to target_url (webhook)"
echo "   - Records response status code"
echo "   - Logs execution in app"
echo ""
echo -e "${GREEN}3. Database Changes:${NC}"
echo "   - New record in 'job_executions' table"
echo "   - Status: 'success' or 'failed'"
echo "   - Timestamp, duration, response code stored"
echo ""
echo -e "${GREEN}4. API Response:${NC}"
echo "   - GET /api/jobs/{id}/executions shows history"
echo "   - GET /api/jobs/{id}/execution-stats shows statistics"
echo ""

# ============================================================================
# STEP 8: Show database schema
# ============================================================================
echo -e "${BLUE}========================================================================${NC}"
echo -e "${YELLOW}🗄️  DATABASE VERIFICATION${NC}"
echo -e "${BLUE}========================================================================${NC}"
echo ""
echo -e "${GREEN}To verify in SQLite directly:${NC}"
echo ""
echo -e "${BLUE}# View the job:${NC}"
echo "sqlite3 instance/cron_jobs.db \"SELECT id, name, cron_expression, is_active FROM jobs WHERE name='Demo-Every-10-Mins';\"" 
echo ""
echo -e "${BLUE}# View executions (before first trigger):${NC}"
echo "sqlite3 instance/cron_jobs.db \"SELECT job_id, status, trigger_type, created_at FROM job_executions WHERE job_id='$JOB_ID';\"" 
echo ""
echo -e "${BLUE}# View executions (after job triggers - run after wait):${NC}"
echo "sqlite3 instance/cron_jobs.db \"SELECT status, trigger_type, duration_seconds, response_status_code FROM job_executions WHERE job_id='$JOB_ID' ORDER BY created_at DESC LIMIT 5;\"" 
echo ""

# ============================================================================
# STEP 9: Summary
# ============================================================================
echo -e "${BLUE}========================================================================${NC}"
echo -e "${YELLOW}✅ DEMONSTRATION SETUP COMPLETE${NC}"
echo -e "${BLUE}========================================================================${NC}"
echo ""
echo -e "${GREEN}Summary:${NC}"
echo -e "  • Job Created: ${BLUE}Demo-Every-10-Mins${NC}"
echo -e "  • Job ID: ${BLUE}$JOB_ID${NC}"
echo -e "  • Cron: ${BLUE}*/10 * * * *${NC} (every 10 minutes)"
echo -e "  • Status: ${BLUE}Active${NC}"
echo ""
echo -e "${GREEN}Next Steps:${NC}"
echo -e "  1. Keep the Flask app running (${BLUE}python -m src${NC})"
echo -e "  2. Watch the app logs for trigger events"
echo -e "  3. Wait for the next 10-minute interval"
echo -e "  4. See the execution in the logs and database"
echo -e "  5. Call the executions endpoint to verify"
echo ""
echo -e "${BLUE}========================================================================${NC}"
