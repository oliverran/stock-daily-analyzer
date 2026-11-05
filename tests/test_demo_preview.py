import json
import re
import socket
from pathlib import Path

import pandas as pd
import pytest

from scripts.update_demo_preview import update_preview


@pytest.mark.parametrize("language", ["zh", "en"])
def test_github_preview_is_reproducible_offline_and_accurate(tmp_path, monkeypatch, language):
    def unexpected_network(*args, **kwargs):
        raise AssertionError("Preview regeneration must stay offline")

    monkeypatch.setattr(socket.socket, "connect", unexpected_network)
    monkeypatch.setattr(socket.socket, "connect_ex", unexpected_network)
    destination = tmp_path / "docs" / "demo"
    update_preview(destination)
    filename = "README.md" if language == "zh" else "README.en.md"
    markdown = (destination / filename).read_text(encoding="utf-8")
    summary = json.loads((destination / "summary.json").read_text(encoding="utf-8"))
    equity = pd.read_csv(destination / "equity.csv", index_col="Date")["equity"]
    holdings = pd.read_csv(destination / "holdings.csv", index_col="Date")

    if language == "zh":
        assert "不是真实市场业绩" in markdown
        assert "GitHub 显示源码" in markdown
        assert "首次安装依赖需要联网" in markdown
    else:
        assert "not historical market performance or investment advice" in markdown
        assert "GitHub shows source" in markdown
        assert "installing dependencies initially requires internet access" in markdown
    assert "[中文](README.md) | [English](README.en.md)" in markdown
    assert equity.index[0] in markdown and equity.index[-1] in markdown
    assert str(summary["observations"]) in markdown
    assert f"{summary['config']['initial_cash']:,.2f}" in markdown
    assert f"{equity.iloc[-1]:,.2f}" in markdown
    for key in ("total_return", "cagr", "max_drawdown"):
        assert f"{summary['metrics'][key]:.2%}" in markdown
    assert f"{summary['metrics']['sharpe']:.2f}" in markdown
    for symbol, weight in holdings.iloc[-1].items():
        assert f"| `{symbol}` | {weight:.2%} |" in markdown
    for output_name in ("equity.csv", "holdings.csv", "summary.json", "report.html", "equity.svg"):
        assert f"]({output_name})" in markdown
        assert (destination / output_name).is_file()

    root = Path(__file__).resolve().parents[1]
    committed = root / "docs" / "demo" / filename
    assert markdown == committed.read_text(encoding="utf-8")
    for link in re.findall(r"\]\(([^)]+)\)", markdown):
        if not link.startswith("https:"):
            assert (committed.parent / link.split("#")[0]).resolve().is_file()
    assert "[直接查看演示，无需安装](docs/demo/README.md)" in (root / "README.md").read_text(encoding="utf-8")
    assert "[View the demo without installing](docs/demo/README.en.md)" in (root / "README.en.md").read_text(encoding="utf-8")
    for root_readme in ("README.md", "README.en.md"):
        assert "[中文](README.md) | [English](README.en.md)" in (root / root_readme).read_text(encoding="utf-8")

    update_preview(destination)
    assert markdown == (destination / filename).read_text(encoding="utf-8")
