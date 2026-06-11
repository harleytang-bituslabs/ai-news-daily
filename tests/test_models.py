from datetime import datetime, timezone

from ai_news.models import NewsItem, dedupe, normalize_url, rank

NOW = datetime(2026, 6, 11, 12, 0, tzinfo=timezone.utc)


def make(url: str, weight: int = 1, score: int = 0, **kw) -> NewsItem:
    return NewsItem(title="t", url=url, source="s", published=NOW, weight=weight, score=score, **kw)


def test_normalize_url_strips_query_fragment_and_trailing_slash():
    assert normalize_url("https://A.com/path/?utm=x#frag") == "https://a.com/path"
    assert normalize_url("https://a.com/path") == normalize_url("https://a.com/path/")


def test_dedupe_keeps_higher_weight():
    low = make("https://a.com/x?ref=hn", weight=1, score=999)
    high = make("https://a.com/x", weight=3, score=0)
    result = dedupe([low, high])
    assert result == [high]


def test_dedupe_same_weight_keeps_higher_score():
    a = make("https://a.com/x", weight=1, score=10)
    b = make("https://a.com/x", weight=1, score=50)
    assert dedupe([a, b]) == [b]


def test_rank_orders_by_weight_then_score_and_truncates():
    items = [
        make("https://a.com/1", weight=1, score=500),
        make("https://a.com/2", weight=3, score=0),
        make("https://a.com/3", weight=2, score=10),
    ]
    ranked = rank(items, max_items=2)
    assert [i.url for i in ranked] == ["https://a.com/2", "https://a.com/3"]


def test_payload_includes_optional_fields_only_when_set():
    plain = make("https://a.com/1").to_payload()
    assert "discussion" not in plain and "score" not in plain

    rich = make("https://a.com/2", score=42, discussion="https://hn.example/1").to_payload()
    assert rich["score"] == 42
    assert rich["discussion"] == "https://hn.example/1"
