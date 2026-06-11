"""Hacker News 來源（Algolia 搜尋 API：AI 關鍵字 + 分數門檻）。"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone

from ai_news.models import NewsItem
from ai_news.sources.base import clean_text, http_get

API_URL = "https://hn.algolia.com/api/v1/search_by_date"

DEFAULT_QUERIES = ["AI", "LLM", "OpenAI", "Anthropic", "Claude", "Gemini", "DeepSeek", "open model"]


@dataclass(frozen=True)
class HackerNewsSource:
    name: str = "Hacker News"
    queries: list = field(default_factory=lambda: list(DEFAULT_QUERIES))
    min_points: int = 30

    def fetch(self, cutoff: datetime) -> list[NewsItem]:
        items, seen_ids = [], set()
        cutoff_ts = int(cutoff.timestamp())
        for query in self.queries:
            resp = http_get(
                API_URL,
                params={
                    "query": query,
                    "tags": "story",
                    "hitsPerPage": 30,
                    "numericFilters": f"created_at_i>{cutoff_ts},points>{self.min_points}",
                },
            )
            for hit in resp.json().get("hits", []):
                story_id = hit["objectID"]
                if story_id in seen_ids:
                    continue
                seen_ids.add(story_id)
                discussion = f"https://news.ycombinator.com/item?id={story_id}"
                items.append(
                    NewsItem(
                        title=clean_text(hit.get("title"), 300),
                        url=hit.get("url") or discussion,
                        source=self.name,
                        published=datetime.fromtimestamp(hit["created_at_i"], tz=timezone.utc),
                        score=hit.get("points", 0),
                        discussion=discussion,
                    )
                )
        return items
