"""Regenerate the GitHub-readable synthetic daily-report example."""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from qf.daily_demo import run_daily_demo  # noqa: E402

if __name__ == "__main__":
    print(run_daily_demo(ROOT / "docs" / "daily-demo"))
