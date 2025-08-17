# GithubTrending

一个自动抓取并美观展示 GitHub Trending 热门仓库榜单的开源项目，支持日榜、周榜、月榜，并可通过 AI 自动生成每个仓库的中文一句话总结。

## 项目亮点
- 🚀 自动爬取 GitHub Trending 前 10 热门仓库（支持日榜、周榜、月榜）
- 📝 展示项目名称、简介、语言、Star、Fork、作者等关键信息
- 🤖 支持通过 OpenRouter 大模型自动生成项目一句话中文总结
- 💡 生成美观的 HTML 卡片页面，支持一键切换榜单类型
- 📅 **历史记录自动保存到 gh-pages 分支**，可查看每日历史榜单
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

## 历史记录功能
本项目通过 GitHub Actions 自动运行，每天北京时间 10 点更新榜单，并将历史记录保存到 `gh-pages` 分支：

- 📂 历史数据保存在 `gh-pages` 分支的 `history/YYYY-MM-DD/` 目录中
- 📊 提供历史统计页面，可查看所有历史记录
- 🔗 每个历史页面都包含完整的榜单数据和样式
- 🌐 通过 GitHub Pages 可直接在线访问历史榜单

### 访问历史记录
1. 打开项目的 GitHub Pages 页面（如：https://yourusername.github.io/GithubTrending/）
2. 点击页面上的「历史记录」链接
3. 选择任意日期查看当日热门项目

## 依赖说明
- requests
- beautifulsoup4
- openai（可选，仅用于AI总结）

## AI 总结功能
如需生成 AI 总结，请在 `github_trending_cards.py` 中填写你的 OpenRouter API Key。

## 效果预览

### 主页面展示
![主页面展示](img.png)

### 历史记录页面
历史统计页面提供：
- 📅 总记录天数统计
- 🕐 最新更新时间
- 📈 数据完整性检查
- 🔗 快速访问任意日期历史榜单

---

欢迎 Star、Fork 和提 Issue！