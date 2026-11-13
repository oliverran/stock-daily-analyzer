"""Regenerate the committed synthetic preview and GitHub-readable summary."""

import json
from pathlib import Path

import pandas as pd

from qf.demo import run_demo


def update_preview(destination: Path) -> None:
    """Keep both Markdown entry points derived from the actual demo outputs."""
    summary_path = run_demo(destination)
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    equity = pd.read_csv(destination / "equity.csv", index_col="Date")["equity"]
    holdings = pd.read_csv(destination / "holdings.csv", index_col="Date")
    metrics = summary["metrics"]
    weights = "\n".join(f"| `{symbol}` | {weight:.2%} |" for symbol, weight in holdings.iloc[-1].items())
    readme = f'''# 合成数据演示：先看结果，再决定是否安装

[中文](README.md) | [English](README.en.md)

**这是虚构价格的模拟输出，不是真实市场业绩，不构成投资建议。**

本页可直接在 GitHub 阅读，无需 Python、API Key 或下载。图表、指标和持仓来自同一次 `stock-analyzer demo` 执行，使用项目的 `DailyBacktester`，不是手写展示数字。

![合成数据净值曲线；不是真实市场业绩](equity.svg)

## 这次演示运行了什么

- 日期：{equity.index[0]} 至 {equity.index[-1]}，共 {summary['observations']} 条工作日观察。
- 虚构标的：{', '.join(f'`{symbol}`' for symbol in summary['symbols'])}。
- 模拟初始资金：{summary['config']['initial_cash']:,.2f}；期末净值：{equity.iloc[-1]:,.2f}。
- {summary['config']['lookback_days']} 日动量因子，Top {summary['config']['top_k']} 等权组合，调仓频率 `{summary['config']['rebalance']}`；因子历史不足时保持现金。
- 普通工作日并非交易所日历。佣金、滑点和交易约束均为示例设置。

## 模拟指标，仅用于理解输出格式

| 指标 | 本次合成演示 |
| --- | ---: |
| 模拟累计收益 | {metrics['total_return']:.2%} |
| 模拟最大回撤 | {metrics['max_drawdown']:.2%} |
| 模拟年化收益 | {metrics['cagr']:.2%} |
| 模拟 Sharpe | {metrics['sharpe']:.2f} |

短期合成样本的年化值和 Sharpe 不代表可实现收益。完整精度与参数见 [summary.json](summary.json)。

## 最后一天的组合权重

{holdings.index[-1]}；`__CASH__` 表示现金。

| 标的 | 权重 |
| --- | ---: |
{weights}

## 查看数据与完整报告

- [净值 CSV](equity.csv)：逐日模拟净值，图表的全部 {summary['observations']} 个观察值来自这里。
- [持仓 CSV](holdings.csv)：每日组合权重。
- [参数与指标 JSON](summary.json)：明确标注合成数据来源，记录模拟设置和指标。
- [完整报告 HTML 源文件](report.html)：GitHub 显示源码。将本目录全部文件保存到本地，再用浏览器打开 `report.html`。点击图表圆点或日期表可查看当天模拟净值与持仓，支持键盘和浏览器返回，无需脚本。

持仓是引擎当日调仓及成本处理后的记录，不代表当日收益贡献、交易信号或成交原因。独立 SVG 保持为可移植的静态图。

## 自己复现

按[快速开始](../../README.md#快速开始)安装后运行：

```bash
stock-analyzer demo
```

打开生成的 `reports/demo/report.html`。演示运行不访问行情、新闻或 LLM 服务；首次安装依赖需要联网。若从源码修改演示，运行 `python scripts/update_demo_preview.py` 可同步本页与数据文件。

[返回项目与真实数据接入说明](../../README.md) · [反馈问题](https://github.com/oliverran/stock-daily-analyzer/issues)

如果输出形式对你的研究有帮助，欢迎在[项目主页](https://github.com/oliverran/stock-daily-analyzer)点 Star。请勿将合成演示指标当作真实业绩传播。
'''
    (destination / "README.md").write_text(readme, encoding="utf-8")
    readme_en = f'''# Synthetic demo: inspect the results before installing

[中文](README.md) | [English](README.en.md)

**These are simulated results from fictional prices, not historical market performance or investment advice.**

Read this page directly on GitHub without Python, an API key, or a download. The chart, metrics, and holdings come from the same `stock-analyzer demo` run using the project's `DailyBacktester`, not manually entered display numbers.

![Synthetic equity curve, not historical market performance](equity.svg)

## What this demo ran

- Dates: {equity.index[0]} to {equity.index[-1]}, with {summary['observations']} weekday observations.
- Fictional symbols: {', '.join(f'`{symbol}`' for symbol in summary['symbols'])}.
- Simulated initial cash: {summary['config']['initial_cash']:,.2f}; final equity: {equity.iloc[-1]:,.2f}.
- {summary['config']['lookback_days']}-day momentum factor, Top {summary['config']['top_k']} equal-weight portfolio, rebalance frequency `{summary['config']['rebalance']}`. The portfolio stays in cash until enough factor history is available.
- Weekdays are not an exchange trading calendar. Commission, slippage, and trading constraints are example settings.

## Simulated metrics: output-format examples only

| Metric | This synthetic demo |
| --- | ---: |
| Simulated total return | {metrics['total_return']:.2%} |
| Simulated maximum drawdown | {metrics['max_drawdown']:.2%} |
| Simulated annualized return | {metrics['cagr']:.2%} |
| Simulated Sharpe ratio | {metrics['sharpe']:.2f} |

Annualized values and Sharpe ratios from a short synthetic sample do not represent achievable returns. See [summary.json](summary.json) for full precision and parameters.

## Portfolio weights on the final day

{holdings.index[-1]}; `__CASH__` means cash.

| Symbol | Weight |
| --- | ---: |
{weights}

## Inspect the data and full report

- [Equity CSV](equity.csv): daily simulated equity, including all {summary['observations']} observations used in the chart.
- [Holdings CSV](holdings.csv): daily portfolio weights.
- [Parameters and metrics JSON](summary.json): synthetic-data provenance, settings, and metrics.
- [Full report HTML source](report.html): GitHub shows source. Save all files in this directory locally, then open `report.html` in a browser. Select a chart point or date-table link to inspect that day's simulated equity and holdings, with keyboard and browser Back support and no scripts.

Holdings are the engine's recorded weights after that day's rebalancing and cost processing, not return attribution, trading signals, or explanations of fills. The standalone SVG remains a portable static chart.

## Reproduce it yourself

Follow the [quick start](../../README.en.md#quick-start), then run:

```bash
stock-analyzer demo
```

Open the generated `reports/demo/report.html`. The demo makes no market-data, news, or LLM requests; installing dependencies initially requires internet access. After changing the demo source, run `python scripts/update_demo_preview.py` to regenerate both language summaries and the data files.

[Back to the project and real-data setup](../../README.en.md) · [Report a problem](https://github.com/oliverran/stock-daily-analyzer/issues)

If the output is useful for your research, a Star on the [repository](https://github.com/oliverran/stock-daily-analyzer) is welcome. Do not present synthetic demo metrics as real market performance.
'''
    (destination / "README.en.md").write_text(readme_en, encoding="utf-8")
    print(f"Updated synthetic preview: {destination}")


if __name__ == "__main__":
    update_preview(Path(__file__).resolve().parents[1] / "docs" / "demo")
