"""主流程：抓取 -> 去重排序 -> 存檔 -> 摘要 -> 輸出。"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from ai_news.config import Settings
from ai_news.models import NewsItem, dedupe, rank
from ai_news.notify import post_to_slack
from ai_news.sources import Source, default_sources
from ai_news.storage import Edition, archive_raw, write_report
from ai_news.summarize import summarize

log = logging.getLogger(__name__)


def collect(sources: list[Source], window_hours: int, max_items: int) -> list[NewsItem]:
    """抓所有來源（單一來源失敗只記 warning）、去重、排序、截斷。"""
    cutoff = datetime.now(timezone.utc) - timedelta(hours=window_hours)
    items: list[NewsItem] = []
    for source in sources:
        try:
            fetched = source.fetch(cutoff)
            log.info("%-20s %d 則", source.name, len(fetched))
            items.extend(fetched)
        except Exception as exc:
            log.warning("%s 抓取失敗：%s", source.name, exc)

    deduped = dedupe(items)
    ranked = rank(deduped, max_items)
    log.info("共 %d 則（去重後 %d，取前 %d）", len(items), len(deduped), len(ranked))
    return ranked


def run(settings: Settings, dry_run: bool = False) -> str | None:
    """執行一期日報。回傳日報內容（dry-run 或無素材時回傳 None）。"""
    edition = Edition(now=datetime.now(ZoneInfo(settings.timezone)), window_hours=settings.window_hours)
    items = collect(default_sources(), settings.window_hours, settings.max_items)
    if not items:
        log.warning("時間窗內沒有抓到任何新聞，結束")
        return None

    if dry_run:
        for item in items:
            print(f"[{item.source}] {item.title}  ({item.published.isoformat()})")
        print(f"\n共 {len(items)} 則（--dry-run，未呼叫 LLM）")
        return None

    archive_raw(items, settings.raw_data_dir, edition)
    digest = summarize(items, edition.label, settings.model)
    write_report(digest, settings.reports_dir, edition, len(items))
    post_to_slack(digest, settings.slack_webhook)
    return digest
