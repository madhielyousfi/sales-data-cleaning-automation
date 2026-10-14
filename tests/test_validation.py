"""Tests for the SQL validation and analytics runner."""

from __future__ import annotations

from pathlib import Path
from unittest import mock

import pandas as pd
import pytest

from src.validation import run_analytics, run_quality_checks, save_analytics


@pytest.fixture()
def cleaned_csv(tmp_path: Path) -> Path:
    """Create a minimal cleaned CSV file."""
    path = tmp_path / "cleaned.csv"
    df = pd.DataFrame(
        {
            "row_id": ["R1", "R2"],
            "order_id": ["ORD1", "ORD2"],
            "order_date": ["2024-01-01", "2024-02-01"],
            "customer_id": ["C1", "C2"],
            "customer_name": ["Alice", "Bob"],
            "customer_email": ["alice@example.com", "bad-email"],
            "product_id": ["P1", "P2"],
            "product_name": ["Widget", "Gadget"],
            "category": ["Electronics", "Books"],
            "quantity": [2, 1],
            "unit_price": [10.0, 5.0],
            "discount": [0.0, 0.0],
            "payment_method": ["Credit Card", "PayPal"],
            "country": ["United States", "Germany"],
            "order_status": ["completed", "canceled"],
            "total_amount": [20.0, 5.0],
            "is_revenue_realized": [True, False],
            "email_valid": [True, False],
            "quarantine_reason": ["", ""],
            "data_quality_notes": ["", ""],
        }
    )
    df.to_csv(path, index=False)
    return path


def test_run_quality_checks(cleaned_csv: Path) -> None:
    """Quality checks return a DataFrame with no invalid numeric issues."""
    sql_path = Path("sql/quality_checks.sql")
    result = run_quality_checks(cleaned_csv, sql_path)
    assert "check_name" in result.columns
    assert "issue_count" in result.columns
    invalid_quantity = result.loc[result["check_name"] == "invalid_quantity", "issue_count"].iloc[0]
    assert int(invalid_quantity) == 0


def test_run_analytics(cleaned_csv: Path) -> None:
    """Analytics return a list of DataFrames."""
    sql_path = Path("sql/sales_analytics.sql")
    results = run_analytics(cleaned_csv, sql_path)
    assert len(results) == 7
    # total sales
    assert results[1].iloc[0]["metric"] == "total_sales"


def test_save_analytics(tmp_path: Path) -> None:
    """save_analytics writes CSV files for each DataFrame."""
    dfs = [pd.DataFrame({"metric": ["total_sales"], "value": ["100.00"]}) for _ in range(7)]
    saved = save_analytics(dfs, tmp_path)
    assert len(saved) == 7
    assert (tmp_path / "total_sales.csv").exists()


def test_main_cli(tmp_path: Path, cleaned_csv: Path) -> None:
    """The validation CLI runs and saves analytics."""
    from src.validation import main

    output_dir = tmp_path / "analytics"
    args = [
        "validation",
        "--cleaned", str(cleaned_csv),
        "--output-dir", str(output_dir),
    ]
    with mock.patch("sys.argv", args):
        main()
    assert (output_dir / "total_valid_records.csv").exists()
