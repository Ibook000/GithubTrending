"""GitHub 趋势雷达。"""

from .app import (
    SCHEMA_VERSION,
    build_payload,
    create_http_session,
    fetch_github_trending,
    fetch_news_bundle,
    generate_fallback_summary,
    generate_news_rss,
    generate_rss,
    generate_site,
    generate_trend_card,
    normalize_news_url,
    parse_news_datetime,
    parse_news_feed,
    parse_trending_html,
    run,
    validate_payload,
)

__all__ = [
    "SCHEMA_VERSION",
    "build_payload",
    "create_http_session",
    "fetch_github_trending",
    "fetch_news_bundle",
    "generate_fallback_summary",
    "generate_news_rss",
    "generate_rss",
    "generate_site",
    "generate_trend_card",
    "normalize_news_url",
    "parse_news_feed",
    "parse_news_datetime",
    "parse_trending_html",
    "run",
    "validate_payload",
]
