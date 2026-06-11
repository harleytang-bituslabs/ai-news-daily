#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""每日 AI 新聞日報產生器。

用法：
    python main.py              # 抓新聞 + 產生日報，寫入 reports/
    python main.py --dry-run    # 只抓新聞並列出，不呼叫 Claude API（測試來源用）
    python main.py --window 24  # 自訂時間窗（小時），預設 13
"""
import argparse
import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from fetcher import fetch_all

BASE_DIR = Path(__file__).resolve().parent
REPORTS_DIR = BASE_DIR / "reports"
LOCAL_TZ = ZoneInfo(os.environ.get("REPORT_TZ", "America/Los_Angeles"))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
log = logging.getLogger("main")


def load_dotenv() -> None:
    """讀取同目錄的 .env（KEY=VALUE 格式），不覆蓋已存在的環境變數。"""
    env_file = BASE_DIR / ".env"
    if not env_file.exists():
        return
    for line in env_file.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip())


def post_to_slack(text: str) -> None:
    """若設定了 SLACK_WEBHOOK_URL，把日報推到 Slack（可選）。"""
    webhook = os.environ.get("SLACK_WEBHOOK_URL")
    if not webhook:
        return
    import requests
    try:
        resp = requests.post(webhook, json={"text": text[:39000]}, timeout=20)
        resp.raise_for_status()
        log.info("已推送到 Slack")
    except Exception as exc:
        log.warning("Slack 推送失敗：%s", exc)


def main() -> int:
    parser = argparse.ArgumentParser(description="每日 AI 新聞日報")
    parser.add_argument("--dry-run", action="store_true", help="只抓新聞不呼叫 Claude")
    parser.add_argument("--window", type=int, default=13, help="抓取時間窗（小時），預設 13（12 小時 + 1 小時緩衝）")
    parser.add_argument("--max-items", type=int, default=40, help="送給 Claude 的新聞上限")
    args = parser.parse_args()

    load_dotenv()

    now = datetime.now(LOCAL_TZ)
    edition = "早報" if now.hour < 12 else "晚報"
    suffix = "am" if now.hour < 12 else "pm"
    edition_label = f"{now:%Y-%m-%d} AI {edition}"

    items = fetch_all(window_hours=args.window, max_items=args.max_items)
    if not items:
        log.warning("時間窗內沒有抓到任何新聞，結束")
        return 0

    # 原始素材落地保存（JSONL）——之後要打標、做 embedding、建向量庫都從這裡回填
    import json
    raw_dir = BASE_DIR / "data" / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    raw_path = raw_dir / f"{now:%Y-%m-%d}-{suffix}.jsonl"
    with raw_path.open("w", encoding="utf-8") as f:
        for it in items:
            f.write(json.dumps(it, ensure_ascii=False) + "\n")
    log.info("原始素材已存檔 %s（%d 則）", raw_path, len(items))

    if args.dry_run:
        for it in items:
            print(f"[{it['source']}] {it['title']}  ({it['published']})")
        print(f"\n共 {len(items)} 則（--dry-run，未呼叫 Claude）")
        return 0

    if not os.environ.get("ANTHROPIC_API_KEY"):
        log.error("缺少 ANTHROPIC_API_KEY（請設定環境變數或寫入 .env）")
        return 1

    from summarizer import summarize
    digest = summarize(items, edition_label)

    header = f"# {edition_label}\n\n> 產生時間：{now:%Y-%m-%d %H:%M %Z}｜資料窗：過去 {args.window} 小時｜素材 {len(items)} 則\n\n"
    report = header + digest

    REPORTS_DIR.mkdir(exist_ok=True)
    out_path = REPORTS_DIR / f"{now:%Y-%m-%d}-{suffix}.md"
    out_path.write_text(report, encoding="utf-8")
    (REPORTS_DIR / "latest.md").write_text(report, encoding="utf-8")
    log.info("日報已寫入 %s", out_path)

    post_to_slack(report)
    return 0


if __name__ == "__main__":
    sys.exit(main())
