"""GitHub 趋势雷达的数据抓取、结构化输出和静态站点生成器。"""

from __future__ import annotations

import concurrent.futures
import hashlib
import json
import os
import re
import shutil
import textwrap
import threading
import time
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from email.utils import format_datetime
from html import escape
from pathlib import Path
from typing import Any
from urllib.parse import parse_qsl, urlencode, urljoin, urlparse, urlunparse
from xml.etree import ElementTree as ET

import requests
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

try:
    from openai import OpenAI
except ImportError:  # pragma: no cover - AI 功能是可选的
    OpenAI = None

try:
    import cairosvg
except (ImportError, OSError):  # pragma: no cover - macOS 可能未安装原生 Cairo
    cairosvg = None

try:
    import segno
except ImportError:  # pragma: no cover - 没有二维码依赖时降级为空
    segno = None

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:  # pragma: no cover - 生产环境由 CairoSVG 负责 PNG 渲染
    Image = ImageDraw = ImageFont = None


SCHEMA_VERSION = "1.0"
NEWS_SCHEMA_VERSION = "1.0"
SITE_NAME = "GitHub 趋势雷达"
SITE_URL = os.environ.get("SITE_URL", "https://ibook000.github.io/GithubTrending").rstrip("/")
DEFAULT_LLM_BASE_URL = "http://154.217.247.37:8317/v1"
DEFAULT_LLM_MODEL = "deepseek-v4-flash"
GITHUB_TRENDING_URL = "https://github.com/trending"
REQUEST_TIMEOUT = (10, 30)
PERIODS = ("daily", "weekly", "monthly")
NEWS_MAX_AGE = timedelta(hours=72)
NEWS_LIMIT = 24
CARD_VARIANTS = {
    "portrait": {"width": 1080, "height": 1440, "label": "竖版"},
    "square": {"width": 1080, "height": 1080, "label": "方形"},
    "og": {"width": 1200, "height": 630, "label": "横版"},
}
NEWS_FEEDS = (
    {
        "id": "github-blog",
        "name": "GitHub Blog",
        "category": "开源生态",
        "url": "https://github.blog/feed/",
        "homepage": "https://github.blog/",
    },
    {
        "id": "huggingface-blog",
        "name": "Hugging Face Blog",
        "category": "AI 模型",
        "url": "https://huggingface.co/blog/feed.xml",
        "homepage": "https://huggingface.co/blog",
    },
    {
        "id": "openai-news",
        "name": "OpenAI News",
        "category": "AI 模型",
        "url": "https://openai.com/news/rss.xml",
        "homepage": "https://openai.com/news/",
    },
    {
        "id": "cncf-blog",
        "name": "CNCF Blog",
        "category": "云原生",
        "url": "https://www.cncf.io/feed/",
        "homepage": "https://www.cncf.io/blog/",
    },
    {
        "id": "linux-foundation",
        "name": "Linux Foundation",
        "category": "开源生态",
        "url": "https://www.linuxfoundation.org/blog/rss.xml",
        "homepage": "https://www.linuxfoundation.org/blog/",
    },
    {
        "id": "arxiv-ai",
        "name": "arXiv AI / ML / NLP",
        "category": "研究",
        "url": "https://export.arxiv.org/api/query?search_query=cat:cs.AI%20OR%20cat:cs.LG%20OR%20cat:cs.CL&start=0&max_results=12&sortBy=submittedDate&sortOrder=descending",
        "homepage": "https://arxiv.org/",
    },
)
BEIJING_TZ = timezone(timedelta(hours=8))
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36"
)


def project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def get_llm_config() -> dict[str, str | None]:
    base_url = os.environ.get("LLM_BASE_URL", DEFAULT_LLM_BASE_URL)
    return {
        "api_key": os.environ.get("LLM_API_KEY")
        or os.environ.get("NVIDIA_API_KEY")
        or os.environ.get("OPENROUTER_API_KEY"),
        "base_url": base_url,
        "model": os.environ.get("LLM_MODEL", DEFAULT_LLM_MODEL),
    }


def create_http_session() -> requests.Session:
    """创建带指数退避重试的 HTTP 会话。"""
    retry = Retry(
        total=3,
        connect=3,
        read=3,
        status=3,
        backoff_factor=0.8,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=frozenset({"GET"}),
        respect_retry_after_header=True,
    )
    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})
    session.mount("https://", HTTPAdapter(max_retries=retry))
    return session


def parse_trending_html(html: str, limit: int = 10) -> list[dict[str, str]]:
    """解析 GitHub Trending HTML，跳过结构异常的单条记录。"""
    soup = BeautifulSoup(html, "html.parser")
    repos: list[dict[str, str]] = []

    for article in soup.select("article.Box-row"):
        repo_link = article.select_one("h2 a[href]")
        if repo_link is None:
            continue

        path = repo_link.get("href", "").strip()
        parts = [part for part in path.split("/") if part]
        if len(parts) < 2:
            continue

        description = article.select_one("p")
        language = article.select_one('[itemprop="programmingLanguage"]')
        stars = article.select_one('a[href$="/stargazers"]')
        forks = article.select_one('a[href$="/forks"], a[href$="/network/members"]')
        repos.append(
            {
                "title": "/".join(parts[:2]),
                "url": urljoin("https://github.com", path),
                "description": description.get_text(" ", strip=True)
                if description
                else "无描述",
                "language": language.get_text(" ", strip=True) if language else "未知",
                "stars": stars.get_text(" ", strip=True) if stars else "0",
                "forks": forks.get_text(" ", strip=True) if forks else "0",
                "author": parts[0],
                "summary": "",
            }
        )
        if len(repos) >= limit:
            break

    return repos


def fetch_github_trending(
    since: str = "daily", session: requests.Session | None = None
) -> list[dict[str, str]]:
    if since not in PERIODS:
        raise ValueError(f"不支持的榜单周期: {since}")

    url = f"{GITHUB_TRENDING_URL}?since={since}"
    owns_session = session is None
    session = session or create_http_session()
    try:
        print(f"🌐 正在访问 {since} 榜单")
        response = session.get(url, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        repos = parse_trending_html(response.text)
        if not repos:
            print(f"⚠️ {since} 榜单未解析到仓库，GitHub 页面结构可能已变化")
        return repos
    except requests.RequestException as exc:
        print(f"❌ 获取 {since} 榜单失败: {type(exc).__name__}: {exc}")
        return []
    finally:
        if owns_session:
            session.close()


def _clean_news_text(value: str | None) -> str:
    if not value:
        return ""
    text = BeautifulSoup(value, "html.parser").get_text(" ", strip=True)
    return re.sub(r"\s+", " ", text).strip()


def normalize_news_url(url: str) -> str:
    """删除追踪参数并保持公开新闻链接稳定。"""
    parsed = urlparse(url.strip())
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return ""
    query = [
        (key, value)
        for key, value in parse_qsl(parsed.query, keep_blank_values=True)
        if not key.lower().startswith(("utm_", "fbclid", "gclid", "mc_cid", "mc_eid"))
    ]
    return urlunparse(
        (parsed.scheme.lower(), parsed.netloc.lower(), parsed.path.rstrip("/") or "/", "", urlencode(query), "")
    )


def news_id(url: str) -> str:
    return hashlib.sha256(normalize_news_url(url).encode("utf-8")).hexdigest()[:16]


def parse_news_datetime(value: str | None, now: datetime | None = None) -> datetime | None:
    if not value:
        return None
    now = now or datetime.now(BEIJING_TZ)
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        try:
            from email.utils import parsedate_to_datetime

            parsed = parsedate_to_datetime(value)
        except (TypeError, ValueError, OverflowError):
            return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=BEIJING_TZ)
    parsed = parsed.astimezone(BEIJING_TZ)
    if parsed > now + timedelta(days=1):
        return now
    return parsed


def news_category(title: str, summary: str, fallback: str) -> str:
    text = f"{title} {summary}".lower()
    categories = (
        (("security", "vulnerability", "cve", "安全"), "安全"),
        (("kubernetes", "cloud native", "cncf", "云原生"), "云原生"),
        (("paper", "research", "arxiv", "benchmark", "论文", "研究"), "研究"),
        (("llm", "model", "agent", "transformer", "inference", "模型", "智能体"), "AI 模型"),
        (("sdk", "cli", "developer", "framework", "开发", "工具"), "开发工具"),
        (("open source", "opensource", "linux", "github", "开源"), "开源生态"),
    )
    for keywords, category in categories:
        if any(keyword in text for keyword in keywords):
            return category
    return fallback or "开源生态"


def news_source_map() -> dict[str, dict[str, str]]:
    return {feed["id"]: feed for feed in NEWS_FEEDS}


def parse_news_feed(
    xml_text: str,
    source: str,
    category: str,
    limit: int = 4,
    source_id: str | None = None,
    source_url: str | None = None,
    now: datetime | None = None,
) -> list[dict[str, Any]]:
    """解析 RSS 2.0 或 Atom 新闻源，过滤无链接和无效日期。"""
    now = now or datetime.now(BEIJING_TZ)
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return []

    items: list[dict[str, Any]] = []
    rss_items = root.findall("./channel/item")
    atom_items = root.findall(".//{http://www.w3.org/2005/Atom}entry")
    candidates = rss_items or atom_items
    atom_ns = "{http://www.w3.org/2005/Atom}"
    for item in candidates:
        if item.tag.endswith("entry"):
            title = _clean_news_text(item.findtext(f"{atom_ns}title"))
            summary = _clean_news_text(
                item.findtext(f"{atom_ns}summary") or item.findtext(f"{atom_ns}content")
            )
            published = _clean_news_text(
                item.findtext(f"{atom_ns}published") or item.findtext(f"{atom_ns}updated")
            )
            link_node = item.find(f"{atom_ns}link[@href]")
            url = link_node.get("href", "") if link_node is not None else ""
        else:
            title = _clean_news_text(item.findtext("title"))
            summary = _clean_news_text(
                item.findtext("description")
                or item.findtext("{http://purl.org/rss/1.0/modules/content/}encoded")
            )
            published = _clean_news_text(
                item.findtext("pubDate") or item.findtext("{http://purl.org/dc/elements/1.1/}date")
            )
            url = str(item.findtext("link") or "").strip()
        canonical_url = normalize_news_url(url)
        if not title or not canonical_url:
            continue
        published_at = parse_news_datetime(published, now=now)
        if published_at is not None and now - published_at > NEWS_MAX_AGE:
            continue
        item_id = news_id(canonical_url)
        items.append(
            {
                "id": item_id,
                "title": title,
                "original_title": title,
                "url": canonical_url,
                "source": source,
                "source_id": source_id or source.lower().replace(" ", "-"),
                "source_url": source_url or canonical_url,
                "category": category,
                "tags": [],
                "published": published,
                "published_at": published_at.isoformat() if published_at else now.isoformat(),
                "fetched_at": now.isoformat(),
                "summary": summary[:220],
                "original_summary": summary[:220],
                "localized": False,
                "stale": False,
            }
        )
        if len(items) >= limit:
            break
    return items


def fetch_news(session: requests.Session | None = None, limit: int = 8) -> list[dict[str, Any]]:
    """向后兼容的公开新闻抓取入口。"""
    bundle = fetch_news_bundle(session=session, limit=limit)
    return bundle["items"]


def fetch_news_bundle(
    session: requests.Session | None = None,
    previous: dict[str, Any] | None = None,
    limit: int = NEWS_LIMIT,
    now: datetime | None = None,
) -> dict[str, Any]:
    """抓取权威源并返回新闻与来源健康状态。"""
    now = now or datetime.now(BEIJING_TZ)
    owns_session = session is None
    session = session or create_http_session()
    grouped_results: list[list[dict[str, Any]]] = []
    source_status: list[dict[str, Any]] = []
    previous_items = (previous or {}).get("items", [])
    source_lookup = news_source_map()
    try:
        for feed in NEWS_FEEDS:
            try:
                response = session.get(feed["url"], timeout=(5, 12))
                response.raise_for_status()
                grouped_results.append(
                    parse_news_feed(
                        response.text,
                        source=feed["name"],
                        category=feed["category"],
                        limit=3,
                        source_id=feed["id"],
                        source_url=feed["homepage"],
                        now=now,
                    )
                )
                source_status.append(
                    {
                        "id": feed["id"],
                        "name": feed["name"],
                        "url": feed["homepage"],
                        "status": "ok",
                        "last_success_at": now.isoformat(),
                    }
                )
            except requests.RequestException as exc:
                print(f"⚠️ 新闻源 {feed['name']} 暂不可用: {type(exc).__name__}")
                grouped_results.append([])
                old_success = next(
                    (source.get("last_success_at") for source in (previous or {}).get("sources", []) if source.get("id") == feed["id"]),
                    None,
                )
                source_status.append(
                    {
                        "id": feed["id"],
                        "name": feed["name"],
                        "url": feed["homepage"],
                        "status": "stale" if old_success else "error",
                        "last_success_at": old_success,
                    }
                )
        results = [
            group[index]
            for index in range(max((len(group) for group in grouped_results), default=0))
            for group in grouped_results
            if index < len(group)
        ]
        stale_by_source: dict[str, list[dict[str, Any]]] = {}
        for item in previous_items:
            source_id = str(item.get("source_id") or "")
            if source_id in source_lookup:
                stale_by_source.setdefault(source_id, []).append({**item, "stale": True})
        if len(source_status) != len(grouped_results):
            raise RuntimeError("新闻源状态与结果数量不一致")
        for index, status in enumerate(source_status):
            group = grouped_results[index]
            if status["status"] in {"stale", "error"} and not group:
                results.extend(stale_by_source.get(status["id"], [])[:3])
        unique: dict[str, dict[str, str]] = {}
        for item in results:
            unique.setdefault(item["id"] or news_id(item["url"]), item)
        # 保持按来源交错的顺序，避免单一来源占满首页；每源限额已在解析阶段执行。
        ordered = list(unique.values())[:limit]
        return {
            "schema_version": NEWS_SCHEMA_VERSION,
            "generated_at": now.isoformat(),
            "items": ordered,
            "sources": source_status,
        }
    finally:
        if owns_session:
            session.close()


def generate_fallback_summary(repo: dict[str, Any]) -> str:
    """在没有 AI 服务时生成稳定、可读的中文摘要。"""
    title = str(repo.get("title", "")).lower()
    description = str(repo.get("description", "")).lower()
    language = repo.get("language") or "未知语言"
    text = f"{title} {description}"
    categories = (
        (("ai", "llm", "agent", "machine learning", "neural"), "人工智能与开发效率"),
        (("api", "rest", "graphql"), "API 与服务开发"),
        (("web", "frontend", "react", "vue", "angular"), "Web 与前端开发"),
        (("backend", "server", "database"), "后端与数据基础设施"),
        (("cli", "command", "terminal"), "命令行与开发者工具"),
        (("security", "vulnerability", "privacy"), "安全与隐私"),
        (("game", "engine"), "游戏与图形开发"),
        (("mobile", "android", "ios"), "移动应用开发"),
    )
    for keywords, category in categories:
        if any(keyword in text for keyword in keywords):
            return f"一个聚焦{category}的 {language} 开源项目"
    preview = str(repo.get("description") or "帮助开发者解决实际问题").rstrip("。.")
    return f"一个使用 {language} 构建的开源项目：{preview[:52]}"


def ai_summarize_projects(
    repos: list[dict[str, str]], api_key: str
) -> list[dict[str, str]]:
    if not repos:
        return repos
    if OpenAI is None:
        for repo in repos:
            repo["summary"] = generate_fallback_summary(repo)
        return repos

    config = get_llm_config()
    is_actions = os.environ.get("GITHUB_ACTIONS") == "true"
    client = OpenAI(
        base_url=config["base_url"],
        api_key=api_key,
        timeout=30 if is_actions else 60,
    )
    success_count = 0
    lock = threading.Lock()
    # 自动部署必须有明确的时间上限。失败时本地摘要足以保证页面正常发布，
    # 因此 Actions 环境不做长时间重试。
    max_retries = 1 if is_actions else 2

    def summarize(repo: dict[str, str]) -> dict[str, str]:
        nonlocal success_count
        prompt = (
            "请用一句自然、客观的中文总结这个 GitHub 项目的核心用途和亮点，"
            "不要使用营销话术或额外符号。\n"
            f"项目名称：{repo['title']}\n简介：{repo['description']}"
        )
        for attempt in range(max_retries):
            try:
                completion = client.chat.completions.create(
                    model=config["model"],
                    messages=[{"role": "user", "content": prompt}],
                    timeout=20 if is_actions else 60,
                )
                content = completion.choices[0].message.content
                repo["summary"] = (content or "").strip() or generate_fallback_summary(repo)
                with lock:
                    success_count += 1
                return repo
            except Exception as exc:  # API SDK 错误类型随版本变化
                print(
                    f"⚠️ {repo['title']} AI 摘要失败 "
                    f"({attempt + 1}/{max_retries}): {type(exc).__name__}"
                )
                if attempt + 1 < max_retries:
                    time.sleep(2**attempt)
        repo["summary"] = generate_fallback_summary(repo)
        return repo

    worker_limit = 10 if is_actions else 5
    with concurrent.futures.ThreadPoolExecutor(
        max_workers=min(worker_limit, len(repos))
    ) as pool:
        result = list(pool.map(summarize, repos))
    print(f"🤖 AI 摘要成功 {success_count}/{len(repos)}")
    return result


def ai_localize_news(
    news: list[dict[str, Any]],
    api_key: str,
    previous: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """将新增 RSS 标题与摘要转为简洁中文，复用历史结果。"""
    if not news or OpenAI is None:
        return news
    config = get_llm_config()
    is_actions = os.environ.get("GITHUB_ACTIONS") == "true"
    client = OpenAI(
        base_url=config["base_url"],
        api_key=api_key,
        timeout=30 if is_actions else 60,
    )
    previous_by_id = {
        str(item.get("id")): item
        for item in (previous or {}).get("items", [])
        if item.get("id")
    }
    pending: list[dict[str, Any]] = []
    for item in news:
        cached = previous_by_id.get(str(item.get("id")))
        if cached and cached.get("localized"):
            item.update(
                {
                    "title": cached.get("title", item["title"]),
                    "original_title": cached.get("original_title", item["title"]),
                    "summary": cached.get("summary", item.get("summary", "")),
                    "original_summary": cached.get("original_summary", item.get("summary", "")),
                    "category": cached.get("category", item.get("category", "开源生态")),
                    "tags": cached.get("tags", []),
                    "localized": True,
                }
            )
        else:
            pending.append(item)
    if not pending:
        print("📰 AI 资讯中文化复用缓存")
        return news

    success_count = 0
    lock = threading.Lock()

    def localize(item: dict[str, Any]) -> dict[str, Any]:
        nonlocal success_count
        original_title = item.get("original_title") or item["title"]
        original_summary = item.get("original_summary") or item.get("summary", "")
        prompt = (
            "请把下面的科技新闻整理成适合中文开发者阅读的内容。"
            "只输出四行，格式严格为“标题：...”“摘要：...”“分类：...”“标签：...”。"
            "分类只能是：AI 模型、研究、开源生态、开发工具、云原生、安全。"
            "标签最多三个，用顿号分隔；不使用营销话术，不补充原文没有的事实。\n"
            f"原标题：{original_title}\n原摘要：{original_summary}"
        )
        try:
            completion = client.chat.completions.create(
                model=config["model"],
                messages=[{"role": "user", "content": prompt}],
                timeout=20 if is_actions else 60,
            )
            content = (completion.choices[0].message.content or "").strip()
            title_match = re.search(r"标题[：:]\s*(.+)", content)
            summary_match = re.search(r"摘要[：:]\s*(.+)", content)
            category_match = re.search(r"分类[：:]\s*(.+)", content)
            tags_match = re.search(r"标签[：:]\s*(.+)", content)
            item["original_title"] = original_title
            item["original_summary"] = original_summary
            if title_match:
                item["title"] = title_match.group(1).strip()
            if summary_match:
                item["summary"] = summary_match.group(1).strip()[:120]
            item["category"] = (
                category_match.group(1).strip()
                if category_match and category_match.group(1).strip()
                else news_category(original_title, original_summary, item.get("category", "开源生态"))
            )
            item["tags"] = (
                [tag.strip() for tag in re.split(r"[、,，]", tags_match.group(1)) if tag.strip()][:3]
                if tags_match
                else []
            )
            if title_match or summary_match or category_match:
                item["localized"] = True
                with lock:
                    success_count += 1
        except Exception as exc:
            print(f"⚠️ {item['source']} 资讯中文化失败: {type(exc).__name__}")
            item["category"] = news_category(original_title, original_summary, item.get("category", "开源生态"))
        return item

    with concurrent.futures.ThreadPoolExecutor(max_workers=min(8, len(pending))) as pool:
        result = list(pool.map(localize, pending))
    merged = []
    pending_by_id = {item.get("id"): item for item in result}
    for item in news:
        merged.append(pending_by_id.get(item.get("id"), item))
    print(f"📰 AI 资讯中文化 {success_count}/{len(pending)}（新增 {len(pending)} 条）")
    return merged


def load_previous_payload(path: Path) -> dict[str, Any] | None:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return None
    if payload.get("schema_version") != SCHEMA_VERSION:
        return None
    return payload


def _movement(current_rank: int, previous_rank: int | None) -> dict[str, Any]:
    if previous_rank is None:
        return {"direction": "new", "amount": None, "label": "新上榜"}
    delta = previous_rank - current_rank
    if delta > 0:
        return {"direction": "up", "amount": delta, "label": f"上升 {delta}"}
    if delta < 0:
        return {"direction": "down", "amount": abs(delta), "label": f"下降 {abs(delta)}"}
    return {"direction": "same", "amount": 0, "label": "持平"}


def build_payload(
    all_repos: dict[str, list[dict[str, Any]]],
    previous: dict[str, Any] | None = None,
    now: datetime | None = None,
    news: list[dict[str, Any]] | None = None,
    news_generated_at: str | None = None,
    news_sources: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    now = now or datetime.now(BEIJING_TZ)
    previous_periods = (previous or {}).get("periods", {})
    appearances: dict[str, list[str]] = {}
    for period in PERIODS:
        for repo in all_repos.get(period, []):
            repo_periods = appearances.setdefault(repo["title"].lower(), [])
            if period not in repo_periods:
                repo_periods.append(period)

    periods: dict[str, list[dict[str, Any]]] = {}
    for period in PERIODS:
        previous_ranks = {
            repo["title"].lower(): int(repo["rank"])
            for repo in previous_periods.get(period, [])
            if repo.get("title") and repo.get("rank")
        }
        seen: set[str] = set()
        items = []
        for repo in all_repos.get(period, []):
            key = repo["title"].lower()
            if key in seen:
                continue
            seen.add(key)
            item = deepcopy(repo)
            item["rank"] = len(items) + 1
            item["summary"] = item.get("summary") or generate_fallback_summary(item)
            item["previous_rank"] = previous_ranks.get(key)
            item["movement"] = _movement(item["rank"], item["previous_rank"])
            item["periods"] = appearances.get(key, [period])
            items.append(item)
        periods[period] = items

    return {
        "schema_version": SCHEMA_VERSION,
        "site": {"name": SITE_NAME, "url": SITE_URL},
        "date": now.strftime("%Y-%m-%d"),
        "generated_at": now.isoformat(),
        "source": GITHUB_TRENDING_URL,
        "periods": periods,
        "news": news or [],
        "news_generated_at": news_generated_at or now.isoformat(),
        "news_sources": news_sources or [],
    }


def validate_payload(payload: dict[str, Any]) -> None:
    if payload.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("开放数据 schema_version 不正确")
    periods = payload.get("periods")
    if not isinstance(periods, dict) or any(period not in periods for period in PERIODS):
        raise ValueError("开放数据缺少榜单周期")
    if not periods["daily"]:
        raise ValueError("日榜为空，拒绝生成会覆盖线上内容的空站点")
    for period in PERIODS:
        ranks = [repo.get("rank") for repo in periods[period]]
        if ranks != list(range(1, len(ranks) + 1)):
            raise ValueError(f"{period} 榜单排名不连续")


def _json_text(payload: dict[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=False, indent=2) + "\n"


def generate_rss(payload: dict[str, Any]) -> str:
    ET.register_namespace("atom", "http://www.w3.org/2005/Atom")
    rss = ET.Element("rss", {"version": "2.0"})
    channel = ET.SubElement(rss, "channel")
    ET.SubElement(channel, "title").text = SITE_NAME
    ET.SubElement(channel, "link").text = f"{SITE_URL}/"
    ET.SubElement(channel, "description").text = "每日 GitHub Trending 中文技术榜单"
    ET.SubElement(channel, "language").text = "zh-CN"
    generated = datetime.fromisoformat(payload["generated_at"])
    ET.SubElement(channel, "lastBuildDate").text = format_datetime(generated)
    ET.SubElement(
        channel,
        "{http://www.w3.org/2005/Atom}link",
        {"href": f"{SITE_URL}/feed.xml", "rel": "self", "type": "application/rss+xml"},
    )
    for repo in payload["periods"]["daily"]:
        item = ET.SubElement(channel, "item")
        ET.SubElement(item, "title").text = f"#{repo['rank']} {repo['title']}"
        ET.SubElement(item, "link").text = repo["url"]
        ET.SubElement(item, "guid", {"isPermaLink": "false"}).text = (
            f"{payload['date']}:{repo['title']}"
        )
        ET.SubElement(item, "pubDate").text = format_datetime(generated)
        ET.SubElement(item, "description").text = (
            f"{repo['summary']}｜{repo['language']}｜{repo['stars']} Stars"
        )
    ET.indent(rss, space="  ")
    return '<?xml version="1.0" encoding="UTF-8"?>\n' + ET.tostring(
        rss, encoding="unicode"
    )


def generate_news_rss(news_payload: dict[str, Any]) -> str:
    ET.register_namespace("atom", "http://www.w3.org/2005/Atom")
    rss = ET.Element("rss", {"version": "2.0"})
    channel = ET.SubElement(rss, "channel")
    ET.SubElement(channel, "title").text = f"{SITE_NAME} · AI 科技与开源资讯"
    ET.SubElement(channel, "link").text = f"{SITE_URL}/#news"
    ET.SubElement(channel, "description").text = "权威一手 AI、开源和开发者生态资讯"
    ET.SubElement(channel, "language").text = "zh-CN"
    generated = datetime.fromisoformat(news_payload["generated_at"])
    ET.SubElement(channel, "lastBuildDate").text = format_datetime(generated)
    ET.SubElement(
        channel,
        "{http://www.w3.org/2005/Atom}link",
        {"href": f"{SITE_URL}/news-feed.xml", "rel": "self", "type": "application/rss+xml"},
    )
    for news in news_payload.get("items", []):
        item = ET.SubElement(channel, "item")
        ET.SubElement(item, "title").text = news.get("title", "科技资讯")
        ET.SubElement(item, "link").text = news.get("url", f"{SITE_URL}/#news")
        ET.SubElement(item, "guid", {"isPermaLink": "false"}).text = news.get("id")
        published = parse_news_datetime(news.get("published_at"), now=generated) or generated
        ET.SubElement(item, "pubDate").text = format_datetime(published)
        ET.SubElement(item, "category").text = news.get("category", "开源生态")
        ET.SubElement(item, "description").text = (
            f"{news.get('summary', '')}｜来源：{news.get('source', '公开资讯')}"
        )
    ET.indent(rss, space="  ")
    return '<?xml version="1.0" encoding="UTF-8"?>\n' + ET.tostring(
        rss, encoding="unicode"
    )


def _card_lines(value: Any, width: int, limit: int = 1) -> list[str]:
    lines = textwrap.wrap(str(value or ""), width=width, break_long_words=True)[:limit]
    if not lines:
        return [""]
    source = str(value or "")
    if len("".join(lines)) < len(source.replace(" ", "")):
        lines[-1] = lines[-1].rstrip("，。,. ") + "…"
    return lines


def _trend_tags(payload: dict[str, Any]) -> list[str]:
    tags: list[str] = []
    for item in payload.get("news", []):
        tags.extend(str(tag) for tag in item.get("tags", []) if tag)
        if item.get("category"):
            tags.append(str(item["category"]))
    for repo in payload.get("periods", {}).get("daily", []):
        if repo.get("language") and repo["language"] != "未知":
            tags.append(str(repo["language"]))
    return list(dict.fromkeys(tags))[:3]


def _card_date(payload: dict[str, Any]) -> str:
    value = payload.get("news_generated_at") or payload.get("generated_at")
    try:
        return datetime.fromisoformat(str(value)).astimezone(BEIJING_TZ).strftime("%Y-%m-%d")
    except (TypeError, ValueError):
        return str(payload.get("date", ""))


def _qr_markup(url: str, x: int, y: int, size: int) -> str:
    if segno is None:
        return ""
    qr = segno.make_qr(url, error="m")
    module_width, _ = qr.symbol_size(scale=1, border=0)
    raw = qr.svg_inline(scale=1, border=0, dark="#f4f7f2", light=None)
    inner = raw[raw.find(">") + 1 : raw.rfind("</svg>")]
    scale = size / module_width
    return f'<g transform="translate({x} {y}) scale({scale:.5f})">{inner}</g>'


def _card_text(lines: list[str], x: int, y: int, size: int, fill: str = "#f4f7f2", weight: int = 400, gap: int = 34, anchor: str = "start") -> str:
    chunks = [
        f'<text x="{x}" y="{y}" text-anchor="{anchor}" font-family="Noto Sans CJK SC,Noto Sans SC,PingFang SC,Microsoft YaHei,sans-serif" font-size="{size}px" font-weight="{weight}" fill="{fill}">'
    ]
    for index, line in enumerate(lines):
        chunks.append(f'<tspan x="{x}" dy="{0 if index == 0 else gap}px">{escape(line)}</tspan>')
    chunks.append("</text>")
    return "".join(chunks)


def _card_base(width: int, height: int) -> list[str]:
    return [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<defs><linearGradient id="bg" x1="0" y1="0" x2="1" y2="1"><stop stop-color="#0b1813"/><stop offset="1" stop-color="#153c2b"/></linearGradient></defs>',
        f'<rect width="{width}" height="{height}" rx="40" fill="url(#bg)"/>',
        f'<circle cx="{width - 70}" cy="80" r="180" fill="#73d69f" opacity=".10"/>',
    ]


def _generate_portrait_card(payload: dict[str, Any]) -> str:
    width, height = 1080, 1440
    daily = payload.get("periods", {}).get("daily", [])[:5]
    news = payload.get("news", [])[:4]
    parts = _card_base(width, height)
    parts.extend([
        _card_text(["GITHUB 趋势雷达", "一图看懂今日开源趋势"], 64, 72, 30, weight=760, gap=42),
        _card_text([_card_date(payload)], 64, 165, 18, fill="#a9c0b1"),
        '<rect x="64" y="205" width="952" height="1" fill="#527261"/>',
        _card_text(["今日热榜"], 64, 252, 23, fill="#9fc6ab", weight=700),
    ])
    y = 300
    for index, repo in enumerate(daily):
        parts.append(f'<rect x="64" y="{y - 34}" width="952" height="110" rx="18" fill="#214f3a" opacity=".9"/>')
        parts.append(_card_text([str(repo.get("rank", index + 1)).zfill(2)], 88, y + 8, 36, fill="#82e4ad", weight=760))
        parts.append(_card_text(_card_lines(repo.get("title"), 31), 170, y, 22, weight=700))
        parts.append(_card_text(_card_lines(repo.get("summary") or repo.get("description"), 48), 170, y + 42, 15, fill="#b9d0c1"))
        parts.append(_card_text([f"★ {repo.get('stars', '0')}  ·  {repo.get('language', '未知')}"], 980, y + 2, 13, fill="#a9c0b1", anchor="end"))
        y += 120
    y += 6
    parts.extend([
        f'<rect x="64" y="{y}" width="952" height="1" fill="#527261"/>',
        _card_text(["AI · 开源 · 开发者资讯"], 64, y + 48, 23, fill="#9fc6ab", weight=700),
    ])
    y += 88
    for item in news:
        label = f"[{item.get('category', '资讯')}] {_card_lines(item.get('title'), 48)[0]}"
        parts.append(_card_text([label], 78, y, 17, weight=600))
        parts.append(_card_text([str(item.get("source", "公开资讯"))], 980, y, 12, fill="#91aa9b", anchor="end"))
        y += 50
    tags = "  ".join(f"#{tag}" for tag in _trend_tags(payload))
    parts.extend([
        '<rect x="64" y="1320" width="952" height="1" fill="#527261"/>',
        _card_text([tags or "#开源 #AI #开发者"], 64, 1360, 14, fill="#82e4ad", weight=650),
        _card_text(["ibook000.github.io/GithubTrending", "数据来自公开权威来源"], 64, 1393, 13, fill="#91aa9b", gap=20),
        _qr_markup(f"{SITE_URL}/", 918, 1334, 78),
        "</svg>",
    ])
    return "".join(parts)


def _generate_square_card(payload: dict[str, Any]) -> str:
    width = height = 1080
    daily = payload.get("periods", {}).get("daily", [])[:3]
    news = payload.get("news", [])[:3]
    parts = _card_base(width, height)
    parts.extend([
        _card_text(["GITHUB 趋势雷达", "今日开源趋势"], 62, 70, 30, weight=760, gap=42),
        _card_text([_card_date(payload)], 62, 160, 18, fill="#a9c0b1"),
        '<rect x="62" y="195" width="956" height="1" fill="#527261"/>',
    ])
    y = 255
    for index, repo in enumerate(daily):
        parts.append(f'<rect x="62" y="{y - 35}" width="956" height="120" rx="18" fill="#214f3a" opacity=".9"/>')
        parts.append(_card_text([str(repo.get("rank", index + 1)).zfill(2)], 88, y + 8, 38, fill="#82e4ad", weight=760))
        parts.append(_card_text(_card_lines(repo.get("title"), 30), 175, y, 23, weight=700))
        parts.append(_card_text(_card_lines(repo.get("summary") or repo.get("description"), 48), 175, y + 44, 15, fill="#b9d0c1"))
        y += 132
    parts.extend([
        f'<rect x="62" y="{y}" width="956" height="1" fill="#527261"/>',
        _card_text(["今日资讯"], 62, y + 48, 23, fill="#9fc6ab", weight=700),
    ])
    y += 88
    for item in news:
        label = f"[{item.get('category', '资讯')}] {_card_lines(item.get('title'), 52)[0]}"
        parts.append(_card_text([label], 76, y, 17, weight=600))
        y += 54
    parts.extend([
        '<rect x="62" y="956" width="956" height="1" fill="#527261"/>',
        _card_text(["  ".join(f"#{tag}" for tag in _trend_tags(payload)) or "#开源 #AI #开发者"], 62, 995, 14, fill="#82e4ad", weight=650),
        _card_text(["ibook000.github.io/GithubTrending"], 62, 1038, 13, fill="#91aa9b"),
        _qr_markup(f"{SITE_URL}/", 912, 974, 86),
        "</svg>",
    ])
    return "".join(parts)


def _generate_og_card(payload: dict[str, Any]) -> str:
    width, height = 1200, 630
    daily = payload.get("periods", {}).get("daily", [])[:3]
    featured = (payload.get("news") or [{}])[0]
    parts = _card_base(width, height)
    parts.extend([
        _card_text(["GITHUB 趋势雷达", "今日开源趋势"], 52, 62, 26, weight=760, gap=36),
        _card_text([_card_date(payload)], 52, 140, 16, fill="#a9c0b1"),
        '<rect x="52" y="170" width="1096" height="1" fill="#527261"/>',
        _card_text(["TOP REPOSITORIES"], 52, 210, 14, fill="#82e4ad", weight=700),
    ])
    y = 258
    for index, repo in enumerate(daily):
        parts.append(_card_text([f"{str(repo.get('rank', index + 1)).zfill(2)}  {_card_lines(repo.get('title'), 29)[0]}"], 58, y, 20, weight=700))
        parts.append(_card_text([f"★ {repo.get('stars', '0')} · {repo.get('language', '未知')}"], 610, y, 13, fill="#9bb6a5", anchor="end"))
        y += 74
    parts.extend([
        '<rect x="665" y="205" width="1" height="310" fill="#527261"/>',
        _card_text(["FEATURED NEWS"], 710, 210, 14, fill="#82e4ad", weight=700),
        _card_text(_card_lines(featured.get("title") or "今日权威资讯正在更新", 24, 3), 710, 265, 26, weight=720, gap=36),
        _card_text(_card_lines(featured.get("summary") or "聚合 AI、开源与开发者生态的一手信息。", 34, 3), 710, 395, 16, fill="#b9d0c1", gap=25),
        _card_text([str(featured.get("source", "公开权威来源"))], 710, 490, 13, fill="#91aa9b"),
        '<rect x="52" y="545" width="1096" height="1" fill="#527261"/>',
        _card_text(["  ".join(f"#{tag}" for tag in _trend_tags(payload)) or "#开源 #AI #开发者"], 52, 582, 14, fill="#82e4ad", weight=650),
        _card_text(["ibook000.github.io/GithubTrending"], 1145, 582, 13, fill="#91aa9b", anchor="end"),
        _qr_markup(f"{SITE_URL}/", 1070, 475, 64),
        "</svg>",
    ])
    return "".join(parts)


def generate_trend_card(payload: dict[str, Any], variant: str = "portrait") -> str:
    generators = {"portrait": _generate_portrait_card, "square": _generate_square_card, "og": _generate_og_card}
    if variant not in generators:
        raise ValueError(f"未知趋势卡片类型: {variant}")
    return generators[variant](payload)


def _fallback_card_png(payload: dict[str, Any], variant: str) -> bytes:
    """在本机缺少原生 Cairo 时生成可用 PNG，线上仍优先使用 CairoSVG。"""
    if Image is None or ImageDraw is None or ImageFont is None:
        raise RuntimeError("缺少 CairoSVG 与 Pillow，无法生成 PNG 趋势卡片")
    from io import BytesIO

    spec = CARD_VARIANTS[variant]
    width, height = int(spec["width"]), int(spec["height"])
    image = Image.new("RGB", (width, height), "#0b1813")
    draw = ImageDraw.Draw(image)
    draw.ellipse((width - 310, -120, width + 80, 270), fill="#153c2b")

    font_candidates = (
        "/System/Library/Fonts/PingFang.ttc",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    )

    def font(size: int) -> Any:
        for path in font_candidates:
            try:
                return ImageFont.truetype(path, size=size)
            except OSError:
                continue
        return ImageFont.load_default()

    margin = 58 if variant == "og" else 64
    draw.text((margin, margin), "GITHUB TRENDING RADAR", font=font(30), fill="#f4f7f2")
    draw.text((margin, margin + 50), _card_date(payload), font=font(18), fill="#a9c0b1")
    y = margin + 118
    daily_limit = 3 if variant != "portrait" else 5
    for index, repo in enumerate(payload.get("periods", {}).get("daily", [])[:daily_limit]):
        row_height = 110 if variant != "og" else 80
        draw.rounded_rectangle(
            (margin, y, width - margin, y + row_height - 12),
            radius=16,
            fill="#214f3a",
        )
        draw.text(
            (margin + 20, y + 20),
            str(repo.get("rank", index + 1)).zfill(2),
            font=font(28),
            fill="#82e4ad",
        )
        draw.text(
            (margin + 90, y + 20),
            _card_lines(repo.get("title"), 34)[0],
            font=font(22),
            fill="#f4f7f2",
        )
        y += row_height
    if variant != "og":
        y += 18
        draw.text((margin, y), "AI / OPEN SOURCE NEWS", font=font(20), fill="#82e4ad")
        y += 48
        news_limit = 4 if variant == "portrait" else 3
        for item in payload.get("news", [])[:news_limit]:
            draw.text(
                (margin + 12, y),
                _card_lines(item.get("title"), 45)[0],
                font=font(17),
                fill="#f4f7f2",
            )
            y += 48
    draw.text(
        (margin, height - 62),
        "ibook000.github.io/GithubTrending",
        font=font(15),
        fill="#91aa9b",
    )
    buffer = BytesIO()
    image.save(buffer, format="PNG", optimize=True)
    return buffer.getvalue()


def generate_card_assets(payload: dict[str, Any], output_dir: Path) -> dict[str, Any]:
    cards_dir = output_dir / "cards"
    card_date = _card_date(payload)
    archive_dir = cards_dir / card_date
    cards_dir.mkdir(parents=True, exist_ok=True)
    archive_dir.mkdir(parents=True, exist_ok=True)
    relevant = {"date": card_date, "daily": payload.get("periods", {}).get("daily", [])[:5], "news": payload.get("news", [])[:4]}
    content_hash = hashlib.sha256(json.dumps(relevant, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()[:16]
    variants: dict[str, Any] = {}
    for variant, spec in CARD_VARIANTS.items():
        svg = generate_trend_card(payload, variant=variant)
        latest_svg = cards_dir / f"latest-{variant}.svg"
        latest_png = cards_dir / f"latest-{variant}.png"
        latest_svg.write_text(svg, encoding="utf-8")
        (archive_dir / f"{variant}.svg").write_text(svg, encoding="utf-8")
        png_bytes = (
            cairosvg.svg2png(
                bytestring=svg.encode("utf-8"),
                output_width=spec["width"],
                output_height=spec["height"],
            )
            if cairosvg is not None
            else _fallback_card_png(payload, variant)
        )
        latest_png.write_bytes(png_bytes)
        (archive_dir / f"{variant}.png").write_bytes(png_bytes)
        svg_path = f"cards/latest-{variant}.svg"
        png_path = f"cards/latest-{variant}.png"
        variants[variant] = {
            "label": spec["label"],
            "width": spec["width"],
            "height": spec["height"],
            # 保留简单路径字段，兼容早期消费者；files 提供完整下载元数据。
            "svg": svg_path,
            "png": png_path,
            "files": {
                "svg": {
                    "path": svg_path,
                    "media_type": "image/svg+xml",
                    "download_url": f"{SITE_URL}/{svg_path}",
                },
                "png": {
                    "path": png_path,
                    "media_type": "image/png",
                    "download_url": f"{SITE_URL}/{png_path}",
                },
            },
        }
    shutil.copy2(cards_dir / "latest-portrait.svg", output_dir / "today-card.svg")
    shutil.copy2(cards_dir / "latest-portrait.png", output_dir / "today-card.png")
    manifest = {"schema_version": "1.0", "generated_at": payload.get("news_generated_at") or payload.get("generated_at"), "date": card_date, "content_hash": content_hash, "variants": variants}
    (cards_dir / "manifest.json").write_text(_json_text(manifest), encoding="utf-8")
    (archive_dir / "manifest.json").write_text(_json_text(manifest), encoding="utf-8")
    return manifest


def generate_site(
    payload: dict[str, Any], output_dir: Path, *, write_trending_snapshot: bool = True
) -> None:
    """生成站点、开放数据、RSS 和 SEO 文件。"""
    validate_payload(payload)
    assets_dir = project_root() / "assets"
    output_dir.mkdir(parents=True, exist_ok=True)
    data_dir = output_dir / "data"
    data_dir.mkdir(exist_ok=True)
    news_dir = data_dir / "news"
    news_dir.mkdir(exist_ok=True)

    payload_text = _json_text(payload)
    (data_dir / "latest.json").write_text(payload_text, encoding="utf-8")
    if write_trending_snapshot:
        (data_dir / f"{payload['date']}.json").write_text(payload_text, encoding="utf-8")
    (output_dir / "feed.xml").write_text(generate_rss(payload), encoding="utf-8")
    news_payload = {
        "schema_version": NEWS_SCHEMA_VERSION,
        "generated_at": payload.get("news_generated_at") or payload["generated_at"],
        "items": payload.get("news", []),
        "sources": payload.get("news_sources", []),
    }
    news_text = _json_text(news_payload)
    news_date = _card_date(payload)
    (news_dir / "latest.json").write_text(news_text, encoding="utf-8")
    (news_dir / f"{news_date}.json").write_text(news_text, encoding="utf-8")
    (output_dir / "news-feed.xml").write_text(
        generate_news_rss(news_payload), encoding="utf-8"
    )
    generate_card_assets(payload, output_dir)

    template = (assets_dir / "index.html").read_text(encoding="utf-8")
    embedded = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).replace(
        "<", "\\u003c"
    )
    json_ld = json.dumps(
        {
            "@context": "https://schema.org",
            "@type": "WebSite",
            "name": SITE_NAME,
            "url": f"{SITE_URL}/",
            "description": "每日更新的 GitHub Trending 中文技术榜单与开放数据。",
            "potentialAction": {
                "@type": "ReadAction",
                "target": f"{SITE_URL}/#news",
            },
        },
        ensure_ascii=False,
    ).replace("<", "\\u003c")
    html = (
        template.replace("{{GENERATED_DATE}}", payload["date"])
        .replace("{{INITIAL_DATA}}", embedded)
        .replace("{{JSON_LD}}", json_ld)
        .replace("{{SITE_URL}}", SITE_URL)
    )
    (output_dir / "index.html").write_text(html, encoding="utf-8")
    (output_dir / "github_trending_cards.html").write_text(html, encoding="utf-8")

    for name in ("styles.css", "app.js", "favicon.svg", "social-card.svg"):
        shutil.copy2(assets_dir / name, output_dir / name)
    (output_dir / "robots.txt").write_text(
        f"User-agent: *\nAllow: /\nSitemap: {SITE_URL}/sitemap.xml\n", encoding="utf-8"
    )
    (output_dir / "sitemap.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        f"  <url><loc>{SITE_URL}/</loc><lastmod>{payload['date']}</lastmod></url>\n"
        f"  <url><loc>{SITE_URL}/history/</loc><lastmod>{payload['date']}</lastmod></url>\n"
        "</urlset>\n",
        encoding="utf-8",
    )
    (output_dir / "metadata.json").write_text(
        _json_text(
            {
                "date": payload["date"],
                "generated_at": payload["generated_at"],
                "source": "GitHub Trending Radar",
                "schema_version": SCHEMA_VERSION,
            }
        ),
        encoding="utf-8",
    )


def fetch_all_periods() -> dict[str, list[dict[str, str]]]:
    result = {period: [] for period in PERIODS}
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(PERIODS)) as pool:
        futures = {pool.submit(fetch_github_trending, period): period for period in PERIODS}
        for future in concurrent.futures.as_completed(futures):
            period = futures[future]
            try:
                result[period] = future.result()
            except Exception as exc:  # 防止单个线程异常中断全部抓取
                print(f"❌ {period} 抓取任务异常: {exc}")
    return result


def _resolved_api_key() -> str | None:
    config = get_llm_config()
    api_key = config["api_key"]
    if not api_key and str(config["base_url"]).startswith("http://"):
        api_key = "not-needed"
    return str(api_key) if api_key else None


def _previous_news_bundle(output_dir: Path, previous_payload: dict[str, Any] | None) -> dict[str, Any] | None:
    bundle = load_previous_payload(output_dir / "data" / "news" / "latest.json")
    if bundle:
        return bundle
    if previous_payload and previous_payload.get("news"):
        return {
            "schema_version": NEWS_SCHEMA_VERSION,
            "generated_at": previous_payload.get("news_generated_at") or previous_payload.get("generated_at"),
            "items": previous_payload.get("news", []),
            "sources": previous_payload.get("news_sources", []),
        }
    return None


def _refresh_news(api_key: str | None, previous: dict[str, Any] | None) -> dict[str, Any]:
    bundle = fetch_news_bundle(previous=previous)
    if api_key and bundle["items"]:
        bundle["items"] = ai_localize_news(bundle["items"], api_key, previous=previous)
    for item in bundle["items"]:
        item["category"] = news_category(
            str(item.get("original_title") or item.get("title") or ""),
            str(item.get("original_summary") or item.get("summary") or ""),
            str(item.get("category") or "开源生态"),
        ) if item.get("category") not in {"AI 模型", "研究", "开源生态", "开发工具", "云原生", "安全"} else item["category"]
    if not bundle["items"]:
        raise RuntimeError("未获取到新闻且没有上一版可用数据，停止部署")
    print(f"📰 资讯聚合 {len(bundle['items'])} 条")
    return bundle


def run(output_dir: Path | str = "site", mode: str = "full") -> dict[str, Any]:
    output_dir = Path(output_dir)
    if mode == "news":
        return run_news_refresh(output_dir)
    if mode != "full":
        raise ValueError(f"不支持的生成模式: {mode}")
    print("🚀 开始生成 GitHub 趋势雷达")
    all_repos = fetch_all_periods()
    if not all_repos["daily"]:
        raise RuntimeError("未获取到日榜数据，停止生成和部署")

    api_key = _resolved_api_key()
    if api_key:
        print("✅ 已检测到 API 密钥（密钥内容已隐藏）")
    else:
        print("ℹ️ 未配置 AI 密钥，将使用本地备用摘要")
    for period in PERIODS:
        repos = all_repos[period]
        if api_key:
            all_repos[period] = ai_summarize_projects(repos, str(api_key))
        else:
            for repo in repos:
                repo["summary"] = generate_fallback_summary(repo)

    previous = load_previous_payload(output_dir / "data" / "latest.json")
    previous_news = _previous_news_bundle(output_dir, previous)
    news_bundle = _refresh_news(api_key, previous_news)
    payload = build_payload(
        all_repos,
        previous=previous,
        news=news_bundle["items"],
        news_generated_at=news_bundle["generated_at"],
        news_sources=news_bundle["sources"],
    )
    generate_site(payload, output_dir, write_trending_snapshot=True)
    print(f"🎉 站点已生成到 {output_dir.resolve()}")
    return payload


def run_news_refresh(output_dir: Path | str = "site") -> dict[str, Any]:
    output_dir = Path(output_dir)
    print("📰 开始轻量刷新 AI 科技与开源资讯")
    previous_payload = load_previous_payload(output_dir / "data" / "latest.json")
    if not previous_payload:
        raise RuntimeError("缺少上一版 data/latest.json，新闻轻量刷新无法继续")
    validate_payload(previous_payload)
    previous_news = _previous_news_bundle(output_dir, previous_payload)
    api_key = _resolved_api_key()
    news_bundle = _refresh_news(api_key, previous_news)
    payload = deepcopy(previous_payload)
    payload["news"] = news_bundle["items"]
    payload["news_generated_at"] = news_bundle["generated_at"]
    payload["news_sources"] = news_bundle["sources"]
    generate_site(payload, output_dir, write_trending_snapshot=False)
    print(f"🎉 新闻与趋势卡片已刷新到 {output_dir.resolve()}")
    return payload


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description=SITE_NAME)
    parser.add_argument(
        "--mode",
        choices=("full", "news"),
        default=os.environ.get("REFRESH_MODE", "full"),
        help="full 抓取全部榜单，news 仅刷新新闻与趋势卡片",
    )
    args = parser.parse_args()
    run(os.environ.get("OUTPUT_DIR", "site"), mode=args.mode)


if __name__ == "__main__":
    main()
