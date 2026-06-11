"""RSS / Atom feed 來源（官方 blog 與媒體 AI 專區）。"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

import feedparser

from ai_news.models import NewsItem
from ai_news.sources.base import clean_text, http_get, struct_time_to_datetime


@dataclass(frozen=True)
class RssSource:
    name: str
    url: str
    weight: int

    def fetch(self, cutoff: datetime) -> list[NewsItem]:
        parsed = feedparser.parse(http_get(self.url).content)
        items = []
        for entry in parsed.entries:
            ts = entry.get("published_parsed") or entry.get("updated_parsed")
            link = entry.get("link")
            if not ts or not link:
                continue
            published = struct_time_to_datetime(ts)
            if published < cutoff:
                continue
            items.append(
                NewsItem(
                    title=clean_text(entry.get("title"), 300),
                    url=link,
                    source=self.name,
                    published=published,
                    summary=clean_text(entry.get("summary")),
                    weight=self.weight,
                )
            )
        return items


# 這些媒體或官方 blog 本身就是 AI 專區，不需再做關鍵字過濾。
# weight：3=官方一手消息, 2=媒體/高品質策展。
# 註：Anthropic / Meta / Microsoft 官方沒有可用的公開 RSS（404/403），
#     其消息由媒體 feed 與 Hacker News 覆蓋。
DEFAULT_FEEDS = [
    RssSource("OpenAI", "https://openai.com/news/rss.xml", 3),
    RssSource("Google DeepMind", "https://deepmind.google/blog/rss.xml", 3),
    RssSource("Google AI Blog", "https://blog.google/technology/ai/rss/", 3),
    RssSource("Hugging Face", "https://huggingface.co/blog/feed.xml", 3),
    RssSource("NVIDIA", "https://blogs.nvidia.com/blog/category/generative-ai/feed/", 2),
    RssSource("TechCrunch AI", "https://techcrunch.com/category/artificial-intelligence/feed/", 2),
    RssSource("The Verge AI", "https://www.theverge.com/rss/ai-artificial-intelligence/index.xml", 2),
    RssSource("VentureBeat AI", "https://venturebeat.com/category/ai/feed/", 2),
    RssSource("Ars Technica AI", "https://arstechnica.com/ai/feed/", 2),
    RssSource("MIT Tech Review AI", "https://www.technologyreview.com/topic/artificial-intelligence/feed", 2),
    RssSource("Simon Willison", "https://simonwillison.net/atom/everything/", 2),
]
