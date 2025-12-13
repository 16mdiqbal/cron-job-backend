#!/bin/bash

# Test Script for POST /api/jobs endpoint
API_URL="http://localhost:5001"

echo "===================================="
echo "Testing Cron Job Scheduler API"
echo "===================================="
echo ""

# Test 1: Health Check
echo "1. Testing Health Check Endpoint..."
curl -s "$API_URL/api/health" | python3 -m json.tool
echo ""
echo ""

# Test 2: Create a valid job
echo "2. Testing POST /api/jobs - Valid Job Creation..."
curl -s -X POST "$API_URL/api/jobs" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Daily Backup Job",
    "cron_expression": "0 2 * * *",
    "target_url": "https://httpbin.org/get"
  }' | python3 -m json.tool
echo ""
echo ""

# Test 3: Create another valid job (every 5 minutes)
echo "3. Testing POST /api/jobs - Another Valid Job..."
curl -s -X POST "$API_URL/api/jobs" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "5 Minute Check",
    "cron_expression": "*/5 * * * *",
    "target_url": "https://httpbin.org/status/200"
  }' | python3 -m json.tool
echo ""
echo ""

# Test 4: Invalid cron expression
echo "4. Testing POST /api/jobs - Invalid Cron Expression..."
curl -s -X POST "$API_URL/api/jobs" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Invalid Job",
    "cron_expression": "invalid cron",
    "target_url": "https://httpbin.org/get"
  }' | python3 -m json.tool
echo ""
echo ""

# Test 5: Missing required fields
echo "5. Testing POST /api/jobs - Missing Required Fields..."
curl -s -X POST "$API_URL/api/jobs" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Incomplete Job"
  }' | python3 -m json.tool
echo ""
echo ""

# Test 6: Empty name
echo "6. Testing POST /api/jobs - Empty Job Name..."
curl -s -X POST "$API_URL/api/jobs" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "",
    "cron_expression": "0 0 * * *",
    "target_url": "https://httpbin.org/get"
  }' | python3 -m json.tool
echo ""
echo ""

echo "===================================="
echo "Testing Complete!"
echo "===================================="
