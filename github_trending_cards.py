import requests
from bs4 import BeautifulSoup
from datetime import datetime
import os

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
        print('未安装openai库，无法生成AI总结。')
        return repos
    client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=api_key,
    )
    for repo in repos:
        prompt = f"请用一句中文总结这个GitHub项目的核心用途和亮点不要有其他符号：\n项目名称：{repo['title']}\n简介：{repo['description']}"
        try:
            completion = client.chat.completions.create(
                model="deepseek/deepseek-r1-0528:free",
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            summary = completion.choices[0].message.content.strip()
            repo['summary'] = summary
        except Exception as e:
            repo['summary'] = 'AI总结生成失败'
            print(f"AI总结失败: {repo['title']} - {e}")
    return repos
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
    api_key = os.getenv('OPENROUTER_API_KEY')
    if api_key:
        print(f'✅ 检测到API密钥: {api_key[:10]}...')
    else:
        print('⚠️ 未检测到OPENROUTER_API_KEY，将不生成AI总结。')
    
    all_repos = {}
    for since in ['daily', 'weekly', 'monthly']:
        print(f'\n📊 开始获取 {since} 榜单...')
        repos = fetch_github_trending(since)
        print(f'📝 获取到 {len(repos)} 个项目')
        
        if api_key and repos:
            print('🤖 开始生成AI总结...')
            repos = ai_summarize_projects(repos, api_key)
            print('✅ AI总结生成完成')
        elif not repos:
            print('⚠️ 未获取到项目数据，跳过AI总结')
        
        all_repos[since] = repos
    
    print('\n🎨 开始生成HTML页面...')
    generate_html(all_repos)
    print('🎉 GitHub趋势榜单生成完成！')