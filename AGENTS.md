# AGENTS.md

## 项目概述

**GithubTrending** 是一个自动抓取并美观展示 GitHub Trending 热门仓库榜单的开源项目。

### 核心功能
- 🚀 自动爬取 GitHub Trending 前 10 热门仓库（支持日榜、周榜、月榜）
- 📝 展示项目名称、简介、语言、Star、Fork、作者等关键信息
- 🤖 支持 OpenAI 兼容接口生成项目中文摘要和资讯中文化
- 📰 聚合 AI、开源与开发者生态公开 RSS 资讯
- 💡 自动生成竖版、方形、横版三种可下载、可分享的今日趋势 SVG/PNG 卡片
- 📅 **历史记录自动保存到 gh-pages 分支**，可查看每日历史榜单
- 🌏 全中文界面，开箱即用

### 技术栈
- **后端**: Python 3.11+ (requests, beautifulsoup4, openai)
- **前端**: HTML5 + CSS3 + JavaScript
- **部署**: GitHub Actions + GitHub Pages

---

## 常用命令

### 本地运行

```bash
# 安装依赖
pip install -r requirements.txt

# 生成趋势榜单；不配置密钥时使用本地备用摘要
python github_trending_cards.py --mode full

# 仅刷新 AI/开源资讯和趋势卡片，不改变 GitHub 排名快照
python github_trending_cards.py --mode news

# 生成历史统计页面
python scripts/generate_history_stats.py

# 测试网络连接
python scripts/check_network.py
```

### 环境变量

```bash
# 可选 AI 摘要与资讯中文化
export LLM_API_KEY="your-api-key-here"
export LLM_BASE_URL="https://your-openai-compatible-endpoint/v1"
export LLM_MODEL="your-model"
```

---

## 项目结构

```
├── github_trending_cards.py    # 向后兼容的命令行入口
├── src/github_trending/        # 抓取、摘要、JSON/RSS和站点生成逻辑
├── assets/                     # HTML、CSS、JavaScript和品牌资源
├── scripts/                    # 历史页与网络诊断脚本
├── tests/                      # 自动化测试
├── requirements.txt            # Python依赖
├── .github/workflows/          # GitHub Actions配置
│   └── generate_trending.yml   # 完整榜单与每 6 小时资讯刷新工作流
├── history/                    # 本地历史记录目录
│   └── YYYY-MM-DD/             # 按日期归档的历史数据
└── docs/assets/                # README 的桌面、移动端和卡片截图
```

---

## 开发指南

### 代码风格
- Python: 使用标准 PEP 8 风格
- HTML/CSS: 遵循项目现有的内联样式和 CSS 变量模式
- 注释: 中文注释，清晰说明功能

### 关键文件说明

#### `src/github_trending/app.py`
- `fetch_github_trending(since)`: 爬取 GitHub Trending 数据
- `ai_summarize_projects(repos, api_key)`: 调用 OpenRouter API 生成中文总结
- `fetch_news_bundle()`: 聚合权威 AI、开源与开发者生态 RSS/Atom，并做 72 小时过滤与失败回退
- `ai_localize_news(news, api_key)`: 将资讯标题与摘要转换成简洁中文
- `generate_trend_card(payload, variant)`: 生成竖版、方形或横版 SVG 趋势卡片
- `generate_card_assets(payload, output_dir)`: 输出 SVG、PNG、二维码和 `cards/manifest.json`
- `generate_fallback_summary(repo)`: 备用总结生成（当 API 失败时）
- `build_payload(all_repos, previous)`: 生成版本化开放数据并计算排名变化
- `generate_site(payload, output_dir)`: 生成 HTML、JSON、RSS 和 SEO 文件

#### `.github/workflows/generate_trending.yml`
- 北京时间 10:00 完整运行；04:00、16:00、22:00 仅刷新资讯
- 包含网络诊断、数据爬取、AI 总结、历史保存、部署到 GitHub Pages

### 添加新功能建议
1. 新增榜单类型 → 修改 `fetch_github_trending()` 的 `since` 参数
2. 修改页面布局 → 更新 `assets/index.html`
3. 调整样式 → 修改 `assets/styles.css`
4. 更换 AI 模型 → 设置 `LLM_MODEL` / `LLM_BASE_URL` 环境变量，或修改默认常量

---

## 部署说明

### GitHub Pages 部署
- 分支: `gh-pages`
- 源文件: `./gh-pages` 目录
- 自动通过 GitHub Actions 部署

### 历史记录
- 存储在 `gh-pages` 分支的 `history/YYYY-MM-DD/` 目录
- 每个历史记录包含: index.html, github_trending_cards.css, metadata.json

---

## 注意事项

1. **API Key**: 使用 SiliconFlow 的 OpenRouter 兼容 API 端点
2. **网络环境**: GitHub Actions 中有特殊的网络配置
3. **依赖版本**: Python 3.11+ 推荐，确保兼容 openai>=1.0.0
4. **重试机制**: AI 总结默认重试 2-3 次，GitHub Actions 中增加重试次数
