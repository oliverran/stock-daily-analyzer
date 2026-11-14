from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Dict, Any, Tuple

from qf.backtest import DailyBacktester, BacktestResult
from qf.config import ExperimentConfig, load_experiment_config, ensure_dir
from qf.data import CachedPriceProvider, YFinancePriceProvider
from qf.trading import TradingRules
from qf.universe import AkshareAStockUniverseProvider


def _build_price_provider(cfg: ExperimentConfig):
    # DataConfig rejects unsupported providers before any run side effects.
    inner = YFinancePriceProvider()
    return CachedPriceProvider(inner, cache_dir=Path(cfg.data.cache_dir))


def run_experiment(config_path: Path, out_dir: Path) -> Tuple[ExperimentConfig, BacktestResult, Path]:
    cfg = load_experiment_config(config_path)
    out_dir = ensure_dir(out_dir / cfg.name)

    uni = AkshareAStockUniverseProvider(
        exclude_prefix=cfg.universe.exclude_prefix,
        include_prefix=cfg.universe.include_prefix,
        exclude_st=cfg.universe.exclude_st,
    ).get_universe(max_stocks=cfg.universe.max_stocks)

    prices = _build_price_provider(cfg)
    bt = DailyBacktester(
        price_provider=prices,
        timeout_seconds=cfg.data.timeout_seconds,
        lookback_days=cfg.factors.lookback_days,
        factor_weights=cfg.factors.weights,
        top_k=cfg.portfolio.top_k,
        max_weight_per_name=cfg.portfolio.max_weight_per_name,
        commission_bps=cfg.backtest.commission_bps,
        slippage_bps=cfg.backtest.slippage_bps,
        trading_rules=TradingRules(
            t_plus_one=cfg.trading.t_plus_one,
            limit_up=cfg.trading.limit_up,
            limit_down=cfg.trading.limit_down,
            stamp_duty_bps=cfg.trading.stamp_duty_bps,
            allow_buy_limit_up=cfg.trading.allow_buy_limit_up,
            allow_sell_limit_down=cfg.trading.allow_sell_limit_down,
        ),
        max_drawdown_halt=cfg.risk.max_drawdown_halt,
    )
    result = bt.run(
        uni,
        start=cfg.backtest.start,
        end=cfg.backtest.end,
        rebalance=cfg.backtest.rebalance,
        initial_cash=cfg.backtest.initial_cash,
    )

    equity_path = out_dir / "equity.csv"
    holdings_path = out_dir / "holdings.csv"
    summary_path = out_dir / "summary.json"

    result.equity.to_frame("equity").to_csv(equity_path, encoding="utf-8")
    result.holdings.to_csv(holdings_path, encoding="utf-8")

    summary: Dict[str, Any] = {
        "config": asdict(cfg),
        "metrics": asdict(result.metrics),
    }
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    return cfg, result, summary_path
