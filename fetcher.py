# -*- coding: utf-8 -*-
"""從 RSS / Hacker News / Reddit 抓取時間窗內的 AI 新聞。

任何單一來源失敗只會記 warning，不會讓整次執行掛掉。
"""
import html
import logging
import re
import time
from datetime import datetime, timedelta, timezone

import feedparser
import requests

from sources import RSS_FEEDS, HN_QUERIES, HN_MIN_POINTS, REDDIT_SUBS

log = logging.getLogger(__name__)

UA = "ai-news-daily/1.0 (internal news digest bot)"
TIMEOUT = 20

TAG_RE = re.compile(r"<[^>]+>")


def _clean(text: str, limit: int = 500) -> str:
    """去除 HTML tag、壓縮空白，截斷到 limit 字元。"""
    if not text:
        return ""
    text = html.unescape(TAG_RE.sub(" ", text))
    text = re.sub(r"\s+", " ", text).strip()
    return text[:limit]


def _norm_url(url: str) -> str:
    """正規化 URL 供去重：去掉 query string 與結尾斜線。"""
    return url.split("?")[0].split("#")[0].rstrip("/").lower()


def fetch_rss(cutoff: datetime) -> list[dict]:
    items = []
    for feed in RSS_FEEDS:
        try:
            resp = requests.get(feed["url"], headers={"User-Agent": UA}, timeout=TIMEOUT)
            resp.raise_for_status()
            parsed = feedparser.parse(resp.content)
            count = 0
            for e in parsed.entries:
                ts = e.get("published_parsed") or e.get("updated_parsed")
                if not ts:
                    continue
                published = datetime.fromtimestamp(time.mktime(ts), tz=timezone.utc)
                if published < cutoff:
                    continue
                link = e.get("link", "")
                if not link:
                    continue
                items.append({
                    "title": _clean(e.get("title", ""), 300),
                    "url": link,
                    "source": feed["name"],
                    "published": published.isoformat(),
                    "summary": _clean(e.get("summary", "")),
                    "weight": feed["weight"],
                    "score": 0,
                })
                count += 1
            log.info("RSS %-20s %d 則", feed["name"], count)
        except Exception as exc:
            log.warning("RSS %s 抓取失敗：%s", feed["name"], exc)
    return items


def fetch_hackernews(cutoff: datetime) -> list[dict]:
    items, seen_ids = [], set()
    cutoff_ts = int(cutoff.timestamp())
    for q in HN_QUERIES:
        try:
            resp = requests.get(
                "https://hn.algolia.com/api/v1/search_by_date",
                params={
                    "query": q,
                    "tags": "story",
                    "hitsPerPage": 30,
                    "numericFilters": f"created_at_i>{cutoff_ts},points>{HN_MIN_POINTS}",
                },
                headers={"User-Agent": UA},
                timeout=TIMEOUT,
            )
            resp.raise_for_status()
            for hit in resp.json().get("hits", []):
                if hit["objectID"] in seen_ids:
                    continue
                seen_ids.add(hit["objectID"])
                url = hit.get("url") or f"https://news.ycombinator.com/item?id={hit['objectID']}"
                items.append({
                    "title": _clean(hit.get("title", ""), 300),
                    "url": url,
                    "source": "Hacker News",
                    "published": datetime.fromtimestamp(hit["created_at_i"], tz=timezone.utc).isoformat(),
                    "summary": "",
                    "weight": 1,
                    "score": hit.get("points", 0),
                    "discussion": f"https://news.ycombinator.com/item?id={hit['objectID']}",
                })
        except Exception as exc:
            log.warning("HN 查詢 %r 失敗：%s", q, exc)
    log.info("Hacker News %d 則", len(items))
    return items


def fetch_reddit(cutoff: datetime) -> list[dict]:
    """Reddit JSON API 會擋雲端 IP，改走 RSS 端點（實測可用）。"""
    items = []
    for cfg in REDDIT_SUBS:
        try:
            resp = requests.get(
                f"https://www.reddit.com/r/{cfg['sub']}/top/.rss",
                params={"t": "day"},
                headers={"User-Agent": UA},
                timeout=TIMEOUT,
            )
            resp.raise_for_status()
            parsed = feedparser.parse(resp.content)
            count = 0
            for e in parsed.entries[: cfg["limit"]]:
                link = e.get("link", "")
                if not link:
                    continue
                ts = e.get("published_parsed") or e.get("updated_parsed")
                published = (
                    datetime.fromtimestamp(time.mktime(ts), tz=timezone.utc)
                    if ts else datetime.now(timezone.utc)
                )
                items.append({
                    "title": _clean(e.get("title", ""), 300),
                    "url": link,
                    "source": f"r/{cfg['sub']}",
                    "published": published.isoformat(),
                    "summary": _clean(e.get("summary", "")),
                    "weight": 1,
                    "score": 0,
                    "discussion": link,
                })
                count += 1
            log.info("Reddit r/%-16s %d 則", cfg["sub"], count)
        except Exception as exc:
            log.warning("Reddit r/%s 抓取失敗：%s", cfg["sub"], exc)
    return items


# repo 連結在 <h2> 標題內（避免抓到 sponsors/login 等其他連結）
GH_REPO_RE = re.compile(r'<h2[^>]*>.*?href="/([A-Za-z0-9_.\-]+/[A-Za-z0-9_.\-]+)"', re.S)
GH_DESC_RE = re.compile(r'<p class="col-9[^"]*">\s*(.*?)\s*</p>', re.S)
GH_STARS_RE = re.compile(r"([\d,]+)\s+stars today")
GH_LANG_RE = re.compile(r'itemprop="programmingLanguage">([^<]+)<')


def fetch_github_trending(limit: int = 15) -> list[dict]:
    """抓 GitHub 每日 trending 前 limit 個 repo（無官方 API，輕量解析 HTML）。

    不做 AI 關鍵字過濾——交給 Claude 在彙整時過濾非 AI 項目。
    """
    items = []
    try:
        resp = requests.get(
            "https://github.com/trending?since=daily",
            headers={"User-Agent": UA},
            timeout=TIMEOUT,
        )
        resp.raise_for_status()
        # 每個 repo 是一個 <article class="Box-row">
        for chunk in resp.text.split('<article class="Box-row">')[1 : limit + 1]:
            m = GH_REPO_RE.search(chunk)
            if not m:
                continue
            repo = m.group(1)
            desc = GH_DESC_RE.search(chunk)
            stars = GH_STARS_RE.search(chunk)
            lang = GH_LANG_RE.search(chunk)
            stars_today = int(stars.group(1).replace(",", "")) if stars else 0
            items.append({
                "title": f"{repo}" + (f"（{lang.group(1)}）" if lang else ""),
                "url": f"https://github.com/{repo}",
                "source": "GitHub Trending",
                "published": datetime.now(timezone.utc).isoformat(),
                "summary": _clean(desc.group(1)) if desc else "",
                "weight": 2,
                "score": stars_today,
                "stars_today": stars_today,
            })
        log.info("GitHub Trending %d 個 repo", len(items))
    except Exception as exc:
        log.warning("GitHub Trending 抓取失敗：%s", exc)
    return items


def fetch_hf_papers(limit: int = 10) -> list[dict]:
    """Hugging Face Daily Papers — 社群每日票選的熱門論文。"""
    items = []
    try:
        resp = requests.get(
            "https://huggingface.co/api/daily_papers",
            params={"limit": 30},
            headers={"User-Agent": UA},
            timeout=TIMEOUT,
        )
        resp.raise_for_status()
        entries = sorted(
            resp.json(),
            key=lambda x: x.get("paper", {}).get("upvotes", 0),
            reverse=True,
        )[:limit]
        for e in entries:
            paper = e.get("paper", {})
            pid = paper.get("id")
            if not pid:
                continue
            items.append({
                "title": _clean(paper.get("title", ""), 300),
                "url": f"https://huggingface.co/papers/{pid}",
                "source": "HF Daily Papers",
                "published": e.get("publishedAt", datetime.now(timezone.utc).isoformat()),
                "summary": _clean(paper.get("summary", "")),
                "weight": 2,
                "score": paper.get("upvotes", 0),
            })
        log.info("HF Daily Papers %d 篇", len(items))
    except Exception as exc:
        log.warning("HF Daily Papers 抓取失敗：%s", exc)
    return items


def fetch_all(window_hours: int, max_items: int) -> list[dict]:
    """抓所有來源、去重、依權重與分數排序後取前 max_items 則。"""
    cutoff = datetime.now(timezone.utc) - timedelta(hours=window_hours)
    items = (
        fetch_rss(cutoff)
        + fetch_hackernews(cutoff)
        + fetch_reddit(cutoff)
        + fetch_github_trending()
        + fetch_hf_papers()
    )

    # 以正規化 URL 去重；重複時保留 weight/score 較高者
    by_url: dict[str, dict] = {}
    for it in items:
        key = _norm_url(it["url"])
        old = by_url.get(key)
        if old is None or (it["weight"], it["score"]) > (old["weight"], old["score"]):
            by_url[key] = it
    deduped = list(by_url.values())

    deduped.sort(key=lambda x: (x["weight"], x["score"], x["published"]), reverse=True)
    if len(deduped) > max_items:
        log.info("共 %d 則，依權重/分數取前 %d 則", len(deduped), max_items)
        deduped = deduped[:max_items]
    else:
        log.info("共 %d 則（去重後）", len(deduped))
    return deduped
