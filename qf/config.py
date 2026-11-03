from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Any


@dataclass(frozen=True)
class UniverseConfig:
    exclude_prefix: List[str]
    include_prefix: Optional[List[str]] = None
    exclude_st: bool = True
    max_stocks: Optional[int] = None


@dataclass(frozen=True)
class DataConfig:
    provider: str
    cache_dir: str
    timeout_seconds: int = 10


@dataclass(frozen=True)
class FactorConfig:
    lookback_days: int
    weights: Dict[str, float]


@dataclass(frozen=True)
class PortfolioConfig:
    top_k: int
    max_weight_per_name: float


@dataclass(frozen=True)
class RiskConfig:
    max_drawdown_halt: Optional[float] = None


@dataclass(frozen=True)
class TradingConfig:
    t_plus_one: bool = True
    limit_up: float = 0.099
    limit_down: float = -0.099
    stamp_duty_bps: float = 10.0
    allow_buy_limit_up: bool = False
    allow_sell_limit_down: bool = False


@dataclass(frozen=True)
class BacktestConfig:
    start: str
    end: str
    rebalance: str
    commission_bps: float = 1.0
    slippage_bps: float = 2.0
    initial_cash: float = 1_000_000.0


@dataclass(frozen=True)
class ExperimentConfig:
    name: str
    market: str
    frequency: str
    universe: UniverseConfig
    data: DataConfig
    factors: FactorConfig
    portfolio: PortfolioConfig
    risk: RiskConfig
    trading: TradingConfig
    backtest: BacktestConfig
    seed: int = 42


def _require(d: Dict[str, Any], k: str) -> Any:
    if k not in d:
        raise ValueError(f"missing config field: {k}")
    return d[k]


def load_experiment_config(path: Path) -> ExperimentConfig:
    raw = json.loads(path.read_text(encoding="utf-8"))
    universe_raw = _require(raw, "universe")
    data_raw = _require(raw, "data")
    factors_raw = _require(raw, "factors")
    portfolio_raw = _require(raw, "portfolio")
    risk_raw = raw.get("risk") or {}
    trading_raw = raw.get("trading") or {}
    backtest_raw = _require(raw, "backtest")

    return ExperimentConfig(
        name=_require(raw, "name"),
        market=_require(raw, "market"),
        frequency=_require(raw, "frequency"),
        universe=UniverseConfig(
            exclude_prefix=list(_require(universe_raw, "exclude_prefix")),
            include_prefix=universe_raw.get("include_prefix"),
            exclude_st=bool(universe_raw.get("exclude_st", True)),
            max_stocks=universe_raw.get("max_stocks"),
        ),
        data=DataConfig(
            provider=_require(data_raw, "provider"),
            cache_dir=_require(data_raw, "cache_dir"),
            timeout_seconds=int(data_raw.get("timeout_seconds", 10)),
        ),
        factors=FactorConfig(
            lookback_days=int(_require(factors_raw, "lookback_days")),
            weights=dict(_require(factors_raw, "weights")),
        ),
        portfolio=PortfolioConfig(
            top_k=int(_require(portfolio_raw, "top_k")),
            max_weight_per_name=float(_require(portfolio_raw, "max_weight_per_name")),
        ),
        risk=RiskConfig(max_drawdown_halt=risk_raw.get("max_drawdown_halt")),
        trading=TradingConfig(
            t_plus_one=bool(trading_raw.get("t_plus_one", True)),
            limit_up=float(trading_raw.get("limit_up", 0.099)),
            limit_down=float(trading_raw.get("limit_down", -0.099)),
            stamp_duty_bps=float(trading_raw.get("stamp_duty_bps", 10.0)),
            allow_buy_limit_up=bool(trading_raw.get("allow_buy_limit_up", False)),
            allow_sell_limit_down=bool(trading_raw.get("allow_sell_limit_down", False)),
        ),
        backtest=BacktestConfig(
            start=_require(backtest_raw, "start"),
            end=_require(backtest_raw, "end"),
            rebalance=_require(backtest_raw, "rebalance"),
            commission_bps=float(backtest_raw.get("commission_bps", 1.0)),
            slippage_bps=float(backtest_raw.get("slippage_bps", 2.0)),
            initial_cash=float(backtest_raw.get("initial_cash", 1_000_000.0)),
        ),
        seed=int(raw.get("seed", 42)),
    )


def ensure_dir(p: Path) -> Path:
    p.mkdir(parents=True, exist_ok=True)
    return p
