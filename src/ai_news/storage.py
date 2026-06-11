"""落地保存：原始素材 JSONL 與日報 Markdown。"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from ai_news.models import NewsItem

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class Edition:
    """一期日報（早報/晚報）。"""

    now: datetime
    window_hours: int

    @property
    def is_morning(self) -> bool:
        return self.now.hour < 12

    @property
    def suffix(self) -> str:
        return "am" if self.is_morning else "pm"

    @property
    def label(self) -> str:
        return f"{self.now:%Y-%m-%d} AI {'早報' if self.is_morning else '晚報'}"

    @property
    def basename(self) -> str:
        return f"{self.now:%Y-%m-%d}-{self.suffix}"


def archive_raw(items: list[NewsItem], raw_dir: Path, edition: Edition) -> Path:
    """原始素材寫入 JSONL——之後打標、embedding、建向量庫都從這裡回填。"""
    raw_dir.mkdir(parents=True, exist_ok=True)
    path = raw_dir / f"{edition.basename}.jsonl"
    with path.open("w", encoding="utf-8") as f:
        for item in items:
            f.write(json.dumps(item.to_record(), ensure_ascii=False) + "\n")
    log.info("原始素材已存檔 %s（%d 則）", path, len(items))
    return path


def write_report(digest: str, reports_dir: Path, edition: Edition, item_count: int) -> Path:
    header = (
        f"# {edition.label}\n\n"
        f"> 產生時間：{edition.now:%Y-%m-%d %H:%M %Z}｜"
        f"資料窗：過去 {edition.window_hours} 小時｜素材 {item_count} 則\n\n"
    )
    report = header + digest
    reports_dir.mkdir(parents=True, exist_ok=True)
    path = reports_dir / f"{edition.basename}.md"
    path.write_text(report, encoding="utf-8")
    (reports_dir / "latest.md").write_text(report, encoding="utf-8")
    log.info("日報已寫入 %s", path)
    return path
