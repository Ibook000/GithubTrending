
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
    response = requests.get(url, headers=headers)
    soup = BeautifulSoup(response.text, 'html.parser')
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
</head>
<body>
    <h1>GitHub 趋势榜单（{today}）</h1>
    <div style="text-align:center;margin-bottom:32px;">
        <button class="btn" onclick="showTab('daily')">日榜</button>
        <button class="btn" onclick="showTab('weekly')">周榜</button>
        <button class="btn" onclick="showTab('monthly')">月榜</button>
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
    function showTab(tab) {
        document.getElementById('daily').style.display = 'none';
        document.getElementById('weekly').style.display = 'none';
        document.getElementById('monthly').style.display = 'none';
        document.getElementById(tab).style.display = '';
    }
    </script>
</body>
</html>'''
    with open('github_trending_cards.html', 'w', encoding='utf-8') as f:
        f.write(html)
    print('已生成 github_trending_cards.html，使用浏览器打开即可查看。')

if __name__ == '__main__':
    api_key = '这是我的keysk-or-v1-2f6818462600771270e5b9e6c0ebe6b0f9e6c7bafc8ee6d1260bca078254339a'
    all_repos = {}
    for since in ['daily', 'weekly', 'monthly']:
        repos = fetch_github_trending(since)
        if api_key:
            repos = ai_summarize_projects(repos, api_key)
        else:
            print('未检测到OPENROUTER_API_KEY，将不生成AI总结。')
        all_repos[since] = repos
    generate_html(all_repos)
