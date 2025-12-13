-- MySQL Database Schema for Cron Job Backend
-- This schema is compatible with MySQL 5.7+
-- Created: December 13, 2025

-- Create database if not exists
CREATE DATABASE IF NOT EXISTS cron_job_backend;
USE cron_job_backend;

-- ============================================================================
-- Users Table
-- ============================================================================
-- Stores user accounts with authentication and role-based access control
CREATE TABLE IF NOT EXISTS users (
    id VARCHAR(36) PRIMARY KEY COMMENT 'UUID primary key',
    username VARCHAR(80) NOT NULL UNIQUE COMMENT 'Unique username',
    email VARCHAR(120) NOT NULL UNIQUE COMMENT 'Unique email address',
    password_hash VARCHAR(255) NOT NULL COMMENT 'PBKDF2-SHA256 password hash',
    role VARCHAR(20) NOT NULL DEFAULT 'viewer' COMMENT 'User role: admin, user, or viewer',
    is_active BOOLEAN NOT NULL DEFAULT TRUE COMMENT 'Whether the user account is active',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'Account creation timestamp',
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT 'Last update timestamp',
    
    -- Indexes for frequently queried columns
    INDEX idx_username (username),
    INDEX idx_email (email),
    INDEX idx_role (role),
    
    CHARSET=utf8mb4,
    COLLATE=utf8mb4_unicode_ci
) ENGINE=InnoDB COMMENT='User accounts table';

-- ============================================================================
-- Jobs Table
-- ============================================================================
-- Stores scheduled cron job configurations
CREATE TABLE IF NOT EXISTS jobs (
    id VARCHAR(36) PRIMARY KEY COMMENT 'UUID primary key',
    name VARCHAR(255) NOT NULL UNIQUE COMMENT 'Unique job name',
    cron_expression VARCHAR(100) NOT NULL COMMENT 'Cron expression for scheduling (e.g., "0 0 * * *")',
    
    -- Webhook target configuration (optional)
    target_url VARCHAR(500) COMMENT 'Generic webhook URL target',
    
    -- GitHub Actions configuration (optional)
    github_owner VARCHAR(255) COMMENT 'GitHub repository owner',
    github_repo VARCHAR(255) COMMENT 'GitHub repository name',
    github_workflow_name VARCHAR(255) COMMENT 'GitHub workflow file name',
    
    -- Job metadata (stored as JSON)
    job_metadata LONGTEXT COMMENT 'JSON metadata for the job',
    
    -- Email notification settings
    enable_email_notifications BOOLEAN NOT NULL DEFAULT FALSE COMMENT 'Whether to send email notifications',
    notification_emails TEXT COMMENT 'Comma-separated list of notification email addresses',
    notify_on_success BOOLEAN NOT NULL DEFAULT FALSE COMMENT 'Send emails on successful execution',
    
    -- Job ownership and status
    created_by VARCHAR(36) COMMENT 'UUID of user who created the job',
    is_active BOOLEAN NOT NULL DEFAULT TRUE COMMENT 'Whether the job is active/enabled',
    
    -- Timestamps
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'Job creation timestamp',
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT 'Last update timestamp',
    
    -- Indexes for frequently queried columns
    INDEX idx_name (name),
    INDEX idx_created_by (created_by),
    INDEX idx_is_active (is_active),
    INDEX idx_enable_email_notifications (enable_email_notifications),
    
    -- Foreign key constraint
    CONSTRAINT fk_jobs_created_by FOREIGN KEY (created_by) 
        REFERENCES users(id) ON DELETE SET NULL ON UPDATE CASCADE,
    
    CHARSET=utf8mb4,
    COLLATE=utf8mb4_unicode_ci
) ENGINE=InnoDB COMMENT='Scheduled cron jobs table';

-- ============================================================================
-- Job Executions Table
-- ============================================================================
-- Tracks execution history of all scheduled and manually triggered jobs
CREATE TABLE IF NOT EXISTS job_executions (
    id VARCHAR(36) PRIMARY KEY COMMENT 'UUID primary key',
    job_id VARCHAR(36) NOT NULL COMMENT 'Reference to the job',
    
    -- Execution status and type
    status VARCHAR(20) NOT NULL COMMENT 'Execution status: success, failed, running',
    trigger_type VARCHAR(20) NOT NULL COMMENT 'Trigger type: scheduled or manual',
    
    -- Execution timing
    started_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'Execution start time',
    completed_at TIMESTAMP NULL COMMENT 'Execution completion time',
    duration_seconds FLOAT COMMENT 'Total execution duration in seconds',
    
    -- Execution details
    execution_type VARCHAR(50) COMMENT 'Type of execution: github_actions or webhook',
    target VARCHAR(500) COMMENT 'Execution target (URL or GitHub workflow path)',
    response_status INT COMMENT 'HTTP response status code',
    error_message LONGTEXT COMMENT 'Error message if execution failed',
    output LONGTEXT COMMENT 'Execution output or response body',
    
    -- Indexes for frequently queried columns
    INDEX idx_job_id (job_id),
    INDEX idx_status (status),
    INDEX idx_trigger_type (trigger_type),
    INDEX idx_started_at (started_at),
    INDEX idx_job_id_started_at (job_id, started_at),
    
    -- Foreign key constraint with cascade delete
    CONSTRAINT fk_job_executions_job_id FOREIGN KEY (job_id) 
        REFERENCES jobs(id) ON DELETE CASCADE ON UPDATE CASCADE,
    
    CHARSET=utf8mb4,
    COLLATE=utf8mb4_unicode_ci
) ENGINE=InnoDB COMMENT='Job execution history table';

-- ============================================================================
-- Views for Common Queries
-- ============================================================================

-- View for job statistics
CREATE OR REPLACE VIEW job_statistics AS
SELECT 
    j.id,
    j.name,
    COUNT(je.id) as total_executions,
    SUM(CASE WHEN je.status = 'success' THEN 1 ELSE 0 END) as successful_executions,
    SUM(CASE WHEN je.status = 'failed' THEN 1 ELSE 0 END) as failed_executions,
    ROUND(
        (SUM(CASE WHEN je.status = 'success' THEN 1 ELSE 0 END) / COUNT(je.id)) * 100,
        2
    ) as success_rate,
    AVG(je.duration_seconds) as avg_duration_seconds,
    MAX(je.started_at) as last_execution_time
FROM jobs j
LEFT JOIN job_executions je ON j.id = je.job_id
GROUP BY j.id, j.name;

-- View for recent executions
CREATE OR REPLACE VIEW recent_executions AS
SELECT 
    je.id,
    je.job_id,
    j.name as job_name,
    je.status,
    je.trigger_type,
    je.started_at,
    je.completed_at,
    je.duration_seconds
FROM job_executions je
JOIN jobs j ON je.job_id = j.id
ORDER BY je.started_at DESC
LIMIT 100;

-- ============================================================================
-- Stored Procedures
-- ============================================================================

-- Procedure to get job execution statistics
DELIMITER $$

CREATE PROCEDURE GetJobStats(IN p_job_id VARCHAR(36))
BEGIN
    SELECT 
        j.id,
        j.name,
        j.cron_expression,
        j.is_active,
        COUNT(je.id) as total_executions,
        SUM(CASE WHEN je.status = 'success' THEN 1 ELSE 0 END) as successful_executions,
        SUM(CASE WHEN je.status = 'failed' THEN 1 ELSE 0 END) as failed_executions,
        ROUND(
            (SUM(CASE WHEN je.status = 'success' THEN 1 ELSE 0 END) / COUNT(je.id)) * 100,
            2
        ) as success_rate,
        AVG(je.duration_seconds) as avg_duration_seconds,
        MAX(je.started_at) as last_execution_time
    FROM jobs j
    LEFT JOIN job_executions je ON j.id = je.job_id
    WHERE j.id = p_job_id
    GROUP BY j.id, j.name, j.cron_expression, j.is_active;
END$$

DELIMITER ;

-- Procedure to cleanup old execution records
DELIMITER $$

CREATE PROCEDURE CleanupOldExecutions(IN p_days_to_keep INT)
BEGIN
    DELETE FROM job_executions
    WHERE created_at < DATE_SUB(NOW(), INTERVAL p_days_to_keep DAY);
END$$

DELIMITER ;

-- ============================================================================
-- Sample Data (Optional - for testing)
-- ============================================================================

-- Uncomment to insert sample data

-- -- Create sample users
-- INSERT INTO users (id, username, email, password_hash, role, is_active) VALUES
-- ('550e8400-e29b-41d4-a716-446655440001', 'admin', 'admin@example.com', 
--  '$pbkdf2-sha256$29000$...hash...', 'admin', TRUE),
-- ('550e8400-e29b-41d4-a716-446655440002', 'john_user', 'john@example.com', 
--  '$pbkdf2-sha256$29000$...hash...', 'user', TRUE);

-- -- Create sample jobs
-- INSERT INTO jobs (id, name, cron_expression, target_url, created_by, is_active) VALUES
-- ('660e8400-e29b-41d4-a716-446655440001', 'Daily Report', '0 9 * * *', 
--  'https://api.example.com/reports', '550e8400-e29b-41d4-a716-446655440001', TRUE),
-- ('660e8400-e29b-41d4-a716-446655440002', 'Hourly Sync', '0 * * * *', 
--  'https://api.example.com/sync', '550e8400-e29b-41d4-a716-446655440001', TRUE);

-- ============================================================================
-- Index Summary
-- ============================================================================
-- Users table indexes:
--   - idx_username: For fast user lookups by username
--   - idx_email: For fast user lookups by email
--   - idx_role: For filtering users by role
-- 
-- Jobs table indexes:
--   - idx_name: For fast job lookups by name
--   - idx_created_by: For finding jobs created by a user
--   - idx_is_active: For finding active/inactive jobs
--   - idx_enable_email_notifications: For notification queries
--
-- Job Executions table indexes:
--   - idx_job_id: For finding executions of a specific job
--   - idx_status: For filtering by execution status
--   - idx_trigger_type: For filtering by trigger type
--   - idx_started_at: For time-based queries
--   - idx_job_id_started_at: Composite index for job + time queries

-- ============================================================================
-- Configuration Notes
-- ============================================================================
-- 
-- Engine: InnoDB
--   - Supports FOREIGN KEY constraints
--   - ACID transactions
--   - Crash recovery
--
-- Character Set: utf8mb4 (supports all Unicode characters including emojis)
-- Collation: utf8mb4_unicode_ci (case-insensitive Unicode collation)
--
-- Timestamps: TIMESTAMP with CURRENT_TIMESTAMP and ON UPDATE
--   - created_at: Set once on creation
--   - updated_at: Auto-updated on every modification
--
-- UUIDs: VARCHAR(36) for UUID storage
--   - Stores as string for better human readability
--   - Can be converted to CHAR(36) for better performance
--
-- Foreign Keys:
--   - jobs.created_by -> users.id (ON DELETE SET NULL)
--   - job_executions.job_id -> jobs.id (ON DELETE CASCADE)
--
-- ============================================================================
