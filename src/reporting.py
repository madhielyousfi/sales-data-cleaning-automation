"""Generate data quality and analytics reports."""

from __future__ import annotations

import argparse
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd

from src.validation import run_analytics, run_quality_checks

logger = logging.getLogger(__name__)


REPORT_SECTIONS = [
    "total_valid_records",
    "total_sales",
    "monthly_sales_trends",
    "revenue_by_category",
    "revenue_by_country",
    "top_selling_products",
    "average_order_value",
]


def _quality_to_markdown(quality_df: pd.DataFrame) -> str:
    """Render quality checks as a Markdown table."""
    lines = ["## Data Quality Checks\n", "| Check | Issue Count |", "|-------|-------------|"]
    for _, row in quality_df.iterrows():
        lines.append(f"| {row['check_name']} | {row['issue_count']} |")
    return "\n".join(lines)


def _quality_to_json(quality_df: pd.DataFrame) -> dict[str, Any]:
    """Convert quality checks to a JSON-friendly dictionary."""
    return {
        "generated_at": datetime.now().isoformat(),
        "checks": quality_df.to_dict(orient="records"),
    }


def generate_quality_report(
    quality_df: pd.DataFrame,
    output_md: Path,
    output_json: Path,
) -> None:
    """Write Markdown and JSON quality reports."""
    output_md.parent.mkdir(parents=True, exist_ok=True)
    output_json.parent.mkdir(parents=True, exist_ok=True)

    md = f"# Data Quality Report\n\nGenerated at {datetime.now().isoformat()}\n\n"
    md += _quality_to_markdown(quality_df)
    output_md.write_text(md, encoding="utf-8")

    json_data = _quality_to_json(quality_df)
    with output_json.open("w", encoding="utf-8") as f:
        json.dump(json_data, f, indent=2, default=str)


def generate_summary_metrics(
    analytics: list[pd.DataFrame],
    output_csv: Path,
) -> None:
    """Combine key analytics into a single summary CSV."""
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    summary_records: list[dict[str, Any]] = []

    if not analytics:
        return

    # metric rows
    for df in analytics[:2]:  # total_valid_records, total_sales
        if "metric" in df.columns and "value" in df.columns:
            for _, row in df.iterrows():
                summary_records.append({"metric": row["metric"], "value": row["value"]})

    # top category and country
    for name, df in [("top_category", analytics[3]), ("top_country", analytics[4])]:
        if not df.empty:
            top = df.iloc[0]
            summary_records.append({"metric": name, "value": str(top.iloc[0])})

    pd.DataFrame(summary_records).to_csv(output_csv, index=False)


def generate_reports(
    cleaned_path: Path,
    *,
    output_md: Path = Path("reports/data_quality_report.md"),
    output_json: Path = Path("reports/data_quality_report.json"),
    output_csv: Path = Path("reports/summary_metrics.csv"),
) -> None:
    """Run validation, analytics, and write all reports."""
    quality_df = run_quality_checks(cleaned_path)
    analytics = run_analytics(cleaned_path)
    generate_quality_report(quality_df, output_md, output_json)
    generate_summary_metrics(analytics, output_csv)
    logger.info("Reports generated at %s, %s, %s", output_md, output_json, output_csv)


def main() -> None:
    """CLI entry point for report generation."""
    parser = argparse.ArgumentParser(description="Generate data quality reports.")
    parser.add_argument("--cleaned", type=Path, default=Path("data/processed/cleaned_sales.csv"))
    report_md = Path("reports/data_quality_report.md")
    report_json = Path("reports/data_quality_report.json")
    parser.add_argument("--report-md", type=Path, default=report_md)
    parser.add_argument("--report-json", type=Path, default=report_json)
    parser.add_argument("--summary-csv", type=Path, default=Path("reports/summary_metrics.csv"))
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)
    generate_reports(
        args.cleaned,
        output_md=args.report_md,
        output_json=args.report_json,
        output_csv=args.summary_csv,
    )


if __name__ == "__main__":
    main()
