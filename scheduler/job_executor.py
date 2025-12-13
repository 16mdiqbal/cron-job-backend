import logging
import requests
import os
from datetime import datetime, timezone
from models import db, JobExecution

logger = logging.getLogger(__name__)


def execute_job(job_id, job_name, job_config, trigger_type='scheduled'):
    """
    Execute a scheduled job by triggering GitHub Actions workflow or calling a webhook URL.
    
    This function is called by APScheduler when a job is triggered.
    It supports two execution modes:
    1. GitHub Actions workflow dispatch (if github_owner, github_repo, github_workflow_name provided)
    2. Generic webhook call (if target_url provided)
    
    Args:
        job_id (str): The unique identifier of the job
        job_name (str): The name of the job
        job_config (dict): Job configuration containing:
            - target_url (optional): Generic webhook URL
            - github_owner (optional): GitHub repository owner
            - github_repo (optional): GitHub repository name
            - github_workflow_name (optional): GitHub workflow file name
            - metadata (optional): Job metadata to pass as workflow inputs
        trigger_type (str): Type of trigger ('scheduled' or 'manual')
    """
    logger.info(f"Executing job '{job_name}' (ID: {job_id}) at {datetime.now(timezone.utc).isoformat()}")
    
    # Create execution record
    execution = JobExecution(job_id=job_id, trigger_type=trigger_type, status='running')
    db.session.add(execution)
    db.session.commit()
    
    try:
        # Priority 1: GitHub Actions workflow dispatch
        if job_config.get('github_owner') and job_config.get('github_repo') and job_config.get('github_workflow_name'):
            result = execute_github_actions(job_name, job_config, execution)
        
        # Priority 2: Generic webhook URL
        elif job_config.get('target_url'):
            result = execute_webhook(job_name, job_config['target_url'], execution)
        
        else:
            error_msg = f"Job '{job_name}' has no valid target (neither GitHub Actions nor webhook URL)"
            logger.error(error_msg)
            execution.mark_completed('failed', error_message=error_msg)
            db.session.commit()
        
    except Exception as e:
        error_msg = f"Unexpected error executing job '{job_name}': {str(e)}"
        logger.error(error_msg)
        execution.mark_completed('failed', error_message=error_msg)
        db.session.commit()


def execute_github_actions(job_name, job_config, execution):
    """
    Trigger a GitHub Actions workflow dispatch.
    
    Args:
        job_name (str): The name of the job
        job_config (dict): Configuration with github_owner, github_repo, github_workflow_name, metadata
        execution (JobExecution): The execution record to update
    """
    github_token = os.getenv('GITHUB_TOKEN')
    if not github_token:
        error_msg = f"GitHub token not configured. Cannot trigger workflow for job '{job_name}'"
        logger.error(error_msg)
        execution.mark_completed('failed', error_message=error_msg)
        db.session.commit()
        return
    
    owner = job_config['github_owner']
    repo = job_config['github_repo']
    workflow_name = job_config['github_workflow_name']
    metadata = job_config.get('metadata', {})
    
    # GitHub API endpoint for workflow dispatch
    url = f"https://api.github.com/repos/{owner}/{repo}/actions/workflows/{workflow_name}/dispatches"
    
    # Update execution record with target
    execution.execution_type = 'github_actions'
    execution.target = f"{owner}/{repo}/{workflow_name}"
    db.session.commit()
    
    headers = {
        'Authorization': f'token {github_token}',
        'Accept': 'application/vnd.github.v3+json',
        'Content-Type': 'application/json'
    }
    
    # Use branch from metadata or default to 'master'
    ref = metadata.get('branchDetails', 'master')
    
    payload = {
        'ref': ref,
        'inputs': metadata  # Pass all metadata as workflow inputs
    }
    
    logger.info(f"Triggering GitHub Actions workflow: {owner}/{repo}/{workflow_name}")
    logger.info(f"Branch: {ref}")
    logger.info(f"Inputs: {metadata}")
    
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=10)
        
        if response.status_code == 204:
            logger.info(f"Job '{job_name}' - GitHub Actions workflow triggered successfully")
            execution.mark_completed('success', response_status=204, output=f"Workflow triggered successfully on branch {ref}")
        else:
            error_msg = f"GitHub Actions dispatch failed. Status: {response.status_code}, Response: {response.text}"
            logger.error(f"Job '{job_name}' - {error_msg}")
            execution.mark_completed('failed', response_status=response.status_code, error_message=error_msg)
        
        db.session.commit()
    
    except requests.exceptions.RequestException as e:
        error_msg = f"GitHub Actions request failed: {str(e)}"
        logger.error(f"Job '{job_name}' - {error_msg}")
        execution.mark_completed('failed', error_message=error_msg)
        db.session.commit()


def execute_webhook(job_name, target_url, execution):
    """
    Call a generic webhook URL.
    
    Args:
        job_name (str): The name of the job
        target_url (str): The webhook URL to call
        execution (JobExecution): The execution record to update
    """
    logger.info(f"Calling webhook: {target_url}")
    
    # Update execution record with target
    execution.execution_type = 'webhook'
    execution.target = target_url
    db.session.commit()
    
    try:
        response = requests.get(target_url, timeout=10)
        logger.info(f"Job '{job_name}' - Webhook called successfully. Status: {response.status_code}")
        
        # Truncate response text if too long
        output = response.text[:1000] if len(response.text) > 1000 else response.text
        
        if response.status_code >= 200 and response.status_code < 300:
            execution.mark_completed('success', response_status=response.status_code, output=output)
        else:
            execution.mark_completed('failed', response_status=response.status_code, 
                                   error_message=f"Webhook returned status {response.status_code}", 
                                   output=output)
        
        db.session.commit()
    
    except requests.exceptions.RequestException as e:
        error_msg = f"Webhook call failed: {str(e)}"
        logger.error(f"Job '{job_name}' - {error_msg}")
        execution.mark_completed('failed', error_message=error_msg)
        db.session.commit()


def trigger_job_manually(job_id, job_name, job_config):
    """
    Manually trigger a job outside of its scheduled time.
    
    This function is called when the /api/jobs/<job_id>/trigger endpoint is invoked.
    
    Args:
        job_id (str): The unique identifier of the job
        job_name (str): The name of the job
        job_config (dict): Job configuration
    """
    logger.info(f"Manually triggering job '{job_name}' (ID: {job_id})")
    execute_job(job_id, job_name, job_config, trigger_type='manual')
