"""新聞來源註冊。新增來源：實作 base.Source 協定後加進 default_sources()。"""
from __future__ import annotations

from ai_news.sources.base import Source
from ai_news.sources.github_trending import GitHubTrendingSource
from ai_news.sources.hackernews import HackerNewsSource
from ai_news.sources.hf_papers import HFPapersSource
from ai_news.sources.reddit import DEFAULT_SUBREDDITS
from ai_news.sources.rss import DEFAULT_FEEDS


def default_sources() -> list[Source]:
    return [
        *DEFAULT_FEEDS,
        HackerNewsSource(),
        *DEFAULT_SUBREDDITS,
        GitHubTrendingSource(),
        HFPapersSource(),
    ]
