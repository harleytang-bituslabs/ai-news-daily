from ai_news.sources.github_trending import parse_trending

FIXTURE = """
<div>
<article class="Box-row">
  <a href="/sponsors/someone">Sponsor</a>
  <h2 class="h3 lh-condensed"><a href="/openai/whisper">openai / whisper</a></h2>
  <p class="col-9 color-fg-muted my-1 pr-4">Robust speech recognition</p>
  <span itemprop="programmingLanguage">Python</span>
  <span>1,234 stars today</span>
</article>
<article class="Box-row">
  <h2 class="h3 lh-condensed"><a href="/foo/bar">foo / bar</a></h2>
</article>
"""


def test_parse_trending_extracts_repo_from_h2_not_sponsor_link():
    items = parse_trending(FIXTURE, limit=10)
    assert [i.url for i in items] == [
        "https://github.com/openai/whisper",
        "https://github.com/foo/bar",
    ]


def test_parse_trending_extracts_metadata():
    item = parse_trending(FIXTURE, limit=10)[0]
    assert item.title == "openai/whisper（Python）"
    assert item.summary == "Robust speech recognition"
    assert item.score == 1234
    assert item.extra["stars_today"] == 1234


def test_parse_trending_respects_limit():
    assert len(parse_trending(FIXTURE, limit=1)) == 1
