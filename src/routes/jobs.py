import logging
import csv
import io
import json
import os
from typing import Optional, Dict, List
from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt, get_jwt_identity
from croniter import croniter
from apscheduler.triggers.cron import CronTrigger
from zoneinfo import ZoneInfo
from sqlalchemy import desc
from ..models import db
from ..models.job import Job
from ..models.job_execution import JobExecution
from ..scheduler import scheduler
from ..scheduler.job_executor import execute_job
from ..utils.auth import role_required, get_current_user, can_modify_job, is_admin
from ..utils.notifications import (
    broadcast_job_created,
    broadcast_job_updated,
    broadcast_job_deleted,
    broadcast_job_enabled,
    broadcast_job_disabled
)

logger = logging.getLogger(__name__)

# Error message constants
ERROR_INTERNAL_SERVER = 'Internal server error'
ERROR_JOB_NOT_FOUND = 'Job not found'

# Create Blueprint
jobs_bp = Blueprint('jobs', __name__, url_prefix='/api')

def _get_scheduler_timezone():
    tz_name = current_app.config.get('SCHEDULER_TIMEZONE', 'Asia/Tokyo')
    try:
        return ZoneInfo(tz_name)
    except Exception:
        logger.warning(f"Invalid SCHEDULER_TIMEZONE '{tz_name}', falling back to UTC")
        return ZoneInfo('UTC')

def _truthy(value: Optional[str]) -> bool:
    if value is None:
        return False
    return value.strip().lower() in {'1', 'true', 'yes', 'y', 'on'}


def _status_to_active(value: Optional[str]) -> bool:
    if value is None:
        return True
    lowered = value.strip().lower()
    if lowered in {'disable', 'disabled', 'inactive', 'false', '0', 'no', 'n', 'off'}:
        return False
    if lowered in {'enable', 'enabled', 'active', 'true', '1', 'yes', 'y', 'on'}:
        return True
    return True


def _normalize_csv_rows(rows: List[List[str]]):
    if not rows:
        raise ValueError('CSV is empty.')

    raw_headers = rows[0] or []
    header_names = [(h or '').strip() for h in raw_headers]
    keep_indexes = [i for i, h in enumerate(header_names) if h]

    if not keep_indexes:
        raise ValueError('CSV header row has no usable column names.')

    kept_headers = [header_names[i] for i in keep_indexes]

    normalized_rows: List[List[str]] = []
    removed_empty_row_count = 0

    for raw_row in rows[1:]:
        padded = list(raw_row or [])
        if len(padded) < len(raw_headers):
            padded.extend([''] * (len(raw_headers) - len(padded)))

        kept = [str(padded[i] or '') for i in keep_indexes]
        if all((c or '').strip() == '' for c in kept):
            removed_empty_row_count += 1
            continue
        normalized_rows.append(kept)

    return kept_headers, normalized_rows, {
        'original_column_count': len(raw_headers),
        'original_row_count': max(0, len(rows) - 1),
        'removed_column_count': len(raw_headers) - len(kept_headers),
        'removed_empty_row_count': removed_empty_row_count,
    }


def _first_non_empty(row: Dict[str, str], keys: List[str]) -> Optional[str]:
    for key in keys:
        value = row.get(key)
        if value is not None and value.strip() != '':
            return value.strip()
    return None


def _lower_key_map(headers: List[str], values: List[str]) -> Dict[str, str]:
    return {str(h or '').strip().lower(): str(values[i] or '').strip() for i, h in enumerate(headers)}


@jobs_bp.route('/jobs', methods=['POST'])
@jwt_required()
@role_required('admin', 'user')
def create_job():
    """
    Create a new scheduled job (Admin and User roles only).
    
    Expected JSON payload:
    {
        "name": "Job Name",
        "cron_expression": "*/5 * * * *",
        "target_url": "https://example.com/webhook"
    }
    
    Headers:
        Authorization: Bearer <access_token>
    
    Returns:
        201: Job created successfully with job details
        400: Bad request (validation errors)
        401: Unauthorized (invalid token)
        403: Forbidden (viewer role)
        500: Internal server error
    """
    try:
        # Validate request has JSON body
        if not request.is_json:
            return jsonify({'error': 'Content-Type must be application/json'}), 400

        data = request.get_json()

        # Validate required fields (only name and cron_expression are mandatory)
        required_fields = ['name', 'cron_expression']
        missing_fields = [field for field in required_fields if field not in data]
        
        if missing_fields:
            return jsonify({
                'error': 'Missing required fields',
                'missing_fields': missing_fields
            }), 400

        name = data['name'].strip()
        cron_expression = data['cron_expression'].strip()

        # Validate name is not empty
        if not name:
            return jsonify({'error': 'Job name cannot be empty'}), 400

        # Check for duplicate job name
        existing_job = Job.query.filter_by(name=name).first()
        if existing_job:
            return jsonify({
                'error': 'Duplicate job name',
                'message': f'A job with the name "{name}" already exists. Please use a unique name.'
            }), 400

        # Validate cron expression
        if not croniter.is_valid(cron_expression):
            return jsonify({
                'error': 'Invalid cron expression',
                'message': 'Please provide a valid cron expression (e.g., "*/5 * * * *" for every 5 minutes)'
            }), 400

        # Optional fields
        target_url = data.get('target_url', '').strip() or None
        github_owner = data.get('github_owner', '').strip() or None
        github_repo = data.get('github_repo', '').strip() or None
        github_workflow_name = data.get('github_workflow_name', '').strip() or None
        metadata = data.get('metadata', {})
        enable_email_notifications = data.get('enable_email_notifications', False)
        notification_emails = data.get('notification_emails', []) if enable_email_notifications else []
        notify_on_success = data.get('notify_on_success', False) if enable_email_notifications else False

        # Validate that at least one target is provided (target_url OR GitHub config)
        if not target_url and not (github_owner and github_repo and github_workflow_name):
            return jsonify({
                'error': 'Missing target configuration',
                'message': 'Please provide either "target_url" or GitHub Actions configuration (github_owner, github_repo, github_workflow_name)'
            }), 400

        # Get current user
        current_user = get_current_user()
        
        # Create new job in database
        new_job = Job(
            name=name,
            cron_expression=cron_expression,
            target_url=target_url,
            github_owner=github_owner,
            github_repo=github_repo,
            github_workflow_name=github_workflow_name,
            created_by=current_user.id if current_user else None,
            is_active=True,
            enable_email_notifications=enable_email_notifications,
            notify_on_success=notify_on_success
        )
        
        # Set metadata if provided
        if metadata:
            new_job.set_metadata(metadata)
        
        # Set notification emails if provided and enabled
        if enable_email_notifications and notification_emails:
            new_job.set_notification_emails(notification_emails)

        db.session.add(new_job)
        db.session.commit()

        # Add job to APScheduler
        try:
            scheduler_tz = _get_scheduler_timezone()
            trigger = CronTrigger.from_crontab(cron_expression, timezone=scheduler_tz)
            job_config = {
                'target_url': new_job.target_url,
                'github_owner': new_job.github_owner,
                'github_repo': new_job.github_repo,
                'github_workflow_name': new_job.github_workflow_name,
                'metadata': new_job.get_metadata(),
                'enable_email_notifications': new_job.enable_email_notifications,
                'notification_emails': new_job.get_notification_emails(),
                'notify_on_success': new_job.notify_on_success
            }
            scheduler.add_job(
                func=execute_job,
                trigger=trigger,
                args=[new_job.id, new_job.name, job_config],
                id=new_job.id,
                name=new_job.name,
                replace_existing=True
            )
            logger.info(f"Job '{new_job.name}' (ID: {new_job.id}) created and scheduled successfully")
            
            # Broadcast notification to all users
            current_user = get_current_user()
            try:
                broadcast_job_created(new_job.name, new_job.id, current_user.email)
                logger.info(f"Broadcast notification sent: Job '{new_job.name}' created")
            except Exception as e:
                logger.error(f"Failed to broadcast job created notification: {str(e)}")
                
        except Exception as e:
            # Rollback database if scheduler fails
            db.session.delete(new_job)
            db.session.commit()
            logger.error(f"Failed to schedule job: {str(e)}")
            return jsonify({
                'error': 'Failed to schedule job',
                'message': str(e)
            }), 500

        return jsonify({
            'message': 'Job created successfully',
            'job': new_job.to_dict()
        }), 201

    except Exception as e:
        logger.error(f"Error creating job: {str(e)}")
        return jsonify({
            'error': ERROR_INTERNAL_SERVER,
            'message': str(e)
        }), 500


@jobs_bp.route('/jobs/bulk-upload', methods=['POST'])
@jwt_required()
@role_required('admin', 'user')
def bulk_upload_jobs():
    """
    Bulk create jobs from a CSV file (Admin and User roles only).

    Expects multipart/form-data with:
      - file: CSV file
      - default_github_owner (optional): default owner when Repo column doesn't include owner/repo
      - dry_run (optional): true/false; when true validates only

    Normalization:
      - Removes empty rows
      - Drops columns with empty headers
    """
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'Missing file', 'message': 'Upload a CSV file using form field "file".'}), 400

        uploaded_file = request.files['file']
        if not uploaded_file or uploaded_file.filename == '':
            return jsonify({'error': 'Missing file', 'message': 'No file selected.'}), 400

        default_owner = (request.form.get('default_github_owner') or os.getenv('DEFAULT_GITHUB_OWNER') or '').strip() or None
        dry_run = _truthy(request.form.get('dry_run'))

        raw_bytes = uploaded_file.read()
        try:
            csv_text = raw_bytes.decode('utf-8-sig')
        except Exception:
            csv_text = raw_bytes.decode('utf-8', errors='replace')

        reader = csv.reader(io.StringIO(csv_text))
        rows = [row for row in reader]
        headers, normalized_rows, stats = _normalize_csv_rows(rows)

        current_user = get_current_user()

        errors = []
        created_jobs = []
        seen_names = set()

        for row_index, values in enumerate(normalized_rows, start=2):
            row = _lower_key_map(headers, values)

            name = _first_non_empty(row, ['job name', 'name'])
            cron_expression = _first_non_empty(row, ['cron schedule (jst)', 'cron expression', 'cron', 'cron_expression'])
            status = _first_non_empty(row, ['status', 'is_active', 'active'])
            target_url = _first_non_empty(row, ['target url', 'target_url', 'url'])

            github_owner = _first_non_empty(row, ['github owner', 'owner', 'github_owner'])
            github_repo = _first_non_empty(row, ['repo', 'github repo', 'github_repo'])
            github_workflow_name = _first_non_empty(row, ['workflow name', 'github workflow name', 'github_workflow_name'])

            branch = _first_non_empty(row, ['branch', 'ref'])
            request_body = _first_non_empty(row, ['request body', 'request_body', 'metadata'])

            if not name or not cron_expression:
                errors.append({'row': row_index, 'error': 'Missing required fields', 'message': 'name and cron_expression are required.'})
                continue

            if name in seen_names:
                errors.append({'row': row_index, 'job_name': name, 'error': 'Duplicate job name in CSV'})
                continue
            seen_names.add(name)

            if Job.query.filter_by(name=name).first():
                errors.append({'row': row_index, 'job_name': name, 'error': 'Duplicate job name', 'message': f'A job with the name "{name}" already exists.'})
                continue

            if not croniter.is_valid(cron_expression):
                errors.append({'row': row_index, 'job_name': name, 'error': 'Invalid cron expression'})
                continue

            is_active = _status_to_active(status)

            metadata: dict = {}
            if request_body:
                try:
                    parsed = json.loads(request_body)
                except Exception as e:
                    errors.append({'row': row_index, 'job_name': name, 'error': 'Invalid JSON in Request Body', 'message': str(e)})
                    continue
                if isinstance(parsed, dict):
                    metadata = parsed
                else:
                    errors.append({'row': row_index, 'job_name': name, 'error': 'Invalid Request Body', 'message': 'Request Body must be a JSON object.'})
                    continue

            if branch and 'branchDetails' not in metadata:
                metadata['branchDetails'] = branch

            # Allow Repo to be either "owner/repo" or just "repo"
            inferred_owner = github_owner
            inferred_repo = github_repo
            if github_repo and '/' in github_repo:
                parts = [p for p in github_repo.split('/') if p]
                if len(parts) == 2:
                    inferred_owner, inferred_repo = parts[0].strip(), parts[1].strip()

            if not target_url and not (inferred_owner or default_owner) and (inferred_repo or github_workflow_name):
                errors.append({'row': row_index, 'job_name': name, 'error': 'Missing GitHub owner', 'message': 'Provide "github_owner" column or default_github_owner.'})
                continue

            effective_owner = inferred_owner or default_owner

            if not target_url and not (effective_owner and inferred_repo and github_workflow_name):
                errors.append({
                    'row': row_index,
                    'job_name': name,
                    'error': 'Missing target configuration',
                    'message': 'Provide target_url or GitHub config (github_owner, github_repo, github_workflow_name).'
                })
                continue

            if dry_run:
                created_jobs.append({'name': name, 'is_active': is_active, 'cron_expression': cron_expression})
                continue

            new_job = Job(
                name=name,
                cron_expression=cron_expression,
                target_url=target_url or None,
                github_owner=effective_owner if not target_url else None,
                github_repo=inferred_repo if not target_url else None,
                github_workflow_name=github_workflow_name if not target_url else None,
                created_by=current_user.id if current_user else None,
                is_active=is_active,
                enable_email_notifications=False,
                notify_on_success=False,
            )
            if metadata:
                new_job.set_metadata(metadata)

            db.session.add(new_job)
            db.session.flush()

            created_jobs.append({'id': new_job.id, 'name': new_job.name, 'is_active': new_job.is_active})

        if dry_run:
            return jsonify({
                'message': 'CSV validated successfully',
                'dry_run': True,
                'stats': stats,
                'created_count': len(created_jobs),
                'error_count': len(errors),
                'errors': errors,
                'jobs': created_jobs,
            }), 200

        db.session.commit()

        # Schedule active jobs after commit; on failures, disable the job and report.
        scheduling_errors = []
        scheduler_tz = _get_scheduler_timezone()
        for job_info in created_jobs:
            job_id = job_info.get('id')
            if not job_id:
                continue
            job = Job.query.get(job_id)
            if not job or not job.is_active:
                continue
            try:
                trigger = CronTrigger.from_crontab(job.cron_expression, timezone=scheduler_tz)
                job_config = {
                    'target_url': job.target_url,
                    'github_owner': job.github_owner,
                    'github_repo': job.github_repo,
                    'github_workflow_name': job.github_workflow_name,
                    'metadata': job.get_metadata(),
                    'enable_email_notifications': job.enable_email_notifications,
                    'notification_emails': job.get_notification_emails(),
                    'notify_on_success': job.notify_on_success,
                }
                scheduler.add_job(
                    func=execute_job,
                    trigger=trigger,
                    args=[job.id, job.name, job_config],
                    id=job.id,
                    name=job.name,
                    replace_existing=True,
                )
            except Exception as e:
                logger.error(f"Failed to schedule bulk job '{job.name}': {str(e)}")
                job.is_active = False
                scheduling_errors.append({'job_name': job.name, 'error': 'Failed to schedule job', 'message': str(e)})

        if scheduling_errors:
            db.session.commit()

        all_errors = errors + scheduling_errors

        return jsonify({
            'message': 'Bulk upload processed',
            'dry_run': False,
            'stats': stats,
            'created_count': len(created_jobs),
            'error_count': len(all_errors),
            'errors': all_errors,
            'jobs': created_jobs,
        }), 200

    except ValueError as e:
        return jsonify({'error': 'Invalid CSV', 'message': str(e)}), 400
    except Exception as e:
        logger.error(f"Error bulk uploading jobs: {str(e)}")
        db.session.rollback()
        return jsonify({'error': ERROR_INTERNAL_SERVER, 'message': str(e)}), 500


@jobs_bp.route('/jobs', methods=['GET'])
@jwt_required()
def list_jobs():
    """
    List all scheduled jobs (All authenticated users).
    
    - Admin: Sees all jobs
    - User: Sees all jobs
    - Viewer: Sees all jobs (read-only)
    
    Headers:
        Authorization: Bearer <access_token>
    
    Returns:
        200: List of all jobs
        401: Unauthorized (invalid token)
        500: Internal server error
    """
    try:
        jobs = Job.query.order_by(desc(Job.created_at)).all()
        return jsonify({
            'count': len(jobs),
            'jobs': [job.to_dict() for job in jobs]
        }), 200
    except Exception as e:
        logger.error(f"Error listing jobs: {str(e)}")
        return jsonify({
            'error': ERROR_INTERNAL_SERVER,
            'message': str(e)
        }), 500


@jobs_bp.route('/jobs/<job_id>', methods=['GET'])
@jwt_required()
def get_job(job_id):
    """
    Get details of a specific job by ID (All authenticated users).
    
    Args:
        job_id: The unique identifier of the job
    
    Headers:
        Authorization: Bearer <access_token>
        
    Returns:
        200: Job details
        401: Unauthorized (invalid token)
        404: Job not found
        500: Internal server error
    """
    try:
        job = Job.query.get(job_id)
        
        if not job:
            return jsonify({
                'error': ERROR_JOB_NOT_FOUND,
                'message': f'No job found with ID: {job_id}'
            }), 404
        
        return jsonify({
            'job': job.to_dict()
        }), 200
        
    except Exception as e:
        logger.error(f"Error retrieving job {job_id}: {str(e)}")
        return jsonify({
            'error': ERROR_INTERNAL_SERVER,
            'message': str(e)
        }), 500


@jobs_bp.route('/jobs/<job_id>', methods=['PUT'])
@jwt_required()
def update_job(job_id):
    """
    Update an existing job.
    
    - Admin: Can update any job
    - User: Can update only their own jobs
    - Viewer: Cannot update jobs
    
    Args:
        job_id: The unique identifier of the job
    
    Headers:
        Authorization: Bearer <access_token>
        
    Returns:
        200: Job updated successfully
        400: Bad request (validation errors)
        401: Unauthorized (invalid token)
        403: Forbidden (not owner or viewer role)
        404: Job not found
        500: Internal server error
    """
    try:
        # Find the job
        job = Job.query.get(job_id)
        
        if not job:
            return jsonify({
                'error': ERROR_JOB_NOT_FOUND,
                'message': f'No job found with ID: {job_id}'
            }), 404
        
        # Check authorization (admin or owner)
        if not can_modify_job(job):
            return jsonify({
                'error': 'Insufficient permissions',
                'message': 'You can only update your own jobs'
            }), 403
        
        # Validate request has JSON body
        if not request.is_json:
            return jsonify({'error': 'Content-Type must be application/json'}), 400
        
        data = request.get_json()
        
        # Track if we need to update the scheduler
        needs_scheduler_update = False
        
        # Update name if provided
        if 'name' in data:
            new_name = data['name'].strip()
            if not new_name:
                return jsonify({'error': 'Job name cannot be empty'}), 400
            
            # Check for duplicate name (excluding current job)
            if new_name != job.name:
                existing_job = Job.query.filter_by(name=new_name).first()
                if existing_job:
                    return jsonify({
                        'error': 'Duplicate job name',
                        'message': f'A job with the name "{new_name}" already exists.'
                    }), 400
                job.name = new_name
                needs_scheduler_update = True
        
        # Update cron expression if provided
        if 'cron_expression' in data:
            new_cron = data['cron_expression'].strip()
            if not croniter.is_valid(new_cron):
                return jsonify({
                    'error': 'Invalid cron expression',
                    'message': 'Please provide a valid cron expression'
                }), 400
            if new_cron != job.cron_expression:
                job.cron_expression = new_cron
                needs_scheduler_update = True
        
        # Update target_url if provided
        if 'target_url' in data:
            job.target_url = data['target_url'].strip() or None
            needs_scheduler_update = True
        
        # Update GitHub configuration if provided
        if 'github_owner' in data:
            job.github_owner = data['github_owner'].strip() or None
            needs_scheduler_update = True
        
        if 'github_repo' in data:
            job.github_repo = data['github_repo'].strip() or None
            needs_scheduler_update = True
        
        if 'github_workflow_name' in data:
            job.github_workflow_name = data['github_workflow_name'].strip() or None
            needs_scheduler_update = True
        
        # Update metadata if provided
        if 'metadata' in data:
            job.set_metadata(data['metadata'])
            needs_scheduler_update = True
        
        # Update email notification settings if provided
        if 'enable_email_notifications' in data:
            job.enable_email_notifications = bool(data['enable_email_notifications'])
            # Clear emails if notifications are being disabled
            if not job.enable_email_notifications:
                job.set_notification_emails([])
                job.notify_on_success = False
            needs_scheduler_update = True
        
        # Update notification emails if provided (only if notifications enabled)
        if 'notification_emails' in data:
            if job.enable_email_notifications:
                job.set_notification_emails(data['notification_emails'])
            else:
                # If notifications are disabled, clear the emails
                job.set_notification_emails([])
            needs_scheduler_update = True
        
        # Update notify_on_success if provided
        if 'notify_on_success' in data:
            job.notify_on_success = bool(data['notify_on_success']) if job.enable_email_notifications else False
            needs_scheduler_update = True
        
        # Track if status changed for notification logic
        status_changed = False
        old_status = None
        
        # Update is_active if provided
        if 'is_active' in data:
            new_status = bool(data['is_active'])
            if new_status != job.is_active:
                old_status = job.is_active
                job.is_active = new_status
                needs_scheduler_update = True
                status_changed = True
        
        # Validate at least one target exists
        if not job.target_url and not (job.github_owner and job.github_repo and job.github_workflow_name):
            return jsonify({
                'error': 'Missing target configuration',
                'message': 'Job must have either target_url or complete GitHub Actions configuration'
            }), 400
        
        # Save to database
        db.session.commit()
        
        # Update scheduler if needed
        if needs_scheduler_update:
            try:
                scheduler_tz = _get_scheduler_timezone()
                # Remove old job from scheduler
                if scheduler.get_job(job_id):
                    scheduler.remove_job(job_id)
                
                # Add updated job if active
                if job.is_active:
                    trigger = CronTrigger.from_crontab(job.cron_expression, timezone=scheduler_tz)
                    job_config = {
                        'target_url': job.target_url,
                        'github_owner': job.github_owner,
                        'github_repo': job.github_repo,
                        'github_workflow_name': job.github_workflow_name,
                        'metadata': job.get_metadata(),
                        'enable_email_notifications': job.enable_email_notifications,
                        'notification_emails': job.get_notification_emails(),
                        'notify_on_success': job.notify_on_success
                    }
                    scheduler.add_job(
                        func=execute_job,
                        trigger=trigger,
                        args=[job.id, job.name, job_config],
                        id=job.id,
                        name=job.name,
                        replace_existing=True
                    )
                logger.info(f"Job '{job.name}' (ID: {job.id}) updated in scheduler")
            except Exception as e:
                logger.error(f"Failed to update scheduler for job '{job.name}': {str(e)}")
                return jsonify({
                    'error': 'Failed to update scheduler',
                    'message': str(e)
                }), 500
        
        # Broadcast notification to all users about job update
        # Send appropriate notification based on what changed
        current_user = get_current_user()
        user_email = current_user.email if current_user else 'Unknown'
        
        try:
            if status_changed:
                # Status changed - send enabled/disabled notification
                if old_status and not job.is_active:
                    broadcast_job_disabled(job.name, job.id, user_email)
                    logger.info(f"Broadcast notification sent: Job '{job.name}' disabled")
                elif not old_status and job.is_active:
                    broadcast_job_enabled(job.name, job.id, user_email)
                    logger.info(f"Broadcast notification sent: Job '{job.name}' enabled")
            else:
                # Generic update notification
                broadcast_job_updated(job.name, job.id, user_email)
                logger.info(f"Broadcast notification sent: Job '{job.name}' updated")
        except Exception as e:
            logger.error(f"Failed to broadcast job notification: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
        
        return jsonify({
            'message': 'Job updated successfully',
            'job': job.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error updating job {job_id}: {str(e)}")
        return jsonify({
            'error': ERROR_INTERNAL_SERVER,
            'message': str(e)
        }), 500


@jobs_bp.route('/jobs/<job_id>', methods=['DELETE'])
@jwt_required()
def delete_job(job_id):
    """
    Delete a job by ID.
    
    - Admin: Can delete any job
    - User: Can delete only their own jobs
    - Viewer: Cannot delete jobs
    
    Args:
        job_id: The unique identifier of the job
    
    Headers:
        Authorization: Bearer <access_token>
        
    Returns:
        200: Job deleted successfully
        401: Unauthorized (invalid token)
        403: Forbidden (not owner or viewer role)
        404: Job not found
        500: Internal server error
    """
    try:
        # Find the job
        job = Job.query.get(job_id)
        
        if not job:
            return jsonify({
                'error': ERROR_JOB_NOT_FOUND,
                'message': f'No job found with ID: {job_id}'
            }), 404
        
        # Check authorization (admin or owner)
        if not can_modify_job(job):
            return jsonify({
                'error': 'Insufficient permissions',
                'message': 'You can only delete your own jobs'
            }), 403
        
        job_name = job.name
        
        # Remove from scheduler if exists
        try:
            if scheduler.get_job(job_id):
                scheduler.remove_job(job_id)
                logger.info(f"Job '{job_name}' (ID: {job_id}) removed from scheduler")
        except Exception as e:
            logger.warning(f"Failed to remove job from scheduler: {str(e)}")
        
        # Delete from database
        db.session.delete(job)
        db.session.commit()
        
        logger.info(f"Job '{job_name}' (ID: {job_id}) deleted successfully")
        
        # Broadcast notification to all users
        current_user = get_current_user()
        try:
            broadcast_job_deleted(job_name, current_user.email)
            logger.info(f"Broadcast notification sent: Job '{job_name}' deleted")
        except Exception as e:
            logger.error(f"Failed to broadcast job deleted notification: {str(e)}")
        
        return jsonify({
            'message': 'Job deleted successfully',
            'deleted_job': {
                'id': job_id,
                'name': job_name
            }
        }), 200
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error deleting job {job_id}: {str(e)}")
        return jsonify({
            'error': ERROR_INTERNAL_SERVER,
            'message': str(e)
        }), 500


@jobs_bp.route('/jobs/<job_id>/executions', methods=['GET'])
@jwt_required()
def get_job_executions(job_id):
    """
    Get execution history for a specific job.
    
    Query Parameters:
        - limit (optional): Maximum number of executions to return (default: 50, max: 200)
        - status (optional): Filter by status ('success', 'failed', 'running')
        - trigger_type (optional): Filter by trigger type ('scheduled', 'manual')
    
    Headers:
        Authorization: Bearer <access_token>
    
    Returns:
        200: List of job executions
        404: Job not found
        500: Internal server error
    """
    try:
        # Check if job exists
        job = Job.query.get(job_id)
        if not job:
            return jsonify({
                'error': ERROR_JOB_NOT_FOUND,
                'message': f'No job found with ID: {job_id}'
            }), 404
        
        # Parse query parameters
        limit = request.args.get('limit', default=50, type=int)
        limit = min(limit, 200)  # Cap at 200
        status = request.args.get('status')
        trigger_type = request.args.get('trigger_type')
        
        # Build query
        query = JobExecution.query.filter_by(job_id=job_id)
        
        # Apply filters
        if status:
            query = query.filter_by(status=status)
        if trigger_type:
            query = query.filter_by(trigger_type=trigger_type)
        
        # Order by most recent first and apply limit
        executions = query.order_by(desc(JobExecution.started_at)).limit(limit).all()
        
        return jsonify({
            'job_id': job_id,
            'job_name': job.name,
            'total_executions': len(executions),
            'executions': [execution.to_dict() for execution in executions]
        }), 200
        
    except Exception as e:
        logger.error(f"Error fetching executions for job {job_id}: {str(e)}")
        return jsonify({
            'error': ERROR_INTERNAL_SERVER,
            'message': str(e)
        }), 500


@jobs_bp.route('/jobs/<job_id>/executions/<execution_id>', methods=['GET'])
@jwt_required()
def get_job_execution_details(job_id, execution_id):
    """
    Get details of a specific job execution.
    
    Headers:
        Authorization: Bearer <access_token>
    
    Returns:
        200: Execution details
        404: Job or execution not found
        500: Internal server error
    """
    try:
        # Check if job exists
        job = Job.query.get(job_id)
        if not job:
            return jsonify({
                'error': ERROR_JOB_NOT_FOUND,
                'message': f'No job found with ID: {job_id}'
            }), 404
        
        # Get execution
        execution = JobExecution.query.filter_by(id=execution_id, job_id=job_id).first()
        if not execution:
            return jsonify({
                'error': 'Execution not found',
                'message': f'No execution found with ID: {execution_id} for job: {job_id}'
            }), 404
        
        return jsonify({
            'job': {
                'id': job.id,
                'name': job.name
            },
            'execution': execution.to_dict()
        }), 200
        
    except Exception as e:
        logger.error(f"Error fetching execution {execution_id} for job {job_id}: {str(e)}")
        return jsonify({
            'error': ERROR_INTERNAL_SERVER,
            'message': str(e)
        }), 500


@jobs_bp.route('/jobs/<job_id>/executions/stats', methods=['GET'])
@jwt_required()
def get_job_execution_stats(job_id):
    """
    Get execution statistics for a specific job.
    
    Headers:
        Authorization: Bearer <access_token>
    
    Returns:
        200: Execution statistics
        404: Job not found
        500: Internal server error
    """
    try:
        # Check if job exists
        job = Job.query.get(job_id)
        if not job:
            return jsonify({
                'error': ERROR_JOB_NOT_FOUND,
                'message': f'No job found with ID: {job_id}'
            }), 404
        
        # Get counts by status
        total = JobExecution.query.filter_by(job_id=job_id).count()
        success = JobExecution.query.filter_by(job_id=job_id, status='success').count()
        failed = JobExecution.query.filter_by(job_id=job_id, status='failed').count()
        running = JobExecution.query.filter_by(job_id=job_id, status='running').count()
        
        # Get latest execution
        latest_execution = JobExecution.query.filter_by(job_id=job_id).order_by(desc(JobExecution.started_at)).first()
        
        # Calculate success rate
        success_rate = (success / total * 100) if total > 0 else 0
        
        # Get average duration for successful executions
        successful_executions = JobExecution.query.filter_by(job_id=job_id, status='success').all()
        avg_duration = None
        if successful_executions:
            durations = [e.duration_seconds for e in successful_executions if e.duration_seconds is not None]
            avg_duration = sum(durations) / len(durations) if durations else None
        
        return jsonify({
            'job_id': job_id,
            'job_name': job.name,
            'statistics': {
                'total_executions': total,
                'success_count': success,
                'failed_count': failed,
                'running_count': running,
                'success_rate': round(success_rate, 2),
                'average_duration_seconds': round(avg_duration, 2) if avg_duration else None
            },
            'latest_execution': latest_execution.to_dict() if latest_execution else None
        }), 200
        
    except Exception as e:
        logger.error(f"Error fetching execution stats for job {job_id}: {str(e)}")
        return jsonify({
            'error': ERROR_INTERNAL_SERVER,
            'message': str(e)
        }), 500


@jobs_bp.route('/health', methods=['GET'])
def health_check():
    """
    Health check endpoint to verify the API is running.
    """
    return jsonify({
        'status': 'healthy',
        'scheduler_running': scheduler.running,
        'scheduled_jobs_count': len(scheduler.get_jobs())
    }), 200
