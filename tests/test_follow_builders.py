"""follow_builders 純解析函數的測試（零網路，仿 test_github_trending 的 fixture 模式）。"""
from __future__ import annotations

from datetime import datetime, timezone

from ai_news.sources.follow_builders import (
    _parse_blog_date,
    parse_blogs_feed,
    parse_podcasts_feed,
    parse_x_feed,
)

GENERATED_AT = "2026-07-09T07:28:29.483Z"
FRESH_CUTOFF = datetime(2026, 7, 9, 0, 0, tzinfo=timezone.utc)   # generatedAt 在視窗內
STALE_CUTOFF = datetime(2026, 7, 9, 12, 0, tzinfo=timezone.utc)  # generatedAt 已過期

X_FEED = {
    "generatedAt": GENERATED_AT,
    "lookbackHours": 24,
    "x": [
        {
            "name": "Swyx",
            "handle": "swyx",
            "tweets": [
                {
                    "id": "1",
                    "text": "one detail i enjoyed about the keynote",
                    "createdAt": "2026-07-08T20:25:44.000Z",
                    "url": "https://x.com/swyx/status/1",
                    "likes": 69,
                    "retweets": 3,
                },
                {
                    "id": "2",
                    "text": "second tweet with more likes",
                    "createdAt": "2026-07-08T10:00:00.000Z",
                    "url": "https://x.com/swyx/status/2",
                    "likes": 500,
                    "retweets": 40,
                },
            ],
        },
        {
            "name": "Andrej Karpathy",
            "handle": "karpathy",
            "tweets": [
                {
                    "id": "3",
                    "text": "LLMs are the new operating system",
                    "createdAt": "2026-07-08T15:00:00.000Z",
                    "url": "https://x.com/karpathy/status/3",
                    "likes": 6631,
                    "retweets": 900,
                },
                {"id": "4", "text": "", "url": "https://x.com/karpathy/status/4", "likes": 1},
            ],
        },
    ],
}

PODCASTS_FEED = {
    "generatedAt": GENERATED_AT,
    "podcasts": [
        {
            "name": "AI & I by Every",
            "title": "How a Writer Uses AI",
            "guid": "85aa2fe0",
            "url": "https://www.youtube.com/watch?v=abc",
            "publishedAt": "2026-07-08T14:49:06.000Z",
            "transcript": (
                "Speaker 1 | 00:00 - 00:14\nI wake up and I don't touch the Internet. " + "深度內容 " * 500
            ),
        },
        {
            "name": "No Priors",
            "title": "Episode without transcript",
            "url": "https://www.youtube.com/watch?v=def",
            "publishedAt": "2026-07-08T00:00:00.000Z",
            "transcript": "",
        },
    ],
    "errors": ["some upstream error"],
}

BLOGS_FEED = {
    "generatedAt": GENERATED_AT,
    "blogs": [
        {
            "name": "Anthropic Engineering",
            "title": "Building agents",
            "url": "https://www.anthropic.com/engineering/building-agents",
            "publishedAt": None,
            "description": "",
            "content": "Long article content about building agents. " * 30,
        },
        {
            "name": "Claude Blog",
            "title": "Claude update",
            "url": "https://claude.com/blog/claude-update",
            "publishedAt": "May 19, 2026",
            "description": "A short description",
            "content": "body",
        },
        {
            "name": "Claude Blog",
            "title": "ISO dated post",
            "url": "https://claude.com/blog/iso-post",
            "publishedAt": "2026-07-08T09:00:00.000Z",
            "content": "body",
        },
    ],
}


# ---- generatedAt 門控 ----

def test_stale_feed_returns_empty():
    assert parse_x_feed(X_FEED, STALE_CUTOFF, 20) == []
    assert parse_podcasts_feed(PODCASTS_FEED, STALE_CUTOFF) == []
    assert parse_blogs_feed(BLOGS_FEED, STALE_CUTOFF) == []


def test_missing_or_garbage_generated_at_returns_empty():
    assert parse_x_feed({"x": []}, FRESH_CUTOFF, 20) == []
    assert parse_x_feed({"generatedAt": "not-a-date", "x": []}, FRESH_CUTOFF, 20) == []


# ---- X feed ----

def test_x_feed_flattens_sorts_and_limits():
    items = parse_x_feed(X_FEED, FRESH_CUTOFF, 2)
    assert len(items) == 2  # limit 生效；空 text 的推文被跳過
    assert items[0].score == 6631  # 按讚數降序
    assert items[1].score == 500


def test_x_feed_item_mapping():
    top = parse_x_feed(X_FEED, FRESH_CUTOFF, 20)[0]
    assert top.title.startswith("Andrej Karpathy（@karpathy）：LLMs are the new")
    assert top.source == "X/Twitter"
    assert top.url == "https://x.com/karpathy/status/3"
    assert top.weight == 2
    assert top.published == datetime(2026, 7, 8, 15, 0, tzinfo=timezone.utc)
    assert top.extra["handle"] == "karpathy"
    assert top.extra["likes"] == 6631


# ---- Podcast feed ----

def test_podcast_transcript_truncated_and_markers_stripped():
    items = parse_podcasts_feed(PODCASTS_FEED, FRESH_CUTOFF)
    assert len(items) == 1  # 無 transcript 的集數被跳過
    episode = items[0]
    assert episode.title == "AI & I by Every：How a Writer Uses AI"
    assert episode.source == "Podcast"
    assert episode.weight == 2
    assert len(episode.summary) <= 1200
    assert "Speaker 1" not in episode.summary
    assert episode.summary.startswith("I wake up")


# ---- Blog feed ----

def test_blog_date_variants_and_mapping():
    items = parse_blogs_feed(BLOGS_FEED, FRESH_CUTOFF)
    assert len(items) == 3
    by_url = {item.url: item for item in items}

    anthropic = by_url["https://www.anthropic.com/engineering/building-agents"]
    assert anthropic.source == "Anthropic Engineering"
    assert anthropic.weight == 3
    # publishedAt 為 null -> 回退到 feed 的 generatedAt
    assert anthropic.published == datetime.fromisoformat("2026-07-09T07:28:29.483+00:00")
    # description 為空 -> 取 content 截斷
    assert anthropic.summary.startswith("Long article content")

    human_date = by_url["https://claude.com/blog/claude-update"]
    assert human_date.published == datetime(2026, 5, 19, tzinfo=timezone.utc)
    assert human_date.summary == "A short description"

    iso_date = by_url["https://claude.com/blog/iso-post"]
    assert iso_date.published == datetime(2026, 7, 8, 9, 0, tzinfo=timezone.utc)


def test_parse_blog_date_fallback():
    fallback = datetime(2026, 1, 1, tzinfo=timezone.utc)
    assert _parse_blog_date(None, fallback) == fallback
    assert _parse_blog_date("gibberish", fallback) == fallback
    assert _parse_blog_date("May 19, 2026", fallback) == datetime(2026, 5, 19, tzinfo=timezone.utc)
    assert _parse_blog_date("2026-07-08T09:00:00.000Z", fallback) == datetime(
        2026, 7, 8, 9, 0, tzinfo=timezone.utc
    )
