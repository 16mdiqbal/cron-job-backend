"""
Async Slack Utilities (Phase 7G).

This is intentionally separate from `src/utils/slack.py` (Flask/sync) to avoid
changing Flask behavior during migration.
"""

import logging
from typing import Optional
from urllib.parse import urlparse

import httpx

logger = logging.getLogger(__name__)


def _is_valid_webhook_url(url: str) -> bool:
    try:
        parsed = urlparse(url)
        if parsed.scheme != "https":
            return False
        if not parsed.netloc:
            return False
        return True
    except Exception:
        return False


async def send_slack_webhook(
    webhook_url: str,
    *,
    text: str,
    channel: Optional[str] = None,
    timeout_s: float = 10.0,
    client: Optional[httpx.AsyncClient] = None,
) -> bool:
    """
    Send a Slack message via incoming webhook.

    Returns True if Slack accepts the payload (HTTP 2xx).
    """
    if not webhook_url or not _is_valid_webhook_url(webhook_url):
        return False

    payload: dict = {"text": text}
    if channel:
        payload["channel"] = channel

    async def _send_with(client_to_use: httpx.AsyncClient) -> bool:
        try:
            resp = await client_to_use.post(webhook_url, json=payload)
            if 200 <= resp.status_code < 300:
                return True
            logger.warning("Slack webhook failed: %s %s", resp.status_code, (resp.text or "")[:200])
            return False
        except Exception as exc:
            logger.warning("Slack webhook request failed: %s", exc)
            return False

    if client is not None:
        return await _send_with(client)

    async with httpx.AsyncClient(timeout=timeout_s) as local_client:
        return await _send_with(local_client)

