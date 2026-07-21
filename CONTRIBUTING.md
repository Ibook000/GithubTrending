# 贡献指南

感谢你帮助改进 GitHub 趋势雷达。欢迎修复抓取兼容性、改善中文摘要、优化无障碍体验或提出新的开放数据用法。

## 本地开发

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
pytest
ruff check .
```

运行真实抓取并在 `site/` 生成站点：

```bash
python github_trending_cards.py
python -m http.server 8000 -d site
```

## 提交 Pull Request

1. 一个 PR 只解决一个清晰问题。
2. 行为变更必须补充测试，并保证不会在失败时部署空榜单。
3. 不要提交 API Key、`.env`、`site/`、历史生成物或编辑器私有配置。
4. UI 变更请附桌面与移动端截图，并检查键盘导航和深浅主题。
5. 提交信息使用简短的动词开头描述，例如 `feat: add language filter`。

提交贡献即表示你同意按 Apache-2.0 许可证发布贡献内容。
