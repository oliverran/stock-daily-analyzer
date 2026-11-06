from datetime import date
from pathlib import Path
from typing import Dict, Optional, List, Any

from config import REPORT_DIR, BACKTEST_DAYS


def generate_report(
    backtest_result: Optional[Dict[str, Any]],
    recommendations: List[Dict[str, Any]],
    summary: Dict[str, Any],
    llm_picks: Optional[Dict[str, Dict[str, Any]]] = None,
    *,
    report_date: Optional[date] = None,
) -> str:
    """Render a report; callers may fix its date for reproducible research samples."""
    lines = [
        "=" * 60,
        f"股票分析日报 - {(report_date or date.today()).isoformat()}",
        "=" * 60,
        "",
    ]

    if backtest_result:
        lines.extend(
            [
                "【历史回测】",
                f"  验证{BACKTEST_DAYS}天前推荐: {backtest_result['total_recommendations']}只股票",
                f"  正确: {backtest_result['correct_count']}只 | 一般: {backtest_result['neutral_count']}只 | 错误: {backtest_result['wrong_count']}只",
                f"  准确率: {backtest_result['accuracy_rate']:.0%}",
                f"  平均收益: {backtest_result['avg_return']:+.2%}",
            ]
        )
        if backtest_result.get("best_pick"):
            lines.append(f"  最佳: {backtest_result['best_pick']} {backtest_result['best_return']:+.2%}")
        if backtest_result.get("worst_pick"):
            lines.append(f"  最差: {backtest_result['worst_pick']} {backtest_result['worst_return']:+.2%}")
        lines.append("")
    else:
        lines.extend(["【历史回测】", "  暂无历史数据可回测", ""])

    lines.append("【今日推荐】")
    lines.append(f"  扫描股票数: {summary.get('total_scanned', 0)}")
    lines.append("")

    for rec_type, stocks in summary.get("recommendations", {}).items():
        lines.append(f"  类型: {rec_type}")
        if stocks:
            for s in stocks:
                lines.append(
                    f"    - {s['name']}({s['code']}): ¥{s['price']:.2f} | RSI:{s['rsi']:.0f} | 量比:{s['vol_ratio']:.2f}"
                )
        else:
            lines.append("    (无符合条件标的)")
        lines.append("")

    if llm_picks:
        lines.append("【LLM智能精选】")
        for rec_type, pick in llm_picks.items():
            lines.append(f"  类型: {rec_type}")
            lines.append(f"    最值得买: {pick.get('name')}({pick.get('ticker')})")
            lines.append(f"    理由: {pick.get('reason')}")
            lines.append("")

    lines.extend(
        [
            "=" * 60,
            "风险提示: 以上分析仅供参考，不构成投资建议。股市有风险，投资需谨慎。",
            "=" * 60,
        ]
    )

    return "\n".join(lines)


def save_report(report: str) -> Path:
    report_file = REPORT_DIR / f"report_{date.today().isoformat()}.txt"
    with open(report_file, "w", encoding="utf-8") as f:
        f.write(report)
    return report_file

