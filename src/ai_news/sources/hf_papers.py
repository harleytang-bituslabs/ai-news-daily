"""Hugging Face Daily Papers 來源——社群每日票選的熱門論文。"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from ai_news.models import NewsItem
from ai_news.sources.base import clean_text, http_get

API_URL = "https://huggingface.co/api/daily_papers"


@dataclass(frozen=True)
class HFPapersSource:
    name: str = "HF Daily Papers"
    limit: int = 10

    def fetch(self, cutoff: datetime) -> list[NewsItem]:  # noqa: ARG002 - 日榜，不看 cutoff
        entries = http_get(API_URL, params={"limit": 30}).json()
        entries.sort(key=lambda e: e.get("paper", {}).get("upvotes", 0), reverse=True)
        items = []
        for entry in entries[: self.limit]:
            paper = entry.get("paper", {})
            paper_id = paper.get("id")
            if not paper_id:
                continue
            published_raw = entry.get("publishedAt")
            published = (
                datetime.fromisoformat(published_raw.replace("Z", "+00:00"))
                if published_raw
                else datetime.now(timezone.utc)
            )
            items.append(
                NewsItem(
                    title=clean_text(paper.get("title"), 300),
                    url=f"https://huggingface.co/papers/{paper_id}",
                    source=self.name,
                    published=published,
                    summary=clean_text(paper.get("summary")),
                    weight=2,
                    score=paper.get("upvotes", 0),
                )
            )
        return items
