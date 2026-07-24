import json
from datetime import datetime
from xml.etree import ElementTree as ET

import pytest
from PIL import Image

from github_trending.app import (
    BEIJING_TZ,
    CARD_VARIANTS,
    build_payload,
    fetch_github_trending,
    fetch_news_bundle,
    generate_news_rss,
    generate_rss,
    generate_site,
    generate_trend_card,
    parse_news_datetime,
    parse_news_feed,
    parse_trending_html,
    validate_payload,
)

SAMPLE_HTML = """
<article class="Box-row">
  <h2><a href="/octocat/Hello-World">octocat / Hello-World</a></h2>
  <p>A small &amp; useful repository</p>
  <span itemprop="programmingLanguage">Python</span>
  <a href="/octocat/Hello-World/stargazers"> 1,234 </a>
  <a href="/octocat/Hello-World/forks"> 56 </a>
</article>
<article class="Box-row">
  <h2><a href="/example/no-description">example / no-description</a></h2>
</article>
<article class="Box-row"><h2>broken entry</h2></article>
"""

SAMPLE_RSS = """
<rss version="2.0"><channel>
  <item><title>Open source AI release</title><link>https://example.com/ai</link>
  <description><![CDATA[<p>A useful <strong>AI</strong> release.</p>]]></description>
  <pubDate>Wed, 22 Jul 2026 02:00:00 GMT</pubDate></item>
</channel></rss>
"""

SAMPLE_ATOM = """
<feed xmlns="http://www.w3.org/2005/Atom">
  <entry><title>Fresh model paper</title><id>tag:arxiv.org,2026:1234</id>
  <link href="https://arxiv.org/abs/1234"/><published>2026-07-22T02:00:00Z</published>
  <summary>Research summary</summary></entry>
</feed>
"""


def repo(title="octocat/Hello-World", language="Python"):
    author = title.split("/")[0]
    return {
        "title": title,
        "url": f"https://github.com/{title}",
        "description": "A useful project",
        "language": language,
        "stars": "1,234",
        "forks": "56",
        "author": author,
        "summary": "一个有用的开源项目",
    }


def test_parse_trending_html_handles_missing_fields_and_broken_entries():
    repos = parse_trending_html(SAMPLE_HTML)
    assert len(repos) == 2
    assert repos[0]["title"] == "octocat/Hello-World"
    assert repos[0]["description"] == "A small & useful repository"
    assert repos[0]["forks"] == "56"
    assert repos[1]["description"] == "无描述"
    assert repos[1]["language"] == "未知"


def test_parse_trending_html_respects_limit():
    assert len(parse_trending_html(SAMPLE_HTML, limit=1)) == 1


def test_fetch_rejects_unknown_period():
    with pytest.raises(ValueError, match="不支持的榜单周期"):
        fetch_github_trending("yearly")


def test_parse_news_feed_supports_rss_and_strips_html():
    news = parse_news_feed(
        SAMPLE_RSS,
        source="Example",
        category="AI",
        source_id="example",
        now=datetime(2026, 7, 22, 10, 0, tzinfo=BEIJING_TZ),
    )
    assert len(news) == 1
    assert news[0]["title"] == "Open source AI release"
    assert news[0]["url"] == "https://example.com/ai"
    assert news[0]["summary"] == "A useful AI release."
    assert news[0]["source_id"] == "example"
    assert news[0]["id"]


def test_parse_news_feed_supports_atom_and_72_hour_window():
    now = datetime(2026, 7, 22, 10, 0, tzinfo=BEIJING_TZ)
    assert parse_news_feed(SAMPLE_ATOM, "arXiv", "研究", now=now)[0]["url"] == "https://arxiv.org/abs/1234"
    old = SAMPLE_RSS.replace("Wed, 22 Jul 2026 02:00:00 GMT", "Sat, 18 Jul 2026 02:00:00 GMT")
    assert parse_news_feed(old, "Example", "AI", now=now) == []


def test_news_datetime_and_url_normalization():
    now = datetime(2026, 7, 22, 10, 0, tzinfo=BEIJING_TZ)
    assert parse_news_datetime("not-a-date", now=now) is None
    from github_trending.app import normalize_news_url

    assert normalize_news_url("HTTPS://EXAMPLE.COM/a/?utm_source=x&keep=1") == "https://example.com/a?keep=1"


def test_build_payload_adds_movement_cross_periods_and_deduplicates():
    previous = {
        "schema_version": "1.0",
        "periods": {"daily": [{"title": "octocat/Hello-World", "rank": 3}]},
    }
    payload = build_payload(
        {
            "daily": [repo(), repo(), repo("new/project", "Go")],
            "weekly": [repo()],
            "monthly": [],
        },
        previous=previous,
        now=datetime(2026, 7, 22, 10, 0, tzinfo=BEIJING_TZ),
    )
    daily = payload["periods"]["daily"]
    assert len(daily) == 2
    assert daily[0]["movement"] == {"direction": "up", "amount": 2, "label": "上升 2"}
    assert daily[0]["periods"] == ["daily", "weekly"]
    assert daily[1]["movement"]["direction"] == "new"


def test_validate_payload_rejects_empty_daily_list():
    payload = build_payload({"daily": [], "weekly": [repo()], "monthly": []})
    with pytest.raises(ValueError, match="日榜为空"):
        validate_payload(payload)


def test_generate_rss_is_valid_xml_and_contains_daily_items():
    payload = build_payload({"daily": [repo()], "weekly": [], "monthly": []})
    rss = generate_rss(payload)
    root = ET.fromstring(rss)
    assert root.tag == "rss"
    assert root.findtext("channel/title") == "GitHub 趋势雷达"
    assert root.findtext("channel/item/title") == "#1 octocat/Hello-World"


def test_generate_site_writes_public_interfaces_and_escapes_embedded_data(tmp_path):
    unsafe = repo('<script>alert("x")</script>/repo')
    payload = build_payload({"daily": [unsafe], "weekly": [], "monthly": []})
    generate_site(payload, tmp_path)

    assert (tmp_path / "data/latest.json").exists()
    assert (tmp_path / f"data/{payload['date']}.json").exists()
    assert (tmp_path / "feed.xml").exists()
    assert (tmp_path / "news-feed.xml").exists()
    assert (tmp_path / "data/news/latest.json").exists()
    assert (tmp_path / "cards/manifest.json").exists()
    assert (tmp_path / "today-card.svg").exists()
    assert (tmp_path / "today-card.png").exists()
    assert (tmp_path / "robots.txt").exists()
    assert (tmp_path / "sitemap.xml").exists()
    html = (tmp_path / "index.html").read_text(encoding="utf-8")
    assert '<script>alert("x")</script>' not in html
    assert "\\u003cscript>alert" in html
    data = json.loads((tmp_path / "data/latest.json").read_text(encoding="utf-8"))
    assert data["schema_version"] == "1.0"


def test_generate_trend_card_contains_daily_repos_and_news():
    payload = build_payload(
        {"daily": [repo()], "weekly": [], "monthly": []},
        news=parse_news_feed(SAMPLE_RSS, source="Example", category="AI"),
    )
    card = generate_trend_card(payload, "portrait")
    root = ET.fromstring(card)
    assert root.tag.endswith("svg")
    assert "octocat/Hello-World" in card
    assert "Open source AI release" in card


def test_news_rss_and_card_variants_are_valid(tmp_path):
    payload = build_payload(
        {"daily": [repo()], "weekly": [], "monthly": []},
        news=parse_news_feed(SAMPLE_RSS, source="Example", category="AI"),
    )
    rss = generate_news_rss({"generated_at": payload["generated_at"], "items": payload["news"]})
    assert ET.fromstring(rss).findtext("channel/item/title") == "Open source AI release"
    generate_site(payload, tmp_path)
    for variant, size in CARD_VARIANTS.items():
        assert ET.parse(tmp_path / f"cards/latest-{variant}.svg").getroot().tag.endswith("svg")
        assert Image.open(tmp_path / f"cards/latest-{variant}.png").size == (size["width"], size["height"])


def test_news_only_site_generation_keeps_immutable_ranking_snapshot(tmp_path):
    first = build_payload(
        {"daily": [repo()], "weekly": [], "monthly": []},
        now=datetime(2026, 7, 22, 10, 0, tzinfo=BEIJING_TZ),
    )
    generate_site(first, tmp_path)
    snapshot = (tmp_path / "data/2026-07-22.json").read_text(encoding="utf-8")
    second = build_payload(
        {"daily": [repo()]},
        news=parse_news_feed(SAMPLE_RSS, "Example", "AI"),
        now=datetime(2026, 7, 22, 16, 0, tzinfo=BEIJING_TZ),
    )
    generate_site(second, tmp_path, write_trending_snapshot=False)
    assert (tmp_path / "data/2026-07-22.json").read_text(encoding="utf-8") == snapshot


def test_news_refresh_falls_back_to_previous_source():
    class Response:
        def __init__(self, text=None, error=None):
            self.text = text or ""
            self.error = error

        def raise_for_status(self):
            if self.error:
                raise self.error

    class Session:
        def get(self, url, timeout=None):
            if "github.blog" in url:
                return Response(error=__import__("requests").RequestException("offline"))
            return Response(SAMPLE_RSS)

    previous = {
        "items": parse_news_feed(
            SAMPLE_RSS.replace("https://example.com/ai", "https://github.blog/old-news"),
            "GitHub Blog",
            "开源生态",
            source_id="github-blog",
        ),
        "sources": [{"id": "github-blog", "last_success_at": "2026-07-22T08:00:00+08:00"}],
    }
    bundle = fetch_news_bundle(Session(), previous=previous, now=datetime(2026, 7, 22, 10, 0, tzinfo=BEIJING_TZ))
    stale = [item for item in bundle["items"] if item["source_id"] == "github-blog"]
    assert stale and stale[0]["stale"] is True


def test_generated_html_exposes_accessible_controls(tmp_path):
    payload = build_payload({"daily": [repo()], "weekly": [], "monthly": []})
    generate_site(payload, tmp_path)
    html = (tmp_path / "index.html").read_text(encoding="utf-8")
    assert 'aria-label="榜单周期"' in html
    assert 'id="search-input"' in html
    assert 'id="language-filter"' in html
    assert 'id="theme-toggle"' in html
    assert 'id="trend-card"' in html
    assert 'id="news-list"' in html
    assert 'id="share-card"' in html
    assert "prefers-reduced-motion" in (tmp_path / "styles.css").read_text(encoding="utf-8")
