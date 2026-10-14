"""Smoke tests for the project scaffold."""

from pathlib import Path


def test_project_directories_exist() -> None:
    """Required directories should be present."""
    root = Path(__file__).resolve().parents[1]
    for subpath in [
        "src",
        "data/raw",
        "data/processed",
        "data/quarantine",
        "sql",
        "tests",
        "reports",
        "docs",
        ".github/workflows",
    ]:
        assert (root / subpath).exists(), f"{subpath} does not exist"
