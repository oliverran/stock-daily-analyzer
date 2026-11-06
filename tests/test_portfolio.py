import pandas as pd
import pytest

from qf.backtest import DailyBacktester
from qf.demo import SyntheticPriceProvider
from qf.portfolio import build_equal_weight_portfolio
from qf.trading import TradingRules, ensure_cash
from qf.universe import Stock


def test_equal_weight_with_cap():
    sel = ["a", "b", "c", "d", "e", "f", "g", "h"]
    p = build_equal_weight_portfolio(sel, max_weight_per_name=0.15)
    assert abs(sum(p.weights.values()) - 1.0) < 1e-9
    assert max(p.weights.values()) <= 0.15 + 1e-9


@pytest.mark.parametrize("count,cap", [(1, 0.5), (2, 0.2), (3, 0.1), (8, 0.05)])
def test_binding_weight_cap_leaves_the_balance_for_cash(count, cap):
    selected = [str(i) for i in range(count)]
    selection = build_equal_weight_portfolio(selected, max_weight_per_name=cap)
    assert selection.weights == {code: cap for code in selected}
    weights = ensure_cash(selection.weights)
    assert weights["__CASH__"] == pytest.approx(1.0 - count * cap)
    assert sum(weights.values()) == pytest.approx(1.0)


def test_weight_cap_preserves_empty_and_nonbinding_portfolios():
    assert build_equal_weight_portfolio([], max_weight_per_name=0.5).weights == {}
    assert build_equal_weight_portfolio(["a", "b"], max_weight_per_name=0.8).weights == {"a": 0.5, "b": 0.5}


def test_backtester_keeps_cash_when_one_selected_symbol_hits_the_cap():
    engine = DailyBacktester(
        price_provider=SyntheticPriceProvider(),
        timeout_seconds=1,
        lookback_days=20,
        factor_weights={"momentum": 1.0},
        top_k=1,
        max_weight_per_name=0.5,
        commission_bps=1.0,
        slippage_bps=2.0,
        trading_rules=TradingRules(),
        max_drawdown_halt=None,
    )
    result = engine.run(
        [Stock(code, code) for code in ("DEMO_A", "DEMO_B", "DEMO_C")],
        start="2024-01-02", end="2024-03-25", rebalance="W-FRI", initial_cash=100_000.0,
    )
    assert len(result.equity) == 60
    assert result.holdings.drop(columns="__CASH__").max().max() == pytest.approx(0.5)
    assert (result.holdings["__CASH__"] >= 0.5 - 1e-9).all()
    pd.testing.assert_series_equal(
        result.holdings.sum(axis=1),
        pd.Series(1.0, index=result.holdings.index),
    )

