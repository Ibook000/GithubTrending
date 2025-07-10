# GithubTrending

一个自动抓取并美观展示 GitHub Trending 热门仓库榜单的开源项目，支持日榜、周榜、月榜，并可通过 AI 自动生成每个仓库的中文一句话总结。

## 项目亮点
- 🚀 自动爬取 GitHub Trending 前 10 热门仓库（支持日榜、周榜、月榜）
- 📝 展示项目名称、简介、语言、Star、Fork、作者等关键信息
- 🤖 支持通过 OpenRouter 大模型自动生成项目一句话中文总结
- 💡 生成美观的 HTML 卡片页面，支持一键切换榜单类型
- 🌏 全中文界面，开箱即用

## 快速开始
1. 安装依赖：
   ```bash
   pip install requests beautifulsoup4 openai
   ```
2. 运行主程序：
   ```bash
   python github_trending_cards.py
   ```
3. 用浏览器打开生成的 `github_trending_cards.html` 查看榜单

## 依赖说明
- requests
- beautifulsoup4
- openai（可选，仅用于AI总结）

## AI 总结功能
如需生成 AI 总结，请在 `github_trending_cards.py` 中填写你的 OpenRouter API Key。

---

欢迎 Star、Fork 和提 Issue！ 
