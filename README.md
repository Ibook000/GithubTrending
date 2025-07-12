# GitHub Trending Cards

一个美观的GitHub趋势榜单展示工具，支持AI智能总结。

## 功能特性

- 📊 获取GitHub日榜、周榜、月榜趋势项目
- 🤖 AI智能总结项目核心功能和亮点
- 🎨 美观的卡片式布局
- 🌓 支持深色/浅色主题切换
- 📱 响应式设计，支持移动端
- ⚡ 流畅的动画效果

## 使用方法

1. 安装依赖：
```bash
pip install -r requirements.txt
```

2. 设置OpenRouter API密钥（可选，用于AI总结）：
```bash
# Windows PowerShell
$env:OPENROUTER_API_KEY="your-api-key-here"

# Linux/Mac
export OPENROUTER_API_KEY="your-api-key-here"
```

3. 运行脚本：
```bash
python github_trending_cards.py
```

4. 打开生成的 `github_trending_cards.html` 文件查看结果

## 截图

![展示效果](展示1.png)

## 技术栈

- Python 3.x
- requests - HTTP请求
- BeautifulSoup4 - HTML解析
- OpenAI - AI总结（通过OpenRouter）
- HTML/CSS/JavaScript - 前端展示

## 许可证

MIT License