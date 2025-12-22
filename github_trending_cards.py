import requests
from bs4 import BeautifulSoup
from datetime import datetime
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

    print(f'🔗 正在连接OpenRouter API...')
    print(f'🔑 API密钥长度: {len(api_key)} 字符')
    print(f'🔑 API密钥前缀: {api_key[:15]}...')
    print(f'🔑 API密钥是否以sk-or-v1开头: {api_key.startswith("sk-or-v1")}')

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
    html = f'''<!DOCTYPE html>
<html lang="zh-cn">
<head>
    <meta charset="UTF-8">
    <title>GitHub 趋势榜单（{today}）</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <link rel="stylesheet" href="github_trending_cards.css">
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
</head>
<body data-theme="light">
    <!-- 主题切换按钮 -->
    <div class="theme-toggle-container">
        <button class="theme-toggle" onclick="toggleTheme()" aria-label="切换主题">
            <i class="fas fa-sun sun-icon"></i>
            <i class="fas fa-moon moon-icon"></i>
        </button>
    </div>

    <!-- 页面标题 -->
    <div class="header-container">
        <h1>
            <i class="fab fa-github"></i>
            GitHub 趋势榜单
            <span class="date-badge">{today}</span>
        </h1>
        <p class="subtitle">发现最热门的开源项目</p>
        
        <!-- 历史记录入口 -->
        <div class="history-entrance">
            <a href="history/" class="history-btn">
                <i class="fas fa-history"></i>
                <span>查看历史记录</span>
            </a>
            <div class="history-tooltip">
                📅 每日历史榜单已保存，点击查看完整记录
            </div>
        </div>
    </div>

    <!-- 标签页导航 -->
    <div class="tab-navigation">
        <button class="tab-btn active" onclick="showTab('daily')" data-tab="daily">
            <i class="fas fa-calendar-day"></i>
            <span>日榜</span>
        </button>
        <button class="tab-btn" onclick="showTab('weekly')" data-tab="weekly">
            <i class="fas fa-calendar-week"></i>
            <span>周榜</span>
        </button>
        <button class="tab-btn" onclick="showTab('monthly')" data-tab="monthly">
            <i class="fas fa-calendar-alt"></i>
            <span>月榜</span>
        </button>
    </div>

    <div id="daily" class="container tab-content">
'''
    for repo in all_repos['daily']:
        html += f'''
        <div class="card">
            <div class="repo-title"><a href="{repo['url']}" target="_blank">{repo['title']}</a></div>
            <div class="desc">{repo['description']}</div>
            <div class="meta">
                <span>🌟 {repo['stars']}</span>
                <span>🍴 {repo['forks']}</span>
                <span>📝 {repo['language']}</span>
            </div>
            <div class="author">作者：{repo['author']}</div>
            <div class="ai-summary"><b>AI总结：</b>{repo.get('summary', '')}</div>
            <a class="btn" href="{repo['url']}" target="_blank">查看仓库</a>
        </div>
'''
    html += '''
    </div>
    <div id="weekly" class="container tab-content" style="display:none;">
'''
    for repo in all_repos['weekly']:
        html += f'''
        <div class="card">
            <div class="repo-title"><a href="{repo['url']}" target="_blank">{repo['title']}</a></div>
            <div class="desc">{repo['description']}</div>
            <div class="meta">
                <span>🌟 {repo['stars']}</span>
                <span>🍴 {repo['forks']}</span>
                <span>📝 {repo['language']}</span>
            </div>
            <div class="author">作者：{repo['author']}</div>
            <div class="ai-summary"><b>AI总结：</b>{repo.get('summary', '')}</div>
            <a class="btn" href="{repo['url']}" target="_blank">查看仓库</a>
        </div>
'''
    html += '''
    </div>
    <div id="monthly" class="container tab-content" style="display:none;">
'''
    for repo in all_repos['monthly']:
        html += f'''
        <div class="card">
            <div class="repo-title"><a href="{repo['url']}" target="_blank">{repo['title']}</a></div>
            <div class="desc">{repo['description']}</div>
            <div class="meta">
                <span>🌟 {repo['stars']}</span>
                <span>🍴 {repo['forks']}</span>
                <span>📝 {repo['language']}</span>
            </div>
            <div class="author">作者：{repo['author']}</div>
            <div class="ai-summary"><b>AI总结：</b>{repo.get('summary', '')}</div>
            <a class="btn" href="{repo['url']}" target="_blank">查看仓库</a>
        </div>
'''
    html += '''
    </div>
    <script>
    // 主题切换功能
    function toggleTheme() {
        const body = document.body;
        const currentTheme = body.getAttribute('data-theme');
        const newTheme = currentTheme === 'light' ? 'dark' : 'light';

        body.setAttribute('data-theme', newTheme);
        localStorage.setItem('theme', newTheme);

        // 添加切换动画
        body.style.transition = 'background-color 0.3s ease, color 0.3s ease';
        setTimeout(() => {
            body.style.transition = '';
        }, 300);
    }

    // 页面加载时恢复主题设置
    document.addEventListener('DOMContentLoaded', function() {
        const savedTheme = localStorage.getItem('theme') || 'light';
        document.body.setAttribute('data-theme', savedTheme);
    });

    // 标签页切换功能
    function showTab(tab) {
        // 隐藏所有标签页内容
        document.getElementById('daily').style.display = 'none';
        document.getElementById('weekly').style.display = 'none';
        document.getElementById('monthly').style.display = 'none';

        // 显示选中的标签页
        document.getElementById(tab).style.display = '';

        // 更新标签页按钮状态
        document.querySelectorAll('.tab-btn').forEach(btn => {
            btn.classList.remove('active');
        });
        document.querySelector(`[data-tab="${tab}"]`).classList.add('active');

        // 添加切换动画
        const container = document.getElementById(tab);
        container.style.opacity = '0';
        container.style.transform = 'translateY(20px)';

        setTimeout(() => {
            container.style.transition = 'opacity 0.4s ease, transform 0.4s ease';
            container.style.opacity = '1';
            container.style.transform = 'translateY(0)';
        }, 50);

        setTimeout(() => {
            container.style.transition = '';
        }, 450);
    }

    // 卡片动画效果
    document.addEventListener('DOMContentLoaded', function() {
        const cards = document.querySelectorAll('.card');

        const observerOptions = {
            threshold: 0.1,
            rootMargin: '0px 0px -50px 0px'
        };

        const observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    entry.target.style.opacity = '1';
                    entry.target.style.transform = 'translateY(0)';
                }
            });
        }, observerOptions);

        cards.forEach((card, index) => {
            card.style.opacity = '0';
            card.style.transform = 'translateY(30px)';
            card.style.transition = `opacity 0.6s ease ${index * 0.1}s, transform 0.6s ease ${index * 0.1}s`;
            observer.observe(card);
        });
    });
    </script>
</body>
</html>'''
    with open('github_trending_cards.html', 'w', encoding='utf-8') as f:
        f.write(html)
    print('已生成 github_trending_cards.html，使用浏览器打开即可查看。')

if __name__ == '__main__':
    print('🚀 开始生成GitHub趋势榜单...')

    # 从环境变量获取API密钥
    api_key = "sk-yqxjmukyxctdsjbkcdtadwjkbtlcxktrfutyxlnestdehygh"
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
