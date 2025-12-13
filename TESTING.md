# Testing Guide for Cron Job Scheduler API

## Step 1: Start the Server

Open a terminal and run:

```bash
cd /Users/mohammadiqbal/Documents/Workspace/cron-job-backend
source venv/bin/activate
python app.py
```

Keep this terminal open - the server will run here. You should see:
```
Database tables created successfully
APScheduler started successfully
Running on http://127.0.0.1:5001
```

## Step 2: Open a New Terminal for Testing

Open a **second terminal** window to run test commands.

## Test Commands

### 1. Health Check
```bash
curl http://localhost:5001/api/health
```

**Expected Response:**
```json
{"scheduled_jobs_count": 0, "scheduler_running": true, "status": "healthy"}
```

---

### 2. Create a Valid Job (Every 5 Minutes)
```bash
curl -X POST http://localhost:5001/api/jobs \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Test Job Every 5 Minutes",
    "cron_expression": "*/5 * * * *",
    "target_url": "https://httpbin.org/get"
  }'
```

**Expected Response (201):**
```json
{
  "job": {
    "cron_expression": "*/5 * * * *",
    "created_at": "2025-12-12T...",
    "id": "uuid-here",
    "is_active": true,
    "name": "Test Job Every 5 Minutes",
    "target_url": "https://httpbin.org/get",
    "updated_at": "2025-12-12T..."
  },
  "message": "Job created successfully"
}
```

---

### 3. Create Another Job (Daily at 2 AM)
```bash
curl -X POST http://localhost:5001/api/jobs \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Daily Backup",
    "cron_expression": "0 2 * * *",
    "target_url": "https://httpbin.org/status/200"
  }'
```

---

### 4. Test Invalid Cron Expression (Should Fail)
```bash
curl -X POST http://localhost:5001/api/jobs \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Invalid Job",
    "cron_expression": "this is not a cron",
    "target_url": "https://httpbin.org/get"
  }'
```

**Expected Response (400):**
```json
{
  "error": "Invalid cron expression",
  "message": "Please provide a valid cron expression (e.g., \"*/5 * * * *\" for every 5 minutes)"
}
```

---

### 5. Test Missing Required Fields (Should Fail)
```bash
curl -X POST http://localhost:5001/api/jobs \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Incomplete Job"
  }'
```

**Expected Response (400):**
```json
{
  "error": "Missing required fields",
  "missing_fields": ["cron_expression", "target_url"]
}
```

---

### 6. Test Empty Job Name (Should Fail)
```bash
curl -X POST http://localhost:5001/api/jobs \
  -H "Content-Type: application/json" \
  -d '{
    "name": "",
    "cron_expression": "0 0 * * *",
    "target_url": "https://httpbin.org/get"
  }'
```

**Expected Response (400):**
```json
{
  "error": "Job name cannot be empty"
}
```

---

## Common Cron Expression Examples

- `*/5 * * * *` - Every 5 minutes
- `0 * * * *` - Every hour (at minute 0)
- `0 0 * * *` - Daily at midnight
- `0 2 * * *` - Daily at 2:00 AM
- `0 0 * * 0` - Weekly on Sunday at midnight
- `0 0 1 * *` - Monthly on the 1st at midnight
- `*/15 9-17 * * 1-5` - Every 15 minutes, 9 AM to 5 PM, Monday to Friday

---

## Checking the Database

To see created jobs in the SQLite database:

```bash
cd /Users/mohammadiqbal/Documents/Workspace/cron-job-backend
sqlite3 cron_jobs.db "SELECT id, name, cron_expression, is_active FROM jobs;"
```

---

## Stopping the Server

Go back to the first terminal where the server is running and press **Ctrl+C**.

---

## Troubleshooting

If port 5001 is in use:
```bash
lsof -i :5001
# Then kill the process: kill -9 <PID>
```

Check server logs:
```bash
tail -f /Users/mohammadiqbal/Documents/Workspace/cron-job-backend/server.log
```
