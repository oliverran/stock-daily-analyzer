from datetime import date
import hashlib
import json
from pathlib import Path
import re
import socket
import sys

import pandas as pd
import pytest
import requests
from curl_cffi import requests as curl_requests

from analyzer import StockAnalyzer
from qf import cli
from qf.daily_demo import REPORT_DATE, _FixtureAnalyzer, run_daily_demo, synthetic_histories
from reporting import generate_report

ROOT = Path(__file__).resolve().parents[1]
FILES = {"inputs.csv", "analysis.json", "daily-report.txt", "README.md", "README.en.md"}


@pytest.fixture(autouse=True)
def offline_only(monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("The daily demo attempted a live service or production workflow")

    monkeypatch.setattr(socket.socket, "connect", forbidden)
    monkeypatch.setattr(socket.socket, "connect_ex", forbidden)
    monkeypatch.setattr(requests.sessions.Session, "request", forbidden)
    monkeypatch.setattr(curl_requests.Session, "request", forbidden)
    for method in ("fetch_stock_data", "get_all_stocks", "scan_market"):
        monkeypatch.setattr(StockAnalyzer, method, forbidden)
    for module_name, names in {
        "database": ("init_database", "save_recommendations", "get_overall_accuracy"),
        "backtester": ("run_backtest",),
        "llm": ("select_top_picks",),
        "notifier": ("send_analysis_complete_notification", "send_error_notification"),
    }.items():
        module = __import__(module_name)
        for name in names:
            monkeypatch.setattr(module, name, forbidden)


def test_daily_demo_runs_real_indicators_rules_and_renderer(tmp_path):
    report_path = run_daily_demo(tmp_path)
    evidence = json.loads((tmp_path / "analysis.json").read_text())
    inputs = pd.read_csv(tmp_path / "inputs.csv")
    assert set(p.name for p in tmp_path.iterdir()) == FILES
    assert len(inputs) == 320
    assert inputs.groupby("Symbol").size().tolist() == [80] * 4
    assert inputs.Date.min() == evidence["input_start"] == "2024-01-01"
    assert inputs.Date.max() == evidence["input_end"] == evidence["report_date"] == "2024-04-19"
    assert evidence["input_sha256"] == hashlib.sha256((tmp_path / "inputs.csv").read_bytes()).hexdigest()
    assert evidence["data_source"] == "deterministic_synthetic"
    assert evidence["historical_review"] is None and evidence["llm_used"] is False
    assert evidence["summary"]["total_scanned"] == 4
    assert evidence["summary"]["counts"] == {"超卖反弹": 1, "趋势向好": 1, "放量突破": 1}
    assert [s["code"] for stocks in evidence["summary"]["recommendations"].values() for s in stocks] == [
        "DEMO_A", "DEMO_B", "DEMO_C",
    ]

    # Recompute from the exported bytes, not from the generator's in-memory frames.
    histories = {
        code: group.set_index(pd.to_datetime(group.Date))[["Close", "Volume"]]
        for code, group in inputs.groupby("Symbol")
    }
    analyzer = _FixtureAnalyzer(histories)
    actual = []
    for record in evidence["analyzed_stocks"]:
        stock = analyzer.analyze_single_stock(record["code"], record["name"])
        actual.append(stock)
        for key in ("price", "rsi", "vol_ratio", "daily_change", "weekly_change"):
            assert record[key] == pytest.approx(stock[key], abs=1e-9)
        assert record["vol_ratio"] == pytest.approx(2_500_000 / ((19_000_000 + 2_500_000) / 20))
    selected = analyzer.generate_recommendations(actual)
    assert {kind: [s["code"] for s in stocks] for kind, stocks in selected.items()} == {
        kind: [s["code"] for s in stocks] for kind, stocks in evidence["summary"]["recommendations"].items()
    }
    report = report_path.read_text()
    expected = generate_report(None, evidence["formatted_recommendations"], evidence["summary"], report_date=REPORT_DATE)
    assert report.endswith(expected + "\n")
    assert "SYNTHETIC DAILY REPORT" in report and "qf/daily_demo.py" in report
    assert "股票分析日报 - 2024-04-19" in report
    assert "准确率:" not in report and "平均收益:" not in report and "【LLM智能精选】" not in report
    assert "暂无历史数据可回测" in report


def test_daily_preview_matches_current_code_and_is_repeatable(tmp_path):
    run_daily_demo(tmp_path)
    first = {name: (tmp_path / name).read_bytes() for name in FILES}
    run_daily_demo(tmp_path)
    for name in FILES:
        assert (tmp_path / name).read_bytes() == first[name]
        assert (ROOT / "docs" / "daily-demo" / name).read_bytes() == first[name], (
            "Run python scripts/update_daily_preview.py"
        )


@pytest.mark.parametrize("custom", [False, True])
def test_daily_demo_cli(tmp_path, monkeypatch, capsys, custom):
    monkeypatch.chdir(tmp_path)
    target = tmp_path / "custom output" if custom else tmp_path / "reports" / "daily-demo"
    args = ["stock-analyzer", "demo-daily"]
    if custom:
        args += ["--out", str(target)]
    monkeypatch.setattr(sys, "argv", args)
    assert cli.main() == 0
    output = capsys.readouterr().out
    assert output.startswith("SYNTHETIC DAILY REPORT")
    assert "4 fictional symbols, 80 weekday observations each" in output
    assert set(p.name for p in target.iterdir()) == FILES
    assert not (tmp_path / "stock_analysis.db").exists()


def test_generated_guides_have_valid_links_and_report(tmp_path):
    run_daily_demo(tmp_path)
    report = (tmp_path / "daily-report.txt").read_text().rstrip()
    prefix = "https://github.com/oliverran/stock-daily-analyzer/blob/main/"
    for name in ("README.md", "README.en.md"):
        guide = (tmp_path / name).read_text()
        assert report in guide
        assert "stock-analyzer demo-daily" in guide
        assert f"docs/daily-demo/{name}" in (ROOT / name).read_text()
        for link in re.findall(r"\]\(([^)]+)\)", guide):
            path = link.split("#")[0]
            if path.startswith(prefix):
                assert (ROOT / path[len(prefix):]).is_file(), path
            else:
                assert (tmp_path / path).is_file(), path


def test_report_date_is_optional_and_does_not_change_live_default():
    summary = {"recommendations": {}, "total_scanned": 0}
    assert f"股票分析日报 - {date.today().isoformat()}" in generate_report(None, [], summary)
    assert "股票分析日报 - 2001-02-03" in generate_report(None, [], summary, report_date=date(2001, 2, 3))


def test_fixture_data_is_fresh_per_call():
    first = synthetic_histories()
    first["DEMO_A"].iloc[0, 0] = -1
    assert synthetic_histories()["DEMO_A"].iloc[0, 0] > 0
