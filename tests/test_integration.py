"""End-to-end integration and idempotency tests."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from src.cli import build_parser, cmd_run_all


@pytest.fixture()
def pipeline_args(tmp_path: Path) -> list[str]:
    """Build CLI arguments for a pipeline run in a temporary directory."""
    return [
        "run-all",
        "--rows", "100",
        "--seed", "42",
        "--raw", str(tmp_path / "raw.csv"),
        "--cleaned-csv", str(tmp_path / "cleaned.csv"),
        "--cleaned-xlsx", str(tmp_path / "cleaned.xlsx"),
        "--quarantine-csv", str(tmp_path / "quarantined.csv"),
        "--quarantine-xlsx", str(tmp_path / "quarantined.xlsx"),
        "--quality-report-md", str(tmp_path / "report.md"),
        "--quality-report-json", str(tmp_path / "report.json"),
        "--summary-csv", str(tmp_path / "summary.csv"),
        "--profile", str(tmp_path / "profile.json"),
    ]


def _read_text(path: Path) -> str:
    """Read file text, or return empty for missing files."""
    return path.read_text(encoding="utf-8") if path.exists() else ""


def test_full_pipeline_runs(pipeline_args: list[str], tmp_path: Path) -> None:
    """The full pipeline writes all expected artifacts."""
    args = build_parser().parse_args(pipeline_args)
    cmd_run_all(args)
    assert (tmp_path / "cleaned.csv").exists()
    assert (tmp_path / "quarantined.csv").exists()
    assert (tmp_path / "report.md").exists()
    assert (tmp_path / "report.json").exists()
    assert (tmp_path / "summary.csv").exists()


def test_pipeline_is_idempotent(tmp_path: Path) -> None:
    """Two runs with the same seed produce identical CSV outputs."""
    def run(output_dir: Path) -> None:
        output_dir.mkdir(parents=True, exist_ok=True)
        args = build_parser().parse_args(
            [
                "run-all",
                "--rows", "100",
                "--seed", "42",
                "--raw", str(output_dir / "raw.csv"),
                "--cleaned-csv", str(output_dir / "cleaned.csv"),
                "--cleaned-xlsx", str(output_dir / "cleaned.xlsx"),
                "--quarantine-csv", str(output_dir / "quarantined.csv"),
                "--quarantine-xlsx", str(output_dir / "quarantined.xlsx"),
                "--quality-report-md", str(output_dir / "report.md"),
                "--quality-report-json", str(output_dir / "report.json"),
                "--summary-csv", str(output_dir / "summary.csv"),
                "--profile", str(output_dir / "profile.json"),
            ]
        )
        cmd_run_all(args)

    run1 = tmp_path / "run1"
    run2 = tmp_path / "run2"
    run(run1)
    run(run2)

    cleaned1 = pd.read_csv(run1 / "cleaned.csv")
    cleaned2 = pd.read_csv(run2 / "cleaned.csv")
    quarantine1 = pd.read_csv(run1 / "quarantined.csv")
    quarantine2 = pd.read_csv(run2 / "quarantined.csv")


    cleaned2 = cleaned2[cleaned1.columns]
    quarantine2 = quarantine2[quarantine1.columns]

    pd.testing.assert_frame_equal(cleaned1, cleaned2)
    pd.testing.assert_frame_equal(quarantine1, quarantine2)


def test_record_count_reconciliation(pipeline_args: list[str], tmp_path: Path) -> None:
    """Raw count equals cleaned plus quarantined counts."""
    args = build_parser().parse_args(pipeline_args)
    cmd_run_all(args)
    raw = pd.read_csv(tmp_path / "raw.csv")
    cleaned = pd.read_csv(tmp_path / "cleaned.csv")
    quarantined = pd.read_csv(tmp_path / "quarantined.csv")
    assert len(raw) == len(cleaned) + len(quarantined)
