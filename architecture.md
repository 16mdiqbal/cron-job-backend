# Backend Architecture for Cron Job Scheduler

## Overview
This document outlines the architecture for a backend service built with Python (using Flask) and APScheduler to handle the scheduling of cron jobs and trigger GitHub Actions.

**Note (Migration):** FastAPI v2 is being introduced side-by-side. The migration plan and phase tracking live in `FASTAPI_MIGRATION_PLAN.md`, and the FastAPI code lives under `src/fastapi_app/` (served under `/api/v2/*`).

## Components

### 1. Framework
- **Flask**: A lightweight web framework for building RESTful APIs.
- **APScheduler**: A Python library to manage scheduled jobs.

### 2. Project Structure
project-root/
│
├── app.py # Main Flask application
├── scheduler/ # Folder for scheduling logic
│ ├── jobs.py # Job definitions and functions
│ └── init.py
│
├── requirements.txt # Project dependencies
└── README.md # Documentation


### 3. API Endpoints

- **`GET /api/jobs`**: List all scheduled jobs.
- **`POST /api/jobs`**: Create a new job (name, schedule, URL/command).
- **`GET /api/jobs/<job_id>`**: Retrieve details of a specific job.
- **`PUT /api/jobs/<job_id>`**: Update an existing job.
- **`DELETE /api/jobs/<job_id>`**: Delete a job.
- **`POST /api/jobs/<job_id>/trigger`**: Manually trigger a job immediately, initiating a GitHub Actions dispatch.

### 4. Job Scheduling and Execution

- **APScheduler Initialization**: Set up the scheduler when the Flask app starts.
- **Cron Expressions**: Allow jobs to be scheduled with cron expressions.
- **GitHub Actions Trigger**: On job execution, make a POST request to the GitHub API to trigger a workflow dispatch event.

### 5. Dependencies and Configuration

- **Dependencies**: Include Flask, APScheduler, and requests (for GitHub API calls) in `requirements.txt`.
- **Configuration**: Add configuration settings for job stores, logging, and GitHub API tokens as needed.

## Conclusion

This architecture provides a robust foundation for building your backend service. You can expand the endpoints and functionality as needed in the future.
