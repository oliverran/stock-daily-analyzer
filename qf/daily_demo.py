"""Reproducible daily-report example using the real indicators, rules and renderer.

Only the data source is replaced. No market scan, database, LLM or notification
workflow is invoked. The synthetic paths exercise the report's three categories;
they are not observations of real securities or evidence of predictive skill.
"""
from datetime import date
import hashlib
import json
from pathlib import Path
from typing import Dict

import numpy as np
import pandas as pd

from analyzer import StockAnalyzer
from config import (
    BOLLINGER_PERIOD, BOLLINGER_STD, MACD_FAST, MACD_SIGNAL, MACD_SLOW,
    MA_PERIODS, MAX_RECOMMENDATIONS_PER_TYPE, MIN_VOLUME_RATIO, RSI_OVERSOLD_SCREEN, RSI_PERIOD,
)
from reporting import generate_report

DAILY_DEMO_WARNING = (
    "SYNTHETIC DAILY REPORT / 合成数据日报示例。Not live market data or investment advice. "
    "不是实时行情、真实荐股或收益记录。"
)
REPORT_DATE = date(2024, 4, 19)
# amplitude, cycle length, phase. Deliberately illustrative, not fitted to a market.
FIXTURES = {
    "DEMO_A": ("虚构样本 A", 0.2, 10, 6),
    "DEMO_B": ("虚构样本 B", 0.2, 15, 2),
    "DEMO_C": ("虚构样本 C", 0.4, 5, 2),
    "DEMO_D": ("虚构样本 D", 0.2, 5, 0),
}


def synthetic_histories() -> Dict[str, pd.DataFrame]:
    """Return 80 ordinary weekdays, including exchange holidays, per fake symbol."""
    dates = pd.bdate_range("2024-01-01", periods=80, name="Date")
    t = np.arange(len(dates))
    return {
        code: pd.DataFrame({
            "Close": np.round(20 + amplitude * np.sin(2 * np.pi * (t + phase) / cycle), 2),
            "Volume": [1_000_000] * 79 + [2_500_000],
        }, index=dates)
        for code, (_, amplitude, cycle, phase) in FIXTURES.items()
    }


class _FixtureAnalyzer(StockAnalyzer):
    """Supply in-memory prices without changing the production analyzer."""

    def __init__(self, histories: Dict[str, pd.DataFrame]):
        super().__init__()
        self.analysis_date = REPORT_DATE
        self._histories = histories

    def fetch_stock_data(self, code: str, period: str = "2mo") -> pd.DataFrame:
        return self._histories[code].copy()


def _plain(value):
    """Convert NumPy scalars and stabilize display-level precision for JSON."""
    if isinstance(value, dict):
        return {key: _plain(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_plain(item) for item in value]
    if isinstance(value, np.generic):
        return _plain(value.item())
    if isinstance(value, float):
        return round(value, 10)
    return value


def _guide(report: str, english: bool) -> str:
    if english:
        intro = """# Daily research report example · synthetic data

[中文](README.md) | [English](README.en.md) | [Project](../../README.en.md)

This is the actual output of the existing indicator calculations, screening rules,
and text-report renderer, fed **fictional prices**. It is not a current market
report. The report retains the application's Chinese labels: 历史回测 = historical
review, 今日推荐 = rule-selected candidates, RSI = relative strength index, and
量比 = current volume / 20-observation average (including the current observation).

**Source:** deterministic formulas in [`qf/daily_demo.py`](../../qf/daily_demo.py).
Four invented symbols each have 80 ordinary weekday observations, **2024-01-01
through 2024-04-19**. The fixed report date is the last input date, not the run date.
Weekdays are not an exchange calendar. These paths were designed to illustrate the
categories; they do not validate the rules on real markets.

## Read the output

The original renderer calls candidates “recommendations”; here every symbol is
fictional. No historical recommendation database is read, so no hit rate or return
is invented. No LLM is called and no LLM commentary is fabricated. There is no
portfolio backtest or order execution in this example.
"""
        instructions = """## Reproduce after installation

From the repository root, after the [installation steps](../../README.en.md#quick-start):

```bash
stock-analyzer demo-daily --out reports/daily-demo
```

On Windows, use `.\\.venv\\Scripts\\stock-analyzer.exe` if the virtual environment
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
Tests regenerate and compare every file. See [`analyzer.py`](../../analyzer.py),
[`strategies.py`](../../strategies.py) and [`reporting.py`](../../reporting.py)
for the production calculations, rules and renderer used here.

The existing [portfolio demo](../demo/README.en.md) is a different workflow.
For real-data reports, use [`stock-analyzer run-daily`](../../README.en.md#real-data-workflows)
only after reviewing its data providers, settings and research limitations.
Offline success does not verify live services or the quality of trading signals.
"""
    else:
        intro = """# 研究日报样例 · 合成数据

[中文](README.md) | [English](README.en.md) | [项目首页](../../README.md)

这份日报由项目现有的**技术指标计算 → 规则筛选 → 文本日报生成器**实际执行得到，
输入是虚构行情，不是当前市场日报。不是手写推荐，也没有伪造模型解读。

**数据来源：** [`qf/daily_demo.py`](../../qf/daily_demo.py) 中的固定公式。
4 个虚构标的，各 80 条普通工作日观察，日期为 **2024-01-01 至 2024-04-19**。
报告日期固定为最后一条输入日期，不是运行当天。普通工作日不等于交易所交易日。
这些人工构造的价格用于展示分类，不用于证明筛选规则在真实市场有效。

## 直接看结果

原有日报生成器将候选股称为“推荐”，本页所有标的均为虚构。
没有读取历史推荐数据库，因此不编造准确率或收益；没有调用 LLM，因此不展示虚构的
“智能精选”。本样例不运行组合回测，也不会下单。量比采用当前成交量除以包含当日的
20 条观察平均成交量，和现有分析器保持一致。
"""
        instructions = """## 安装后复现

在仓库根目录完成[安装步骤](../../README.md#快速开始)后运行：

```bash
stock-analyzer demo-daily --out reports/daily-demo
```

Windows 未激活虚拟环境时，使用 `.\\.venv\\Scripts\\stock-analyzer.exe`。
用文本编辑器打开 `reports/daily-demo/daily-report.txt` 即可查看。
命令不请求行情、新闻或模型服务，也不写入日报数据库。重复运行会覆盖所选目录内
下列 5 个同名文件，需要保留旧结果时请换一个输出目录。

- [daily-report.txt](daily-report.txt)：带明确合成数据声明的实际日报输出。
- [inputs.csv](inputs.csv)：全部 320 条虚构收盘价和成交量输入。
- [analysis.json](analysis.json)：来源、日期、输入 SHA-256、参数、实际计算的
  指标、筛选分类和格式化候选记录。
- [README.md](README.md) 与 [README.en.md](README.en.md)：自动生成的中英文阅读说明。

更新仓库预览：`python scripts/update_daily_preview.py`。测试会重新生成并逐个核对文件。
所用生产代码见 [`analyzer.py`](../../analyzer.py)、[`strategies.py`](../../strategies.py)
和 [`reporting.py`](../../reporting.py)。

[组合回测演示](../demo/README.md)属于另一个流程。接入真实行情前请阅读
[`stock-analyzer run-daily` 的配置与研究边界](../../README.md#接入真实数据)。
离线演示通过不代表在线服务可用，也不能验证信号的投资价值。
"""
    guide = intro + "\n```text\n" + report.rstrip() + "\n```\n\n" + instructions
    # Repository links stay usable even when --out is outside the checkout.
    root = "https://github.com/oliverran/stock-daily-analyzer/blob/main/"
    return guide.replace("(../../", "(" + root).replace("(../demo/", "(" + root + "docs/demo/")


def run_daily_demo(out_dir: Path) -> Path:
    """Write five reproducible files without invoking the live daily workflow."""
    histories = synthetic_histories()
    analyzer = _FixtureAnalyzer(histories)
    stocks = []
    for code, (name, *_rest) in FIXTURES.items():
        result = analyzer.analyze_single_stock(code, name)
        if result is None:
            raise RuntimeError(f"Synthetic analysis failed for {code}")
        stocks.append(result)
    grouped = analyzer.generate_recommendations(stocks)
    recommendations = [
        analyzer.format_recommendation(stock, kind)
        for kind, selected in grouped.items() for stock in selected
    ]
    summary = {
        "date": REPORT_DATE.isoformat(), "total_scanned": len(stocks),
        "recommendations": grouped, "counts": {kind: len(selected) for kind, selected in grouped.items()},
    }
    input_frame = pd.concat([
        frame.reset_index().assign(Symbol=code)[["Date", "Symbol", "Close", "Volume"]]
        for code, frame in histories.items()
    ], ignore_index=True)
    input_csv = input_frame.to_csv(index=False, float_format="%.2f", lineterminator="\n")
    evidence = _plain({
        "demo": True, "data_source": "deterministic_synthetic", "warning": DAILY_DEMO_WARNING,
        "source_file": "qf/daily_demo.py", "report_date": REPORT_DATE.isoformat(),
        "input_start": "2024-01-01", "input_end": REPORT_DATE.isoformat(),
        "observations_per_symbol": 80, "symbols": list(FIXTURES),
        "input_sha256": hashlib.sha256(input_csv.encode("utf-8")).hexdigest(),
        "formula": "Close=round(20+amplitude*sin(2*pi*(t+phase)/cycle),2); t=0..79; "
                   "Volume=1000000 except final observation=2500000",
        "fixtures": {code: {"name": name, "amplitude": amplitude, "cycle": cycle, "phase": phase}
                     for code, (name, amplitude, cycle, phase) in FIXTURES.items()},
        "indicator_settings": {
            "rsi_period": RSI_PERIOD, "macd_fast": MACD_FAST, "macd_slow": MACD_SLOW,
            "macd_signal": MACD_SIGNAL, "ma_periods": MA_PERIODS,
            "bollinger_period": BOLLINGER_PERIOD, "bollinger_std": BOLLINGER_STD,
            "volume_average_observations": 20,
        },
        "screening_settings": {
            "rsi_oversold_screen": RSI_OVERSOLD_SCREEN, "min_volume_ratio": MIN_VOLUME_RATIO,
            "max_recommendations_per_type": MAX_RECOMMENDATIONS_PER_TYPE,
            "rules_source": "strategies.py (includes fixed trend and breakout thresholds)",
        },
        "historical_review": None, "llm_used": False, "analyzed_stocks": stocks,
        "summary": summary, "formatted_recommendations": recommendations,
    })
    report = (
        DAILY_DEMO_WARNING + "\n"
        "Source / 来源: qf/daily_demo.py; deterministic_synthetic; 2024-01-01..2024-04-19.\n"
        "日期为固定样本日期，不是今日行情。无历史收益记录，无 LLM 解读。\n\n"
        + generate_report(None, recommendations, summary, report_date=REPORT_DATE) + "\n"
    )
    outputs = {
        "inputs.csv": input_csv,
        "analysis.json": json.dumps(evidence, ensure_ascii=False, indent=2, allow_nan=False) + "\n",
        "daily-report.txt": report,
        "README.md": _guide(report, english=False),
        "README.en.md": _guide(report, english=True),
    }
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    for name, content in outputs.items():
        (out_dir / name).write_bytes(content.encode("utf-8"))
    return out_dir / "daily-report.txt"
