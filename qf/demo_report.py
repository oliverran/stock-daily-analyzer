"""Static, dependency-free presentation of the explicitly synthetic demo."""

from __future__ import annotations

import json
import math
from html import escape
from pathlib import Path
from typing import Any

import pandas as pd


def render_equity_svg(equity: pd.Series, *, link_observations: bool = False) -> str:
    """Render every observation as an accessible, self-contained SVG chart."""
    values = [float(value) for value in equity]
    if not values or any(not math.isfinite(value) or value <= 0 for value in values):
        raise ValueError("Demo equity must contain finite, positive values")
    dates = [escape(str(value.date() if hasattr(value, "date") else value)) for value in equity.index]
    low, high = min(values), max(values)
    padding = max((high - low) * 0.15, high * 0.001)
    low, high = low - padding, high + padding
    left, right, top, bottom = 100, 920, 112, 346
    points = " ".join(
        f"{left + (right - left) * i / max(len(values) - 1, 1):.2f},"
        f"{bottom - (value - low) / (high - low) * (bottom - top):.2f}"
        for i, value in enumerate(values)
    )
    grid = []
    links = ""
    if link_observations:
        links = "".join(
            f'<a href="#day-{i}" aria-label="查看 {date} 的模拟净值与持仓">'
            f'<circle cx="{point.split(",")[0]}" cy="{point.split(",")[1]}" r="5" '
            f'fill="#077d86" stroke="white"><title>{date}: {value:,.2f}</title></circle></a>'
            for i, (date, value, point) in enumerate(zip(dates, values, points.split()))
        )
    for i in range(5):
        y = top + (bottom - top) * i / 4
        value = high - (high - low) * i / 4
        grid.append(
            f'<line x1="{left}" x2="{right}" y1="{y}" y2="{y}" stroke="#dbe4ec"/>'
            f'<text x="86" y="{y + 5}" text-anchor="end" fill="#526075" font-size="14">{value:,.0f}</text>'
        )
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 960 440" role="img" aria-labelledby="chart-title chart-description">
<title id="chart-title">Synthetic demo equity | 合成数据演示净值</title>
<desc id="chart-description">{len(values)} weekday observations, {dates[0]} to {dates[-1]}. Starting value {values[0]:,.2f}; final value {values[-1]:,.2f}. Fictional prices, not historical market performance. Full data in equity.csv.</desc>
<rect width="960" height="440" rx="16" fill="#f8fafc"/>
<g font-family="system-ui, sans-serif">
<text x="36" y="40" font-size="22" font-weight="700" fill="#13283f">Synthetic demo equity</text>
<text x="36" y="67" font-size="15" fill="#8a4110">FICTIONAL DATA · Not historical performance or investment advice</text>
<text x="100" y="97" font-size="13" fill="#526075">Simulation units · y-axis zoomed to observed range</text>
{''.join(grid)}
<polyline data-series="equity" points="{points}" fill="none" stroke="#077d86" stroke-width="3" stroke-linejoin="round"/>
{links}
<text x="{left}" y="377" font-size="14" fill="#526075">{dates[0]}</text>
<text x="{right}" y="377" text-anchor="end" font-size="14" fill="#526075">{dates[-1]}</text>
<text x="36" y="414" font-size="14" fill="#526075">{len(values)} weekday observations · Fixed synthetic prices · No API key or market-data requests</text>
</g>
</svg>
'''


def write_demo_report(out_dir: Path, equity: pd.Series, holdings: pd.DataFrame, summary: dict[str, Any]) -> None:
    """Write HTML and SVG beside the demo's CSV/JSON, without scripts or URLs."""
    if summary.get("demo") is not True or summary.get("data_source") != "deterministic_synthetic":
        raise ValueError("This report is only for explicitly labelled synthetic demo data")
    if not equity.index.equals(holdings.index) or len(equity) != summary.get("observations"):
        raise ValueError("Demo observations and holdings must match equity dates")
    if holdings.empty or any(not math.isfinite(float(value)) for value in holdings.to_numpy().flat):
        raise ValueError("Demo holdings must contain finite values")
    chart = render_equity_svg(equity)
    linked_chart = render_equity_svg(equity, link_observations=True)
    # A linked chart is a group, not a single image whose descendants may be hidden
    # from assistive technology. The downloadable SVG stays self-contained.
    linked_chart = linked_chart.replace('role="img"', 'role="group"')
    observations = []
    for i, (date, value) in enumerate(equity.items()):
        label = escape(str(date.date() if hasattr(date, "date") else date))
        rows = "".join(
            f'<tr><th scope="row">{escape(str(symbol))}</th><td>{float(weight):.2%}</td></tr>'
            for symbol, weight in holdings.iloc[i].items()
        )
        observations.append(
            f'<article class="observation" id="day-{i}" tabindex="-1" aria-labelledby="day-title-{i}">'
            f'<h3 id="day-title-{i}">{label} · 模拟净值 {float(value):,.2f}</h3>'
            f'<table><caption>当日记录权重 · __CASH__ 表示现金</caption>'
            f'<thead><tr><th scope="col">标的</th><th scope="col">权重</th></tr></thead>'
            f'<tbody>{rows}</tbody></table><p><a href="#chart">返回图表</a> · '
            f'<a href="#daily-data">选择其他日期</a></p></article>'
        )
    metrics = summary["metrics"]
    if any(not math.isfinite(float(metrics[name])) for name in ("total_return", "cagr", "sharpe", "max_drawdown")):
        raise ValueError("Demo metrics must be finite")
    cards = "".join(
        f'<article class="metric"><span>{label}</span><strong>{float(metrics[key]):{fmt}}</strong></article>'
        for label, key, fmt in (
            ("模拟累计收益 / Total return", "total_return", ".2%"),
            ("模拟最大回撤 / Max drawdown", "max_drawdown", ".2%"),
            ("模拟年化收益 / CAGR", "cagr", ".2%"),
            ("模拟 Sharpe", "sharpe", ".2f"),
        )
    )
    last_weights = "".join(
        f'<tr><th scope="row">{escape(str(symbol))}</th><td>{float(weight):.2%}</td></tr>'
        for symbol, weight in holdings.iloc[-1].items()
    )
    daily_rows = "".join(
        f'<tr><th scope="row"><a href="#day-{i}">{escape(str(date.date() if hasattr(date, "date") else date))}</a></th>'
        f'<td>{float(value):,.2f}</td></tr>'
        for i, (date, value) in enumerate(equity.items())
    )
    config_json = escape(json.dumps(summary["config"], ensure_ascii=False, indent=2, allow_nan=False))
    symbols = escape(", ".join(str(symbol) for symbol in summary["symbols"]))
    start = escape(str(equity.index[0].date() if hasattr(equity.index[0], "date") else equity.index[0]))
    end = escape(str(equity.index[-1].date() if hasattr(equity.index[-1], "date") else equity.index[-1]))
    warning = escape(str(summary["warning"]))
    calendar = escape(str(summary["calendar"]))
    html = f'''<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'; base-uri 'none'; form-action 'none'">
<meta name="description" content="Stock Daily Analyzer 合成数据演示：由离线回测引擎生成的净值、模拟指标、持仓与参数。无需 API Key；不是真实市场业绩，不构成投资建议。">
<meta property="og:title" content="合成数据研究演示 | Stock Daily Analyzer">
<meta property="og:description" content="Synthetic data only: reproducible offline backtest, equity chart, holdings and parameters. Not historical performance or investment advice.">
<meta property="og:type" content="website">
<title>合成数据研究演示 | Stock Daily Analyzer</title>
<style>
* {{ box-sizing: border-box; }}
body {{ margin: 0; background: #eef3f6; color: #13283f; font: 16px/1.65 system-ui, sans-serif; }}
main {{ max-width: 1120px; margin: auto; padding: 40px 24px; }}
header {{ margin-bottom: 24px; }}
.eyebrow {{ color: #077078; font-size: 13px; font-weight: 750; letter-spacing: .09em; }}
h1 {{ font-size: clamp(28px, 5vw, 44px); line-height: 1.2; margin: 12px 0; }}
h2 {{ font-size: 21px; margin: 0 0 12px; }}
p {{ margin: 10px 0; }}
.subtitle, .muted {{ color: #526075; }}
.warning {{ border: 1px solid #e7b27a; background: #fff5e9; color: #713b0e; border-radius: 12px; padding: 16px 20px; }}
.warning strong {{ display: block; }}
.grid {{ display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 12px; margin: 20px 0; }}
.metric, .panel {{ background: white; border: 1px solid #dbe4ec; border-radius: 14px; padding: 20px; }}
.metric span {{ color: #526075; font-size: 13px; display: block; }}
.metric strong {{ font-size: 28px; display: block; margin-top: 8px; }}
.panel {{ margin-top: 20px; }}
.columns {{ display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }}
svg {{ width: 100%; height: auto; display: block; }}
figure {{ margin: 20px 0 0; }}
figcaption {{ margin: 12px 0; color: #526075; font-size: 14px; }}
nav {{ display: flex; flex-wrap: wrap; gap: 10px; margin-top: 20px; }}
a {{ color: #006c75; text-underline-offset: 3px; }}
nav a {{ padding: 9px 15px; border-radius: 8px; background: #e3f2f2; text-decoration: none; }}
a:focus-visible, summary:focus-visible {{ outline: 3px solid #b46b20; outline-offset: 4px; }}
table {{ width: 100%; border-collapse: collapse; font-variant-numeric: tabular-nums; }}
th, td {{ text-align: left; padding: 9px 0; border-bottom: 1px solid #e5ebf0; overflow-wrap: anywhere; }}
td {{ text-align: right; }}
caption {{ text-align: left; color: #526075; padding-bottom: 10px; }}
pre {{ background: #f3f6f9; padding: 16px; border-radius: 10px; overflow-x: auto; font-size: 13px; }}
code {{ overflow-wrap: anywhere; }}
summary {{ cursor: pointer; font-weight: 650; }}
.observation {{ display: none; scroll-margin-top: 16px; }}
.observation:target {{ display: block; outline: 3px solid #077d86; outline-offset: 8px; }}
svg a:focus-visible circle, svg a:hover circle {{ fill: #b46b20; stroke-width: 3; }}
footer {{ padding-top: 24px; font-size: 14px; color: #526075; }}
@media (max-width: 720px) {{ .grid, .columns {{ grid-template-columns: 1fr 1fr; }} main {{ padding: 24px 16px; }} .columns {{ grid-template-columns: 1fr; }} .metric {{ padding: 14px; }} .metric strong {{ font-size: 24px; }} }}
@media print {{ body {{ background: white; }} main {{ padding: 0; }} .panel, .metric, figure {{ break-inside: avoid; }} }}
</style>
</head>
<body><main>
<header><p class="eyebrow">STOCK DAILY ANALYZER · OFFLINE DEMO</p>
<h1>让第一次运行，看得见结果。</h1>
<p class="subtitle">真实回测引擎，固定的虚构价格。无需 API Key，打开本地文件即可查看。</p>
</header>
<aside class="warning"><strong>合成数据演示，不是真实市场业绩，也不构成投资建议。</strong>{warning}</aside>
<nav aria-label="演示数据文件"><a href="equity.csv">净值 CSV</a><a href="holdings.csv">持仓 CSV</a><a href="summary.json">参数与指标 JSON</a><a href="equity.svg">独立图表 SVG</a></nav>
<section aria-labelledby="overview"><h2 id="overview" style="margin-top:24px">模拟结果 / Simulation only</h2>
<p class="muted">{start} 至 {end} · {len(equity)} 条工作日观察 · {symbols}</p>
<div class="grid">{cards}</div>
<p class="muted">这些指标只演示输出格式；短期合成样本的年化值和 Sharpe 不代表可实现收益。</p>
<figure id="chart">{linked_chart}<figcaption>点击图中圆点查看对应日期的模拟净值与持仓；手机或键盘用户也可使用下方日期表。逐点绘制 equity.csv 的全部观察值。纵轴为模拟资金单位，已缩放到观察区间。历史数据不足因子回看窗口时保持现金。</figcaption></figure>
</section>
<section class="panel" aria-labelledby="observation-title"><h2 id="observation-title">按日期查看模拟持仓</h2>
<p>在图表圆点或<a href="#daily-data">日期表</a>中选择一天。权重来自 holdings.csv 的同一行，是引擎当日调仓及成本处理后的记录，不代表当日收益的贡献权重、交易信号或成交原因。</p>
{''.join(observations)}</section>
<div class="columns">
<section class="panel"><h2>最后一天的组合权重</h2><table><caption>{end} · __CASH__ 表示现金</caption><thead><tr><th scope="col">标的</th><th scope="col" style="text-align:right">权重</th></tr></thead><tbody>{last_weights}</tbody></table></section>
<section class="panel"><h2>下一步可以做什么</h2><ol><li>打开 CSV，核对净值与每日持仓。</li><li>重新运行 <code>stock-analyzer demo --out reports/another-demo</code>，比较输出。</li><li>回到项目 README，了解真实数据接入与研究边界。</li></ol><p>本页没有脚本、CDN、字体下载或数据上传。CSV / JSON 链接指向同目录文件。</p></section>
</div>
<section class="panel"><h2>如何阅读这个演示</h2><p>数据是 DEMO_A、DEMO_B、DEMO_C 的固定价格公式，调用项目的 DailyBacktester，包含示例佣金、滑点和交易约束。它不验证行情接口、新闻或 LLM 服务。</p><p>{calendar} 使用普通工作日，并非交易所日历。交易约束是简化示例，不应用于推断实盘表现。</p><details><summary>查看完整模拟参数</summary><pre>{config_json}</pre></details></section>
<section class="panel" id="daily-data"><details open><summary>查看全部 {len(equity)} 条净值数据（点击日期查看持仓）</summary><table><caption>图表的文字替代。显示值保留两位小数，完整精度见 equity.csv。</caption><thead><tr><th scope="col">日期</th><th scope="col" style="text-align:right">模拟净值</th></tr></thead><tbody>{daily_rows}</tbody></table></details></section>
<footer>Stock Daily Analyzer · 仅供学习和研究 · Synthetic data only. Not investment advice.</footer>
</main></body></html>
'''
    (out_dir / "equity.svg").write_text(chart, encoding="utf-8")
    (out_dir / "report.html").write_text(html, encoding="utf-8")
