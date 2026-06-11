"""命令列入口：ai-news 或 python -m ai_news。"""
from __future__ import annotations

import argparse
import logging
import os
import sys
from pathlib import Path

from ai_news.config import (
    DEFAULT_MAX_ITEMS,
    DEFAULT_WINDOW_HOURS,
    Settings,
    load_dotenv,
)
from ai_news.pipeline import run

REQUIRED_KEY_BY_PROVIDER = {
    "anthropic": "ANTHROPIC_API_KEY",
    "openai": "OPENAI_API_KEY",
    "google": "GOOGLE_API_KEY",
}


def main(argv: list[str] = None) -> int:
    parser = argparse.ArgumentParser(prog="ai-news", description="每日 AI 新聞日報產生器")
    parser.add_argument("--dry-run", action="store_true", help="只抓新聞並列出，不呼叫 LLM")
    parser.add_argument(
        "--window", type=int, default=DEFAULT_WINDOW_HOURS,
        help=f"抓取時間窗（小時），預設 {DEFAULT_WINDOW_HOURS}",
    )
    parser.add_argument(
        "--max-items", type=int, default=DEFAULT_MAX_ITEMS,
        help=f"送給 LLM 的新聞上限，預設 {DEFAULT_MAX_ITEMS}",
    )
    parser.add_argument(
        "--base-dir", type=Path, default=Path.cwd(),
        help="工作目錄（.env / reports / data 的所在），預設目前目錄",
    )
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

    base_dir = args.base_dir.resolve()
    load_dotenv(base_dir)
    settings = Settings.from_env(base_dir, window_hours=args.window, max_items=args.max_items)

    required_key = REQUIRED_KEY_BY_PROVIDER[settings.model.provider]
    if not args.dry_run and not os.environ.get(required_key):
        logging.error("缺少 %s（SUMMARIZER_MODEL=%s）", required_key, settings.model)
        return 1

    run(settings, dry_run=args.dry_run)
    return 0


if __name__ == "__main__":
    sys.exit(main())
