from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List

import pandas as pd


@dataclass(frozen=True)
class PortfolioSelection:
    weights: Dict[str, float]


def select_top_k(scores: pd.Series, *, top_k: int) -> List[str]:
    s = scores.dropna().sort_values(ascending=False)
    return list(s.head(top_k).index)


def build_equal_weight_portfolio(
    selected: List[str],
    *,
    max_weight_per_name: float,
) -> PortfolioSelection:
    if not selected:
        return PortfolioSelection(weights={})
    n = len(selected)
    w = 1.0 / n
    w = min(w, max_weight_per_name)
    weights = {c: w for c in selected}
    total = sum(weights.values())
    if total > 0:
        weights = {k: v / total for k, v in weights.items()}
    return PortfolioSelection(weights=weights)


def turnover(prev: Dict[str, float], nxt: Dict[str, float]) -> float:
    keys = set(prev.keys()) | set(nxt.keys())
    return float(sum(abs(nxt.get(k, 0.0) - prev.get(k, 0.0)) for k in keys))

