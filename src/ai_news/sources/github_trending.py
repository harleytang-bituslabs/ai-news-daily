"""GitHub Trending 來源（每日熱榜，無官方 API，輕量解析 HTML）。

非 AI 的 repo 不在這裡過濾——prompt 要求 LLM 在彙整時略過。
解析邏輯抽成純函式 parse_trending() 以便單元測試。
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timezone

from ai_news.models import NewsItem
from ai_news.sources.base import clean_text, http_get

TRENDING_URL = "https://github.com/trending?since=daily"

# repo 連結在 <h2> 標題內（避免抓到 sponsors/login 等其他連結）
_REPO_RE = re.compile(r'<h2[^>]*>.*?href="/([A-Za-z0-9_.\-]+/[A-Za-z0-9_.\-]+)"', re.S)
_DESC_RE = re.compile(r'<p class="col-9[^"]*">\s*(.*?)\s*</p>', re.S)
_STARS_RE = re.compile(r"([\d,]+)\s+stars today")
_LANG_RE = re.compile(r'itemprop="programmingLanguage">([^<]+)<')


def parse_trending(page_html: str, limit: int) -> list[NewsItem]:
    now = datetime.now(timezone.utc)
    items = []
    for chunk in page_html.split('<article class="Box-row">')[1 : limit + 1]:
        repo_match = _REPO_RE.search(chunk)
        if not repo_match:
            continue
        repo = repo_match.group(1)
        desc = _DESC_RE.search(chunk)
        stars = _STARS_RE.search(chunk)
        lang = _LANG_RE.search(chunk)
        stars_today = int(stars.group(1).replace(",", "")) if stars else 0
        items.append(
            NewsItem(
                title=repo + (f"（{lang.group(1)}）" if lang else ""),
                url=f"https://github.com/{repo}",
                source="GitHub Trending",
                published=now,
                summary=clean_text(desc.group(1)) if desc else "",
                weight=2,
                score=stars_today,
                extra={"stars_today": stars_today},
            )
        )
    return items


@dataclass(frozen=True)
class GitHubTrendingSource:
    name: str = "GitHub Trending"
    limit: int = 15

    def fetch(self, cutoff: datetime) -> list[NewsItem]:  # noqa: ARG002 - trending 是日榜，不看 cutoff
        return parse_trending(http_get(TRENDING_URL).text, self.limit)
