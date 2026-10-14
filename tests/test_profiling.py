"""Tests for the profiling module."""

from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import mock

from src.generate_data import generate_sales_data
from src.profiling import main, profile_dataframe, save_profile


def test_profile_dataframe_keys() -> None:
    """Profile output contains expected keys."""
    df = generate_sales_data(rows=500, seed=42)
    profile = profile_dataframe(df)
    assert profile["total_rows"] == len(df)
    assert "memory_mb" in profile
    assert "null_counts" in profile
    assert "duplicate_business_keys" in profile
    assert "top_values" in profile


def test_save_profile_writes_file() -> None:
    """save_profile writes a JSON file."""
    df = generate_sales_data(rows=100, seed=42)
    with TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "profile.json"
        save_profile(df, path)
        assert path.exists()
        loaded = json.loads(path.read_text(encoding="utf-8"))
        assert loaded["total_rows"] == len(df)


def test_main_writes_profile(tmp_path: Path) -> None:
    """The CLI entry point writes a profiling JSON file."""
    raw_path = tmp_path / "raw_sales.csv"
    generate_sales_data(rows=50, seed=42).to_csv(raw_path, index=False)
    profile_path = tmp_path / "profile.json"
    args = ["profiling", "--input", str(raw_path), "--output", str(profile_path)]
    with mock.patch("sys.argv", args):
        main()
    assert profile_path.exists()
