"""通知通道。目前只有 Slack incoming webhook；要加 Telegram/Email 在這裡擴充。"""
from __future__ import annotations

import logging

import requests

log = logging.getLogger(__name__)

SLACK_TEXT_LIMIT = 39000  # Slack 訊息上限 40k 字元，留緩衝


def post_to_slack(text: str, webhook_url: str | None) -> None:
    if not webhook_url:
        return
    try:
        resp = requests.post(webhook_url, json={"text": text[:SLACK_TEXT_LIMIT]}, timeout=20)
        resp.raise_for_status()
        log.info("已推送到 Slack")
    except requests.RequestException as exc:
        log.warning("Slack 推送失敗：%s", exc)
