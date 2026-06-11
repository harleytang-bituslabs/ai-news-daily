"""來源介面與共用 HTTP 工具。

新增來源：實作 Source 協定（name 屬性 + fetch 方法），
並在 sources/__init__.py 的 default_sources() 註冊。
fetch() 可以直接拋例外——pipeline 會隔離單一來源的失敗。
"""
from __future__ import annotations

import html
import re
import time
from datetime import datetime, timezone
from typing import Protocol

import requests

from ai_news.models import NewsItem

USER_AGENT = "ai-news-daily/0.2 (internal news digest bot)"
TIMEOUT = 20

_TAG_RE = re.compile(r"<[^>]+>")


class Source(Protocol):
    name: str

    def fetch(self, cutoff: datetime) -> list[NewsItem]:
        """回傳 cutoff 之後的新聞項目。"""
        ...


def http_get(url: str, **kwargs) -> requests.Response:
    """共用 GET：統一 UA 與 timeout，4xx/5xx 直接 raise。"""
    kwargs.setdefault("timeout", TIMEOUT)
    headers = {"User-Agent": USER_AGENT, **kwargs.pop("headers", {})}
    resp = requests.get(url, headers=headers, **kwargs)
    resp.raise_for_status()
    return resp


def clean_text(text: str | None, limit: int = 500) -> str:
    """去除 HTML tag、壓縮空白、截斷。"""
    if not text:
        return ""
    text = html.unescape(_TAG_RE.sub(" ", text))
    return re.sub(r"\s+", " ", text).strip()[:limit]


def struct_time_to_datetime(ts: time.struct_time) -> datetime:
    return datetime.fromtimestamp(time.mktime(ts), tz=timezone.utc)
