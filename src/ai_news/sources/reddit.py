"""Reddit 來源。

JSON API 會擋雲端 IP（403），改走 RSS 端點（實測可用）。
RSS 不含分數，靠「過去一天 top 排序」本身當品質門檻、取前 N 則。
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

import feedparser

from ai_news.models import NewsItem
from ai_news.sources.base import clean_text, http_get, struct_time_to_datetime


@dataclass(frozen=True)
class RedditSource:
    subreddit: str
    limit: int

    @property
    def name(self) -> str:
        return f"r/{self.subreddit}"

    def fetch(self, cutoff: datetime) -> list[NewsItem]:
        resp = http_get(
            f"https://www.reddit.com/r/{self.subreddit}/top/.rss",
            params={"t": "day"},
        )
        parsed = feedparser.parse(resp.content)
        items = []
        for entry in parsed.entries[: self.limit]:
            link = entry.get("link")
            if not link:
                continue
            ts = entry.get("published_parsed") or entry.get("updated_parsed")
            published = struct_time_to_datetime(ts) if ts else datetime.now(timezone.utc)
            items.append(
                NewsItem(
                    title=clean_text(entry.get("title"), 300),
                    url=link,
                    source=self.name,
                    published=published,
                    summary=clean_text(entry.get("summary")),
                    discussion=link,
                )
            )
        return items


DEFAULT_SUBREDDITS = [
    RedditSource("LocalLLaMA", limit=8),
    RedditSource("MachineLearning", limit=5),
    RedditSource("artificial", limit=5),
]
