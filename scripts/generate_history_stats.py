#!/usr/bin/env python3
"""根据 history/YYYY-MM-DD 目录生成历史档案首页。"""

from __future__ import annotations

import json
from datetime import datetime, timedelta
from html import escape
from pathlib import Path

HISTORY_DIR = Path("history")
DATE_FORMAT = "%Y-%m-%d"


def history_dates() -> list[str]:
    if not HISTORY_DIR.exists():
        return []
    dates = []
    for path in HISTORY_DIR.iterdir():
        if not path.is_dir():
            continue
        try:
            datetime.strptime(path.name, DATE_FORMAT)
        except ValueError:
            continue
        dates.append(path.name)
    return sorted(dates, reverse=True)


def record_info(day: str) -> dict[str, str | bool]:
    directory = HISTORY_DIR / day
    metadata = {}
    try:
        metadata = json.loads((directory / "metadata.json").read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        pass
    has_data = (directory / "data.json").exists()
    complete = (directory / "index.html").exists() and (directory / "metadata.json").exists()
    return {
        "day": day,
        "generated_at": str(metadata.get("generated_at") or "未知时间"),
        "complete": complete,
        "has_data": has_data,
    }


def streak(dates: list[str]) -> int:
    if not dates:
        return 0
    values = {datetime.strptime(value, DATE_FORMAT).date() for value in dates}
    cursor = max(values)
    count = 0
    while cursor in values:
        count += 1
        cursor -= timedelta(days=1)
    return count


def render(dates: list[str]) -> str:
    records = [record_info(day) for day in dates]
    rows = []
    for record in records:
        status = "完整快照" if record["complete"] else "历史兼容记录"
        data_link = (
            f'<a href="{record["day"]}/data.json">JSON</a>' if record["has_data"] else ""
        )
        rows.append(
            f'''<article class="archive-item">
              <div><time datetime="{record['day']}">{escape(str(record['day']))}</time>
              <p>{escape(status)} · {escape(str(record['generated_at']))}</p></div>
              <div class="archive-actions">{data_link}<a href="{record['day']}/">查看榜单 ↗</a></div>
            </article>'''
        )
    archive = "\n".join(rows) or '<div class="empty-state"><strong>暂无历史记录</strong><p>首次自动运行后会在这里生成每日快照。</p></div>'
    latest = dates[0] if dates else "暂无"
    return f'''<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>历史档案 · GitHub 趋势雷达</title><meta name="description" content="浏览 GitHub 趋势雷达的每日历史快照。">
<link rel="icon" href="../favicon.svg" type="image/svg+xml"><link rel="stylesheet" href="../styles.css">
<style>
.archive-hero{{padding:90px 0 55px;border-bottom:1px solid var(--border)}}.archive-hero h1{{font-size:clamp(44px,7vw,78px)}}
.archive-stats{{display:flex;gap:40px;color:var(--muted)}}.archive-stats strong{{display:block;color:var(--text);font-size:28px}}
.archive-list{{display:grid;gap:10px;padding:55px 0 90px}}.archive-item{{display:flex;align-items:center;justify-content:space-between;gap:30px;padding:24px 26px;background:var(--surface);border:1px solid var(--border);border-radius:14px}}
.archive-item time{{font-size:24px;font-weight:750;letter-spacing:-.03em}}.archive-item p{{margin:2px 0 0;color:var(--muted);font-size:13px}}.archive-actions{{display:flex;gap:18px;color:var(--accent);font-weight:650}}
@media(max-width:600px){{.archive-item{{align-items:flex-start;flex-direction:column}}.archive-stats{{display:grid;grid-template-columns:1fr 1fr}}}}
</style></head><body>
<header class="site-header"><a class="brand" href="../"><span class="brand-mark">⌁</span><span>GitHub 趋势雷达</span></a><nav class="header-nav"><a href="../">今日榜单</a><a href="../data/latest.json">数据</a><a href="../feed.xml">RSS</a></nav></header>
<main><section class="archive-hero"><p class="overline">DAILY ARCHIVE</p><h1>历史档案</h1><p class="hero-description">回看每天的热门仓库，观察技术主题如何出现、升温与沉淀。</p>
<div class="archive-stats"><div><strong>{len(dates)}</strong>归档天数</div><div><strong>{streak(dates)}</strong>连续更新</div><div><strong>{latest}</strong>最新快照</div></div></section>
<section class="archive-list">{archive}</section></main>
<footer class="site-footer"><p>GitHub 趋势雷达历史档案</p><p><a href="../">返回今日榜单</a></p></footer></body></html>'''


def generate_history_stats() -> None:
    HISTORY_DIR.mkdir(exist_ok=True)
    dates = history_dates()
    (HISTORY_DIR / "index.html").write_text(render(dates), encoding="utf-8")
    print(f"历史档案已生成，共 {len(dates)} 条记录")


if __name__ == "__main__":
    generate_history_stats()
