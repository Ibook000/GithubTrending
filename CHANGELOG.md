# Changelog

本项目遵循 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)；版本号遵循语义化版本。

## [Unreleased]

### Added
- “GitHub 趋势雷达”极简响应式首页。
- 搜索、语言筛选、跨榜标记、排名变化、本地收藏和分享。
- AI、开源与开发者生态公开 RSS 资讯聚合和中文化。
- 自动生成可下载、可分享的 `today-card.svg` 今日趋势卡片。
- 权威 AI 科技与开源资讯独立接口 `data/news/latest.json`、`news-feed.xml`。
- 竖版、方形、横版 SVG/PNG 趋势卡片及 `cards/manifest.json`。
- `data/latest.json`、每日 JSON 快照、RSS、sitemap 和社交分享元数据。
- Apache-2.0 许可证、贡献规范、安全政策、Issue/PR 模板和 Dependabot。

### Changed
- 日榜、周榜、月榜改为并行抓取，并增加网络重试和空数据部署保护。
- AI 摘要改为可选能力，失败时使用本地稳定摘要。
- 生成器、脚本、前端资源和测试按职责整理。
- 新闻源调整为 GitHub Blog、Hugging Face、OpenAI、CNCF、Linux Foundation 与 arXiv；仅收录最近 72 小时内容并支持单源陈旧回退。
- 首页改为“今日概览 → GitHub 热榜 → AI 科技资讯 → 多尺寸趋势卡片”的紧凑布局，新闻支持分类和来源筛选。
- 自动任务改为北京时间 10:00 完整更新、04:00/16:00/22:00 新闻轻量刷新。

### Added
- 新增 8 个新闻源：TechCrunch AI、Wired AI、Ars Technica、量子位、36氪、InfoQ 中文、钛媒体、爱范儿、雷锋网。
- 国内权威科技媒体覆盖 AI 大模型、开发者工具、开源生态等方向。
- 每源取数从 3 条增至 4 条，新闻总量上限提升至 30 条。

### Security
- API Key 不再以任何前缀或长度形式输出到日志。
- 移除内置明文 HTTP LLM 默认公网地址；未显式配置 `LLM_BASE_URL` 或已知提供商密钥时仅使用本地摘要。
