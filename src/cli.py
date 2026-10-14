"""Unified command-line interface for the sales data cleaning pipeline."""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from src.cleaning import clean_data, load_raw_data, save_cleaned_data
from src.generate_data import generate_sales_data, save_raw_data
from src.profiling import save_profile
from src.reporting import generate_reports
from src.validation import run_analytics, run_quality_checks, save_analytics

DEFAULTS = {
    "raw": Path("data/raw/raw_sales.csv"),
    "profile": Path("reports/profiling_snapshot.json"),
    "cleaned_csv": Path("data/processed/cleaned_sales.csv"),
    "cleaned_xlsx": Path("data/processed/cleaned_sales.xlsx"),
    "quarantine_csv": Path("data/quarantine/quarantined_sales.csv"),
    "quarantine_xlsx": Path("data/quarantine/quarantined_sales.xlsx"),
    "quality_report_md": Path("reports/data_quality_report.md"),
    "quality_report_json": Path("reports/data_quality_report.json"),
    "summary_csv": Path("reports/summary_metrics.csv"),
    "analytics_dir": Path("reports"),
    "seed": 42,
    "rows": 7_500,
}

logger = logging.getLogger(__name__)


def _setup_logging(level: int = logging.INFO) -> None:
    """Configure root logging for the CLI."""
    log_dir = Path("reports")
    log_dir.mkdir(parents=True, exist_ok=True)
    file_handler = logging.FileHandler(log_dir / "pipeline.log")
    file_handler.setFormatter(
        logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s"),
    )
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[logging.StreamHandler(sys.stdout), file_handler],
    )


def _add_common_args(parser: argparse.ArgumentParser) -> None:
    """Add shared arguments to a subparser."""
    parser.add_argument("--raw", type=Path, default=DEFAULTS["raw"])
    parser.add_argument("--seed", type=int, default=DEFAULTS["seed"])


def cmd_generate(args: argparse.Namespace) -> int:
    """Generate synthetic raw data."""
    df = generate_sales_data(rows=args.rows, seed=args.seed)
    save_raw_data(df, args.raw)
    logger.info("Generated %d rows at %s", len(df), args.raw)
    return 0


def cmd_profile(args: argparse.Namespace) -> int:
    """Profile raw data."""
    import pandas as pd

    df = pd.read_csv(args.raw)
    save_profile(df, args.profile)
    logger.info("Profile saved to %s", args.profile)
    return 0


def cmd_clean(args: argparse.Namespace) -> int:
    """Clean raw data and write outputs."""
    raw_df = load_raw_data(args.raw)
    cleaned, quarantined, _log = clean_data(raw_df)
    save_cleaned_data(
        cleaned,
        quarantined,
        csv_cleaned=args.cleaned_csv,
        excel_cleaned=args.cleaned_xlsx,
        csv_quarantine=args.quarantine_csv,
        excel_quarantine=args.quarantine_xlsx,
    )
    logger.info(
        "Cleaned: %d rows, Quarantined: %d rows",
        len(cleaned),
        len(quarantined),
    )
    return 0


def cmd_validate(args: argparse.Namespace) -> int:
    """Run SQL validation and analytics on cleaned data."""
    quality = run_quality_checks(args.cleaned)
    analytics = run_analytics(args.cleaned)
    save_analytics(analytics, args.analytics_dir)
    logger.info("Quality checks complete:\n%s", quality.to_string(index=False))
    return 0


def cmd_report(args: argparse.Namespace) -> int:
    """Generate Markdown/JSON/CSV reports."""
    generate_reports(
        args.cleaned,
        output_md=args.quality_report_md,
        output_json=args.quality_report_json,
        output_csv=args.summary_csv,
    )
    logger.info("Reports generated")
    return 0


def cmd_run_all(args: argparse.Namespace) -> int:
    """Run the full pipeline end-to-end."""
    logger.info("Starting full pipeline run")
    cmd_generate(args)
    cmd_profile(args)
    cmd_clean(args)
    cmd_validate(args)
    cmd_report(args)
    logger.info("Full pipeline complete")
    return 0


def build_parser() -> argparse.ArgumentParser:
    """Build the argparse CLI."""
    parser = argparse.ArgumentParser(
        prog="sales-pipeline",
        description="Sales data cleaning and automation pipeline",
    )
    parser.add_argument("--verbose", action="store_true", help="Enable debug logging")
    sub = parser.add_subparsers(dest="command", required=True)

    gen = sub.add_parser("generate", help="Generate synthetic raw data")
    gen.add_argument("--rows", type=int, default=DEFAULTS["rows"])
    _add_common_args(gen)
    gen.set_defaults(func=cmd_generate)

    prof = sub.add_parser("profile", help="Profile raw data")
    _add_common_args(prof)
    prof.add_argument("--profile", type=Path, default=DEFAULTS["profile"])
    prof.set_defaults(func=cmd_profile)

    clean = sub.add_parser("clean", help="Clean raw data")
    _add_common_args(clean)
    clean.add_argument("--cleaned-csv", type=Path, default=DEFAULTS["cleaned_csv"])
    clean.add_argument("--cleaned-xlsx", type=Path, default=DEFAULTS["cleaned_xlsx"])
    clean.add_argument("--quarantine-csv", type=Path, default=DEFAULTS["quarantine_csv"])
    clean.add_argument("--quarantine-xlsx", type=Path, default=DEFAULTS["quarantine_xlsx"])
    clean.set_defaults(func=cmd_clean)

    validate = sub.add_parser("validate", help="Run SQL validation and analytics")
    validate.add_argument("--cleaned", type=Path, default=DEFAULTS["cleaned_csv"])
    validate.add_argument("--analytics-dir", type=Path, default=DEFAULTS["analytics_dir"])
    validate.set_defaults(func=cmd_validate)

    report = sub.add_parser("report", help="Generate reports")
    report.add_argument("--cleaned", type=Path, default=DEFAULTS["cleaned_csv"])
    report.add_argument("--quality-report-md", type=Path, default=DEFAULTS["quality_report_md"])
    report.add_argument("--quality-report-json", type=Path, default=DEFAULTS["quality_report_json"])
    report.add_argument("--summary-csv", type=Path, default=DEFAULTS["summary_csv"])
    report.set_defaults(func=cmd_report)

    run_all = sub.add_parser("run-all", help="Run the full pipeline end-to-end")
    run_all.add_argument("--rows", type=int, default=DEFAULTS["rows"])
    _add_common_args(run_all)
    run_all.add_argument("--profile", type=Path, default=DEFAULTS["profile"])
    run_all.add_argument("--cleaned-csv", type=Path, default=DEFAULTS["cleaned_csv"])
    run_all.add_argument("--cleaned-xlsx", type=Path, default=DEFAULTS["cleaned_xlsx"])
    run_all.add_argument("--quarantine-csv", type=Path, default=DEFAULTS["quarantine_csv"])
    run_all.add_argument("--quarantine-xlsx", type=Path, default=DEFAULTS["quarantine_xlsx"])
    run_all.add_argument("--cleaned", type=Path, default=DEFAULTS["cleaned_csv"])
    run_all.add_argument("--analytics-dir", type=Path, default=DEFAULTS["analytics_dir"])
    report_md = DEFAULTS["quality_report_md"]
    report_json = DEFAULTS["quality_report_json"]
    run_all.add_argument("--quality-report-md", type=Path, default=report_md)
    run_all.add_argument("--quality-report-json", type=Path, default=report_json)
    run_all.add_argument("--summary-csv", type=Path, default=DEFAULTS["summary_csv"])
    run_all.set_defaults(func=cmd_run_all)

    return parser


def main() -> None:
    """CLI entry point."""
    parser = build_parser()
    args = parser.parse_args()
    _setup_logging(logging.DEBUG if args.verbose else logging.INFO)
    sys.exit(args.func(args))


if __name__ == "__main__":
    main()
