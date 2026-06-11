"""核心資料模型。"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class NewsItem:
    """單則新聞素材，所有來源統一產出這個型別。"""

    title: str
    url: str
    source: str
    published: datetime
    summary: str = ""
    weight: int = 1          # 來源權重：3=官方一手, 2=媒體/策展, 1=社群
    score: int = 0           # 來源內的熱度分數（HN points、GitHub 當日星數等）
    discussion: str | None = None  # 討論串連結（HN/Reddit）
    extra: dict = field(default_factory=dict)

    @property
    def dedupe_key(self) -> str:
        return normalize_url(self.url)

    @property
    def rank_key(self) -> tuple:
        return (self.weight, self.score, self.published)

    def to_payload(self) -> dict[str, Any]:
        """送給 LLM 的精簡表示。"""
        payload: dict[str, Any] = {
            "title": self.title,
            "url": self.url,
            "source": self.source,
            "published": self.published.isoformat(),
        }
        if self.summary:
            payload["summary"] = self.summary
        if self.discussion:
            payload["discussion"] = self.discussion
        if self.score:
            payload["score"] = self.score
        payload.update(self.extra)
        return payload

    def to_record(self) -> dict[str, Any]:
        """落地存檔（JSONL）的完整表示。"""
        record = self.to_payload()
        record["weight"] = self.weight
        return record


def normalize_url(url: str) -> str:
    """正規化 URL 供去重：去掉 query/fragment 與結尾斜線。"""
    return url.split("?")[0].split("#")[0].rstrip("/").lower()


def dedupe(items: list[NewsItem]) -> list[NewsItem]:
    """以正規化 URL 去重；重複時保留 (weight, score) 較高者。"""
    by_key: dict[str, NewsItem] = {}
    for item in items:
        existing = by_key.get(item.dedupe_key)
        if existing is None or (item.weight, item.score) > (existing.weight, existing.score):
            by_key[item.dedupe_key] = item
    return list(by_key.values())


def rank(items: list[NewsItem], max_items: int) -> list[NewsItem]:
    """依「來源權重 > 熱度 > 時間」排序並截斷。"""
    return sorted(items, key=lambda x: x.rank_key, reverse=True)[:max_items]
