"""Regenerate the committed synthetic preview after installing the project."""

from pathlib import Path

from qf.demo import run_demo


if __name__ == "__main__":
    destination = Path(__file__).resolve().parents[1] / "docs" / "demo"
    run_demo(destination)
    print(f"Updated synthetic preview: {destination}")
