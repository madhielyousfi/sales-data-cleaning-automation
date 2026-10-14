"""Tests for the unified CLI."""

from __future__ import annotations

from pathlib import Path

from src.cli import build_parser, cmd_run_all


def test_build_parser_run_all() -> None:
    """Parser accepts the run-all subcommand."""
    parser = build_parser()
    args = parser.parse_args(["run-all", "--seed", "1"])
    assert args.command == "run-all"
    assert args.seed == 1


def test_run_all(tmp_path: Path) -> None:
    """run-all produces all expected outputs."""
    raw = tmp_path / "raw.csv"
    cleaned_csv = tmp_path / "cleaned.csv"
    cleaned_xlsx = tmp_path / "cleaned.xlsx"
    q_csv = tmp_path / "quarantined.csv"
    q_xlsx = tmp_path / "quarantined.xlsx"
    report_md = tmp_path / "report.md"
    report_json = tmp_path / "report.json"
    summary = tmp_path / "summary.csv"
    profile = tmp_path / "profile.json"

    args = build_parser().parse_args(
        [
            "run-all",
            "--rows", "100",
            "--seed", "42",
            "--raw", str(raw),
            "--cleaned-csv", str(cleaned_csv),
            "--cleaned-xlsx", str(cleaned_xlsx),
            "--quarantine-csv", str(q_csv),
            "--quarantine-xlsx", str(q_xlsx),
            "--quality-report-md", str(report_md),
            "--quality-report-json", str(report_json),
            "--summary-csv", str(summary),
            "--profile", str(profile),
        ]
    )
    cmd_run_all(args)
    assert raw.exists()
    assert cleaned_csv.exists()
    assert cleaned_xlsx.exists()
    assert q_csv.exists()
    assert report_md.exists()
    assert report_json.exists()
    assert summary.exists()
    assert profile.exists()
