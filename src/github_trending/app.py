"""GitHub 趋势雷达的数据抓取、结构化输出和静态站点生成器。"""

from __future__ import annotations

import concurrent.futures
import json
import os
import shutil
import threading
import time
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from email.utils import format_datetime
from pathlib import Path
from typing import Any
from urllib.parse import urljoin
from xml.etree import ElementTree as ET

import requests
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

try:
    from openai import OpenAI
except ImportError:  # pragma: no cover - AI 功能是可选的
    OpenAI = None


SCHEMA_VERSION = "1.0"
SITE_NAME = "GitHub 趋势雷达"
SITE_URL = os.environ.get("SITE_URL", "https://ibook000.github.io/GithubTrending").rstrip("/")
DEFAULT_LLM_BASE_URL = "https://integrate.api.nvidia.com/v1"
DEFAULT_LLM_MODEL = "minimaxai/minimax-m2.7"
GITHUB_TRENDING_URL = "https://github.com/trending"
REQUEST_TIMEOUT = (10, 30)
PERIODS = ("daily", "weekly", "monthly")
BEIJING_TZ = timezone(timedelta(hours=8))
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36"
)


def project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def get_llm_config() -> dict[str, str | None]:
    return {
        "api_key": os.environ.get("NVIDIA_API_KEY")
        or os.environ.get("OPENROUTER_API_KEY"),
        "base_url": os.environ.get("LLM_BASE_URL", DEFAULT_LLM_BASE_URL),
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


def generate_site(payload: dict[str, Any], output_dir: Path) -> None:
    """生成站点、开放数据、RSS 和 SEO 文件。"""
    validate_payload(payload)
    assets_dir = project_root() / "assets"
    output_dir.mkdir(parents=True, exist_ok=True)
    data_dir = output_dir / "data"
    data_dir.mkdir(exist_ok=True)

    payload_text = _json_text(payload)
    (data_dir / "latest.json").write_text(payload_text, encoding="utf-8")
    (data_dir / f"{payload['date']}.json").write_text(payload_text, encoding="utf-8")
    (output_dir / "feed.xml").write_text(generate_rss(payload), encoding="utf-8")

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


def run(output_dir: Path | str = "site") -> dict[str, Any]:
    output_dir = Path(output_dir)
    print("🚀 开始生成 GitHub 趋势雷达")
    all_repos = fetch_all_periods()
    if not all_repos["daily"]:
        raise RuntimeError("未获取到日榜数据，停止生成和部署")

    config = get_llm_config()
    api_key = config["api_key"]
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
    payload = build_payload(all_repos, previous=previous)
    generate_site(payload, output_dir)
    print(f"🎉 站点已生成到 {output_dir.resolve()}")
    return payload


def main() -> None:
    run(os.environ.get("OUTPUT_DIR", "site"))


if __name__ == "__main__":
    main()
