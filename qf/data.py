from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import pandas as pd
import yfinance as yf

from qf.config import ensure_dir
from qf.symbols import to_yfinance_ticker


@dataclass(frozen=True)
class PriceFrame:
    df: pd.DataFrame


class PriceProvider:
    def history(self, code: str, *, start: str, end: str, timeout_seconds: int) -> Optional[PriceFrame]:
        raise NotImplementedError


class YFinancePriceProvider(PriceProvider):
    def history(self, code: str, *, start: str, end: str, timeout_seconds: int) -> Optional[PriceFrame]:
        ticker = to_yfinance_ticker(code)
        try:
            df = yf.download(ticker, start=start, end=end, progress=False, timeout=timeout_seconds)
        except TypeError:
            df = yf.download(ticker, start=start, end=end, progress=False)
        except Exception:
            return None
        if df is None or df.empty:
            return None
        df = df.copy()
        if "Date" not in df.columns:
            df.index = pd.to_datetime(df.index)
        return PriceFrame(df=df)


class CachedPriceProvider(PriceProvider):
    def __init__(self, inner: PriceProvider, cache_dir: Path):
        self._inner = inner
        self._cache_dir = ensure_dir(cache_dir)

    def _path(self, code: str, start: str, end: str) -> Path:
        safe = code.replace(".", "_")
        return self._cache_dir / f"{safe}_{start}_{end}.csv"

    def history(self, code: str, *, start: str, end: str, timeout_seconds: int) -> Optional[PriceFrame]:
        p = self._path(code, start, end)
        if p.exists():
            try:
                df = pd.read_csv(p, parse_dates=["Date"])
                df = df.set_index("Date")
                return PriceFrame(df=df)
            except Exception:
                pass
        pf = self._inner.history(code, start=start, end=end, timeout_seconds=timeout_seconds)
        if pf is None:
            return None
        df = pf.df.copy()
        df.index = pd.to_datetime(df.index)
        df.index.name = "Date"
        out = df.reset_index()
        try:
            out.to_csv(p, index=False, encoding="utf-8")
        except Exception:
            pass
        return PriceFrame(df=df)
