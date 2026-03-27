import requests
from bs4 import BeautifulSoup
from datetime import datetime
from html import escape
import os
import concurrent.futures

# openai库导入
try:
    from openai import OpenAI
except ImportError:
    OpenAI = None

# 获取GitHub Trending前10仓库数据

def fetch_github_trending(since='daily'):
    # since: 'daily', 'weekly', 'monthly'
    url = f'https://github.com/trending?since={since}'
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'}

    try:
        print(f'🌐 正在访问: {url}')
        response = requests.get(url, headers=headers, timeout=30)
        print(f'📡 响应状态码: {response.status_code}')
        response.raise_for_status()

        soup = BeautifulSoup(response.text, 'html.parser')
        print(f'📄 页面解析成功，内容长度: {len(response.text)} 字符')
    except requests.exceptions.Timeout:
        print(f'⏰ 获取 {since} 榜单超时（30秒）')
        return []
    except requests.exceptions.ConnectionError:
        print(f'🔌 网络连接错误，无法访问GitHub')
        return []
    except requests.exceptions.HTTPError as e:
        print(f'🚫 HTTP错误: {e}')
        return []
    except Exception as e:
        print(f'❌ 获取 {since} 榜单失败: {e}')
        return []
    repo_list = []
    for repo in soup.find_all('article', class_='Box-row')[:10]:
        title = repo.h2.a.get_text(strip=True).replace('\n', '').replace(' ', '')
        repo_url = 'https://github.com' + repo.h2.a['href']
        description = repo.p.get_text(strip=True) if repo.p else '无描述'
        lang_tag = repo.find('span', itemprop='programmingLanguage')
        language = lang_tag.get_text(strip=True) if lang_tag else '未知'
        stars = repo.find('a', href=lambda x: x and x.endswith('/stargazers'))
        stars = stars.get_text(strip=True) if stars else '0'
        forks = repo.find('a', href=lambda x: x and x.endswith('/network/members'))
        forks = forks.get_text(strip=True) if forks else '0'
        author = repo.h2.a['href'].split('/')[1]
        repo_list.append({
            'title': title,
            'url': repo_url,
            'description': description,
            'language': language,
            'stars': stars,
            'forks': forks,
            'author': author,
            'summary': ''  # 预留AI总结
        })
    return repo_list

# 调用OpenRouter大模型生成总结
def ai_summarize_projects(repos, api_key):
    if OpenAI is None:
        print('❌ 未安装openai库，无法生成AI总结。')
        return repos

    print('🔌 正在连接 OpenRouter 兼容 API...')
    print('🔑 已检测到 API 密钥，开始生成 AI 总结')

    # 检测是否在GitHub Actions环境中
    is_github_actions = os.environ.get('GITHUB_ACTIONS') == 'true'
    if is_github_actions:
        print('🏃 检测到GitHub Actions环境，使用增强的网络配置')

    try:
        # 为GitHub Actions环境配置更长的超时时间和重试机制
        timeout_duration = 120 if is_github_actions else 60
        client = OpenAI(
            base_url="https://api.siliconflow.cn/v1",
            api_key=api_key,
            timeout=timeout_duration
        )
        print(f'✅ OpenRouter客户端创建成功 (超时: {timeout_duration}秒)')
    except Exception as e:
        print(f'❌ 创建OpenRouter客户端失败: {e}')
        return repos

    success_count = 0
    max_retries = 3 if is_github_actions else 2
    
    def process_repo(repo):
        nonlocal success_count
        print(f'🤖 正在处理项目: {repo["title"]}')
        prompt = f'请用一句中文总结这个GitHub项目的核心用途和亮点不要有其他符号：\n项目名称：{repo["title"]}\n简介：{repo["description"]}'

        retry_count = 0
        while retry_count < max_retries:
            try:
                # 为GitHub Actions环境使用更保守的超时设置
                request_timeout = 90 if is_github_actions else 60
                completion = client.chat.completions.create(
                    model="deepseek-ai/DeepSeek-R1-0528-Qwen3-8B",
                    messages=[
                        {"role": "user", "content": prompt}
                    ],
                    timeout=request_timeout
                )
                summary = completion.choices[0].message.content.strip()
                repo['summary'] = summary
                success_count += 1
                print(f'✅ AI总结成功: {repo["title"]} - {summary[:50]}...')
                return repo
            except Exception as e:
                retry_count += 1
                error_type = type(e).__name__
                print(f"❌ AI总结失败 (尝试 {retry_count}/{max_retries}): {repo['title']} - {error_type}: {str(e)}")

                if retry_count < max_retries:
                    # 根据环境调整等待时间
                    wait_time = 10 if is_github_actions else 5
                    print(f'⏳ 等待{wait_time}秒后重试...')
                    import time
                    time.sleep(wait_time)
                else:
                    # 所有重试都失败，使用备用总结
                    repo['summary'] = f"一个{repo.get('language', '未知语言')}项目：{repo['description'][:30]}..."
                    print(f'🔄 使用备用总结: {repo["title"]} - {repo["summary"]}')
                    return repo
    
    # 使用并行处理
    with concurrent.futures.ThreadPoolExecutor(max_workers=min(5, len(repos))) as executor:
        repos = list(executor.map(process_repo, repos))

    print(f'📊 AI总结统计: 成功 {success_count}/{len(repos)} 个项目')
    
    # 如果在GitHub Actions中且成功率很低，给出建议
    if is_github_actions and success_count < len(repos) * 0.3:
        print('⚠️ GitHub Actions环境中AI总结成功率较低，建议检查网络连接或API配置')
        print('🔄 为失败的项目生成智能备用总结...')
        
        # 为没有成功总结的项目生成更智能的备用总结
        for repo in repos:
            if repo.get('summary') == 'AI总结生成失败' or not repo.get('summary'):
                repo['summary'] = generate_fallback_summary(repo)
    
    return repos

def generate_fallback_summary(repo):
    """生成智能的备用总结"""
    title = repo.get('title', '').lower()
    description = repo.get('description', '').lower()
    language = repo.get('language', '未知')
    
    # 基于项目名称和描述的关键词匹配
    if any(keyword in title or keyword in description for keyword in ['api', 'rest', 'graphql']):
        return f"一个基于{language}的API开发框架或工具"
    elif any(keyword in title or keyword in description for keyword in ['web', 'frontend', 'react', 'vue', 'angular']):
        return f"一个{language}前端Web开发项目"
    elif any(keyword in title or keyword in description for keyword in ['backend', 'server', 'database']):
        return f"一个{language}后端服务或数据库相关项目"
    elif any(keyword in title or keyword in description for keyword in ['cli', 'command', 'tool']):
        return f"一个{language}命令行工具或实用程序"
    elif any(keyword in title or keyword in description for keyword in ['ai', 'ml', 'machine learning', 'neural']):
        return f"一个{language}人工智能或机器学习项目"
    elif any(keyword in title or keyword in description for keyword in ['game', 'engine']):
        return f"一个{language}游戏开发相关项目"
    elif any(keyword in title or keyword in description for keyword in ['mobile', 'android', 'ios']):
        return f"一个{language}移动应用开发项目"
    else:
        # 通用总结
        desc_preview = repo.get('description', '')[:40]
        return f"一个使用{language}开发的开源项目：{desc_preview}..."
# 生成HTML卡片页面


def generate_html(all_repos):
    today = datetime.now().strftime('%Y-%m-%d')
    active_period = 'daily'
    period_titles = {
        'daily': '日榜',
        'weekly': '周榜',
        'monthly': '月榜'
    }
    period_descriptions = {
        'daily': '追踪今天刚刚升温的项目，适合快速发现新热点。',
        'weekly': '观察一周内持续发酵的仓库，更容易看出真正被社区验证的方向。',
        'monthly': '筛选月度长坡厚雪型项目，适合判断长期关注价值。'
    }
    period_accents = {
        'daily': 'TODAY SIGNAL',
        'weekly': 'WEEKLY MOMENTUM',
        'monthly': 'MONTHLY ARC'
    }

    total_repos = sum(len(repos) for repos in all_repos.values())
    featured_repo = all_repos.get('daily', [{}])[0] if all_repos.get('daily') else {}

    def safe_text(value, default=''):
        if value is None:
            value = default
        text = str(value).strip()
        if not text:
            text = default
        return escape(text, quote=True)

    def summary_text(repo):
        summary = str(repo.get('summary', '') or '').strip()
        if not summary:
            return '暂未生成 AI 总结，先通过原始描述和数据判断是否值得深入。'
        return summary

    def build_meta_pills(repo):
        return f'''
                    <span class="meta-pill"><i class="fa-solid fa-star"></i>{safe_text(repo.get("stars"), "0")}</span>
                    <span class="meta-pill"><i class="fa-solid fa-code-fork"></i>{safe_text(repo.get("forks"), "0")}</span>
                    <span class="meta-pill"><i class="fa-solid fa-code"></i>{safe_text(repo.get("language"), "未知")}</span>
        '''

    def build_repo_entry(repo, rank, period_key):
        title = safe_text(repo.get('title'), '未知仓库')
        url = safe_text(repo.get('url'), '#')
        description = safe_text(repo.get('description'), '暂无项目描述')
        summary = safe_text(summary_text(repo))
        author = safe_text(repo.get('author'), '未知作者')

        return f'''
                <article class="repo-entry reveal-item" style="--entry-delay:{rank * 60}ms;">
                    <div class="repo-rank">{rank:02d}</div>
                    <div class="repo-main">
                        <div class="repo-heading">
                            <span class="repo-kicker">{safe_text(period_titles[period_key])}</span>
                            <h3 class="repo-title"><a href="{url}" target="_blank" rel="noopener noreferrer">{title}</a></h3>
                        </div>
                        <p class="repo-desc">{description}</p>
                        <div class="repo-summary">
                            <span class="summary-label">AI 一句话</span>
                            <p>{summary}</p>
                        </div>
                    </div>
                    <div class="repo-side">
                        <div class="repo-meta">
{build_meta_pills(repo)}
                        </div>
                        <div class="author-line">
                            <i class="fa-regular fa-user"></i>
                            <span>作者 {author}</span>
                        </div>
                        <a class="btn" href="{url}" target="_blank" rel="noopener noreferrer">查看仓库</a>
                    </div>
                </article>
        '''

    def build_repo_section(period_key, repos):
        hidden_attr = '' if period_key == active_period else ' hidden'
        active_class = ' active' if period_key == active_period else ''
        if repos:
            entries_html = ''.join(
                build_repo_entry(repo, rank, period_key)
                for rank, repo in enumerate(repos, start=1)
            )
        else:
            entries_html = '''
                <div class="empty-state reveal-item">
                    <p>这一档榜单暂时没有抓取到数据，请稍后再试。</p>
                </div>
            '''

        return f'''
            <section id="{period_key}" class="tab-content{active_class}" role="tabpanel" aria-labelledby="tab-{period_key}"{hidden_attr}>
                <div class="section-head reveal-item">
                    <div class="section-copy">
                        <span class="eyebrow">{safe_text(period_accents[period_key])}</span>
                        <h2>{safe_text(period_titles[period_key])}</h2>
                        <p>{safe_text(period_descriptions[period_key])}</p>
                    </div>
                    <div class="section-meta">
                        <span class="section-count">{len(repos):02d}</span>
                        <span class="section-note">Top {len(repos)} repositories</span>
                    </div>
                </div>
                <div class="repo-list">
{entries_html}
                </div>
            </section>
        '''

    featured_title = safe_text(featured_repo.get('title'), '今日榜单即将更新')
    featured_url = safe_text(featured_repo.get('url'), '#')
    featured_description = safe_text(
        featured_repo.get('description'),
        'GitHub Trending 的最新热门项目会展示在这里。'
    )
    featured_summary = safe_text(summary_text(featured_repo))
    featured_author = safe_text(featured_repo.get('author'), 'GitHub')
    featured_stars = safe_text(featured_repo.get('stars'), '0')
    featured_language = safe_text(featured_repo.get('language'), '未知')

    repo_sections = ''.join(
        build_repo_section(period_key, all_repos.get(period_key, []))
        for period_key in ['daily', 'weekly', 'monthly']
    )

    html = f'''<!DOCTYPE html>
<html lang="zh-cn">
<head>
    <meta charset="UTF-8">
    <title>GitHub 趋势榜单（{today}）</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Noto+Sans+SC:wght@400;500;700;800&family=Space+Grotesk:wght@400;500;700&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="github_trending_cards.css">
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
</head>
<body data-theme="light">
    <div class="theme-toggle-container">
        <button class="theme-toggle" onclick="toggleTheme()" aria-label="切换主题">
            <i class="fas fa-sun sun-icon"></i>
            <i class="fas fa-moon moon-icon"></i>
        </button>
    </div>

    <main class="page-shell">
        <section class="hero reveal-item">
            <div class="hero-copy">
                <div class="hero-topline">
                    <span class="eyebrow">OPEN SOURCE RADAR</span>
                    <span class="date-badge">{today}</span>
                </div>
                <h1>GitHub 趋势榜单</h1>
                <p class="hero-lead">把 GitHub Trending 做成一张更好扫读的中文技术榜单，帮助你在几分钟内判断哪些项目值得点开。</p>
                <div class="hero-actions">
                    <a href="#repo-sections" class="primary-link">开始浏览</a>
                    <a href="history/" class="history-btn">查看历史记录</a>
                </div>
                <div class="hero-strip">
                    <div class="hero-stat">
                        <strong>3</strong>
                        <span>日 / 周 / 月榜</span>
                    </div>
                    <div class="hero-stat">
                        <strong>{total_repos:02d}</strong>
                        <span>本次收录项目</span>
                    </div>
                    <div class="hero-stat">
                        <strong>AI</strong>
                        <span>一句话辅助筛选</span>
                    </div>
                </div>
                <p class="hero-caption">自动抓取 GitHub Trending Top 10，结合作者、语言、Star 与 AI 摘要快速建立第一判断。</p>
            </div>

            <aside class="hero-spotlight reveal-item">
                <span class="spotlight-label">DAILY HIGHLIGHT</span>
                <h2><a href="{featured_url}" target="_blank" rel="noopener noreferrer">{featured_title}</a></h2>
                <p class="spotlight-desc">{featured_description}</p>
                <div class="spotlight-meta">
                    <span><i class="fa-solid fa-star"></i>{featured_stars}</span>
                    <span><i class="fa-solid fa-code"></i>{featured_language}</span>
                    <span><i class="fa-regular fa-user"></i>{featured_author}</span>
                </div>
                <div class="spotlight-summary">
                    <span>AI 一句话</span>
                    <p>{featured_summary}</p>
                </div>
            </aside>
        </section>

        <section class="tabs-shell reveal-item" id="repo-sections">
            <div class="section-intro">
                <span class="eyebrow">TREND WINDOWS</span>
                <h2>按时间尺度切换热度</h2>
                <p>日榜看刚起势的项目，周榜看持续发酵的方向，月榜更适合判断长期关注价值。</p>
            </div>
            <div class="tab-navigation" role="tablist" aria-label="趋势榜单切换">
                <button id="tab-daily" class="tab-btn active" onclick="showTab('daily')" data-tab="daily" role="tab" aria-selected="true" aria-controls="daily">
                    <span class="tab-label">日榜</span>
                    <span class="tab-sub">Today</span>
                </button>
                <button id="tab-weekly" class="tab-btn" onclick="showTab('weekly')" data-tab="weekly" role="tab" aria-selected="false" aria-controls="weekly">
                    <span class="tab-label">周榜</span>
                    <span class="tab-sub">Week</span>
                </button>
                <button id="tab-monthly" class="tab-btn" onclick="showTab('monthly')" data-tab="monthly" role="tab" aria-selected="false" aria-controls="monthly">
                    <span class="tab-label">月榜</span>
                    <span class="tab-sub">Month</span>
                </button>
            </div>
        </section>

        <div class="repo-sections">
{repo_sections}
        </div>

        <footer class="page-footer">
            <p>数据来源 GitHub Trending · 支持日榜、周榜、月榜 · 历史页面保存在 gh-pages 分支</p>
            <p>页面生成时间 {today}</p>
        </footer>
    </main>

    <script>
    function applyTheme(theme) {{
        document.body.setAttribute('data-theme', theme);
        localStorage.setItem('theme', theme);
    }}

    function toggleTheme() {{
        const currentTheme = document.body.getAttribute('data-theme');
        const nextTheme = currentTheme === 'light' ? 'dark' : 'light';
        applyTheme(nextTheme);
    }}

    function showTab(tab) {{
        const sections = document.querySelectorAll('.tab-content');
        const buttons = document.querySelectorAll('.tab-btn');

        sections.forEach(section => {{
            const active = section.id === tab;
            section.hidden = !active;
            section.classList.toggle('active', active);
        }});

        buttons.forEach(button => {{
            const active = button.dataset.tab === tab;
            button.classList.toggle('active', active);
            button.setAttribute('aria-selected', active ? 'true' : 'false');
        }});
    }}

    document.addEventListener('DOMContentLoaded', function() {{
        applyTheme(localStorage.getItem('theme') || 'light');
        showTab('{active_period}');

        const observer = new IntersectionObserver((entries) => {{
            entries.forEach(entry => {{
                if (entry.isIntersecting) {{
                    entry.target.classList.add('in-view');
                }}
            }});
        }}, {{
            threshold: 0.12,
            rootMargin: '0px 0px -10% 0px'
        }});

        document.querySelectorAll('.reveal-item').forEach(item => {{
            observer.observe(item);
        }});
    }});
    </script>
</body>
</html>'''
    with open('github_trending_cards.html', 'w', encoding='utf-8') as f:
        f.write(html)
    print('已生成 github_trending_cards.html，使用浏览器打开即可查看。')

def create_metadata_file():
    """创建元数据文件，记录生成时间和相关信息"""
    import json
    from datetime import datetime, timezone, timedelta
    
    try:
        # 获取当前北京时间
        beijing_tz = timezone(timedelta(hours=8))
        current_time = datetime.now(beijing_tz)
        
        # 创建元数据
        metadata = {
            "date": current_time.strftime('%Y-%m-%d'),
            "generated_at": current_time.isoformat(),
            "source": "GitHub Trending Scraper",
            "version": "1.0"
        }
        
        # 写入metadata.json文件
        with open('metadata.json', 'w', encoding='utf-8') as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)
            
        print(f"✅ 元数据文件已创建: {current_time.strftime('%Y-%m-%d %H:%M:%S')} (北京时间)")
        
    except Exception as e:
        print(f"⚠️ 创建元数据文件失败: {e}")


if __name__ == '__main__':
    print('🚀 开始生成GitHub趋势榜单...')

    # 从环境变量获取API密钥
    api_key = os.environ.get('OPENROUTER_API_KEY')
    if api_key:
        print(f'✅ 检测到API密钥: {api_key[:10]}...')
    else:
        print('⚠️ 未检测到OPENROUTER_API_KEY，将不生成AI总结。')

    all_repos = {'daily': [], 'weekly': [], 'monthly': []}
    # 依次获取三个榜单的数据，避免重复请求
    for since in ['daily', 'weekly', 'monthly']:
        print(f'\n📊 开始获取 {since} 榜单...')
        repos = fetch_github_trending(since)
        print(f'📝 获取到 {len(repos)} 个项目')

        if api_key and repos:
            print('🤖 开始生成AI总结...')
            repos = ai_summarize_projects(repos, api_key)
            print('✅ AI总结生成完成')

            # 检查是否有成功的AI总结，如果都失败了则使用备用方案
            successful_summaries = sum(1 for repo in repos if repo.get('summary') and repo['summary'] != 'AI总结生成失败')
            if successful_summaries == 0:
                print('⚠️ 所有AI总结都失败，使用备用总结方案...')
                for repo in repos:
                    # 生成简单的备用总结
                    lang = repo.get('language', '未知')
                    desc = repo.get('description', '无描述')[:50]
                    repo['summary'] = f"一个使用{lang}开发的项目：{desc}..."
                print(f'✅ 已为 {len(repos)} 个项目生成备用总结')
        elif not repos:
            print('⚠️ 未获取到项目数据，跳过AI总结')

        all_repos[since] = repos

    print('\n🎨 开始生成HTML页面...')
    generate_html(all_repos)
    
    # 创建元数据文件，记录生成时间
    create_metadata_file()
    
    print('🎉 GitHub趋势榜单生成完成！')
