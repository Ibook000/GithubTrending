import json
from datetime import datetime
from xml.etree import ElementTree as ET

import pytest

from github_trending.app import (
    BEIJING_TZ,
    build_payload,
    fetch_github_trending,
    generate_rss,
    generate_site,
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
    assert (tmp_path / "robots.txt").exists()
    assert (tmp_path / "sitemap.xml").exists()
    html = (tmp_path / "index.html").read_text(encoding="utf-8")
    assert '<script>alert("x")</script>' not in html
    assert "\\u003cscript>alert" in html
    data = json.loads((tmp_path / "data/latest.json").read_text(encoding="utf-8"))
    assert data["schema_version"] == "1.0"


def test_generated_html_exposes_accessible_controls(tmp_path):
    payload = build_payload({"daily": [repo()], "weekly": [], "monthly": []})
    generate_site(payload, tmp_path)
    html = (tmp_path / "index.html").read_text(encoding="utf-8")
    assert 'aria-label="榜单周期"' in html
    assert 'id="search-input"' in html
    assert 'id="language-filter"' in html
    assert 'id="theme-toggle"' in html
    assert "prefers-reduced-motion" in (tmp_path / "styles.css").read_text(encoding="utf-8")
