# AGENTS.md

## 项目概述

**GithubTrending** 是一个自动抓取并美观展示 GitHub Trending 热门仓库榜单的开源项目。

### 核心功能
- 🚀 自动爬取 GitHub Trending 前 10 热门仓库（支持日榜、周榜、月榜）
- 📝 展示项目名称、简介、语言、Star、Fork、作者等关键信息
- 🤖 支持通过 OpenRouter 大模型自动生成项目中文一句话总结
- 💡 生成美观的 HTML 卡片页面，支持一键切换榜单类型
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

# 生成趋势榜单（需要设置 NVIDIA_API_KEY 或 OPENROUTER_API_KEY 环境变量）
python github_trending_cards.py

# 生成历史统计页面
python generate_history_stats.py

# 测试网络连接
python test_network.py
```

### 环境变量

```bash
# AI 总结功能需要设置 API Key
export NVIDIA_API_KEY="your-api-key-here"
```

---

## 项目结构

```
├── github_trending_cards.py    # 主程序 - 爬取数据、生成AI总结、创建HTML
├── github_trending_cards.css   # CSS样式 - 卡片布局、主题切换、响应式设计
├── github_trending_cards.html  # 生成的HTML页面示例
├── generate_history_stats.py   # 历史统计页面生成器
├── upload_html.py              # 将HTML上传到GitHub仓库
├── test_network.py             # 网络连接测试工具
├── requirements.txt            # Python依赖
├── .github/workflows/          # GitHub Actions配置
│   └── generate_trending.yml   # 自动部署工作流
├── history/                    # 本地历史记录目录
│   └── YYYY-MM-DD/             # 按日期归档的历史数据
└── img.png                     # 项目展示图片
```

---

## 开发指南

### 代码风格
- Python: 使用标准 PEP 8 风格
- HTML/CSS: 遵循项目现有的内联样式和 CSS 变量模式
- 注释: 中文注释，清晰说明功能

### 关键文件说明

#### `github_trending_cards.py`
- `fetch_github_trending(since)`: 爬取 GitHub Trending 数据
- `ai_summarize_projects(repos, api_key)`: 调用 OpenRouter API 生成中文总结
- `generate_fallback_summary(repo)`: 备用总结生成（当 API 失败时）
- `generate_html(all_repos)`: 生成 HTML 页面
- `create_metadata_file()`: 创建元数据文件

#### `.github/workflows/generate_trending.yml`
- 每天 UTC 2点（北京时间 10点）自动运行
- 包含网络诊断、数据爬取、AI 总结、历史保存、部署到 GitHub Pages

### 添加新功能建议
1. 新增榜单类型 → 修改 `fetch_github_trending()` 的 `since` 参数
2. 修改页面布局 → 更新 `generate_html()` 函数中的 HTML 模板
3. 调整样式 → 修改 `github_trending_cards.css`
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
