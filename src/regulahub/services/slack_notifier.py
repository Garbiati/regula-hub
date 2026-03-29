"""Slack webhook notifier for pipeline alerts."""

import logging

import httpx

from regulahub.config import get_pipeline_settings

logger = logging.getLogger(__name__)


async def send_slack_alert(message: str, *, context: dict | None = None) -> bool:
    """Send alert to Slack via incoming webhook. Returns True if delivered.

    Does not raise on failure — logs a warning and returns False.
    """
    settings = get_pipeline_settings()
    url = settings.slack_webhook_url
    if not url:
        logger.debug("Slack webhook URL not configured, skipping alert")
        return False

    blocks = [
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": f":rotating_light: *RegulaHub Pipeline Alert*\n{message}"},
        },
    ]
    if context:
        fields = [{"type": "mrkdwn", "text": f"*{k}:* {v}"} for k, v in context.items()]
        blocks.append({"type": "section", "fields": fields})

    payload = {"blocks": blocks}

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(url, json=payload)
            if resp.status_code == 200:
                logger.info("Slack alert sent successfully")
                return True
            logger.warning("Slack webhook returned %s: %s", resp.status_code, resp.text[:200])
            return False
    except Exception:
        logger.warning("Failed to send Slack alert")
        return False
