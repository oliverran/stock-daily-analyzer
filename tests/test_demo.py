import json
import socket
import sys

import pandas as pd
import pytest

from qf import cli
from qf.data import YFinancePriceProvider
from qf.demo import SyntheticPriceProvider, run_demo
from qf.universe import AkshareAStockUniverseProvider


@pytest.fixture(autouse=True)
def no_external_services(monkeypatch):
    def unexpected_call(*args, **kwargs):
        pytest.fail("The offline demo attempted to access an external service")

    monkeypatch.setattr(socket.socket, "connect", unexpected_call)
    monkeypatch.setattr(socket.socket, "connect_ex", unexpected_call)
    monkeypatch.setattr(YFinancePriceProvider, "history", unexpected_call)
    monkeypatch.setattr(AkshareAStockUniverseProvider, "get_universe", unexpected_call)
    for name in ("ARK_API_KEY", "ARK_MODEL_ID", "VOLC_API_KEY", "VOLC_MODEL_ID"):
        monkeypatch.delenv(name, raising=False)


def test_demo_writes_labelled_outputs_and_holds_fictional_symbols(tmp_path):
    summary_path = run_demo(tmp_path / "demo")
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    assert summary["demo"] is True
    assert summary["data_source"] == "deterministic_synthetic"
    assert "Not historical market data" in summary["warning"]
    assert summary["observations"] == 60
    assert summary["symbols"] == ["DEMO_A", "DEMO_B", "DEMO_C"]
    assert set(summary["metrics"]) == {"total_return", "cagr", "sharpe", "max_drawdown"}

    equity = pd.read_csv(summary_path.parent / "equity.csv", index_col="Date")
    holdings = pd.read_csv(summary_path.parent / "holdings.csv", index_col="Date")
    assert len(equity) == len(holdings) == 60
    assert equity.iloc[0, 0] == summary["config"]["initial_cash"]
    assert equity["equity"].nunique() > 1
    assert holdings["__CASH__"].iloc[0] == 1.0
    assert (holdings["__CASH__"] < 1.0).any()
    assert holdings.drop(columns="__CASH__").max().max() <= 0.5
    assert (holdings.sum(axis=1) - 1.0).abs().max() < 1e-9
    assert set(holdings.columns) <= {"__CASH__", *summary["symbols"]}


def test_demo_is_repeatable(tmp_path):
    first = run_demo(tmp_path / "first").parent
    second = run_demo(tmp_path / "second").parent
    for name in ("equity.csv", "holdings.csv", "summary.json"):
        assert (first / name).read_bytes() == (second / name).read_bytes()
    before = (first / "summary.json").read_bytes()
    run_demo(first)
    assert (first / "summary.json").read_bytes() == before


@pytest.mark.parametrize("custom_out", [False, True])
def test_demo_cli_without_credentials(tmp_path, monkeypatch, capsys, custom_out):
    monkeypatch.chdir(tmp_path)
    out = tmp_path / "custom output" if custom_out else tmp_path / "reports" / "demo"
    argv = ["stock-analyzer", "demo"]
    if custom_out:
        argv.extend(["--out", str(out)])
    monkeypatch.setattr(sys, "argv", argv)
    assert cli.main() == 0
    output = capsys.readouterr().out
    assert "Synthetic data only" in output
    assert "3 fictional symbols, 60 weekday observations" in output
    assert (out / "summary.json").is_file()


def test_synthetic_provider_honors_dates_and_does_not_expose_mutable_data():
    provider = SyntheticPriceProvider()
    prices = provider.history("DEMO_A", start="2024-02-01", end="2024-02-05", timeout_seconds=1)
    assert prices.df.index.strftime("%Y-%m-%d").tolist() == ["2024-02-01", "2024-02-02", "2024-02-05"]
    original = prices.df.iloc[0, 0]
    prices.df.iloc[0, 0] = -1
    again = provider.history("DEMO_A", start="2024-02-01", end="2024-02-05", timeout_seconds=1)
    assert again.df.iloc[0, 0] == original
    assert provider.history("UNKNOWN", start="2024-01-01", end="2024-12-31", timeout_seconds=1) is None
