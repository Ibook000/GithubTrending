#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
生成历史统计页面
扫描 history 目录，输出更美观的历史档案页
"""

import json
import os
from datetime import datetime, timedelta, timezone
from html import escape


DATE_FORMAT = "%Y-%m-%d"
REQUIRED_FILES = ["index.html", "github_trending_cards.css", "metadata.json"]
BEIJING_TZ = timezone(timedelta(hours=8))
WEEKDAYS = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]


def list_history_dirs():
    """扫描 history 目录中的日期子目录"""
    history_dirs = []
    if not os.path.exists("history"):
        return history_dirs

    for item in os.listdir("history"):
        item_path = os.path.join("history", item)
        if not os.path.isdir(item_path):
            continue
        try:
            datetime.strptime(item, DATE_FORMAT)
            history_dirs.append(item)
        except ValueError:
            continue

    history_dirs.sort(reverse=True)
    return history_dirs


def parse_generated_time(date_dir):
    """解析历史记录的生成时间"""
    metadata_path = os.path.join("history", date_dir, "metadata.json")
    index_path = os.path.join("history", date_dir, "index.html")

    if os.path.exists(metadata_path):
        try:
            with open(metadata_path, "r", encoding="utf-8") as file:
                metadata = json.load(file)
            generated_at = metadata.get("generated_at")
            if generated_at:
                dt = datetime.fromisoformat(str(generated_at).replace("Z", "+00:00"))
                return dt.astimezone(BEIJING_TZ)
        except Exception as error:
            print(f"读取 {metadata_path} 失败: {error}")

    if os.path.exists(index_path):
        try:
            timestamp = os.path.getmtime(index_path)
            return datetime.fromtimestamp(timestamp, BEIJING_TZ)
        except OSError as error:
            print(f"读取 {index_path} 修改时间失败: {error}")

    return None


def format_generated_time(dt):
    if dt is None:
        return "未知"
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def format_display_date(date_dir):
    try:
        date_obj = datetime.strptime(date_dir, DATE_FORMAT)
        return f"{date_obj.strftime('%Y年%m月%d日')} {WEEKDAYS[date_obj.weekday()]}"
    except ValueError:
        return date_dir


def format_relative_label(date_dir, latest_date):
    if not latest_date:
        return ""
    try:
        current = datetime.strptime(date_dir, DATE_FORMAT).date()
        latest = datetime.strptime(latest_date, DATE_FORMAT).date()
        delta = (latest - current).days
    except ValueError:
        return ""

    if delta == 0:
        return "最新"
    if delta == 1:
        return "前一天"
    if delta < 7:
        return f"{delta} 天前"
    if delta < 30:
        return f"{delta // 7} 周前"
    return f"{delta} 天前"


def is_complete_record(date_dir):
    dir_path = os.path.join("history", date_dir)
    return all(os.path.exists(os.path.join(dir_path, name)) for name in REQUIRED_FILES)


def compute_streak(history_dirs):
    """从最新记录开始计算连续天数"""
    if not history_dirs:
        return 0

    dates = {datetime.strptime(item, DATE_FORMAT).date() for item in history_dirs}
    current = max(dates)
    streak = 0
    while current in dates:
        streak += 1
        current -= timedelta(days=1)
    return streak


def build_history_items(history_dirs, latest_date):
    items = []
    for index, date_dir in enumerate(history_dirs, start=1):
        generated_dt = parse_generated_time(date_dir)
        complete = is_complete_record(date_dir)
        status_text = "完整" if complete else "缺文件"
        status_class = "is-complete" if complete else "is-warning"
        relative_text = format_relative_label(date_dir, latest_date)

        items.append(
            f"""
            <article class="history-item reveal-item" style="--delay:{index * 55}ms;">
                <div class="history-rank">{index:02d}</div>
                <div class="history-main">
                    <div class="history-topline">
                        <span class="history-chip {status_class}">{escape(status_text)}</span>
                        {'<span class="history-chip muted">' + escape(relative_text) + '</span>' if relative_text else ''}
                    </div>
                    <h3>{escape(format_display_date(date_dir))}</h3>
                    <p class="history-time">生成时间：{escape(format_generated_time(generated_dt))}</p>
                    <p class="history-note">归档包含当日榜单页面、样式文件和元数据，方便回溯某天的热门项目。</p>
                </div>
                <div class="history-actions">
                    <span class="history-path">history/{escape(date_dir)}/</span>
                    <a href="{escape(date_dir)}/" class="history-link" target="_blank" rel="noopener noreferrer">查看页面</a>
                </div>
            </article>
            """
        )
    return "\n".join(items)


def build_history_html(total_days, latest_date, earliest_date, data_integrity, integrity_detail, streak_days, history_items_html):
    latest_text = latest_date or "无数据"
    earliest_text = earliest_date or "无数据"

    empty_html = """
        <div class="empty-state reveal-item">
            <p>当前还没有历史记录。下一次自动生成后，这里会开始沉淀每日榜单。</p>
        </div>
    """

    archive_html = history_items_html if history_items_html else empty_html

    return f"""<!DOCTYPE html>
<html lang="zh-cn">
<head>
    <meta charset="UTF-8">
    <title>GitHub 趋势榜单 - 历史档案</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Noto+Sans+SC:wght@400;500;700;800&family=Space+Grotesk:wght@400;500;700&display=swap" rel="stylesheet">
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
    <style>
        :root {{
            --bg-page: #f3ecdf;
            --bg-page-accent: rgba(203, 111, 52, 0.18);
            --bg-page-cool: rgba(15, 118, 110, 0.14);
            --surface: rgba(255, 248, 239, 0.76);
            --surface-strong: rgba(255, 252, 247, 0.92);
            --surface-muted: rgba(255, 255, 255, 0.56);
            --hero-bg: linear-gradient(135deg, #111827 0%, #19212d 45%, #0f766e 140%);
            --hero-panel: rgba(12, 18, 26, 0.64);
            --text-primary: #122033;
            --text-secondary: #45556d;
            --text-muted: #6f7d90;
            --text-inverse: #f8fafc;
            --accent: #c56b2b;
            --accent-soft: rgba(197, 107, 43, 0.14);
            --accent-cool: #2c9c94;
            --border: rgba(18, 32, 51, 0.12);
            --border-strong: rgba(18, 32, 51, 0.22);
            --shadow-soft: 0 24px 60px rgba(34, 37, 41, 0.14);
            --shadow-hero: 0 42px 96px rgba(7, 10, 17, 0.26);
        }}

        * {{
            box-sizing: border-box;
        }}

        html {{
            scroll-behavior: smooth;
        }}

        body {{
            margin: 0;
            min-height: 100vh;
            font-family: "Noto Sans SC", "PingFang SC", "Microsoft YaHei", sans-serif;
            color: var(--text-primary);
            line-height: 1.7;
            background:
                radial-gradient(circle at top left, var(--bg-page-accent), transparent 34%),
                radial-gradient(circle at 88% 12%, var(--bg-page-cool), transparent 28%),
                linear-gradient(180deg, var(--bg-page) 0%, color-mix(in srgb, var(--bg-page) 88%, #ffffff 12%) 100%);
        }}

        body::before,
        body::after {{
            content: "";
            position: fixed;
            width: 34vw;
            height: 34vw;
            pointer-events: none;
            z-index: 0;
            filter: blur(84px);
            opacity: 0.4;
        }}

        body::before {{
            top: -8vw;
            right: -10vw;
            background: var(--bg-page-accent);
        }}

        body::after {{
            bottom: -12vw;
            left: -12vw;
            background: var(--bg-page-cool);
        }}

        a {{
            color: inherit;
        }}

        .page-shell {{
            position: relative;
            z-index: 1;
            width: min(1320px, calc(100% - 32px));
            margin: 0 auto;
            padding: 24px 0 56px;
        }}

        .hero {{
            position: relative;
            overflow: hidden;
            display: grid;
            grid-template-columns: minmax(0, 1.18fr) minmax(320px, 0.82fr);
            gap: 32px;
            min-height: min(860px, calc(100svh - 48px));
            padding: clamp(78px, 11vw, 132px) clamp(24px, 4vw, 52px) 36px;
            border-radius: 36px;
            background: var(--hero-bg);
            box-shadow: var(--shadow-hero);
        }}

        .hero::before,
        .hero::after {{
            content: "";
            position: absolute;
            border-radius: 999px;
            pointer-events: none;
        }}

        .hero::before {{
            width: 42vw;
            height: 42vw;
            top: -16vw;
            right: -8vw;
            background: radial-gradient(circle, rgba(255, 218, 185, 0.24) 0%, rgba(255, 218, 185, 0) 68%);
        }}

        .hero::after {{
            width: 28vw;
            height: 28vw;
            bottom: -12vw;
            left: 34%;
            background: radial-gradient(circle, rgba(88, 199, 194, 0.18) 0%, rgba(88, 199, 194, 0) 74%);
        }}

        .hero-copy,
        .hero-panel {{
            position: relative;
            z-index: 1;
        }}

        .hero-copy {{
            display: flex;
            flex-direction: column;
            justify-content: center;
            max-width: 720px;
        }}

        .eyebrow,
        .metric-number,
        .archive-count,
        .history-rank,
        .history-link,
        .hero h1,
        .archive-head h2 {{
            font-family: "Space Grotesk", "Noto Sans SC", sans-serif;
        }}

        .eyebrow {{
            display: inline-flex;
            align-items: center;
            gap: 10px;
            color: rgba(248, 250, 252, 0.76);
            font-size: 0.82rem;
            font-weight: 700;
            letter-spacing: 0.2em;
            text-transform: uppercase;
        }}

        .eyebrow::before {{
            content: "";
            width: 42px;
            height: 1px;
            background: rgba(248, 250, 252, 0.4);
        }}

        .hero h1 {{
            margin: 18px 0 0;
            color: var(--text-inverse);
            font-size: clamp(3.2rem, 8vw, 6rem);
            line-height: 0.97;
            letter-spacing: -0.08em;
        }}

        .hero-lead {{
            max-width: 38rem;
            margin: 20px 0 0;
            color: rgba(248, 250, 252, 0.82);
            font-size: clamp(1.02rem, 1.7vw, 1.22rem);
        }}

        .hero-actions {{
            display: flex;
            flex-wrap: wrap;
            gap: 14px;
            margin-top: 32px;
        }}

        .primary-link,
        .secondary-link,
        .history-link {{
            display: inline-flex;
            align-items: center;
            justify-content: center;
            min-height: 48px;
            padding: 0 20px;
            border-radius: 999px;
            text-decoration: none;
            transition: transform 0.24s ease, background 0.24s ease, border-color 0.24s ease, color 0.24s ease;
        }}

        .primary-link {{
            background: var(--accent);
            color: #fff9f4;
            font-weight: 700;
            box-shadow: 0 18px 28px rgba(197, 107, 43, 0.22);
        }}

        .secondary-link {{
            border: 1px solid rgba(248, 250, 252, 0.18);
            background: rgba(248, 250, 252, 0.08);
            color: rgba(248, 250, 252, 0.92);
            backdrop-filter: blur(12px);
        }}

        .primary-link:hover,
        .secondary-link:hover,
        .history-link:hover {{
            transform: translateY(-2px);
        }}

        .metrics-grid {{
            display: grid;
            grid-template-columns: repeat(2, minmax(0, 1fr));
            gap: 14px;
            margin-top: 34px;
        }}

        .metric-card {{
            padding: 18px;
            border-radius: 24px;
            border: 1px solid rgba(248, 250, 252, 0.12);
            background: rgba(248, 250, 252, 0.06);
            backdrop-filter: blur(14px);
        }}

        .metric-number {{
            display: block;
            color: var(--text-inverse);
            font-size: clamp(1.6rem, 2.2vw, 2.4rem);
            letter-spacing: -0.06em;
            line-height: 1;
        }}

        .metric-label {{
            display: block;
            margin-top: 8px;
            color: rgba(248, 250, 252, 0.74);
            font-size: 0.92rem;
        }}

        .hero-note {{
            margin: 18px 0 0;
            color: rgba(248, 250, 252, 0.62);
            font-size: 0.92rem;
        }}

        .hero-panel {{
            align-self: end;
            padding: 28px;
            border-radius: 28px;
            border: 1px solid rgba(248, 250, 252, 0.12);
            background: var(--hero-panel);
            backdrop-filter: blur(18px);
        }}

        .panel-label {{
            display: inline-block;
            color: rgba(248, 250, 252, 0.64);
            font-family: "Space Grotesk", "Noto Sans SC", sans-serif;
            font-size: 0.76rem;
            letter-spacing: 0.22em;
            text-transform: uppercase;
        }}

        .panel-title {{
            margin: 14px 0 0;
            color: var(--text-inverse);
            font-size: clamp(1.7rem, 2.8vw, 2.5rem);
            line-height: 1.08;
        }}

        .panel-copy,
        .panel-list {{
            margin: 16px 0 0;
            color: rgba(248, 250, 252, 0.78);
        }}

        .panel-list {{
            padding-left: 18px;
        }}

        .archive-shell {{
            margin-top: 30px;
            padding: 0 12px;
        }}

        .archive-head {{
            display: flex;
            justify-content: space-between;
            align-items: end;
            gap: 20px;
            padding-bottom: 22px;
            border-bottom: 1px solid var(--border-strong);
        }}

        .archive-head h2 {{
            margin: 10px 0 0;
            font-size: clamp(2rem, 4vw, 3.3rem);
            line-height: 1;
            letter-spacing: -0.06em;
        }}

        .archive-head .eyebrow {{
            color: var(--text-muted);
        }}

        .archive-head .eyebrow::before {{
            background: var(--border-strong);
        }}

        .archive-head p {{
            margin: 12px 0 0;
            color: var(--text-secondary);
            max-width: 52rem;
        }}

        .archive-side {{
            display: flex;
            flex-direction: column;
            align-items: flex-end;
            color: var(--text-muted);
        }}

        .archive-count {{
            color: var(--accent);
            font-size: clamp(2rem, 4vw, 3.4rem);
            line-height: 1;
            letter-spacing: -0.08em;
        }}

        .archive-note {{
            font-size: 0.86rem;
            letter-spacing: 0.1em;
            text-transform: uppercase;
        }}

        .archive-list {{
            display: flex;
            flex-direction: column;
        }}

        .history-item {{
            display: grid;
            grid-template-columns: 88px minmax(0, 1fr) minmax(220px, 260px);
            gap: 24px;
            padding: 28px 8px;
            border-bottom: 1px solid var(--border);
            opacity: 0;
            transform: translateY(28px);
            transition:
                opacity 0.6s ease,
                transform 0.6s ease,
                background 0.24s ease,
                border-color 0.24s ease;
            transition-delay: var(--delay, 0ms);
        }}

        .history-item:hover {{
            background: color-mix(in srgb, var(--surface) 78%, transparent 22%);
            border-color: var(--border-strong);
        }}

        .history-rank {{
            display: flex;
            align-items: flex-start;
            justify-content: center;
            color: var(--accent);
            font-size: clamp(2.1rem, 4vw, 3.4rem);
            font-weight: 700;
            letter-spacing: -0.08em;
            line-height: 0.9;
            opacity: 0.82;
        }}

        .history-topline {{
            display: flex;
            flex-wrap: wrap;
            gap: 10px;
        }}

        .history-chip {{
            display: inline-flex;
            align-items: center;
            min-height: 34px;
            padding: 0 12px;
            border-radius: 999px;
            border: 1px solid var(--border);
            background: var(--surface-muted);
            color: var(--text-secondary);
            font-size: 0.84rem;
            font-weight: 700;
        }}

        .history-chip.is-complete {{
            color: var(--accent-cool);
            border-color: rgba(44, 156, 148, 0.24);
            background: rgba(44, 156, 148, 0.1);
        }}

        .history-chip.is-warning {{
            color: var(--accent);
            border-color: rgba(197, 107, 43, 0.24);
            background: rgba(197, 107, 43, 0.1);
        }}

        .history-chip.muted {{
            color: var(--text-muted);
        }}

        .history-main h3 {{
            margin: 14px 0 0;
            font-family: "Space Grotesk", "Noto Sans SC", sans-serif;
            font-size: clamp(1.4rem, 2vw, 2rem);
            line-height: 1.08;
            letter-spacing: -0.04em;
        }}

        .history-time,
        .history-note,
        .history-path {{
            color: var(--text-secondary);
        }}

        .history-time {{
            margin: 14px 0 0;
        }}

        .history-note {{
            margin: 10px 0 0;
            max-width: 52rem;
        }}

        .history-actions {{
            display: flex;
            flex-direction: column;
            align-items: flex-start;
            gap: 14px;
        }}

        .history-path {{
            display: inline-flex;
            align-items: center;
            min-height: 40px;
            padding: 0 14px;
            border-radius: 999px;
            border: 1px solid var(--border);
            background: var(--surface-muted);
            font-size: 0.9rem;
        }}

        .history-link {{
            border: 1px solid var(--border-strong);
            background: transparent;
            color: var(--text-primary);
            font-weight: 700;
        }}

        .history-link:hover {{
            border-color: var(--accent);
            color: var(--accent);
        }}

        .empty-state {{
            padding: 52px 8px;
            color: var(--text-secondary);
        }}

        .hero,
        .hero-panel,
        .archive-head,
        .empty-state {{
            opacity: 0;
            transform: translateY(28px);
            transition: opacity 0.65s ease, transform 0.65s ease;
        }}

        .hero.in-view,
        .hero-panel.in-view,
        .archive-head.in-view,
        .history-item.in-view,
        .empty-state.in-view {{
            opacity: 1;
            transform: translateY(0);
        }}

        ::selection {{
            background: var(--accent);
            color: #fff;
        }}

        @media (max-width: 1120px) {{
            .hero {{
                min-height: auto;
                grid-template-columns: 1fr;
            }}

            .hero-panel,
            .archive-side {{
                align-self: auto;
            }}

            .archive-head {{
                flex-direction: column;
                align-items: flex-start;
            }}

            .archive-side {{
                align-items: flex-start;
            }}

            .history-item {{
                grid-template-columns: 72px minmax(0, 1fr);
            }}

            .history-actions {{
                grid-column: 2;
            }}
        }}

        @media (max-width: 780px) {{
            .page-shell {{
                width: min(100% - 20px, 100%);
                padding-top: 14px;
            }}

            .hero {{
                padding: 72px 18px 28px;
                border-radius: 28px;
            }}

            .metrics-grid {{
                grid-template-columns: 1fr;
            }}

            .archive-shell {{
                padding-inline: 4px;
            }}

            .history-item {{
                grid-template-columns: 1fr;
                gap: 18px;
                padding: 22px 4px;
            }}

            .history-rank {{
                justify-content: flex-start;
            }}

            .history-actions {{
                grid-column: auto;
            }}
        }}

        @media (max-width: 540px) {{
            .hero h1 {{
                font-size: clamp(2.7rem, 15vw, 4rem);
            }}

            .archive-head h2 {{
                font-size: clamp(1.8rem, 10vw, 2.6rem);
            }}

            .hero-actions {{
                flex-direction: column;
            }}

            .primary-link,
            .secondary-link,
            .history-link {{
                width: 100%;
            }}
        }}

        @media (prefers-reduced-motion: reduce) {{
            html {{
                scroll-behavior: auto;
            }}

            *,
            *::before,
            *::after {{
                animation: none !important;
                transition: none !important;
            }}

            .hero,
            .hero-panel,
            .archive-head,
            .history-item,
            .empty-state {{
                opacity: 1 !important;
                transform: none !important;
            }}
        }}
    </style>
</head>
<body>
    <main class="page-shell">
        <section class="hero reveal-item">
            <div class="hero-copy">
                <span class="eyebrow">History Archive</span>
                <h1>历史榜单档案</h1>
                <p class="hero-lead">把每天生成的 GitHub Trending 页面收进一个可回看的时间仓库，方便你按日期复盘当时的开源热点。</p>
                <div class="hero-actions">
                    <a href="../" class="primary-link">返回最新榜单</a>
                    <a href="#archive-list" class="secondary-link">浏览全部记录</a>
                </div>
                <div class="metrics-grid">
                    <div class="metric-card">
                        <span class="metric-number">{total_days}</span>
                        <span class="metric-label">已归档天数</span>
                    </div>
                    <div class="metric-card">
                        <span class="metric-number">{escape(latest_text)}</span>
                        <span class="metric-label">最新记录日期</span>
                    </div>
                    <div class="metric-card">
                        <span class="metric-number">{escape(data_integrity)}</span>
                        <span class="metric-label">数据完整率 {escape(integrity_detail)}</span>
                    </div>
                    <div class="metric-card">
                        <span class="metric-number">{streak_days}</span>
                        <span class="metric-label">从最新记录起连续归档天数</span>
                    </div>
                </div>
                <p class="hero-note">最早记录：{escape(earliest_text)} · 所有历史页均保存在 gh-pages 分支的 history 目录中。</p>
            </div>

            <aside class="hero-panel reveal-item">
                <span class="panel-label">Archive Notes</span>
                <h2 class="panel-title">按日期回看热度变化</h2>
                <p class="panel-copy">历史页适合做三件事：回看某天的热门项目、观察一段时间的热词漂移、验证某个项目何时真正开始升温。</p>
                <ul class="panel-list">
                    <li>每条记录都可以直达当日完整页面</li>
                    <li>页面会标记档案是否完整，方便排查缺失文件</li>
                    <li>视觉风格已与首页统一，切换浏览更自然</li>
                </ul>
            </aside>
        </section>

        <section class="archive-shell" id="archive-list">
            <div class="archive-head reveal-item">
                <div>
                    <span class="eyebrow">Daily Snapshots</span>
                    <h2>按时间顺序浏览</h2>
                    <p>这里按日期倒序展示所有历史快照。你可以快速定位最新记录，也可以往前追溯某个技术方向刚开始爆发的时间点。</p>
                </div>
                <div class="archive-side">
                    <span class="archive-count">{total_days}</span>
                    <span class="archive-note">ARCHIVED DAYS</span>
                </div>
            </div>

            <div class="archive-list">
                {archive_html}
            </div>
        </section>
    </main>

    <script>
        document.addEventListener('DOMContentLoaded', function () {{
            const observer = new IntersectionObserver((entries) => {{
                entries.forEach((entry) => {{
                    if (entry.isIntersecting) {{
                        entry.target.classList.add('in-view');
                    }}
                }});
            }}, {{
                threshold: 0.12,
                rootMargin: '0px 0px -10% 0px'
            }});

            document.querySelectorAll('.reveal-item').forEach((item) => {{
                observer.observe(item);
            }});
        }});
    </script>
</body>
</html>"""


def generate_history_stats():
    """生成历史统计页面"""
    history_dirs = list_history_dirs()
    total_days = len(history_dirs)
    latest_date = history_dirs[0] if history_dirs else ""
    earliest_date = history_dirs[-1] if history_dirs else ""

    if history_dirs:
        earliest_dt = datetime.strptime(earliest_date, DATE_FORMAT)
        current_dt = datetime.now()
        expected_days = (current_dt - earliest_dt).days + 1
        complete_records = sum(1 for item in history_dirs if is_complete_record(item))
        data_integrity = f"{(complete_records / expected_days * 100):.1f}%"
        integrity_detail = f"{complete_records}/{expected_days} 天"
    else:
        data_integrity = "100%"
        integrity_detail = "0/0 天"

    streak_days = compute_streak(history_dirs)
    history_items_html = build_history_items(history_dirs, latest_date)
    html_content = build_history_html(
        total_days=total_days,
        latest_date=latest_date,
        earliest_date=earliest_date,
        data_integrity=data_integrity,
        integrity_detail=integrity_detail,
        streak_days=streak_days,
        history_items_html=history_items_html,
    )

    os.makedirs("history", exist_ok=True)
    with open("history/index.html", "w", encoding="utf-8") as file:
        file.write(html_content)

    print("历史统计页面已生成")
    print("统计信息:")
    print(f"   - 总记录天数: {total_days}")
    print(f"   - 最新日期: {latest_date or '无数据'}")
    print(f"   - 最早日期: {earliest_date or '无数据'}")
    print(f"   - 数据完整性: {data_integrity} ({integrity_detail})")
    print(f"   - 连续归档天数: {streak_days}")


if __name__ == "__main__":
    generate_history_stats()
