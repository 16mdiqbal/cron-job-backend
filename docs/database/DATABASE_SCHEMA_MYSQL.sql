-- MySQL Database Schema for cron-job-backend (FastAPI)
-- Compatibility: MySQL 5.7+ (InnoDB, utf8mb4)
--
-- This file is generated from the current SQLAlchemy models under `src/models/`.
-- For SQLite dev mode, schema is managed automatically on startup.
--
-- If you want a different database name, change it here (and in your deployment env).
+
+CREATE DATABASE IF NOT EXISTS `cron_job_backend` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
+USE `cron_job_backend`;
+
+-- --------------------------------------------------------------------------
+-- Table: job_categories
+-- --------------------------------------------------------------------------
+CREATE TABLE `job_categories` (
+  `id` VARCHAR(36) NOT NULL,
+  `slug` VARCHAR(100) NOT NULL,
+  `name` VARCHAR(255) NOT NULL,
+  `is_active` BOOL NOT NULL,
+  `created_at` DATETIME NOT NULL,
+  `updated_at` DATETIME NOT NULL,
+  PRIMARY KEY (`id`)
+) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
+
+CREATE UNIQUE INDEX `ix_job_categories_slug` ON `job_categories` (`slug`);
+
+-- --------------------------------------------------------------------------
+-- Table: pic_teams
+-- --------------------------------------------------------------------------
+CREATE TABLE `pic_teams` (
+  `id` VARCHAR(36) NOT NULL,
+  `slug` VARCHAR(100) NOT NULL,
+  `name` VARCHAR(255) NOT NULL,
+  `slack_handle` VARCHAR(255),
+  `is_active` BOOL NOT NULL,
+  `created_at` DATETIME NOT NULL,
+  `updated_at` DATETIME NOT NULL,
+  PRIMARY KEY (`id`)
+) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
+
+CREATE UNIQUE INDEX `ix_pic_teams_slug` ON `pic_teams` (`slug`);
+
+-- --------------------------------------------------------------------------
+-- Table: slack_settings
+-- --------------------------------------------------------------------------
+CREATE TABLE `slack_settings` (
+  `id` VARCHAR(36) NOT NULL,
+  `is_enabled` BOOL NOT NULL,
+  `webhook_url` TEXT,
+  `channel` VARCHAR(255),
+  `created_at` DATETIME NOT NULL,
+  `updated_at` DATETIME NOT NULL,
+  PRIMARY KEY (`id`)
+) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
+
+-- --------------------------------------------------------------------------
+-- Table: users
+-- --------------------------------------------------------------------------
+CREATE TABLE `users` (
+  `id` VARCHAR(36) NOT NULL,
+  `username` VARCHAR(80) NOT NULL,
+  `email` VARCHAR(120) NOT NULL,
+  `password_hash` VARCHAR(255) NOT NULL,
+  `role` VARCHAR(20) NOT NULL,
+  `is_active` BOOL NOT NULL,
+  `created_at` DATETIME,
+  `updated_at` DATETIME,
+  PRIMARY KEY (`id`)
+) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
+
+CREATE UNIQUE INDEX `ix_users_email` ON `users` (`email`);
+CREATE UNIQUE INDEX `ix_users_username` ON `users` (`username`);
+
+-- --------------------------------------------------------------------------
+-- Table: jobs
+-- --------------------------------------------------------------------------
+CREATE TABLE `jobs` (
+  `id` VARCHAR(36) NOT NULL,
+  `name` VARCHAR(255) NOT NULL,
+  `cron_expression` VARCHAR(100) NOT NULL,
+  `target_url` VARCHAR(500),
+  `github_owner` VARCHAR(255),
+  `github_repo` VARCHAR(255),
+  `github_workflow_name` VARCHAR(255),
+  `job_metadata` TEXT,
+  `category` VARCHAR(100) NOT NULL,
+  `end_date` DATE,
+  `pic_team` VARCHAR(100),
+  `enable_email_notifications` BOOL NOT NULL,
+  `notification_emails` TEXT,
+  `notify_on_success` BOOL NOT NULL,
+  `created_by` VARCHAR(36),
+  `is_active` BOOL NOT NULL,
+  `created_at` DATETIME NOT NULL,
+  `updated_at` DATETIME NOT NULL,
+  PRIMARY KEY (`id`),
+  UNIQUE (`name`),
+  FOREIGN KEY (`created_by`) REFERENCES `users` (`id`)
+) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
+
+-- --------------------------------------------------------------------------
+-- Table: user_notification_preferences
+-- --------------------------------------------------------------------------
+CREATE TABLE `user_notification_preferences` (
+  `id` VARCHAR(36) NOT NULL,
+  `user_id` VARCHAR(36) NOT NULL,
+  `email_on_job_success` BOOL NOT NULL,
+  `email_on_job_failure` BOOL NOT NULL,
+  `email_on_job_disabled` BOOL NOT NULL,
+  `browser_notifications` BOOL NOT NULL,
+  `daily_digest` BOOL NOT NULL,
+  `weekly_report` BOOL NOT NULL,
+  `created_at` DATETIME,
+  `updated_at` DATETIME,
+  PRIMARY KEY (`id`),
+  UNIQUE (`user_id`),
+  FOREIGN KEY (`user_id`) REFERENCES `users` (`id`)
+) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
+
+-- --------------------------------------------------------------------------
+-- Table: user_ui_preferences
+-- --------------------------------------------------------------------------
+CREATE TABLE `user_ui_preferences` (
+  `id` VARCHAR(36) NOT NULL,
+  `user_id` VARCHAR(36) NOT NULL,
+  `jobs_table_columns` TEXT,
+  `created_at` DATETIME NOT NULL,
+  `updated_at` DATETIME NOT NULL,
+  PRIMARY KEY (`id`),
+  UNIQUE (`user_id`),
+  FOREIGN KEY (`user_id`) REFERENCES `users` (`id`)
+) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
+
+-- --------------------------------------------------------------------------
+-- Table: job_executions
+-- --------------------------------------------------------------------------
+CREATE TABLE `job_executions` (
+  `id` VARCHAR(36) NOT NULL,
+  `job_id` VARCHAR(36) NOT NULL,
+  `status` VARCHAR(20) NOT NULL,
+  `trigger_type` VARCHAR(20) NOT NULL,
+  `started_at` DATETIME NOT NULL,
+  `completed_at` DATETIME,
+  `duration_seconds` FLOAT,
+  `execution_type` VARCHAR(50),
+  `target` VARCHAR(500),
+  `response_status` INTEGER,
+  `error_message` TEXT,
+  `output` TEXT,
+  PRIMARY KEY (`id`),
+  FOREIGN KEY (`job_id`) REFERENCES `jobs` (`id`) ON DELETE CASCADE
+) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
+
+CREATE INDEX `ix_job_executions_job_id` ON `job_executions` (`job_id`);
+
+-- --------------------------------------------------------------------------
+-- Table: notifications
+-- --------------------------------------------------------------------------
+CREATE TABLE `notifications` (
+  `id` VARCHAR(36) NOT NULL,
+  `user_id` VARCHAR(36) NOT NULL,
+  `title` VARCHAR(255) NOT NULL,
+  `message` TEXT NOT NULL,
+  `type` VARCHAR(50) NOT NULL,
+  `related_job_id` VARCHAR(36),
+  `related_execution_id` VARCHAR(36),
+  `is_read` BOOL NOT NULL,
+  `read_at` DATETIME,
+  `created_at` DATETIME NOT NULL,
+  PRIMARY KEY (`id`),
+  FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE,
+  FOREIGN KEY (`related_job_id`) REFERENCES `jobs` (`id`) ON DELETE SET NULL,
+  FOREIGN KEY (`related_execution_id`) REFERENCES `job_executions` (`id`) ON DELETE SET NULL
+) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

