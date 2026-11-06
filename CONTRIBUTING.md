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

## 可选：运行 Notebook 教程检查

```bash
python -m pip install -e ".[notebook]"
python scripts/check_demo_notebook.py
```

该脚本在临时目录启动本地 Jupyter 内核，默认跳过 Notebook 中的联网安装单元，改用已安装的当前代码。安装之后，它阻止教程发出外部请求，检查 60 行合成数据、三个 TopK 场景、SVG 输出和仅包含演示文件的 ZIP。需要允许本机内核通信。使用 `--install` 可执行固定提交的联网安装，替换当前环境中的项目版本；只在可丢弃的环境中使用。CI 在 Python 3.12 上用该选项检查完整安装与执行过程。它不验证 Google 登录或 Colab 运行时可用性。

Notebook 安装单元固定到一个已存在的项目提交，避免直接追随变化的 main。更新教程依赖的 API 时，应一起更新此提交，并核查该固定版本；不要提交执行输出、运行时路径或凭据。

## 更新可复现日报样例

`stock-analyzer demo-daily` 使用固定虚构行情运行现有指标、筛选规则和文本日报生成器。
修改相关逻辑后运行 `python scripts/update_daily_preview.py`，更新 `docs/daily-demo/` 的五个文件。
测试会在禁止外部请求和生产工作流副作用的条件下重新生成并核对输出，包含输入 SHA-256、
实际指标和日期。不要手写候选、LLM 理由、准确率或收益来替代真实执行。
