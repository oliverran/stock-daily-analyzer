from pathlib import Path
import json

import pytest

from qf.config import DataConfig, load_experiment_config


def test_load_experiment_config():
    cfg = load_experiment_config(Path("experiments/default_a_share_daily.json"))
    assert cfg.market == "A股"
    assert cfg.frequency == "日频"
    assert cfg.backtest.rebalance in ("W-FRI", "W", "weekly")


@pytest.mark.parametrize("provider", ["akshare", "yfianance", "", "YFinance", None, [], {}])
def test_reject_unsupported_price_provider(provider):
    with pytest.raises(ValueError, match="unsupported data.provider"):
        DataConfig(provider=provider, cache_dir="unused-cache")


def test_supported_price_provider():
    cfg = DataConfig(provider="yfinance", cache_dir="unused-cache")
    assert cfg.provider == "yfinance"


def test_bad_provider_stops_before_network_and_output(tmp_path, monkeypatch):
    from qf import experiment

    def unexpected(*args, **kwargs):
        pytest.fail("invalid provider must not fetch a universe or build a price provider")

    monkeypatch.setattr(experiment.AkshareAStockUniverseProvider, "get_universe", unexpected)
    monkeypatch.setattr(experiment, "YFinancePriceProvider", unexpected)
    raw = json.loads(Path("experiments/default_a_share_daily.json").read_text(encoding="utf-8"))
    raw["data"]["provider"] = "akshare"
    raw["data"]["cache_dir"] = str(tmp_path / "cache")
    path = tmp_path / "invalid.json"
    path.write_text(json.dumps(raw), encoding="utf-8")

    with pytest.raises(ValueError, match="supported value: 'yfinance'"):
        experiment.run_experiment(path, tmp_path / "output")
    assert not (tmp_path / "output").exists()
    assert not (tmp_path / "cache").exists()

