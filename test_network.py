#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
网络连接测试脚本
用于诊断GitHub Actions环境中的网络连接问题
"""

import os
import sys
import time
import requests
from urllib.parse import urlparse

def test_basic_connectivity():
    """测试基本网络连接"""
    print("🌐 测试基本网络连接...")
    
    test_urls = [
        "https://www.google.com",
        "https://api.github.com",
        "https://openrouter.ai",
        "https://httpbin.org/ip"
    ]
    
    for url in test_urls:
        try:
            response = requests.get(url, timeout=10)
            print(f"✅ {url}: {response.status_code}")
        except Exception as e:
            print(f"❌ {url}: {e}")

def test_openrouter_api():
    """测试OpenRouter API连接"""
    print("\n🤖 测试OpenRouter API连接...")
    
    api_key = os.environ.get('OPENROUTER_API_KEY')
    if not api_key:
        print("❌ 未找到OPENROUTER_API_KEY环境变量")
        return
    
    print(f"🔑 API密钥长度: {len(api_key)}")
    print(f"🔑 API密钥前缀: {api_key[:15]}...")
    
    try:
        # 测试API连接
        headers = {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json'
        }
        
        # 简单的API测试请求
        test_data = {
            "model": "deepseek/deepseek-r1-0528:free",
            "messages": [{"role": "user", "content": "Hello"}],
            "max_tokens": 10
        }
        
        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers=headers,
            json=test_data,
            timeout=30
        )
        
        print(f"📡 API响应状态: {response.status_code}")
        if response.status_code == 200:
            print("✅ OpenRouter API连接成功")
        else:
            print(f"❌ API错误: {response.text[:200]}")
            
    except Exception as e:
        print(f"❌ OpenRouter API连接失败: {e}")

def test_dns_resolution():
    """测试DNS解析"""
    print("\n🔍 测试DNS解析...")
    
    import socket
    
    domains = [
        "openrouter.ai",
        "api.openrouter.ai",
        "github.com",
        "google.com"
    ]
    
    for domain in domains:
        try:
            ip = socket.gethostbyname(domain)
            print(f"✅ {domain} -> {ip}")
        except Exception as e:
            print(f"❌ {domain}: {e}")

def show_environment_info():
    """显示环境信息"""
    print("\n📋 环境信息:")
    print(f"Python版本: {sys.version}")
    print(f"操作系统: {os.name}")
    print(f"GitHub Actions: {os.environ.get('GITHUB_ACTIONS', 'false')}")
    print(f"Runner OS: {os.environ.get('RUNNER_OS', 'unknown')}")
    
    # 显示相关环境变量
    env_vars = [
        'GITHUB_ACTIONS',
        'RUNNER_OS',
        'PYTHONUNBUFFERED',
        'REQUESTS_CA_BUNDLE',
        'HTTP_PROXY',
        'HTTPS_PROXY'
    ]
    
    print("\n🔧 环境变量:")
    for var in env_vars:
        value = os.environ.get(var, '未设置')
        print(f"  {var}: {value}")

def main():
    """主函数"""
    print("🚀 开始网络连接诊断...")
    print("=" * 50)
    
    show_environment_info()
    test_dns_resolution()
    test_basic_connectivity()
    test_openrouter_api()
    
    print("\n" + "=" * 50)
    print("✅ 网络诊断完成")

if __name__ == "__main__":
    main()