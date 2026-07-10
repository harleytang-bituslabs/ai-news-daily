"""follow-builders feed 來源——消費上游 GitHub Actions 預先產生的 feed JSON。

上游（github.com/zarazhangrui/follow-builders）每天 ~06:17 UTC 抓取 26 位 AI Builder
的 X 帳號、6 檔 Podcast（含 pod2txt 轉錄稿）與 Anthropic Engineering / Claude Blog
兩個官方 blog，把「上次執行以來的新內容」提交成 feed-*.json。這裡直接讀公開
raw URL，不需要 X API token 或 pod2txt key。

新鮮度門控：上游一天產生一次、本管線一天跑兩班——若按單條時間過 cutoff 會
系統性漏掉約一半內容，完全忽略 cutoff 則兩班重複。因此以頂層 generatedAt 做
整包門控：generatedAt 落在本次視窗內才回傳全部條目，否則整包跳過；每天恰好
納入一班（正常情況為早班），上游延遲時晚班自動撿起。
"""
from __future__ import annotations

import logging
import os
import re
from dataclasses import dataclass
from datetime import datetime, timezone

from ai_news.models import NewsItem
from ai_news.sources.base import Source, clean_text, http_get

log = logging.getLogger(__name__)

DEFAULT_FEED_BASE = "https://raw.githubusercontent.com/zarazhangrui/follow-builders/main"

# 轉錄稿裡的說話人標記，如 "Speaker 1 | 00:00 - 00:14"
_SPEAKER_RE = re.compile(r"Speaker \d+ \| [\d:]+ - [\d:]+")


def _parse_iso(raw: str | None) -> datetime | None:
    if not raw:
        return None
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None


def _feed_generated_at(data: dict, cutoff: datetime, feed_name: str) -> datetime | None:
    """回傳視窗內的 generatedAt；過期或缺失回 None（整包跳過，fail-closed 防重複）。"""
    generated = _parse_iso(data.get("generatedAt"))
    if generated is None:
        log.warning("%s feed 缺少可解析的 generatedAt，整包跳過", feed_name)
        return None
    if generated < cutoff:
        return None
    return generated


def _parse_blog_date(raw: str | None, fallback: datetime) -> datetime:
    """blog 的 publishedAt 沒有統一格式：Anthropic Engineering 是 null，
    Claude Blog 是 "May 19, 2026"。依次試 ISO、英文日期，都失敗用 feed 生成時間。"""
    parsed = _parse_iso(raw)
    if parsed is not None:
        return parsed
    if raw:
        try:
            return datetime.strptime(raw, "%B %d, %Y").replace(tzinfo=timezone.utc)
        except ValueError:
            pass
    return fallback


def parse_x_feed(data: dict, cutoff: datetime, limit: int) -> list[NewsItem]:
    generated = _feed_generated_at(data, cutoff, "X/Twitter")
    if generated is None:
        return []
    items = []
    for builder in data.get("x", []):
        name = builder.get("name") or builder.get("handle") or ""
        handle = builder.get("handle") or ""
        for tweet in builder.get("tweets", []):
            url = tweet.get("url")
            text = tweet.get("text")
            if not url or not text:
                continue
            items.append(
                NewsItem(
                    title=f"{name}（@{handle}）：{clean_text(text, 80)}",
                    url=url,
                    source="X/Twitter",
                    published=_parse_iso(tweet.get("createdAt")) or generated,
                    summary=clean_text(text, 600),
                    weight=2,
                    score=tweet.get("likes") or 0,
                    extra={
                        "author": name,
                        "handle": handle,
                        "likes": tweet.get("likes", 0),
                        "retweets": tweet.get("retweets", 0),
                    },
                )
            )
    items.sort(key=lambda item: item.score, reverse=True)
    return items[:limit]


def parse_podcasts_feed(data: dict, cutoff: datetime) -> list[NewsItem]:
    generated = _feed_generated_at(data, cutoff, "Podcast")
    if generated is None:
        return []
    items = []
    for episode in data.get("podcasts", []):
        url = episode.get("url")
        transcript = episode.get("transcript")
        if not url or not transcript:
            continue  # 沒有轉錄稿就沒有摘要素材，跳過
        show = episode.get("name") or ""
        items.append(
            NewsItem(
                title=clean_text(f"{show}：{episode.get('title') or ''}", 300),
                url=url,
                source="Podcast",
                published=_parse_iso(episode.get("publishedAt")) or generated,
                # 轉錄稿可達數十 KB，剝掉說話人標記後硬截斷再進 LLM payload
                summary=clean_text(_SPEAKER_RE.sub(" ", transcript), 1200),
                weight=2,
                extra={"show": show},
            )
        )
    return items


def parse_blogs_feed(data: dict, cutoff: datetime) -> list[NewsItem]:
    generated = _feed_generated_at(data, cutoff, "官方 Blog")
    if generated is None:
        return []
    items = []
    for post in data.get("blogs", []):
        url = post.get("url")
        title = post.get("title")
        if not url or not title:
            continue
        items.append(
            NewsItem(
                title=clean_text(title, 300),
                url=url,
                source=post.get("name") or "Official Blog",
                published=_parse_blog_date(post.get("publishedAt"), generated),
                summary=clean_text(post.get("description") or post.get("content")),
                weight=3,
            )
        )
    return items


@dataclass(frozen=True)
class FollowBuildersXSource:
    name: str = "X/Twitter Builders"
    base_url: str = DEFAULT_FEED_BASE
    limit: int = 20  # feed 一天約 40 則，按讚數取前 20 以免擠掉其他來源

    def fetch(self, cutoff: datetime) -> list[NewsItem]:
        return parse_x_feed(http_get(f"{self.base_url}/feed-x.json").json(), cutoff, self.limit)


@dataclass(frozen=True)
class FollowBuildersPodcastSource:
    name: str = "Podcast"
    base_url: str = DEFAULT_FEED_BASE

    def fetch(self, cutoff: datetime) -> list[NewsItem]:
        return parse_podcasts_feed(http_get(f"{self.base_url}/feed-podcasts.json").json(), cutoff)


@dataclass(frozen=True)
class FollowBuildersBlogSource:
    name: str = "Anthropic/Claude Blog"
    base_url: str = DEFAULT_FEED_BASE

    def fetch(self, cutoff: datetime) -> list[NewsItem]:
        return parse_blogs_feed(http_get(f"{self.base_url}/feed-blogs.json").json(), cutoff)


def follow_builders_sources() -> list[Source]:
    """執行時（load_dotenv 之後）讀環境變數，讓 default_sources() 保持零參數。"""
    base = os.environ.get("FOLLOW_BUILDERS_FEED_BASE", DEFAULT_FEED_BASE).rstrip("/")
    return [
        FollowBuildersXSource(base_url=base),
        FollowBuildersPodcastSource(base_url=base),
        FollowBuildersBlogSource(base_url=base),
    ]
