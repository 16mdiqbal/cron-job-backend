# 🎯 Quick Start: Automatic Cron Trigger Demonstration

## What You'll Do

Create a test job that triggers **every 10 minutes** and verify it works automatically!

## 3-Step Quick Start

### Step 1️⃣: Start the Flask App

```bash
python -m src
```

**Output:**
```
 * Running on http://0.0.0.0:5001
```

Leave this running in one terminal.

---

### Step 2️⃣: Create the Test Job

In a **new terminal**, run:

```bash
./demo_cron_trigger.sh
```

**Output will show:**
- ✅ Admin authentication
- ✅ Job created: "Demo-Every-10-Mins"
- ✅ Job ID (copy this!)
- ✅ Instructions for verification

---

### Step 3️⃣: Verify It Works

**Wait for the next 10-minute interval**, then verify in a **third terminal**:

```bash
# Use the JOB_ID from Step 2
./verify_cron_trigger.sh <JOB_ID>
```

**Example:**
```bash
./verify_cron_trigger.sh a1b2c3d4-e5f6-g7h8-i9j0-k1l2m3n4o5p6
```

**Output shows:**
- ✅ Job details
- ✅ Execution count
- ✅ Execution history
- ✅ Database records

---

## What to Watch For

### In Flask App Terminal (Terminal 1)

Look for this when job triggers:

```
INFO:apscheduler.executors.default:Executing job 'Demo-Every-10-Mins' at 14:20:00
```

### Execution Timeline

| Time | Status |
|------|--------|
| 14:00 - 14:09 | Waiting (APScheduler checking every second) |
| **14:10:00** | **TRIGGER!** ✅ Execution recorded |
| 14:10 - 14:19 | Waiting |
| **14:20:00** | **TRIGGER!** ✅ Execution recorded |
| 14:20 - 14:29 | Waiting |
| **14:30:00** | **TRIGGER!** ✅ Execution recorded |

---

## Verification Summary

### ✅ Verification Points

1. **App Logs**
   - Watch Flask terminal for "Executing job" messages
   - Appears at :00, :10, :20, :30, :40, :50 minutes

2. **Execution History API**
   - Returns list of all times job triggered
   - Shows status: `success` or `failed`
   - Shows duration and response codes

3. **Execution Statistics**
   - `total_executions` increases
   - `successful_executions` increases
   - `average_duration` calculated

4. **Database Records**
   - `jobs` table: Job definition
   - `job_executions` table: Execution history
   - One record per trigger event

---

## Files Created for This Demo

| File | Purpose |
|------|---------|
| **demo_cron_trigger.sh** | Creates test job and shows setup |
| **verify_cron_trigger.sh** | Queries execution history and stats |
| **CRON_TRIGGER_DEMO.md** | Detailed guide with troubleshooting |

---

## Cron Expression Reference

The test job uses: **`*/10 * * * *`**

| Expression | Meaning | Example Trigger Times |
|---|---|---|
| `* * * * *` | Every minute | 14:00, 14:01, 14:02, ... |
| `*/5 * * * *` | Every 5 minutes | 14:00, 14:05, 14:10, 14:15, ... |
| `*/10 * * * *` | Every 10 minutes | 14:00, 14:10, 14:20, 14:30, ... |
| `0 * * * *` | Every hour | 14:00, 15:00, 16:00, ... |
| `0 2 * * *` | Daily at 2 AM | 2:00 AM every day |

---

## Troubleshooting

### ❌ Job Doesn't Trigger After 15 Minutes?

1. **Check Flask is running:**
   ```bash
   # In terminal 1, should see: Running on http://0.0.0.0:5001
   ```

2. **Check job is active:**
   ```bash
   sqlite3 instance/cron_jobs.db "SELECT name, is_active FROM jobs WHERE name='Demo-Every-10-Mins';"
   # Should show: Demo-Every-10-Mins|1
   ```

3. **Check cron expression:**
   ```bash
   sqlite3 instance/cron_jobs.db "SELECT cron_expression FROM jobs WHERE name='Demo-Every-10-Mins';"
   # Should show: */10 * * * *
   ```

4. **Check current minute:**
   ```bash
   date +%M
   # If shows 23, job triggers at :30 (wait 7 mins)
   ```

### ❌ Executions Show 0?

**Reason:** Jobs only record executions when they actually trigger.

**Wait for:** Next :00, :10, :20, :30, :40, or :50 minute mark

**Example:**
- Current time: 14:18
- Next trigger: 14:20 (wait 2 minutes)
- Then execute: `./verify_cron_trigger.sh <JOB_ID>`

---

## How It Actually Works

### Memory-Based Checking (Super Efficient!)

```
APScheduler Background Thread (runs continuously):
  
  Every 1 second:
    current_time = now()  // e.g., 14:20:00
    
    for each job in scheduler.jobs:
      if job.cron_trigger matches current_time:
        execute_job()  // Trigger!
        record execution in database
        
    sleep(1 second)
```

### Why It's Automatic

✅ Loaded from database at startup  
✅ Stored in memory as CronTrigger objects  
✅ Checked continuously every second  
✅ Triggered immediately on match  
✅ No polling, no delays, no external service needed  

---

## Next Steps

After verification:

1. ✅ Try different cron expressions (see reference above)
2. ✅ Create multiple jobs and watch them trigger simultaneously
3. ✅ Enable email notifications to get alerts
4. ✅ Use GitHub Actions as target instead of webhook
5. ✅ Monitor execution history and statistics

---

## API Endpoints Used

```bash
# Create job
curl -X POST http://localhost:5001/api/jobs \
  -H "Authorization: Bearer {TOKEN}" \
  -d '{"name": "...", "cron_expression": "*/10 * * * *", ...}'

# Get execution history
curl -X GET http://localhost:5001/api/jobs/{JOB_ID}/executions \
  -H "Authorization: Bearer {TOKEN}"

# Get execution stats
curl -X GET http://localhost:5001/api/jobs/{JOB_ID}/execution-stats \
  -H "Authorization: Bearer {TOKEN}"
```

---

## Summary

✅ **Automatic:** APScheduler continuously checks cron times  
✅ **Reliable:** Jobs trigger at scheduled intervals  
✅ **Verifiable:** Full execution history in database  
✅ **Scalable:** Handles multiple jobs simultaneously  

**Start with:** `./demo_cron_trigger.sh` 🚀
