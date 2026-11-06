import ast
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
NOTEBOOK = ROOT / "notebooks" / "offline_demo.ipynb"


def test_notebook_source_is_clean_valid_python_and_installs_a_fixed_revision():
    notebook = json.loads(NOTEBOOK.read_text(encoding="utf-8"))
    assert notebook["nbformat"] == 4
    cells = [cell for cell in notebook["cells"] if cell["cell_type"] == "code"]
    assert [cell["id"] for cell in cells] == ["install", "run-demo", "inspect", "compare", "export"]
    for cell in cells:
        ast.parse("".join(cell["source"]))
        assert cell["execution_count"] is None
        assert cell["outputs"] == []
    assert cells[0]["metadata"]["tags"] == ["installation"]
    assert re.search(r'SOURCE_REVISION = "[0-9a-f]{40}"', "".join(cells[0]["source"]))
    assert all("installation" not in cell["metadata"]["tags"] for cell in cells[1:])


def test_both_readmes_link_to_the_same_committed_notebook():
    link = "https://colab.research.google.com/github/oliverran/stock-daily-analyzer/blob/main/notebooks/offline_demo.ipynb"
    for name in ("README.md", "README.en.md"):
        readme = (ROOT / name).read_text(encoding="utf-8")
        assert link in readme
        assert "(notebooks/offline_demo.ipynb)" in readme
