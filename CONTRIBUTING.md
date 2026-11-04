# 贡献指南

## 开发环境

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
```

## 质量检查

```bash
ruff check .
pytest -q
```

## 提交规范

- 变更保持最小、可审查
- 新功能必须带最小测试
- 不要提交任何密钥、Token、个人隐私信息


## 可选：离线报告的浏览器检查

核心运行不依赖浏览器或 Playwright。修改可视化报告时，可以额外执行：

```bash
python -m pip install playwright
python -m playwright install chromium
python scripts/check_demo_report.py
```

该脚本在离线浏览器环境中检查桌面和手机宽度、展开 / 收起完整数据、SVG 链接和返回导航，并将截图写入 `reports/browser-check/screenshots/`。CI 在 Python 3.12 的任务中运行同一脚本，保存截图供人工检查。布局冒烟检查不等同于跨浏览器或视觉回归测试。
