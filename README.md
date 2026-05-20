# GitHub 趋势榜单 - GitHub Pages 分支

这个分支用于托管项目的在线页面与历史快照，所有内容均由 GitHub Actions 自动生成和发布。

## 在线访问

### 最新榜单首页
地址：
[https://ibook000.github.io/GithubTrending/](https://ibook000.github.io/GithubTrending/)

首页当前提供：
- 海报式 Hero 首屏
- 日榜 / 周榜 / 月榜切换
- 今日焦点项目展示
- AI 一句话总结
- 深浅主题切换

### 历史档案页
地址：
[https://ibook000.github.io/GithubTrending/history/](https://ibook000.github.io/GithubTrending/history/)

历史页当前提供：
- 归档天数统计
- 最新日期与最早日期信息
- 数据完整率
- 连续归档天数
- 按日期倒序浏览历史快照

### 历史快照目录
格式：
`https://ibook000.github.io/GithubTrending/history/YYYY-MM-DD/`

示例：
- `https://ibook000.github.io/GithubTrending/history/2024-11-01/`

## 分支内容
```text
gh-pages/
├── index.html
├── github_trending_cards.css
├── history/
│   ├── index.html
│   ├── YYYY-MM-DD/
│   │   ├── index.html
│   │   ├── github_trending_cards.css
│   │   └── metadata.json
│   └── ...
├── img.png
└── README.md
```

## 自动更新方式
- GitHub Actions 每天北京时间 10:00 自动运行
- 自动抓取 GitHub Trending 榜单
- 自动生成首页与历史档案页
- 自动将结果发布到 `gh-pages` 分支

## 功能说明

### 首页体验
- 聚焦最新榜单
- 支持多时间维度切换
- 便于快速扫读热门项目

### 历史体验
- 适合回看某一天的热门项目
- 可用于追踪热点项目出现时间
- 支持直接进入某一天的完整页面

## 项目地址
- 主仓库：
  [https://github.com/Ibook000/GithubTrending](https://github.com/Ibook000/GithubTrending)
- 问题反馈：
  [https://github.com/Ibook000/GithubTrending/issues](https://github.com/Ibook000/GithubTrending/issues)

---

提示：这个分支是自动生成的，若要修改页面逻辑或样式，请在主分支更新源代码。
