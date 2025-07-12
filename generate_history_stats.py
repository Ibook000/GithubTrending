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
        metadata = {}
        if os.path.exists(metadata_path):
            try:
                with open(metadata_path, 'r', encoding='utf-8') as f:
                    metadata = json.load(f)
            except:
                pass
        
        # 格式化日期显示
        try:
            date_obj = datetime.strptime(date_dir, '%Y-%m-%d')
            formatted_date = date_obj.strftime('%Y年%m月%d日')
            weekday = ['周一', '周二', '周三', '周四', '周五', '周六', '周日'][date_obj.weekday()]
        except:
            formatted_date = date_dir
            weekday = ""
        
        # 获取项目统计
        daily_count = metadata.get('daily_count', 0)
        weekly_count = metadata.get('weekly_count', 0)
        monthly_count = metadata.get('monthly_count', 0)
        ai_success_rate = metadata.get('ai_success_rate', 0)
        
        # 检查文件完整性
        status_icon = "✅" if complete_records > 0 else "⚠️"
        
        history_items_html += f"""
        <div class="history-item">
            <div class="date-info">
                <div class="date-main">{formatted_date}</div>
                <div class="date-sub">{weekday} {status_icon}</div>
            </div>
            <div class="stats-info">
                <div class="stat-item">
                    <span class="stat-label">日榜:</span>
                    <span class="stat-value">{daily_count}</span>
                </div>
                <div class="stat-item">
                    <span class="stat-label">周榜:</span>
                    <span class="stat-value">{weekly_count}</span>
                </div>
                <div class="stat-item">
                    <span class="stat-label">月榜:</span>
                    <span class="stat-value">{monthly_count}</span>
                </div>
                <div class="stat-item">
                    <span class="stat-label">AI成功率:</span>
                    <span class="stat-value">{ai_success_rate:.1f}%</span>
                </div>
            </div>
            <div class="action-buttons">
                <a href="history/{date_dir}/index.html" class="btn-view" target="_blank">查看详情</a>
            </div>
        </div>
        """
    
    # 生成完整的HTML页面
    html_content = f"""<!DOCTYPE html>
<html lang="zh-cn">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>GitHub趋势历史统计</title>
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: 'Segoe UI', 'SF Pro Display', -apple-system, BlinkMacSystemFont, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            color: #333;
            line-height: 1.6;
        }}
        
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
        }}
        
        .header {{
            text-align: center;
            margin-bottom: 40px;
            color: white;
        }}
        
        .header h1 {{
            font-size: 2.5rem;
            margin-bottom: 10px;
            text-shadow: 0 2px 4px rgba(0,0,0,0.3);
        }}
        
        .header .subtitle {{
            font-size: 1.1rem;
            opacity: 0.9;
        }}
        
        .stats-overview {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 40px;
        }}
        
        .stat-card {{
            background: rgba(255, 255, 255, 0.95);
            border-radius: 12px;
            padding: 20px;
            text-align: center;
            box-shadow: 0 4px 20px rgba(0,0,0,0.1);
            backdrop-filter: blur(10px);
        }}
        
        .stat-card .number {{
            font-size: 2rem;
            font-weight: bold;
            color: #667eea;
            margin-bottom: 5px;
        }}
        
        .stat-card .label {{
            color: #666;
            font-size: 0.9rem;
        }}
        
        .history-list {{
            background: rgba(255, 255, 255, 0.95);
            border-radius: 12px;
            padding: 20px;
            box-shadow: 0 4px 20px rgba(0,0,0,0.1);
            backdrop-filter: blur(10px);
        }}
        
        .history-item {{
            display: grid;
            grid-template-columns: 200px 1fr auto;
            gap: 20px;
            align-items: center;
            padding: 15px;
            border-bottom: 1px solid #eee;
            transition: all 0.3s ease;
        }}
        
        .history-item:hover {{
            background: rgba(102, 126, 234, 0.05);
            border-radius: 8px;
        }}
        
        .history-item:last-child {{
            border-bottom: none;
        }}
        
        .date-info .date-main {{
            font-weight: bold;
            font-size: 1.1rem;
            color: #333;
        }}
        
        .date-info .date-sub {{
            color: #666;
            font-size: 0.9rem;
        }}
        
        .stats-info {{
            display: flex;
            gap: 20px;
            flex-wrap: wrap;
        }}
        
        .stat-item {{
            display: flex;
            flex-direction: column;
            align-items: center;
            min-width: 60px;
        }}
        
        .stat-label {{
            font-size: 0.8rem;
            color: #666;
            margin-bottom: 2px;
        }}
        
        .stat-value {{
            font-weight: bold;
            color: #667eea;
        }}
        
        .btn-view {{
            background: linear-gradient(45deg, #667eea, #764ba2);
            color: white;
            padding: 8px 16px;
            border-radius: 6px;
            text-decoration: none;
            font-size: 0.9rem;
            transition: all 0.3s ease;
        }}
        
        .btn-view:hover {{
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(102, 126, 234, 0.3);
        }}
        
        .back-button {{
            position: fixed;
            top: 20px;
            left: 20px;
            background: rgba(255, 255, 255, 0.9);
            color: #667eea;
            padding: 10px 15px;
            border-radius: 8px;
            text-decoration: none;
            font-weight: bold;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            transition: all 0.3s ease;
        }}
        
        .back-button:hover {{
            background: white;
            transform: translateY(-2px);
        }}
        
        @media (max-width: 768px) {{
            .history-item {{
                grid-template-columns: 1fr;
                gap: 10px;
                text-align: center;
            }}
            
            .stats-info {{
                justify-content: center;
            }}
            
            .header h1 {{
                font-size: 2rem;
            }}
        }}
    </style>
</head>
<body>
    <a href="index.html" class="back-button">
        <i class="fas fa-arrow-left"></i> 返回主页
    </a>
    
    <div class="container">
        <div class="header">
            <h1><i class="fas fa-chart-line"></i> GitHub趋势历史统计</h1>
            <p class="subtitle">追踪开源项目的发展轨迹</p>
        </div>
        
        <div class="stats-overview">
            <div class="stat-card">
                <div class="number">{total_days}</div>
                <div class="label">记录天数</div>
            </div>
            <div class="stat-card">
                <div class="number">{latest_date}</div>
                <div class="label">最新记录</div>
            </div>
            <div class="stat-card">
                <div class="number">{data_integrity}</div>
                <div class="label">数据完整性</div>
            </div>
            <div class="stat-card">
                <div class="number">{complete_records}</div>
                <div class="label">完整记录</div>
            </div>
        </div>
        
        <div class="history-list">
            <h2 style="margin-bottom: 20px; color: #333;">
                <i class="fas fa-history"></i> 历史记录
            </h2>
            {history_items_html if history_items_html else '<p style="text-align: center; color: #666; padding: 40px;">暂无历史记录</p>'}
        </div>
    </div>
</body>
</html>"""
    
    # 写入文件
    output_path = os.path.join('history', 'index.html')
    os.makedirs('history', exist_ok=True)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    print(f"✅ 历史统计页面已生成: {output_path}")
    print(f"📊 统计信息:")
    print(f"   - 总记录天数: {total_days}")
    print(f"   - 最新记录: {latest_date}")
    print(f"   - 数据完整性: {data_integrity}")
    print(f"   - 完整记录数: {complete_records}")

if __name__ == "__main__":
    generate_history_stats()