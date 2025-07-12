#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import base64
import requests
import os

def upload_html_to_github():
    """上传HTML文件到GitHub"""
    
    # 读取HTML文件
    with open('github_trending_cards.html', 'r', encoding='utf-8') as f:
        html_content = f.read()
    
    # 编码为base64
    content_encoded = base64.b64encode(html_content.encode('utf-8')).decode('utf-8')
    
    # GitHub API配置
    owner = "Ibook000"
    repo = "GithubTrending"
    path = "github_trending_cards.html"
    
    # 获取当前文件的SHA（如果存在）
    url = f"https://api.github.com/repos/{owner}/{repo}/contents/{path}"
    
    try:
        response = requests.get(url)
        if response.status_code == 200:
            current_sha = response.json()['sha']
            print(f"Found existing file with SHA: {current_sha}")
        else:
            current_sha = None
            print("File doesn't exist, will create new")
    except Exception as e:
        print(f"Error getting file info: {e}")
        current_sha = None
    
    # 准备更新数据
    data = {
        "message": "更新GitHub趋势榜单HTML - 包含AI总结",
        "content": content_encoded,
        "branch": "main"
    }
    
    if current_sha:
        data["sha"] = current_sha
    
    # 发送请求
    try:
        response = requests.put(url, json=data)
        if response.status_code in [200, 201]:
            print("✅ HTML文件上传成功!")
            result = response.json()
            print(f"📄 文件大小: {len(html_content)} 字符")
            print(f"🔗 查看地址: {result['content']['html_url']}")
        else:
            print(f"❌ 上传失败: {response.status_code}")
            print(f"错误信息: {response.text}")
    except Exception as e:
        print(f"❌ 上传过程中出错: {e}")

if __name__ == "__main__":
    upload_html_to_github()