# Changelog

本项目遵循 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)；版本号遵循语义化版本。

## [Unreleased]

### Added
- “GitHub 趋势雷达”极简响应式首页。
- 搜索、语言筛选、跨榜标记、排名变化、本地收藏和分享。
- AI、开源与开发者生态公开 RSS 资讯聚合和中文化。
- 自动生成可下载、可分享的 `today-card.svg` 今日趋势卡片。
- `data/latest.json`、每日 JSON 快照、RSS、sitemap 和社交分享元数据。
- Apache-2.0 许可证、贡献规范、安全政策、Issue/PR 模板和 Dependabot。

### Changed
- 日榜、周榜、月榜改为并行抓取，并增加网络重试和空数据部署保护。
- AI 摘要改为可选能力，失败时使用本地稳定摘要。
- 生成器、脚本、前端资源和测试按职责整理。

### Security
- API Key 不再以任何前缀或长度形式输出到日志。
