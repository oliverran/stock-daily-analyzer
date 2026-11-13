"""Execute the tutorial, optionally including its pinned network install cell.

Run with the notebook extra installed: python -m pip install -e '.[notebook]'.
This tests a local Jupyter kernel, not the Google Colab service or its sign-in UI.
"""
from __future__ import annotations

import argparse
import json
import tempfile
from pathlib import Path
from html.parser import HTMLParser
from zipfile import ZipFile

import nbformat
import pandas as pd
from nbclient import NotebookClient


ROOT = Path(__file__).resolve().parents[1]
NOTEBOOK = ROOT / "notebooks" / "offline_demo.ipynb"


class ReportLinks(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids = set()
        self.fragments = set()
        self.has_script = False
        self.csp = ""

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "article" and attrs.get("id", "").startswith("day-"):
            self.ids.add(attrs["id"])
        if attrs.get("href", "").startswith("#day-"):
            self.fragments.add(attrs["href"][1:])
        self.has_script |= tag == "script"
        if tag == "meta" and attrs.get("http-equiv") == "Content-Security-Policy":
            self.csp = attrs.get("content", "")


def verify_report(report: str, observations: int) -> None:
    parsed = ReportLinks()
    parsed.feed(report)
    expected = {f"day-{i}" for i in range(observations)}
    assert parsed.ids == parsed.fragments == expected, "Export must include every linked daily observation"
    assert not parsed.has_script, "Export must remain script-free"
    assert "default-src 'none'" in parsed.csp


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--install", action="store_true", help="Run the pinned pip install cell; use a disposable environment")
    args = parser.parse_args()
    notebook = nbformat.read(NOTEBOOK, as_version=4)
    nbformat.validate(notebook)
    # Kernel transport is already initialized. Guard both Python sockets and the
    # native HTTP transport used by yfinance, without changing tutorial cells.
    guard = nbformat.v4.new_code_cell("""
import socket
import requests
from curl_cffi.requests import Session as CurlSession
def unexpected_request(*args, **kwargs):
    raise AssertionError("The tutorial attempted to access an external service")
socket.socket.connect = unexpected_request
socket.socket.connect_ex = unexpected_request
requests.sessions.Session.request = unexpected_request
CurlSession.request = unexpected_request
""", id="validation-guard")
    install_index = next(i for i, cell in enumerate(notebook.cells) if cell.get("id") == "install")
    notebook.cells.insert(install_index + 1, guard)
    with tempfile.TemporaryDirectory(prefix="stock-notebook-check-") as temp:
        client = NotebookClient(
            notebook,
            timeout=120,
            kernel_name="python3",
            resources={"metadata": {"path": temp}},
            skip_cells_with_tag="skip-none" if args.install else "installation",
        )
        client.execute()
        executed = [cell for cell in notebook.cells if cell.cell_type == "code" and cell.execution_count is not None]
        assert len(executed) == (6 if args.install else 5), "All intended tutorial cells and the guard must execute"
        assert not any(output.output_type == "error" for cell in executed for output in cell.outputs)
        assert any("image/svg+xml" in output.get("data", {}) for cell in executed for output in cell.outputs)
        archives = list(Path(temp).glob("stock-demo-*.zip"))
        assert len(archives) == 1
        expected_names = {"equity.csv", "holdings.csv", "summary.json", "equity.svg", "report.html",
                          "synthetic-comparison.csv", "synthetic-comparison-holdings.csv"}
        with ZipFile(archives[0]) as archive:
            assert set(archive.namelist()) == expected_names
            summary = json.loads(archive.read("summary.json"))
            assert summary["data_source"] == "deterministic_synthetic"
            verify_report(archive.read("report.html").decode("utf-8"), summary["observations"])
            with archive.open("synthetic-comparison.csv") as source:
                comparison = pd.read_csv(source).set_index("top_k")
            assert comparison.index.tolist() == [1, 2, 3]
            assert abs(comparison.loc[1, "final_cash_weight"] - 0.5) < 1e-9
            assert abs(comparison.loc[2, "total_return"] - summary["metrics"]["total_return"]) < 1e-9
            assert comparison["total_return"].nunique() > 1
        print("Notebook validated: four tutorial cells executed with external requests blocked; "
              "SVG, 60 linked daily holdings in the script-free HTML export, three TopK scenarios, and seven-file ZIP verified.")
        print("Pinned installation verified." if args.install else "Installation cell skipped intentionally.")
        print("Google Colab runtime not exercised.")


if __name__ == "__main__":
    main()
