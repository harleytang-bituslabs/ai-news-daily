"""通知通道。目前只有 Slack incoming webhook；要加 Telegram/Email 在這裡擴充。"""
from __future__ import annotations

import logging
import re

import requests

log = logging.getLogger(__name__)

SLACK_TEXT_LIMIT = 39000  # Slack 訊息上限 40k 字元，留緩衝

_HEADING_RE = re.compile(r"^#{1,6}\s+(.*)$")
_BOLD_RE = re.compile(r"\*\*(.+?)\*\*")
_LINK_RE = re.compile(r"\[([^\]]+)\]\((https?://[^)\s]+)\)")
_HR_RE = re.compile(r"^\s*(?:-{3,}|\*{3,}|_{3,})\s*$")
_BULLET_RE = re.compile(r"^(\s*)-\s+")


def markdown_to_mrkdwn(text: str) -> str:
    """標準 Markdown -> Slack mrkdwn。

    Slack 不渲染 # 標題、**粗體**、---、[文字](URL)，會原樣顯示成符號。
    逐行轉換：標題變整行粗體、**→*、連結變 <url|文字>、水平線變長橫線、
    "- " 列表變 "• "；程式碼圍欄內原樣保留。報告 .md 檔不經過這裡，維持標準 Markdown。
    """
    lines = []
    in_fence = False
    for line in text.splitlines():
        if line.lstrip().startswith("```"):
            in_fence = not in_fence
            lines.append(line)
            continue
        if in_fence:
            lines.append(line)
            continue
        heading = _HEADING_RE.match(line)
        if heading:
            content = _BOLD_RE.sub(r"\1", heading.group(1).strip())  # 標題內的 ** 去掉，整行加粗
            content = _LINK_RE.sub(r"<\2|\1>", content)
            lines.append(f"*{content}*")
            continue
        if _HR_RE.match(line):
            lines.append("──────────")
            continue
        converted = _LINK_RE.sub(r"<\2|\1>", line)
        converted = _BOLD_RE.sub(r"*\1*", converted)
        lines.append(_BULLET_RE.sub(r"\1• ", converted))
    return "\n".join(lines)


def broadcast_to_slack(text: str, webhook_urls: list[str]) -> int:
    """推送到多個 Slack webhook（群推送），單一 webhook 失敗不影響其他。回傳成功數。"""
    mrkdwn = markdown_to_mrkdwn(text)
    sent = 0
    for index, url in enumerate(webhook_urls, start=1):
        try:
            resp = requests.post(url, json={"text": mrkdwn[:SLACK_TEXT_LIMIT]}, timeout=20)
            resp.raise_for_status()
            sent += 1
        except requests.RequestException as exc:
            log.warning("Slack webhook #%d 推送失敗：%s", index, exc)
    if webhook_urls:
        log.info("Slack 推送：%d/%d 成功", sent, len(webhook_urls))
    return sent
