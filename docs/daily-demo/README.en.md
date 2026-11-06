# Daily research report example · synthetic data

[中文](README.md) | [English](README.en.md) | [Project](https://github.com/oliverran/stock-daily-analyzer/blob/main/README.en.md)

This is the actual output of the existing indicator calculations, screening rules,
and text-report renderer, fed **fictional prices**. It is not a current market
report. The report retains the application's Chinese labels: 历史回测 = historical
review, 今日推荐 = rule-selected candidates, RSI = relative strength index, and
量比 = current volume / 20-observation average (including the current observation).

**Source:** deterministic formulas in [`qf/daily_demo.py`](https://github.com/oliverran/stock-daily-analyzer/blob/main/qf/daily_demo.py).
Four invented symbols each have 80 ordinary weekday observations, **2024-01-01
through 2024-04-19**. The fixed report date is the last input date, not the run date.
Weekdays are not an exchange calendar. These paths were designed to illustrate the
categories; they do not validate the rules on real markets.

## Read the output

The original renderer calls candidates “recommendations”; here every symbol is
fictional. No historical recommendation database is read, so no hit rate or return
is invented. No LLM is called and no LLM commentary is fabricated. There is no
portfolio backtest or order execution in this example.

```text
SYNTHETIC DAILY REPORT / 合成数据日报示例。Not live market data or investment advice. 不是实时行情、真实荐股或收益记录。
Source / 来源: qf/daily_demo.py; deterministic_synthetic; 2024-01-01..2024-04-19.
日期为固定样本日期，不是今日行情。无历史收益记录，无 LLM 解读。

============================================================
股票分析日报 - 2024-04-19
============================================================

【历史回测】
  暂无历史数据可回测

【今日推荐】
  扫描股票数: 4

  类型: 超卖反弹
    - 虚构样本 A(DEMO_A): ¥20.00 | RSI:44 | 量比:2.33

  类型: 趋势向好
    - 虚构样本 B(DEMO_B): ¥20.12 | RSI:56 | 量比:2.33

  类型: 放量突破
    - 虚构样本 C(DEMO_C): ¥20.38 | RSI:52 | 量比:2.33

============================================================
风险提示: 以上分析仅供参考，不构成投资建议。股市有风险，投资需谨慎。
============================================================
```

## Reproduce after installation

From the repository root, after the [installation steps](https://github.com/oliverran/stock-daily-analyzer/blob/main/README.en.md#quick-start):

```bash
stock-analyzer demo-daily --out reports/daily-demo
```

On Windows, use `.\.venv\Scripts\stock-analyzer.exe` if the virtual environment
is not activated. Open `reports/daily-demo/daily-report.txt` in a text editor.
The command makes no market-data, news, or model requests and does not write to
the daily-report database. It overwrites the five named files in the chosen
output directory; choose a new directory to preserve an earlier run.

- [daily-report.txt](daily-report.txt): the generated, explicitly labeled report.
- [inputs.csv](inputs.csv): all 320 fictional close/volume observations.
- [analysis.json](analysis.json): source/date, input SHA-256, settings, computed
  indicators, selections and formatted candidate records.
- [README.md](README.md) and [README.en.md](README.en.md): generated reading guides.

To refresh this checked-in example, run `python scripts/update_daily_preview.py`.
Tests regenerate and compare every file. See [`analyzer.py`](https://github.com/oliverran/stock-daily-analyzer/blob/main/analyzer.py),
[`strategies.py`](https://github.com/oliverran/stock-daily-analyzer/blob/main/strategies.py) and [`reporting.py`](https://github.com/oliverran/stock-daily-analyzer/blob/main/reporting.py)
for the production calculations, rules and renderer used here.

The existing [portfolio demo](https://github.com/oliverran/stock-daily-analyzer/blob/main/docs/demo/README.en.md) is a different workflow.
For real-data reports, use [`stock-analyzer run-daily`](https://github.com/oliverran/stock-daily-analyzer/blob/main/README.en.md#real-data-workflows)
only after reviewing its data providers, settings and research limitations.
Offline success does not verify live services or the quality of trading signals.
