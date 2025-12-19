import logging
from typing import Optional
from urllib.parse import urlparse
import requests

logger = logging.getLogger(__name__)


def _is_valid_webhook_url(url: str) -> bool:
    try:
        parsed = urlparse(url)
        if parsed.scheme != 'https':
            return False
        if not parsed.netloc:
            return False
        return True
    except Exception:
        return False


def send_slack_message(webhook_url: str, text: str, channel: Optional[str] = None) -> bool:
    """
    Send a Slack message via incoming webhook.
    Returns True if Slack accepts the payload (HTTP 2xx).
    """
    if not webhook_url or not _is_valid_webhook_url(webhook_url):
        return False

    payload: dict = {'text': text}
    if channel:
        payload['channel'] = channel

    try:
        resp = requests.post(webhook_url, json=payload, timeout=10)
        if 200 <= resp.status_code < 300:
            return True
        logger.warning(f"Slack webhook failed: {resp.status_code} {resp.text[:200]}")
        return False
    except Exception as e:
        logger.warning(f"Slack webhook request failed: {e}")
        return False
