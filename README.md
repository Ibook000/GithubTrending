# 📊 GitHub趋势榜单 - GitHub Pages分支

> 欢迎来到 **GitHub趋势榜单** 项目的GitHub Pages分支！这个分支专门用于托管项目的在线展示和历史数据。

## 🌐 在线访问

### 🏠 主页面
**地址**: https://ibook000.github.io/GithubTrending/

访问主页面查看最新生成的GitHub趋势榜单，包含：
- 🔥 当前热门项目排行榜
- 📈 日榜/周榜/月榜切换
- 🤖 AI智能项目总结
- 💡 项目详细信息展示

### 📅 历史记录
**地址**: https://ibook000.github.io/GithubTrending/history/

查看所有历史记录：
- 📊 总记录天数统计
- 🕐 最新更新时间
- 📈 数据完整性检查
- 🔗 快速访问任意日期历史榜单

### 📂 历史数据目录
**格式**: `https://ibook000.github.io/GithubTrending/history/YYYY-MM-DD/`

**示例**:
- 2024年8月17日: https://ibook000.github.io/GithubTrending/history/2024-08-17/
- 2024年8月16日: https://ibook000.github.io/GithubTrending/history/2024-08-16/

## 📁 分支结构

```
gh-pages/
├── index.html                    # 主页面（最新榜单）
├── github_trending_cards.css     # 主页面样式
├── history/                      # 历史数据目录
│   ├── index.html               # 历史统计页面
│   ├── 2024-08-17/              # 每日历史记录
│   │   ├── index.html           # 当日榜单页面
│   │   ├── github_trending_cards.css  # 当日样式
│   │   └── metadata.json        # 当日元数据
│   ├── 2024-08-16/
│   └── ...
├── img.png                      # 项目展示图片
└── README.md                    # 本文件
```

## 🔄 更新频率

- ⏰ **每天北京时间 10:00** 自动更新
- 🤖 **GitHub Actions** 自动运行
- 📅 **每日保存** 历史记录到独立目录
- 🔄 **实时部署** 到GitHub Pages

## 🎯 功能特色

### 🏆 热门项目展示
- 自动爬取GitHub Trending前10名
- 支持日榜、周榜、月榜切换
- 展示项目语言、Star、Fork等关键信息

### 🤖 AI智能总结
- 使用OpenRouter大模型API
- 自动生成项目中文一句话总结
- 帮助快速理解项目核心功能

### 📊 历史数据分析
- 完整的每日历史记录
- 数据完整性统计
- 可视化历史趋势

### 📱 响应式设计
- 支持手机、平板、电脑访问
- 美观的卡片式布局
- 流畅的交互体验

## 🚀 技术栈

- **前端**: HTML5 + CSS3 + JavaScript
- **数据**: GitHub API + 自动化爬虫
- **部署**: GitHub Pages + GitHub Actions
- **AI**: OpenRouter大模型API

## 📞 联系作者

- 📧 **邮箱**: ibook@outlook.be
- 💬 **微信**: IBO0OK
- 🐙 **GitHub**: [@Ibook000](https://github.com/Ibook000)

## 🌟 项目地址

- **主仓库**: https://github.com/Ibook000/GithubTrending
- **问题反馈**: https://github.com/Ibook000/GithubTrending/issues

## 📝 使用说明

1. **查看最新榜单**: 直接访问主页面
2. **查看历史**: 点击主页面上的「历史记录」链接
3. **分享项目**: 复制具体日期的URL分享给他人
4. **数据验证**: 通过历史统计页面查看数据完整性

---

> 💡 **提示**: 这个分支是自动生成的，所有文件都由GitHub Actions自动创建和更新。如需修改项目逻辑，请查看主分支的源代码。