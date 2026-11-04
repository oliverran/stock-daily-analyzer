"""Deterministic, offline introduction to the existing research backtester."""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Optional

import pandas as pd

from qf.backtest import DailyBacktester
from qf.data import PriceFrame, PriceProvider
from qf.demo_report import write_demo_report
from qf.trading import TradingRules
from qf.universe import Stock


DEMO_WARNING = "Synthetic data only. Not historical market data or investment advice."


class SyntheticPriceProvider(PriceProvider):
    """Fixed fictional prices, without network calls, credentials, or a cache."""

    def __init__(self) -> None:
        dates = pd.bdate_range("2024-01-02", periods=60)
        self._panel = {}
        for code, base, drift, phase in (
            ("DEMO_A", 100.0, 0.15, 0),
            ("DEMO_B", 80.0, 0.08, 4),
            ("DEMO_C", 120.0, -0.03, 8),
        ):
            self._panel[code] = pd.DataFrame(
                {
                    "Close": [base + drift * i + ((i + phase) % 12 - 6) * 0.25 for i in range(len(dates))],
                    "Volume": [100_000 + ((i + phase) % 5) * 10_000 for i in range(len(dates))],
                },
                index=dates,
            )

    def history(self, code: str, *, start: str, end: str, timeout_seconds: int) -> Optional[PriceFrame]:
        df = self._panel.get(code)
        if df is None:
            return None
        return PriceFrame(df=df.loc[start:end].copy())


def run_demo(out_dir: Path) -> Path:
    """Write actual backtester outputs using synthetic inputs, never live data."""
    universe = [Stock(code, code) for code in ("DEMO_A", "DEMO_B", "DEMO_C")]
    # These are illustrative simulation settings, not current exchange rules or fees.
    trading_rules = TradingRules()
    settings = {
        "start": "2024-01-02",
        "end": "2024-03-25",
        "rebalance": "W-FRI",
        "initial_cash": 100_000.0,
    }
    engine_settings = {
        "timeout_seconds": 1,
        "lookback_days": 20,
        "factor_weights": {"momentum": 1.0},
        "top_k": 2,
        "max_weight_per_name": 0.5,
        "commission_bps": 1.0,
        "slippage_bps": 2.0,
        "max_drawdown_halt": None,
    }
    backtester = DailyBacktester(
        price_provider=SyntheticPriceProvider(),
        trading_rules=trading_rules,
        **engine_settings,
    )
    result = backtester.run(universe, **settings)

    out_dir.mkdir(parents=True, exist_ok=True)
    result.equity.rename_axis("Date").to_frame("equity").to_csv(out_dir / "equity.csv", encoding="utf-8")
    result.holdings.to_csv(out_dir / "holdings.csv", encoding="utf-8")
    summary = {
        "demo": True,
        "data_source": "deterministic_synthetic",
        "warning": DEMO_WARNING,
        "calendar": "Weekdays only; not an exchange trading calendar.",
        "observations": len(result.equity),
        "symbols": [stock.code for stock in universe],
        "config": {**settings, **engine_settings, "trading": asdict(trading_rules)},
        "metrics": asdict(result.metrics),
    }
    summary_path = out_dir / "summary.json"
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    write_demo_report(out_dir, result.equity, result.holdings, summary)
    return summary_path
