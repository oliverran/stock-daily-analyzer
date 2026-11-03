from typing import Optional, Dict

import pandas as pd

from qf.backtest import DailyBacktester
from qf.data import PriceFrame, PriceProvider
from qf.trading import TradingRules
from qf.universe import Stock


class DummyPriceProvider(PriceProvider):
    def __init__(self, panel: Dict[str, pd.DataFrame]):
        self._panel = panel

    def history(self, code: str, *, start: str, end: str, timeout_seconds: int) -> Optional[PriceFrame]:
        df = self._panel.get(code)
        if df is None:
            return None
        return PriceFrame(df=df)


def test_backtest_runs_smoke():
    dates = pd.date_range("2024-01-01", periods=10, freq="B")
    df1 = pd.DataFrame(
        {"Close": [100 + i for i in range(len(dates))], "Volume": [1000] * len(dates)},
        index=dates,
    )
    df2 = pd.DataFrame(
        {"Close": [100 + 0.5 * i for i in range(len(dates))], "Volume": [1000] * len(dates)},
        index=dates,
    )
    provider = DummyPriceProvider({"000001": df1, "000002": df2})
    bt = DailyBacktester(
        price_provider=provider,
        timeout_seconds=1,
        lookback_days=3,
        factor_weights={"momentum": 1.0},
        top_k=1,
        max_weight_per_name=1.0,
        commission_bps=0.0,
        slippage_bps=0.0,
        trading_rules=TradingRules(),
        max_drawdown_halt=None,
    )
    res = bt.run([Stock("000001", "a"), Stock("000002", "b")], start="2024-01-01", end="2024-01-31", rebalance="W", initial_cash=1_000_000.0)
    assert not res.equity.empty
    assert res.equity.iloc[0] == 1_000_000.0

