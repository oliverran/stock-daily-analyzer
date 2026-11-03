from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class PerfMetrics:
    total_return: float
    cagr: float
    sharpe: float
    max_drawdown: float


def max_drawdown(equity: pd.Series) -> float:
    if equity.empty:
        return 0.0
    peak = equity.cummax()
    dd = (equity / peak) - 1.0
    return float(dd.min())


def sharpe_ratio(daily_returns: pd.Series, trading_days: int = 252) -> float:
    r = daily_returns.dropna()
    if r.empty:
        return 0.0
    mu = r.mean()
    sd = r.std()
    if sd == 0 or np.isnan(sd):
        return 0.0
    return float((mu / sd) * np.sqrt(trading_days))


def cagr(equity: pd.Series, trading_days: int = 252) -> float:
    if equity.empty:
        return 0.0
    total = float(equity.iloc[-1] / equity.iloc[0] - 1.0)
    years = len(equity) / trading_days
    if years <= 0:
        return 0.0
    return float((1.0 + total) ** (1.0 / years) - 1.0)


def compute_metrics(equity: pd.Series) -> PerfMetrics:
    if equity.empty:
        return PerfMetrics(total_return=0.0, cagr=0.0, sharpe=0.0, max_drawdown=0.0)
    rets = equity.pct_change().fillna(0.0)
    return PerfMetrics(
        total_return=float(equity.iloc[-1] / equity.iloc[0] - 1.0),
        cagr=cagr(equity),
        sharpe=sharpe_ratio(rets),
        max_drawdown=max_drawdown(equity),
    )

