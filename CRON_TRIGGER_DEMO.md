# Cron Job Automatic Trigger Demonstration Guide

## Overview

This guide demonstrates how APScheduler automatically triggers cron jobs based on their scheduling. You'll create a job that executes every 10 minutes and verify it triggers automatically by checking the execution history.

## Prerequisites

- Flask app running: `python -m src`
- Admin credentials: `username: admin`, `password: admin123`
- Default database location: `instance/cron_jobs.db`

## Quick Start (3 Steps)

### Step 1: Start the Flask Application

```bash
# Terminal 1: Start the app
python -m src
```

You should see output like:
```
 * Serving Flask app 'src.app'
 * Running on http://0.0.0.0:5001
 * Press CTRL+C to quit
```

Keep this running - APScheduler runs in the background within this process.

### Step 2: Create a Test Cron Job (Every 10 Minutes)

```bash
# Terminal 2: Run the demonstration script
./demo_cron_trigger.sh
```

This script will:
1. ✅ Authenticate with admin credentials
2. ✅ Create a job named "Demo-Every-10-Mins" with cron `*/10 * * * *`
3. ✅ Display the job ID and details
4. ✅ Show instructions for monitoring

**Output includes:**
- Job ID (save this)
- Confirmation that job is active
- Instructions for verification

### Step 3: Wait and Verify Execution

The job will automatically trigger at the next 10-minute interval (00, 10, 20, 30, 40, 50 minutes).

**Option A: Check Logs (Real-time)**

Watch Terminal 1 (Flask app) logs for:
```
Executing job 'Demo-Every-10-Mins' (ID: uuid) at 2025-12-13T14:20:00.000000+00:00
```

**Option B: Query Execution History (After Trigger)**

```bash
# Terminal 3: Verify execution history
./verify_cron_trigger.sh <JOB_ID>
```

Replace `<JOB_ID>` with the ID from Step 2.

This will show:
- ✅ Job details
- ✅ Execution count
- ✅ Execution status (success/failed)
- ✅ Database records

## Detailed Explanation: How It Works

### Timeline Example

```
Time: 14:00 AM  → App starts
                 → APScheduler loads all active jobs from database
                 → "Demo-Every-10-Mins" loaded with cron trigger (*/10 * * * *)
                 → APScheduler starts background thread

Time: 14:00-14:10 → APScheduler checks every second in background
                    → 14:00, 14:01, 14:02, ... = No match
                    → Continues silently

Time: 14:10:00 → APScheduler checks: Does current time match? YES!
                 → Executes job immediately
                 → Logs: "Executing job 'Demo-Every-10-Mins'..."
                 → Creates JobExecution record in database
                 → Sends webhook to target_url
                 → Next trigger: 14:20:00

Time: 14:10:01-14:20:00 → Continues checking, no match

Time: 14:20:00 → MATCH! Executes again
                 → Creates another JobExecution record
                 → And so on...
```

### Architecture Flow

```
DATABASE (Persistent Storage)
│
├─ jobs table
│  └─ "Demo-Every-10-Mins" with cron_expression = "*/10 * * * *"
│
└─ job_executions table
   ├─ Execution 1 at 14:10:00 → status: success
   ├─ Execution 2 at 14:20:00 → status: success
   └─ Execution 3 at 14:30:00 → status: success
      
MEMORY (App Process)
│
├─ APScheduler (Background Thread)
│  └─ Continuous Loop:
│     - Check current time every 1 second
│     - Compare against loaded job triggers
│     - If match → execute_job()
│
└─ CronTrigger Objects
   └─ "Demo-Every-10-Mins" trigger
      ├─ Parsed: "every 10 minutes"
      ├─ Next run: 14:10:00 (updated after each execution)
      └─ Status: Active

API Endpoints (Verification)
│
├─ GET /api/jobs/{id}/executions
│  └─ Returns list of all executions for this job
│
└─ GET /api/jobs/{id}/execution-stats
   └─ Returns statistics (total, successful, failed, average duration)
```

## Verification Methods

### Method 1: App Logs (Real-time, Immediate)

Watch the terminal where Flask is running. Look for:

```
INFO:apscheduler.executors.default:Executing job 'Demo-Every-10-Mins' (ID: abc-def-123) at 2025-12-13T14:20:00.000000+00:00
```

**Pros:** See execution in real-time  
**Cons:** Only visible while app is running

### Method 2: Execution History API

```bash
# Get execution history for the job
curl -X GET http://localhost:5001/api/jobs/{JOB_ID}/executions \
  -H "Authorization: Bearer {TOKEN}"
```

**Response Example:**
```json
{
  "executions": [
    {
      "id": "exec-1",
      "job_id": "job-id",
      "status": "success",
      "trigger_type": "scheduled",
      "duration_seconds": 0.5,
      "response_status_code": 200,
      "output": "Webhook triggered successfully",
      "created_at": "2025-12-13T14:20:15.123456+00:00"
    },
    {
      "id": "exec-2",
      "job_id": "job-id",
      "status": "success",
      "trigger_type": "scheduled",
      "duration_seconds": 0.45,
      "response_status_code": 200,
      "output": "Webhook triggered successfully",
      "created_at": "2025-12-13T14:30:15.654321+00:00"
    }
  ]
}
```

### Method 3: Execution Statistics

```bash
# Get execution statistics
curl -X GET http://localhost:5001/api/jobs/{JOB_ID}/execution-stats \
  -H "Authorization: Bearer {TOKEN}"
```

**Response Example:**
```json
{
  "total_executions": 3,
  "successful_executions": 3,
  "failed_executions": 0,
  "average_duration": 0.48,
  "last_execution": "2025-12-13T14:30:15.654321+00:00"
}
```

### Method 4: Direct Database Query

```bash
# View job record
sqlite3 instance/cron_jobs.db \
  "SELECT id, name, cron_expression, is_active FROM jobs WHERE name='Demo-Every-10-Mins';"

# View all executions
sqlite3 instance/cron_jobs.db \
  "SELECT id, status, trigger_type, duration_seconds, created_at FROM job_executions WHERE job_id='<JOB_ID>' ORDER BY created_at DESC;"

# Count executions by status
sqlite3 instance/cron_jobs.db \
  "SELECT status, COUNT(*) FROM job_executions WHERE job_id='<JOB_ID>' GROUP BY status;"
```

## Expected Results

After waiting for 10+ minutes:

| Verification Method | Expected Result |
|---|---|
| **App Logs** | "Executing job 'Demo-Every-10-Mins'" appears at :00, :10, :20, :30, etc. |
| **Executions API** | Array contains at least 1-2 execution records |
| **Stats API** | `total_executions ≥ 1`, `successful_executions ≥ 1` |
| **Database** | `job_executions` table has records for this job_id |

## Troubleshooting

### Issue: Job Doesn't Trigger

**Check 1: Is the app running?**
```bash
# App should be running with this output
python -m src
# Output: Running on http://0.0.0.0:5001
```

**Check 2: Is APScheduler enabled?**
```bash
# Default is true, unless SCHEDULER_ENABLED=false
echo $SCHEDULER_ENABLED  # Should be empty or "true"
```

**Check 3: Is the job active?**
```bash
sqlite3 instance/cron_jobs.db "SELECT is_active FROM jobs WHERE name='Demo-Every-10-Mins';"
# Should return: 1 (true)
```

**Check 4: Is the cron expression valid?**
```bash
sqlite3 instance/cron_jobs.db "SELECT cron_expression FROM jobs WHERE name='Demo-Every-10-Mins';"
# Should return: */10 * * * *
```

### Issue: Execution Records Don't Appear

**Wait longer:** Execution records only appear when the cron time matches. The job triggers at :00, :10, :20, :30, :40, :50 minutes.

**Current time:** Check what minute you're at
```bash
date +%M  # Shows current minute
```

**Time until next trigger:** If current time is 14:23, job triggers at 14:30 (wait 7 minutes).

### Issue: App Stops and Jobs Stop Triggering

**Reason:** APScheduler runs in the Flask app process. If app stops, scheduler stops.

**Solution:** Restart the app
```bash
# Stop current app (Ctrl+C)
# Start again
python -m src
```

The jobs will reload from the database and resume triggering at the next interval.

## Advanced Testing

### Test with Different Cron Expressions

```bash
# Every minute (for faster testing)
curl -X POST http://localhost:5001/api/jobs \
  -H "Authorization: Bearer {TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Test-Every-Minute",
    "cron_expression": "* * * * *",
    "target_url": "https://webhook.site/test",
    "enable_email_notifications": false
  }'

# Every 5 minutes
curl -X POST http://localhost:5001/api/jobs \
  -H "Authorization: Bearer {TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Test-Every-5-Mins",
    "cron_expression": "*/5 * * * *",
    "target_url": "https://webhook.site/test",
    "enable_email_notifications": false
  }'
```

### Observe Multiple Concurrent Executions

Create jobs with different triggers and watch them execute at the same time:
- Job A: Every 20 minutes (00, 20, 40)
- Job B: Every 30 minutes (00, 30)

At minute 00: Both execute simultaneously ✓

### Monitor APScheduler Performance

Add this to your app startup to log scheduler info:

```python
# In src/app.py
logger.info(f"Scheduler running: {scheduler.running}")
logger.info(f"Active jobs: {len(scheduler.get_jobs())}")
for job in scheduler.get_jobs():
    logger.info(f"  - {job.name}: {job.trigger} (next run: {job.next_run_time})")
```

## Summary

**What You've Verified:**
✅ APScheduler continuously checks cron times every second  
✅ When time matches, job triggers automatically  
✅ Execution is logged and recorded in database  
✅ Execution history is accessible via API  
✅ Jobs persist across app restarts  

**Key Takeaway:**
The automatic triggering happens because:
1. APScheduler loads jobs from DB at startup
2. It runs a background thread that checks every second
3. When current time matches cron expression → job executes
4. Execution is recorded and accessible via API

No manual intervention needed - set it and forget it! 🚀
