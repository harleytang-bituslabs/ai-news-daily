"""通知通道。目前只有 Slack incoming webhook；要加 Telegram/Email 在這裡擴充。"""
from __future__ import annotations

import logging

import requests

log = logging.getLogger(__name__)

SLACK_TEXT_LIMIT = 39000  # Slack 訊息上限 40k 字元，留緩衝


def broadcast_to_slack(text: str, webhook_urls: list[str]) -> int:
    """推送到多個 Slack webhook（群推送），單一 webhook 失敗不影響其他。回傳成功數。"""
    sent = 0
    for index, url in enumerate(webhook_urls, start=1):
        try:
            resp = requests.post(url, json={"text": text[:SLACK_TEXT_LIMIT]}, timeout=20)
            resp.raise_for_status()
            sent += 1
        except requests.RequestException as exc:
            log.warning("Slack webhook #%d 推送失敗：%s", index, exc)
    if webhook_urls:
        log.info("Slack 推送：%d/%d 成功", sent, len(webhook_urls))
    return sent
