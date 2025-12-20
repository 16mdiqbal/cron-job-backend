import logging
import csv
import io
import json
import os
import re
from datetime import datetime, date, time, timezone, timedelta
from typing import Optional, Dict, List
from urllib.parse import urlparse
import requests
from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt, get_jwt_identity
from croniter import croniter
from apscheduler.triggers.cron import CronTrigger
from zoneinfo import ZoneInfo
from sqlalchemy import desc
from sqlalchemy import func
from ..models import db
from ..models.job import Job
from ..models.job_category import JobCategory
from ..models.pic_team import PicTeam
from ..models.job_execution import JobExecution
from ..models.slack_settings import SlackSettings
from ..scheduler import scheduler
from ..scheduler.job_executor import execute_job, execute_job_with_app_context, trigger_job_manually
from ..utils.auth import role_required, get_current_user, can_modify_job, is_admin
from ..utils.notifications import (
    broadcast_job_created,
    broadcast_job_updated,
    broadcast_job_deleted,
    broadcast_job_enabled,
    broadcast_job_disabled
)
from ..utils.api_errors import safe_error_message

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


def _compute_next_execution_at(job: Job) -> Optional[str]:
    """
    Compute next scheduled run without relying on an in-process APScheduler instance.
    This keeps "Next run" correct even if the scheduler is disabled in this process.
    """
    try:
        if not job.is_active:
            return None
        tz = _get_scheduler_timezone()
        now = datetime.now(tz)
        trigger = CronTrigger.from_crontab(job.cron_expression, timezone=tz)
        next_run_time = trigger.get_next_fire_time(None, now)
        return next_run_time.isoformat() if next_run_time else None
    except Exception:
        return None

def _get_default_github_owner() -> str:
    return (os.getenv('DEFAULT_GITHUB_OWNER') or 'Pay-Baymax').strip()

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

def _parse_iso_date_or_datetime(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None

    raw = value.strip()
    if not raw:
        return None

    # Date-only inputs like "2025-12-18"
    try:
        if len(raw) == 10 and raw[4] == '-' and raw[7] == '-':
            d = date.fromisoformat(raw)
            return datetime.combine(d, time.min, tzinfo=timezone.utc)
    except Exception:
        pass

    # Datetime inputs like "2025-12-18T12:34:56Z" or with offset
    normalized = raw.replace('Z', '+00:00')
    dt = datetime.fromisoformat(normalized)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    else:
        dt = dt.astimezone(timezone.utc)
    return dt


def _cron_validation_error(expression: str) -> Optional[str]:
    expr = (expression or '').strip()
    if not expr:
        return 'Cron expression is required.'

    # UI convention: 5-field crontab (minute hour day month day-of-week)
    parts = expr.split()
    if len(parts) != 5:
        return 'Cron expression must have exactly 5 fields (minute hour day month day-of-week).'

    try:
        CronTrigger.from_crontab(expr, timezone=_get_scheduler_timezone())
    except Exception as e:
        return str(e) or 'Invalid cron expression.'
    return None


def _cron_next_runs(expression: str, count: int = 5) -> List[str]:
    scheduler_tz = _get_scheduler_timezone()
    trigger = CronTrigger.from_crontab((expression or '').strip(), timezone=scheduler_tz)
    now = datetime.now(scheduler_tz)
    prev = None
    runs: List[str] = []
    for _ in range(max(0, min(int(count or 0), 20))):
        nxt = trigger.get_next_fire_time(prev, now)
        if not nxt:
            break
        runs.append(nxt.isoformat())
        prev = nxt
        now = nxt
    return runs


def _slugify(value: str) -> str:
    v = (value or '').strip().lower()
    v = re.sub(r'[^a-z0-9]+', '-', v)
    v = re.sub(r'-{2,}', '-', v).strip('-')
    return v


def _resolve_category_slug(raw: Optional[str]) -> str:
    """
    Resolve a category from either a slug or a display name.
    Falls back to 'general' when missing.
    """
    if raw is None:
        return 'general'
    val = raw.strip()
    if not val:
        return 'general'

    # First try slug match
    slug = _slugify(val)
    category = JobCategory.query.filter_by(slug=slug).first()
    if category:
        return category.slug

    # Then try name match (case-insensitive)
    category = JobCategory.query.filter(func.lower(JobCategory.name) == val.lower()).first()
    if category:
        return category.slug

    return slug  # still return a normalized slug for validation messaging


def _validate_category_slug(slug: str) -> Optional[str]:
    if slug == 'general':
        return None
    exists = JobCategory.query.filter_by(slug=slug).first()
    if not exists:
        return 'Unknown category. Create it in Settings → Categories first, or choose General.'
    return None


def _today_jst() -> date:
    return datetime.now(_get_scheduler_timezone()).date()


def _parse_end_date(value: Optional[str]) -> Optional[date]:
    if value is None:
        return None
    raw = (value or '').strip()
    if not raw:
        return None
    try:
        return date.fromisoformat(raw)
    except Exception as e:
        raise ValueError('Invalid end_date. Use YYYY-MM-DD.') from e


def _resolve_pic_team_slug(raw: Optional[str]) -> Optional[str]:
    """
    Resolve a PIC team from either a slug or a display name.
    Returns a normalized slug (even if it doesn't exist) so validation can explain.
    """
    if raw is None:
        return None
    val = raw.strip()
    if not val:
        return None

    slug = _slugify(val)
    team = PicTeam.query.filter_by(slug=slug).first()
    if team:
        return team.slug

    team = PicTeam.query.filter(func.lower(PicTeam.name) == val.lower()).first()
    if team:
        return team.slug

    return slug


def _validate_pic_team_slug(slug: Optional[str]) -> Optional[str]:
    if not slug:
        return 'PIC team is required. Create one in Settings → PIC Teams.'
    team = PicTeam.query.filter_by(slug=slug).first()
    if not team:
        return 'Unknown PIC team. Create it in Settings → PIC Teams first.'
    if not team.is_active:
        return 'PIC team is disabled. Enable it in Settings → PIC Teams or choose another.'
    return None


def _get_or_create_slack_settings() -> SlackSettings:
    settings = SlackSettings.query.first()
    if not settings:
        settings = SlackSettings(is_enabled=False, webhook_url=None, channel=None)
        db.session.add(settings)
        db.session.commit()
    return settings


@jobs_bp.route('/settings/slack', methods=['GET'])
@jwt_required()
@role_required('admin')
def get_slack_settings():
    settings = _get_or_create_slack_settings()
    return jsonify({'slack_settings': settings.to_dict()}), 200


@jobs_bp.route('/settings/slack', methods=['PUT'])
@jwt_required()
@role_required('admin')
def update_slack_settings():
    if not request.is_json:
        return jsonify({'error': 'Content-Type must be application/json'}), 400

    data = request.get_json(silent=True) or {}
    settings = _get_or_create_slack_settings()

    if 'is_enabled' in data:
        settings.is_enabled = bool(data.get('is_enabled'))

    if 'webhook_url' in data:
        webhook_url = (data.get('webhook_url') or '').strip()
        settings.webhook_url = webhook_url or None

    if 'channel' in data:
        channel = (data.get('channel') or '').strip()
        settings.channel = channel or None

    if settings.is_enabled and not settings.webhook_url:
        return jsonify({'error': 'Invalid settings', 'message': 'webhook_url is required when Slack is enabled.'}), 400

    db.session.commit()
    return jsonify({'message': 'Slack settings updated', 'slack_settings': settings.to_dict()}), 200


@jobs_bp.route('/job-categories', methods=['GET'])
@jwt_required()
def list_job_categories():
    """
    List job categories (All authenticated users).
    Non-admins only see active categories.
    """
    include_inactive = _truthy(request.args.get('include_inactive'))
    query = JobCategory.query
    if not is_admin() or not include_inactive:
        query = query.filter(JobCategory.is_active.is_(True))
    categories = query.order_by(func.lower(JobCategory.name)).all()
    return jsonify({'categories': [c.to_dict() for c in categories]}), 200


@jobs_bp.route('/job-categories', methods=['POST'])
@jwt_required()
@role_required('admin')
def create_job_category():
    if not request.is_json:
        return jsonify({'error': 'Content-Type must be application/json'}), 400
    data = request.get_json(silent=True) or {}
    name = (data.get('name') or '').strip()
    if not name:
        return jsonify({'error': 'Missing required fields', 'message': '"name" is required.'}), 400

    slug = (data.get('slug') or '').strip()
    slug = _slugify(slug or name)
    if not slug:
        return jsonify({'error': 'Invalid slug', 'message': 'Unable to generate a valid slug from name.'}), 400

    if JobCategory.query.filter_by(slug=slug).first():
        return jsonify({'error': 'Duplicate slug', 'message': f'Category slug "{slug}" already exists.'}), 409

    category = JobCategory(slug=slug, name=name, is_active=True)
    db.session.add(category)
    db.session.commit()
    return jsonify({'message': 'Category created', 'category': category.to_dict()}), 201


@jobs_bp.route('/job-categories/<category_id>', methods=['PUT'])
@jwt_required()
@role_required('admin')
def update_job_category(category_id):
    if not request.is_json:
        return jsonify({'error': 'Content-Type must be application/json'}), 400
    category = JobCategory.query.get(category_id)
    if not category:
        return jsonify({'error': 'Not found', 'message': f'No category found with ID: {category_id}'}), 404

    data = request.get_json(silent=True) or {}
    jobs_updated = 0

    # Slug is always derived from name to keep them strictly aligned.
    if 'name' in data:
        name = (data.get('name') or '').strip()
        if not name:
            return jsonify({'error': 'Invalid name', 'message': 'Name cannot be empty.'}), 400

        if category.slug == 'general' and name != category.name:
            return jsonify({'error': 'Invalid category', 'message': 'The "General" category cannot be renamed.'}), 400

        desired_slug = _slugify(name)
        if not desired_slug:
            return jsonify({'error': 'Invalid slug', 'message': 'Unable to generate a valid slug from name.'}), 400

        if desired_slug != category.slug:
            if JobCategory.query.filter_by(slug=desired_slug).first():
                return jsonify({'error': 'Duplicate slug', 'message': f'Category slug "{desired_slug}" already exists.'}), 409

            old_slug = category.slug
            jobs_updated = (
                Job.query.filter(Job.category == old_slug)
                .update({'category': desired_slug}, synchronize_session=False)
            )
            category.slug = desired_slug

        category.name = name

    # Backwards-compatible: if a client still sends slug explicitly, reject.
    if 'slug' in data:
        return jsonify({
            'error': 'Invalid payload',
            'message': 'Slug cannot be edited directly; it is derived from name.',
        }), 400

    if 'is_active' in data:
        category.is_active = bool(data.get('is_active'))

    db.session.commit()
    return jsonify({'message': 'Category updated', 'category': category.to_dict(), 'jobs_updated': jobs_updated}), 200


@jobs_bp.route('/job-categories/<category_id>', methods=['DELETE'])
@jwt_required()
@role_required('admin')
def delete_job_category(category_id):
    category = JobCategory.query.get(category_id)
    if not category:
        return jsonify({'error': 'Not found', 'message': f'No category found with ID: {category_id}'}), 404

    # Soft-delete: disable instead of removing (jobs may reference its slug).
    category.is_active = False
    db.session.commit()
    return jsonify({'message': 'Category disabled', 'category': category.to_dict()}), 200


@jobs_bp.route('/pic-teams', methods=['GET'])
@jwt_required()
def list_pic_teams():
    """
    List PIC teams (All authenticated users).
    Non-admins only see active teams.
    """
    include_inactive = _truthy(request.args.get('include_inactive'))
    query = PicTeam.query
    if not is_admin() or not include_inactive:
        query = query.filter(PicTeam.is_active.is_(True))
    teams = query.order_by(func.lower(PicTeam.name)).all()
    return jsonify({'pic_teams': [t.to_dict() for t in teams]}), 200


@jobs_bp.route('/pic-teams', methods=['POST'])
@jwt_required()
@role_required('admin')
def create_pic_team():
    if not request.is_json:
        return jsonify({'error': 'Content-Type must be application/json'}), 400
    data = request.get_json(silent=True) or {}
    name = (data.get('name') or '').strip()
    if not name:
        return jsonify({'error': 'Missing required fields', 'message': '"name" is required.'}), 400

    slug = (data.get('slug') or '').strip()
    slug = _slugify(slug or name)
    if not slug:
        return jsonify({'error': 'Invalid slug', 'message': 'Unable to generate a valid slug from name.'}), 400

    if PicTeam.query.filter_by(slug=slug).first():
        return jsonify({'error': 'Duplicate slug', 'message': f'PIC team slug "{slug}" already exists.'}), 409

    slack_handle = (data.get('slack_handle') or '').strip()
    if not slack_handle:
        return jsonify({'error': 'Missing required fields', 'message': '"slack_handle" is required.'}), 400

    team = PicTeam(slug=slug, name=name, slack_handle=slack_handle, is_active=True)
    db.session.add(team)
    db.session.commit()
    return jsonify({'message': 'PIC team created', 'pic_team': team.to_dict()}), 201


@jobs_bp.route('/pic-teams/<team_id>', methods=['PUT'])
@jwt_required()
@role_required('admin')
def update_pic_team(team_id):
    if not request.is_json:
        return jsonify({'error': 'Content-Type must be application/json'}), 400
    team = PicTeam.query.get(team_id)
    if not team:
        return jsonify({'error': 'Not found', 'message': f'No PIC team found with ID: {team_id}'}), 404

    data = request.get_json(silent=True) or {}
    jobs_updated = 0

    if 'name' in data:
        name = (data.get('name') or '').strip()
        if not name:
            return jsonify({'error': 'Invalid name', 'message': 'Name cannot be empty.'}), 400

        desired_slug = _slugify(name)
        if not desired_slug:
            return jsonify({'error': 'Invalid slug', 'message': 'Unable to generate a valid slug from name.'}), 400

        if desired_slug != team.slug:
            if PicTeam.query.filter_by(slug=desired_slug).first():
                return jsonify({'error': 'Duplicate slug', 'message': f'PIC team slug "{desired_slug}" already exists.'}), 409

            old_slug = team.slug
            jobs_updated = (
                Job.query.filter(Job.pic_team == old_slug)
                .update({'pic_team': desired_slug}, synchronize_session=False)
            )
            team.slug = desired_slug

        team.name = name

    if 'slug' in data:
        return jsonify({
            'error': 'Invalid payload',
            'message': 'Slug cannot be edited directly; it is derived from name.',
        }), 400

    if 'is_active' in data:
        team.is_active = bool(data.get('is_active'))

    if 'slack_handle' in data:
        slack_handle = (data.get('slack_handle') or '').strip()
        if not slack_handle:
            return jsonify({'error': 'Invalid slack_handle', 'message': 'slack_handle cannot be empty.'}), 400
        team.slack_handle = slack_handle

    db.session.commit()
    return jsonify({'message': 'PIC team updated', 'pic_team': team.to_dict(), 'jobs_updated': jobs_updated}), 200


@jobs_bp.route('/pic-teams/<team_id>', methods=['DELETE'])
@jwt_required()
@role_required('admin')
def delete_pic_team(team_id):
    team = PicTeam.query.get(team_id)
    if not team:
        return jsonify({'error': 'Not found', 'message': f'No PIC team found with ID: {team_id}'}), 404

    team.is_active = False
    db.session.commit()
    return jsonify({'message': 'PIC team disabled', 'pic_team': team.to_dict()}), 200


@jobs_bp.route('/jobs/validate-cron', methods=['POST'])
@jwt_required()
def validate_cron_expression():
    """
    Validate cron expression and return an explanatory message.
    """
    if not request.is_json:
        return jsonify({'error': 'Content-Type must be application/json'}), 400
    data = request.get_json(silent=True) or {}
    expression = (data.get('expression') or data.get('cron_expression') or '').strip()

    err = _cron_validation_error(expression)
    if err:
        return jsonify({'valid': False, 'error': 'Invalid cron expression', 'message': err}), 200
    return jsonify({'valid': True, 'message': 'Valid cron expression'}), 200


@jobs_bp.route('/jobs/cron-preview', methods=['POST'])
@jwt_required()
def cron_preview():
    """
    Return the next N run times for a cron expression (JST by default).
    """
    if not request.is_json:
        return jsonify({'error': 'Content-Type must be application/json'}), 400
    data = request.get_json(silent=True) or {}
    expression = (data.get('expression') or data.get('cron_expression') or '').strip()
    count = data.get('count') or 5

    err = _cron_validation_error(expression)
    if err:
        return jsonify({'error': 'Invalid cron expression', 'message': err}), 400

    tz = current_app.config.get('SCHEDULER_TIMEZONE', 'Asia/Tokyo')
    runs = _cron_next_runs(expression, count=int(count))
    return jsonify({'timezone': tz, 'next_runs': runs, 'count': len(runs)}), 200


@jobs_bp.route('/jobs/test-run', methods=['POST'])
@jwt_required()
@role_required('admin', 'user')
def test_run_job():
    """
    Execute a one-off test run for the given job configuration WITHOUT creating a Job or JobExecution.
    Keeps the app quiet: no persisted executions, no notifications.
    """
    if not request.is_json:
        return jsonify({'error': 'Content-Type must be application/json'}), 400
    data = request.get_json(silent=True) or {}

    target_url = (data.get('target_url') or '').strip() or None
    github_owner = (data.get('github_owner') or '').strip() or None
    github_repo = (data.get('github_repo') or '').strip() or None
    github_workflow_name = (data.get('github_workflow_name') or '').strip() or None
    metadata = data.get('metadata') or {}
    if metadata and not isinstance(metadata, dict):
        return jsonify({'error': 'Invalid metadata', 'message': '"metadata" must be an object.'}), 400

    if not target_url and not (github_owner and github_repo and github_workflow_name):
        return jsonify({
            'error': 'Missing target configuration',
            'message': 'Provide target_url or GitHub config (github_owner, github_repo, github_workflow_name).'
        }), 400

    timeout_seconds = float(data.get('timeout_seconds') or 10)
    timeout_seconds = max(1.0, min(timeout_seconds, 30.0))

    if target_url:
        parsed = urlparse(target_url)
        if parsed.scheme not in {'http', 'https'}:
            return jsonify({'error': 'Invalid target_url', 'message': 'Webhook URL must start with http:// or https://'}), 400
        try:
            resp = requests.post(target_url, json=metadata or {}, timeout=timeout_seconds)
            ok = 200 <= resp.status_code < 300
            return jsonify({
                'ok': ok,
                'type': 'webhook',
                'status_code': resp.status_code,
                'message': 'Webhook test run succeeded.' if ok else 'Webhook test run failed.',
            }), 200
        except Exception as e:
            return jsonify({'ok': False, 'type': 'webhook', 'error': 'Request failed', 'message': safe_error_message(e, 'Request failed')}), 200

    token = (os.getenv('GITHUB_TOKEN') or '').strip()
    if not token:
        return jsonify({
            'ok': False,
            'type': 'github',
            'error': 'GitHub token not configured',
            'message': 'Set GITHUB_TOKEN in backend .env to test-run GitHub workflows.',
        }), 200

    ref = None
    if isinstance(metadata, dict):
        ref = (metadata.get('ref') or metadata.get('branch') or '').strip() or None
    ref = ref or 'main'

    dispatch_url = f'https://api.github.com/repos/{github_owner}/{github_repo}/actions/workflows/{github_workflow_name}/dispatches'
    payload = {'ref': ref}
    if metadata:
        payload['inputs'] = metadata

    try:
        resp = requests.post(
            dispatch_url,
            headers={
                'Authorization': f'Bearer {token}',
                'Accept': 'application/vnd.github+json',
                'X-GitHub-Api-Version': '2022-11-28',
            },
            json=payload,
            timeout=timeout_seconds,
        )
        ok = resp.status_code in {201, 204}
        return jsonify({
            'ok': ok,
            'type': 'github',
            'status_code': resp.status_code,
            'message': 'GitHub workflow dispatch triggered.' if ok else 'GitHub workflow dispatch failed.',
        }), 200
    except Exception as e:
        return jsonify({'ok': False, 'type': 'github', 'error': 'Request failed', 'message': safe_error_message(e, 'Request failed')}), 200


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

        # Validate required fields
        required_fields = ['name', 'cron_expression', 'end_date']
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
        cron_err = _cron_validation_error(cron_expression)
        if cron_err:
            return jsonify({
                'error': 'Invalid cron expression',
                'message': cron_err
            }), 400

        # Optional fields
        target_url = data.get('target_url', '').strip() or None
        github_owner = data.get('github_owner', '').strip() or None
        github_repo = data.get('github_repo', '').strip() or None
        github_workflow_name = data.get('github_workflow_name', '').strip() or None
        category = _resolve_category_slug(data.get('category'))
        category_error = _validate_category_slug(category)
        if category_error:
            return jsonify({'error': 'Invalid category', 'message': category_error}), 400
        metadata = data.get('metadata', {})
        enable_email_notifications = data.get('enable_email_notifications', False)
        notification_emails = data.get('notification_emails', []) if enable_email_notifications else []
        notify_on_success = data.get('notify_on_success', False) if enable_email_notifications else False

        # Required lifecycle/ownership fields
        try:
            end_date = _parse_end_date(data.get('end_date'))
        except ValueError as e:
            return jsonify({'error': 'Invalid end_date', 'message': safe_error_message(e, 'Invalid end_date')}), 400
        if not end_date:
            return jsonify({'error': 'Missing required fields', 'message': '"end_date" is required (YYYY-MM-DD).'}), 400
        if end_date < _today_jst():
            return jsonify({'error': 'Invalid end_date', 'message': 'end_date must be today or in the future (JST).'}), 400

        pic_team_raw = data.get('pic_team') or data.get('pic_team_slug')
        pic_team = _resolve_pic_team_slug(pic_team_raw)
        pic_team_error = _validate_pic_team_slug(pic_team)
        if pic_team_error:
            return jsonify({'error': 'Invalid PIC team', 'message': pic_team_error}), 400

        # Validate that at least one target is provided (target_url OR GitHub config)
        if not target_url and not (github_owner and github_repo and github_workflow_name):
            # Allow GitHub jobs without owner; default it to the configured org/owner.
            if github_repo and github_workflow_name and not github_owner:
                github_owner = _get_default_github_owner()
            else:
                return jsonify({
                    'error': 'Missing target configuration',
                    'message': 'Please provide either "target_url" or GitHub Actions configuration (github_owner, github_repo, github_workflow_name)'
                }), 400

        # If this is a GitHub job and owner is omitted, fill it in.
        if not target_url and github_repo and github_workflow_name and not github_owner:
            github_owner = _get_default_github_owner()

        # Re-validate targets after defaulting.
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
            category=category,
            end_date=end_date,
            pic_team=pic_team,
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

        # Add job to APScheduler (best-effort, only if scheduler is running in this process)
        if scheduler.running:
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
                    func=execute_job_with_app_context,
                    trigger=trigger,
                    args=[new_job.id, new_job.name, job_config],
                    id=new_job.id,
                    name=new_job.name,
                    replace_existing=True
                )
                logger.info(f"Job '{new_job.name}' (ID: {new_job.id}) created and scheduled successfully")
            except Exception as e:
                # Rollback database if scheduler fails
                db.session.delete(new_job)
                db.session.commit()
                logger.error(f"Failed to schedule job: {str(e)}")
                return jsonify({
                    'error': 'Failed to schedule job',
                    'message': safe_error_message(e, 'Failed to schedule job')
                }), 500

        # Broadcast notification to all users
        try:
            broadcast_job_created(new_job.name, new_job.id, current_user.email if current_user else 'Unknown')
            logger.info(f"Broadcast notification sent: Job '{new_job.name}' created")
        except Exception as e:
            logger.error(f"Failed to broadcast job created notification: {str(e)}")

        return jsonify({
            'message': 'Job created successfully',
            'job': new_job.to_dict()
        }), 201

    except Exception as e:
        logger.error(f"Error creating job: {str(e)}")
        return jsonify({
            'error': ERROR_INTERNAL_SERVER,
            'message': safe_error_message(e)
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

        # Default GitHub owner:
        # - form field `default_github_owner` (frontend)
        # - env var `DEFAULT_GITHUB_OWNER`
        # - fallback to app default (see `_get_default_github_owner`)
        default_owner = (request.form.get('default_github_owner') or os.getenv('DEFAULT_GITHUB_OWNER') or '').strip()
        if not default_owner:
            default_owner = _get_default_github_owner()
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
            category_raw = _first_non_empty(row, ['category', 'job category', 'job_category'])
            category = _resolve_category_slug(category_raw)
            category_error = _validate_category_slug(category)
            if category_error:
                errors.append({'row': row_index, 'job_name': name, 'error': 'Invalid category', 'message': category_error})
                continue

            end_date_raw = _first_non_empty(row, ['end date', 'end_date'])
            pic_team_raw = _first_non_empty(row, ['pic team', 'pic_team', 'pic team slug', 'pic_team_slug'])
            try:
                end_date = _parse_end_date(end_date_raw)
            except ValueError as e:
                errors.append({'row': row_index, 'job_name': name, 'error': 'Invalid end_date', 'message': safe_error_message(e, 'Invalid end_date')})
                continue
            if not end_date:
                errors.append({'row': row_index, 'job_name': name, 'error': 'Missing required fields', 'message': 'end_date (YYYY-MM-DD) is required.'})
                continue
            if end_date < _today_jst():
                errors.append({'row': row_index, 'job_name': name, 'error': 'Invalid end_date', 'message': 'end_date must be today or in the future (JST).'})
                continue

            pic_team = _resolve_pic_team_slug(pic_team_raw)
            pic_team_error = _validate_pic_team_slug(pic_team)
            if pic_team_error:
                errors.append({'row': row_index, 'job_name': name, 'error': 'Invalid PIC team', 'message': pic_team_error})
                continue

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

            cron_err = _cron_validation_error(cron_expression)
            if cron_err:
                errors.append({'row': row_index, 'job_name': name, 'error': 'Invalid cron expression', 'message': cron_err})
                continue

            is_active = _status_to_active(status)

            metadata: dict = {}
            if request_body:
                try:
                    parsed = json.loads(request_body)
                except Exception as e:
                    errors.append({'row': row_index, 'job_name': name, 'error': 'Invalid JSON in Request Body', 'message': safe_error_message(e, 'Invalid JSON in Request Body')})
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
                created_jobs.append({'name': name, 'is_active': is_active, 'cron_expression': cron_expression, 'end_date': end_date_raw, 'pic_team': pic_team})
                continue

            new_job = Job(
                name=name,
                cron_expression=cron_expression,
                target_url=target_url or None,
                github_owner=effective_owner if not target_url else None,
                github_repo=inferred_repo if not target_url else None,
                github_workflow_name=github_workflow_name if not target_url else None,
                category=category,
                end_date=end_date,
                pic_team=pic_team,
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

        # Schedule active jobs after commit (best-effort, only if scheduler is running in this process).
        scheduling_errors = []
        if scheduler.running:
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
                        func=execute_job_with_app_context,
                        trigger=trigger,
                        args=[job.id, job.name, job_config],
                        id=job.id,
                        name=job.name,
                        replace_existing=True,
                    )
                except Exception as e:
                    logger.error(f"Failed to schedule bulk job '{job.name}': {str(e)}")
                    job.is_active = False
                    scheduling_errors.append({'job_name': job.name, 'error': 'Failed to schedule job', 'message': safe_error_message(e, 'Failed to schedule job')})

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
        return jsonify({'error': 'Invalid CSV', 'message': safe_error_message(e, 'Invalid CSV')}), 400
    except Exception as e:
        logger.error(f"Error bulk uploading jobs: {str(e)}")
        db.session.rollback()
        return jsonify({'error': ERROR_INTERNAL_SERVER, 'message': safe_error_message(e)}), 500


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
        last_exec_rows = (
            db.session.query(JobExecution.job_id, func.max(JobExecution.started_at))
            .group_by(JobExecution.job_id)
            .all()
        )
        last_exec_by_job_id = {job_id: started_at for job_id, started_at in last_exec_rows}

        jobs_payload = []
        for job in jobs:
            payload = job.to_dict()
            last_execution_at = last_exec_by_job_id.get(job.id)
            payload['last_execution_at'] = last_execution_at.isoformat() if last_execution_at else None

            payload['next_execution_at'] = _compute_next_execution_at(job)

            jobs_payload.append(payload)

        return jsonify({
            'count': len(jobs),
            'jobs': jobs_payload,
        }), 200
    except Exception as e:
        logger.error(f"Error listing jobs: {str(e)}")
        return jsonify({
            'error': ERROR_INTERNAL_SERVER,
            'message': safe_error_message(e)
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
        
        payload = job.to_dict()
        last_execution_at = (
            db.session.query(func.max(JobExecution.started_at))
            .filter(JobExecution.job_id == job.id)
            .scalar()
        )
        payload['last_execution_at'] = last_execution_at.isoformat() if last_execution_at else None

        payload['next_execution_at'] = _compute_next_execution_at(job)

        return jsonify({'job': payload}), 200
        
    except Exception as e:
        logger.error(f"Error retrieving job {job_id}: {str(e)}")
        return jsonify({
            'error': ERROR_INTERNAL_SERVER,
            'message': safe_error_message(e)
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
            cron_err = _cron_validation_error(new_cron)
            if cron_err:
                return jsonify({
                    'error': 'Invalid cron expression',
                    'message': cron_err
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

        # If this is a GitHub job and owner is missing, default it.
        if not job.target_url and job.github_repo and job.github_workflow_name and not job.github_owner:
            job.github_owner = _get_default_github_owner()
            needs_scheduler_update = True
        
        # Update metadata if provided
        if 'metadata' in data:
            job.set_metadata(data['metadata'])
            needs_scheduler_update = True

        if 'category' in data:
            category = _resolve_category_slug(data.get('category'))
            category_error = _validate_category_slug(category)
            if category_error:
                return jsonify({'error': 'Invalid category', 'message': category_error}), 400
            if category != job.category:
                job.category = category
                needs_scheduler_update = True

        if 'end_date' in data:
            try:
                parsed_end_date = _parse_end_date(data.get('end_date'))
            except ValueError as e:
                return jsonify({'error': 'Invalid end_date', 'message': safe_error_message(e, 'Invalid end_date')}), 400
            if not parsed_end_date:
                return jsonify({'error': 'Invalid end_date', 'message': 'end_date is required (YYYY-MM-DD).'}), 400
            if parsed_end_date < _today_jst():
                return jsonify({'error': 'Invalid end_date', 'message': 'end_date must be today or in the future (JST).'}), 400
            if parsed_end_date != job.end_date:
                job.end_date = parsed_end_date
                needs_scheduler_update = True

        if 'pic_team' in data or 'pic_team_slug' in data:
            pic_team_raw = data.get('pic_team') or data.get('pic_team_slug')
            pic_team = _resolve_pic_team_slug(pic_team_raw)
            pic_team_error = _validate_pic_team_slug(pic_team)
            if pic_team_error:
                return jsonify({'error': 'Invalid PIC team', 'message': pic_team_error}), 400
            if pic_team != job.pic_team:
                job.pic_team = pic_team
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

        # Guard: cannot (re)enable a job after its end_date.
        if job.is_active and job.end_date and job.end_date < _today_jst():
            return jsonify({
                'error': 'Job expired',
                'message': 'Job cannot be enabled after end_date has passed. Update end_date first.',
            }), 400
        
        # Validate at least one target exists
        if not job.target_url and not (job.github_owner and job.github_repo and job.github_workflow_name):
            return jsonify({
                'error': 'Missing target configuration',
                'message': 'Job must have either target_url or complete GitHub Actions configuration'
            }), 400
        
        # Save to database
        db.session.commit()
        
        # Update scheduler if needed (best-effort, only if scheduler is running in this process)
        if needs_scheduler_update and scheduler.running:
            try:
                scheduler_tz = _get_scheduler_timezone()
                # Remove old job from scheduler
                if scheduler.get_job(job_id):
                    scheduler.remove_job(job_id)
                
                # Add updated job if active
                if job.is_active and not (job.end_date and job.end_date < _today_jst()):
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
                        func=execute_job_with_app_context,
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
                    'message': safe_error_message(e, 'Failed to update scheduler')
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
            'message': safe_error_message(e)
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
        
        # Remove from scheduler if exists (best-effort, only if scheduler is running in this process)
        if scheduler.running:
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
            'message': safe_error_message(e)
        }), 500


@jobs_bp.route('/jobs/<job_id>/execute', methods=['POST'])
@jwt_required()
@role_required('admin', 'user')
def execute_job_now(job_id):
    """
    Execute a job immediately (manual trigger), optionally overriding runtime config.

    Overrides are NOT persisted to the database; they apply only to this execution.

    Expected JSON payload (all optional):
    {
      "metadata": { ... },              // overrides metadata for this run
      "target_url": "https://...",      // only for webhook jobs
      "github_owner": "...",            // only for GitHub jobs
      "github_repo": "...",             // only for GitHub jobs
      "github_workflow_name": "..."     // only for GitHub jobs
    }
    """
    try:
        job = Job.query.get(job_id)
        if not job:
            return jsonify({'error': ERROR_JOB_NOT_FOUND, 'message': f'No job found with ID: {job_id}'}), 404

        # Authorization: admin can execute any; users can execute own jobs
        if not can_modify_job(job):
            return jsonify({'error': 'Insufficient permissions', 'message': 'You can only execute your own jobs'}), 403

        # Guard against executing jobs after end_date
        if job.end_date and job.end_date < _today_jst():
            if job.is_active:
                job.is_active = False
                db.session.commit()
                if scheduler.running:
                    try:
                        if scheduler.get_job(job.id):
                            scheduler.remove_job(job.id)
                    except Exception:
                        pass
            return jsonify({
                'error': 'Job expired',
                'message': 'This job has passed its end_date and was auto-paused.',
            }), 400

        data = request.get_json(silent=True) or {}
        if not isinstance(data, dict):
            return jsonify({'error': 'Invalid payload', 'message': 'JSON body must be an object.'}), 400

        override_metadata = data.get('metadata')
        if override_metadata is not None and not isinstance(override_metadata, dict):
            return jsonify({'error': 'Invalid payload', 'message': '"metadata" must be a JSON object.'}), 400

        github_token = (data.get('github_token') or '').strip() or None
        dispatch_url = (data.get('dispatch_url') or '').strip() or None

        def _parse_dispatch_url(value: str):
            candidate = value if '://' in value else f'https://{value}'
            parsed = urlparse(candidate)
            path = parsed.path.strip('/')
            parts = [p for p in path.split('/') if p]
            # {owner}/{repo}/actions/workflows/{workflow}
            if len(parts) >= 5 and parts[2] == 'actions' and parts[3] == 'workflows':
                return parts[0], parts[1], parts[4]
            raise ValueError('Invalid dispatch URL format. Expected /<owner>/<repo>/actions/workflows/<workflow>.')

        base_config = {
            'target_url': job.target_url,
            'github_owner': job.github_owner,
            'github_repo': job.github_repo,
            'github_workflow_name': job.github_workflow_name,
            'metadata': job.get_metadata(),
            'enable_email_notifications': job.enable_email_notifications,
            'notification_emails': job.get_notification_emails(),
            'notify_on_success': job.notify_on_success,
        }

        # Apply overrides for same job type (do not allow switching target type here)
        if job.target_url:
            if 'target_url' in data:
                base_config['target_url'] = (data.get('target_url') or '').strip() or job.target_url
            # ignore github overrides for webhook jobs
        else:
            # GitHub job
            if dispatch_url:
                try:
                    owner, repo, workflow_name = _parse_dispatch_url(dispatch_url)
                except ValueError as e:
                    return jsonify({'error': 'Invalid payload', 'message': safe_error_message(e, 'Invalid payload')}), 400
                base_config['github_owner'] = owner
                base_config['github_repo'] = repo
                base_config['github_workflow_name'] = workflow_name

            if 'github_owner' in data:
                base_config['github_owner'] = (data.get('github_owner') or '').strip() or job.github_owner
            if 'github_repo' in data:
                base_config['github_repo'] = (data.get('github_repo') or '').strip() or job.github_repo
            if 'github_workflow_name' in data:
                base_config['github_workflow_name'] = (data.get('github_workflow_name') or '').strip() or job.github_workflow_name

            if github_token:
                base_config['github_token'] = github_token

        if override_metadata is not None:
            base_config['metadata'] = override_metadata

        # Validate target config is still present
        if not base_config.get('target_url') and not (
            base_config.get('github_owner') and base_config.get('github_repo') and base_config.get('github_workflow_name')
        ):
            return jsonify({'error': 'Missing target configuration', 'message': 'Job has no valid target configuration to execute.'}), 400

        # Manual execution (runs immediately)
        # Call executor directly to avoid any import/name issues during runtime.
        execute_job(job.id, job.name, base_config, trigger_type='manual')

        return jsonify({'message': 'Job triggered successfully', 'job_id': job.id}), 200
    except Exception as e:
        logger.error(f"Error executing job {job_id}: {str(e)}")
        return jsonify({'error': ERROR_INTERNAL_SERVER, 'message': safe_error_message(e)}), 500


@jobs_bp.route('/jobs/<job_id>/executions', methods=['GET'])
@jwt_required()
def get_job_executions(job_id):
    """
    Get execution history for a specific job.
    
    Query Parameters:
        - limit (optional): Maximum number of executions to return (default: 50, max: 200)
        - status (optional): Filter by status ('success', 'failed', 'running')
        - trigger_type (optional): Filter by trigger type ('scheduled', 'manual')
        - from (optional): ISO date/datetime (inclusive, based on started_at)
        - to (optional): ISO date/datetime (exclusive, based on started_at). Date-only treated as inclusive day.
    
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
        from_raw = request.args.get('from')
        to_raw = request.args.get('to')
        from_dt = _parse_iso_date_or_datetime(from_raw)
        to_dt = _parse_iso_date_or_datetime(to_raw)
        if to_raw and to_dt and len(to_raw.strip()) == 10:
            to_dt = to_dt + timedelta(days=1)
        if from_dt and to_dt and from_dt >= to_dt:
            return jsonify({'error': 'Invalid date range', 'message': '"from" must be earlier than "to".'}), 400
        
        # Build query
        query = JobExecution.query.filter_by(job_id=job_id)
        
        # Apply filters
        if status:
            statuses = [s.strip() for s in status.split(',') if s.strip()]
            if len(statuses) == 1:
                query = query.filter_by(status=statuses[0])
            elif len(statuses) > 1:
                query = query.filter(JobExecution.status.in_(statuses))
        if trigger_type:
            query = query.filter_by(trigger_type=trigger_type)
        if from_dt:
            query = query.filter(JobExecution.started_at >= from_dt)
        if to_dt:
            query = query.filter(JobExecution.started_at < to_dt)
        
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
            'message': safe_error_message(e)
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
            'message': safe_error_message(e)
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
            'message': safe_error_message(e)
        }), 500


@jobs_bp.route('/executions', methods=['GET'])
@jwt_required()
def list_executions():
    """
    List executions across all jobs (All authenticated users).

    Query Parameters:
        - page (optional): Page number (default: 1)
        - limit (optional): Page size (default: 20, max: 200)
        - job_id (optional): Filter by job_id
        - status (optional): success|failed|running (or comma-separated list)
        - trigger_type (optional): scheduled|manual
        - execution_type (optional): github_actions|webhook
        - from (optional): ISO date/datetime (inclusive, based on started_at)
        - to (optional): ISO date/datetime (exclusive, based on started_at). Date-only treated as inclusive day.
    """
    try:
        page = request.args.get('page', default=1, type=int)
        limit = request.args.get('limit', default=20, type=int)
        limit = min(max(limit, 1), 200)
        page = max(page, 1)

        job_id = request.args.get('job_id')
        status = request.args.get('status')
        trigger_type = request.args.get('trigger_type')
        execution_type = request.args.get('execution_type')
        from_raw = request.args.get('from')
        to_raw = request.args.get('to')
        from_dt = _parse_iso_date_or_datetime(from_raw)
        to_dt = _parse_iso_date_or_datetime(to_raw)
        if to_raw and to_dt and len(to_raw.strip()) == 10:
            to_dt = to_dt + timedelta(days=1)
        if from_dt and to_dt and from_dt >= to_dt:
            return jsonify({'error': 'Invalid date range', 'message': '"from" must be earlier than "to".'}), 400

        query = JobExecution.query.join(Job, JobExecution.job_id == Job.id)

        if job_id:
            query = query.filter(JobExecution.job_id == job_id)
        if status:
            statuses = [s.strip() for s in status.split(',') if s.strip()]
            if len(statuses) == 1:
                query = query.filter(JobExecution.status == statuses[0])
            elif len(statuses) > 1:
                query = query.filter(JobExecution.status.in_(statuses))
        if trigger_type:
            query = query.filter(JobExecution.trigger_type == trigger_type)
        if execution_type:
            query = query.filter(JobExecution.execution_type == execution_type)
        if from_dt:
            query = query.filter(JobExecution.started_at >= from_dt)
        if to_dt:
            query = query.filter(JobExecution.started_at < to_dt)

        total = query.count()
        total_pages = (total + limit - 1) // limit if total else 0

        executions = (
            query.order_by(desc(JobExecution.started_at))
            .offset((page - 1) * limit)
            .limit(limit)
            .all()
        )

        payload = []
        for execution in executions:
            data = execution.to_dict()
            data['job_name'] = execution.job.name if execution.job else None
            data['github_repo'] = execution.job.github_repo if execution.job else None
            payload.append(data)

        return jsonify({
            'executions': payload,
            'total': total,
            'page': page,
            'limit': limit,
            'total_pages': total_pages
        }), 200
    except Exception as e:
        logger.error(f"Error listing executions: {str(e)}")
        return jsonify({'error': ERROR_INTERNAL_SERVER, 'message': safe_error_message(e)}), 500


@jobs_bp.route('/executions/<execution_id>', methods=['GET'])
@jwt_required()
def get_execution(execution_id):
    """Get a single execution by ID (All authenticated users)."""
    try:
        execution = JobExecution.query.join(Job, JobExecution.job_id == Job.id).filter(JobExecution.id == execution_id).first()
        if not execution:
            return jsonify({'error': 'Execution not found', 'message': f'No execution found with ID: {execution_id}'}), 404

        data = execution.to_dict()
        data['job_name'] = execution.job.name if execution.job else None
        data['github_repo'] = execution.job.github_repo if execution.job else None

        return jsonify({'execution': data}), 200
    except Exception as e:
        logger.error(f"Error retrieving execution {execution_id}: {str(e)}")
        return jsonify({'error': ERROR_INTERNAL_SERVER, 'message': safe_error_message(e)}), 500


@jobs_bp.route('/executions/statistics', methods=['GET'])
@jwt_required()
def get_execution_statistics():
    """
    Execution summary stats across all jobs (or a single job via job_id).

    Optional query params:
      - job_id: filter to one job
      - from: ISO date/datetime (inclusive, based on started_at)
      - to: ISO date/datetime (exclusive, based on started_at). If a date-only value is provided,
            it will be treated as the start of that day (UTC) + 1 day to make it inclusive for UI.
    """
    try:
        job_id = request.args.get('job_id')
        from_raw = request.args.get('from')
        to_raw = request.args.get('to')

        from_dt = _parse_iso_date_or_datetime(from_raw)
        to_dt = _parse_iso_date_or_datetime(to_raw)

        # If `to` is a date-only string, make it inclusive by adding 1 day (treat as exclusive upper bound).
        if to_raw and to_dt and len(to_raw.strip()) == 10:
            to_dt = to_dt + timedelta(days=1)

        if from_dt and to_dt and from_dt >= to_dt:
            return jsonify({
                'error': 'Invalid date range',
                'message': '"from" must be earlier than "to".',
            }), 400

        base = JobExecution.query
        if job_id:
            base = base.filter(JobExecution.job_id == job_id)
        if from_dt:
            base = base.filter(JobExecution.started_at >= from_dt)
        if to_dt:
            base = base.filter(JobExecution.started_at < to_dt)

        total = base.count()
        successful = base.filter(JobExecution.status == 'success').count()
        failed = base.filter(JobExecution.status == 'failed').count()
        running = base.filter(JobExecution.status == 'running').count()

        avg_duration = base.with_entities(func.avg(JobExecution.duration_seconds)).scalar() or 0.0
        success_rate = (successful / total * 100.0) if total else 0.0

        return jsonify({
            'total_executions': total,
            'successful_executions': successful,
            'failed_executions': failed,
            'running_executions': running,
            'success_rate': success_rate,
            'average_duration_seconds': avg_duration,
            'range': {
                'from': from_dt.isoformat() if from_dt else None,
                'to': to_dt.isoformat() if to_dt else None,
            },
        }), 200
    except Exception as e:
        logger.error(f"Error getting execution statistics: {str(e)}")
        return jsonify({'error': ERROR_INTERNAL_SERVER, 'message': safe_error_message(e)}), 500


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
