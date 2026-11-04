import json
from html.parser import HTMLParser
from pathlib import Path
from xml.etree import ElementTree as ET

import pandas as pd
import pytest

from qf.demo import run_demo
from qf.demo_report import render_equity_svg, write_demo_report


class Document(HTMLParser):
    def __init__(self, html):
        super().__init__()
        self.tags = []
        self.attributes = []
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        self.tags.append(tag)
        self.attributes.extend(attrs)


def demo_data(tmp_path):
    summary_path = run_demo(tmp_path)
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    equity = pd.read_csv(tmp_path / "equity.csv", index_col="Date", parse_dates=True)["equity"]
    holdings = pd.read_csv(tmp_path / "holdings.csv", index_col="Date", parse_dates=True)
    return equity, holdings, summary


def test_report_is_self_contained_and_matches_outputs(tmp_path):
    equity, holdings, summary = demo_data(tmp_path)
    html = (tmp_path / "report.html").read_text(encoding="utf-8")
    document = Document(html)
    assert not {"script", "link", "iframe", "object", "embed", "img", "form"}.intersection(document.tags)
    assert not [key for key, _ in document.attributes if key.startswith("on") or key == "src"]
    assert sorted(value for key, value in document.attributes if key == "href") == [
        "equity.csv", "equity.svg", "holdings.csv", "summary.json"
    ]
    assert "Content-Security-Policy" in html
    assert "default-src 'none'" in html
    assert '<meta name="description"' in html
    assert '<title>合成数据研究演示 | Stock Daily Analyzer</title>' in html
    assert 'content="Synthetic data only:' in html
    assert "Not historical market data or investment advice" in html
    for value in equity:
        assert f"{value:,.2f}" in html
    for value in holdings.iloc[-1]:
        assert f"{value:.2%}" in html
    for metric in ("total_return", "cagr", "max_drawdown"):
        assert f"{summary['metrics'][metric]:.2%}" in html
    assert f"{summary['metrics']['sharpe']:.2f}" in html
    chart = (tmp_path / "equity.svg").read_text(encoding="utf-8")
    assert chart in html
    root = ET.fromstring(chart)
    line = root.find("./{http://www.w3.org/2000/svg}g/{http://www.w3.org/2000/svg}polyline")
    points = [tuple(map(float, item.split(","))) for item in line.attrib["points"].split()]
    assert len(points) == summary["observations"] == 60
    values = equity.tolist()
    padding = max((max(values) - min(values)) * 0.15, max(values) * 0.001)
    low, high = min(values) - padding, max(values) + padding
    for i, (x, y) in enumerate(points):
        assert x == pytest.approx(100 + 820 * i / 59, abs=0.006)
        assert y == pytest.approx(346 - (values[i] - low) / (high - low) * 234, abs=0.006)


@pytest.mark.parametrize("values", [[], [0], [-1], [float("nan")], [float("inf")]])
def test_chart_rejects_invalid_equity(values):
    with pytest.raises(ValueError, match="finite, positive"):
        render_equity_svg(pd.Series(values, dtype=float))


@pytest.mark.parametrize("values", [[100.0], [100.0, 100.0]])
def test_chart_supports_single_and_constant_values(values):
    chart = render_equity_svg(pd.Series(values))
    assert "nan" not in chart.lower()
    assert "inf" not in chart.lower()
    root = ET.fromstring(chart)
    line = root.find("./{http://www.w3.org/2000/svg}g/{http://www.w3.org/2000/svg}polyline")
    assert len(line.attrib["points"].split()) == len(values)


def test_report_escapes_dynamic_text(tmp_path):
    equity, holdings, summary = demo_data(tmp_path)
    attack = '<img src="https://example.invalid/track" onerror="alert(1)">'
    summary["warning"] = attack
    summary["calendar"] = attack
    summary["symbols"] = [attack]
    summary["config"]["label"] = attack
    holdings = holdings.rename(columns={holdings.columns[0]: attack})
    write_demo_report(tmp_path, equity, holdings, summary)
    html = (tmp_path / "report.html").read_text(encoding="utf-8")
    assert attack not in html
    assert "&lt;img" in html
    assert "img" not in Document(html).tags
    chart = render_equity_svg(pd.Series([100.0], index=[attack]))
    assert attack not in chart
    ET.fromstring(chart)


def test_report_rejects_unlabelled_or_inconsistent_data(tmp_path):
    equity, holdings, summary = demo_data(tmp_path)
    with pytest.raises(ValueError, match="explicitly labelled"):
        write_demo_report(tmp_path, equity, holdings, {**summary, "demo": False})
    with pytest.raises(ValueError, match="must match"):
        write_demo_report(tmp_path, equity, holdings.iloc[:-1], summary)
    with pytest.raises(ValueError, match="metrics must be finite"):
        write_demo_report(tmp_path, equity, holdings, {**summary, "metrics": {**summary["metrics"], "sharpe": float("nan")}})
    holdings.iloc[0, 0] = float("nan")
    with pytest.raises(ValueError, match="holdings must contain finite"):
        write_demo_report(tmp_path, equity, holdings, summary)


def test_committed_preview_matches_demo(tmp_path):
    equity, holdings, summary = demo_data(tmp_path)
    preview = Path(__file__).resolve().parents[1] / "docs" / "demo"
    committed_summary = json.loads((preview / "summary.json").read_text(encoding="utf-8"))
    assert committed_summary["config"] == summary["config"]
    assert committed_summary["metrics"] == pytest.approx(summary["metrics"])
    pd.testing.assert_frame_equal(pd.read_csv(preview / "equity.csv"), pd.read_csv(tmp_path / "equity.csv"))
    pd.testing.assert_frame_equal(pd.read_csv(preview / "holdings.csv"), pd.read_csv(tmp_path / "holdings.csv"))
    # Presentation rounds values to two decimals. It should stay in sync even
    # when supported pandas versions serialize insignificant CSV digits differently.
    for filename in ("equity.svg", "report.html"):
        assert (preview / filename).read_text(encoding="utf-8") == (tmp_path / filename).read_text(encoding="utf-8")
