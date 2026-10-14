"""Tests for the reporting module."""

from __future__ import annotations

import json
from pathlib import Path
from unittest import mock

import pandas as pd

from src.reporting import generate_quality_report, generate_reports, generate_summary_metrics


def test_generate_quality_report(tmp_path: Path) -> None:
    """generate_quality_report writes Markdown and JSON."""
    df = pd.DataFrame(
        {"check_name": ["invalid_quantity", "bad_email"], "issue_count": [0, 5]}
    )
    md_path = tmp_path / "report.md"
    json_path = tmp_path / "report.json"
    generate_quality_report(df, md_path, json_path)
    assert md_path.exists()
    assert json_path.exists()
    data = json.loads(json_path.read_text(encoding="utf-8"))
    assert len(data["checks"]) == 2


def test_generate_summary_metrics(tmp_path: Path) -> None:
    """generate_summary_metrics writes a summary CSV."""
    analytics = [
        pd.DataFrame({"metric": ["total_valid_records"], "value": ["100"]}),
        pd.DataFrame({"metric": ["total_sales"], "value": ["500.00"]}),
        pd.DataFrame(),  # placeholder
        pd.DataFrame({"category": ["Electronics"], "revenue": [300.0]}),
        pd.DataFrame({"country": ["United States"], "revenue": [200.0]}),
        pd.DataFrame(),
        pd.DataFrame({"metric": ["average_order_value"], "value": ["50.00"]}),
    ]
    output_csv = tmp_path / "summary.csv"
    generate_summary_metrics(analytics, output_csv)
    assert output_csv.exists()


def test_generate_reports(tmp_path: Path) -> None:
    """generate_reports writes all three report files."""
    cleaned = tmp_path / "cleaned.csv"
    pd.DataFrame(
        {
            "row_id": ["R1"],
            "order_id": ["ORD1"],
            "order_date": ["2024-01-01"],
            "customer_id": ["C1"],
            "customer_name": ["Alice"],
            "customer_email": ["alice@example.com"],
            "product_id": ["P1"],
            "product_name": ["Widget"],
            "category": ["Electronics"],
            "quantity": [1],
            "unit_price": [10.0],
            "discount": [0.0],
            "payment_method": ["Credit Card"],
            "country": ["United States"],
            "order_status": ["completed"],
            "total_amount": [10.0],
            "is_revenue_realized": [True],
            "email_valid": [True],
            "quarantine_reason": [""],
            "data_quality_notes": [""],
        }
    ).to_csv(cleaned, index=False)

    md = tmp_path / "report.md"
    json_file = tmp_path / "report.json"
    summary = tmp_path / "summary.csv"
    generate_reports(cleaned, output_md=md, output_json=json_file, output_csv=summary)
    assert md.exists()
    assert json_file.exists()
    assert summary.exists()


def test_main_cli(tmp_path: Path) -> None:
    """The reporting CLI writes report files."""
    from src.reporting import main

    cleaned = tmp_path / "cleaned.csv"
    pd.DataFrame(
        {
            "row_id": ["R1"],
            "order_id": ["ORD1"],
            "order_date": ["2024-01-01"],
            "customer_id": ["C1"],
            "customer_name": ["Alice"],
            "customer_email": ["alice@example.com"],
            "product_id": ["P1"],
            "product_name": ["Widget"],
            "category": ["Electronics"],
            "quantity": [1],
            "unit_price": [10.0],
            "discount": [0.0],
            "payment_method": ["Credit Card"],
            "country": ["United States"],
            "order_status": ["completed"],
            "total_amount": [10.0],
            "is_revenue_realized": [True],
            "email_valid": [True],
            "quarantine_reason": [""],
            "data_quality_notes": [""],
        }
    ).to_csv(cleaned, index=False)

    md = tmp_path / "report.md"
    json_file = tmp_path / "report.json"
    summary = tmp_path / "summary.csv"
    args = [
        "reporting",
        "--cleaned", str(cleaned),
        "--report-md", str(md),
        "--report-json", str(json_file),
        "--summary-csv", str(summary),
    ]
    with mock.patch("sys.argv", args):
        main()
    assert md.exists()
    assert json_file.exists()
    assert summary.exists()
