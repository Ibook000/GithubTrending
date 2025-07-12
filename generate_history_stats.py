#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
生成历史统计页面
扫描history目录，生成包含所有历史记录的统计页面
"""

import os
import json
from datetime import datetime, timedelta
import glob

def generate_history_stats():
    """生成历史统计页面"""
    
    # 扫描历史目录
    history_dirs = []
    if os.path.exists('history'):
        for item in os.listdir('history'):
            item_path = os.path.join('history', item)
            if os.path.isdir(item_path) and item != 'index.html':
                # 验证是否为日期格式的目录
                try:
                    datetime.strptime(item, '%Y-%m-%d')
                    history_dirs.append(item)
                except ValueError:
                    continue
    
    # 按日期排序（最新的在前）
    history_dirs.sort(reverse=True)
    
    # 生成统计数据
    total_days = len(history_dirs)
    latest_date = history_dirs[0] if history_dirs else "无数据"
    
    # 计算数据完整性（检查文件是否完整）
    complete_records = 0
    for date_dir in history_dirs:
        required_files = ['index.html', 'github_trending_cards.css', 'metadata.json']
        dir_path = os.path.join('history', date_dir)
        if all(os.path.exists(os.path.join(dir_path, f)) for f in required_files):
            complete_records += 1
    
    data_integrity = f"{(complete_records / total_days * 100):.1f}%" if total_days > 0 else "100%"
    
    # 生成历史记录HTML
    history_items_html = ""
    for date_dir in history_dirs:
        # 读取元数据
        metadata_path = os.path.join('history', date_dir, 'metadata.json')
        generated_time = "未知"
        if os.path.exists(metadata_path):
            try:
                with open(metadata_path, 'r', encoding='utf-8') as f:
                    metadata = json.load(f)
                    generated_time = metadata.get('generated_at', '未知')
            except:
                pass
        
        # 格式化日期显示
        try:
            date_obj = datetime.strptime(date_dir, '%Y-%m-%d')
            formatted_date = date_obj.strftime('%Y年%m月%d日')
            weekday = ['周一', '周二', '周三', '周四', '周五', '周六', '周日'][date_obj.weekday()]
            display_date = f"{formatted_date} {weekday}"
        except:
            display_date = date_dir
        
        history_items_html += f'''
        <div class="history-item">
            <div>
                <div class="history-date">{display_date}</div>
                <div class="history-meta">生成时间: {generated_time}</div>
            </div>
            <div>
                <a href="{date_dir}/" class="history-link" target="_blank">
                    <i class="fas fa-external-link-alt"></i> 查看页面
                </a>
            </div>
        </div>'''
    
    # 生成完整的HTML页面
    html_content = f'''<!DOCTYPE html>
<html lang="zh-cn">
<head>
    <meta charset="UTF-8">
    <title>GitHub趋势榜单 - 历史统计</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
    <style>
        * {{ box-sizing: border-box; }}
        body {{
            font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont, sans-serif;
            margin: 0;
            padding: 20px;
            background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
            min-height: 100vh;
            line-height: 1.6;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
        }}
        .header {{
            text-align: center;
            margin-bottom: 40px;
            background: white;
            padding: 30px;
            border-radius: 16px;
            box-shadow: 0 4px 16px rgba(0,0,0,0.1);
        }}
        .header h1 {{
            color: #2563eb;
            margin-bottom: 10px;
            font-size: 2.5rem;
        }}
        .header p {{
            color: #6b7280;
            font-size: 1.1rem;
        }}
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
            margin-bottom: 40px;
        }}
        .stat-card {{
            background: white;
            border-radius: 12px;
            padding: 25px;
            box-shadow: 0 4px 16px rgba(0,0,0,0.1);
            text-align: center;
            transition: transform 0.2s ease;
        }}
        .stat-card:hover {{
            transform: translateY(-4px);
        }}
        .stat-card h3 {{
            color: #374151;
            margin-bottom: 15px;
            font-size: 1.1rem;
        }}
        .stat-number {{
            font-size: 2.5rem;
            font-weight: bold;
            color: #2563eb;
            margin-bottom: 5px;
        }}
        .stat-label {{
            color: #6b7280;
            font-size: 0.9rem;
        }}
        .history-list {{
            background: white;
            border-radius: 12px;
            padding: 25px;
            box-shadow: 0 4px 16px rgba(0,0,0,0.1);
        }}
        .history-list h2 {{
            color: #374151;
            margin-bottom: 20px;
            font-size: 1.5rem;
        }}
        .history-item {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 20px 15px;
            border-bottom: 1px solid #e5e7eb;
            transition: background 0.2s;
        }}
        .history-item:hover {{
            background: #f9fafb;
        }}
        .history-item:last-child {{
            border-bottom: none;
        }}
        .history-date {{
            font-weight: 600;
            color: #374151;
            font-size: 1.1rem;
        }}
        .history-meta {{
            color: #6b7280;
            font-size: 0.9rem;
            margin-top: 4px;
        }}
        .history-link {{
            color: #2563eb;
            text-decoration: none;
            padding: 10px 20px;
            border-radius: 8px;
            border: 2px solid #2563eb;
            transition: all 0.2s;
            font-weight: 600;
        }}
        .history-link:hover {{
            background: #2563eb;
            color: white;
            transform: translateY(-2px);
        }}
        .back-link {{
            display: inline-block;
            margin-bottom: 20px;
            color: #2563eb;
            text-decoration: none;
            font-weight: 600;
        }}
        .back-link:hover {{
            text-decoration: underline;
        }}
        @media (max-width: 768px) {{
            .history-item {{
                flex-direction: column;
                align-items: flex-start;
                gap: 15px;
            }}
            .stats-grid {{
                grid-template-columns: 1fr;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <a href="../" class="back-link">
            <i class="fas fa-arrow-left"></i> 返回最新页面
        </a>
        
        <div class="header">
            <h1><i class="fab fa-github"></i> GitHub趋势榜单历史统计</h1>
            <p>查看每日GitHub热门项目的历史记录和趋势分析</p>
        </div>
        
        <div class="stats-grid">
            <div class="stat-card">
                <h3><i class="fas fa-calendar-alt"></i> 总记录天数</h3>
                <div class="stat-number">{total_days}</div>
                <div class="stat-label">天</div>
            </div>
            <div class="stat-card">
                <h3><i class="fas fa-clock"></i> 最新更新</h3>
                <div class="stat-number" style="font-size: 1.5rem;">{latest_date}</div>
                <div class="stat-label">最后生成日期</div>
            </div>
            <div class="stat-card">
                <h3><i class="fas fa-chart-line"></i> 数据完整性</h3>
                <div class="stat-number">{data_integrity}</div>
                <div class="stat-label">完整记录比例</div>
            </div>
        </div>
        
        <div class="history-list">
            <h2><i class="fas fa-history"></i> 历史记录 ({total_days} 条)</h2>
            {history_items_html if history_items_html else '<p style="text-align: center; color: #6b7280; padding: 40px;">暂无历史记录</p>'}
        </div>
    </div>
</body>
</html>'''
    
    # 确保history目录存在
    os.makedirs('history', exist_ok=True)
    
    # 写入文件
    with open('history/index.html', 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    print(f"✅ 历史统计页面已生成")
    print(f"📊 统计信息:")
    print(f"   - 总记录天数: {total_days}")
    print(f"   - 最新日期: {latest_date}")
    print(f"   - 数据完整性: {data_integrity}")

if __name__ == '__main__':
    generate_history_stats()