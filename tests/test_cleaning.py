"""Tests for the cleaning engine."""

from __future__ import annotations

from pathlib import Path
from unittest import mock

import pandas as pd
import pytest

from src.cleaning import (
    _calculate_total_amount,
    _map_country,
    _standardize_categories,
    clean_data,
    load_raw_data,
    save_cleaned_data,
)


@pytest.fixture()
def valid_raw_df() -> pd.DataFrame:
    """A small valid raw DataFrame."""
    return pd.DataFrame(
        {
            "row_id": ["R0000001", "R0000002"],
            "order_id": ["ORD-0000001", "ORD-0000002"],
            "order_date": ["2024-01-15", "2024-02-20"],
            "customer_id": ["C0000001", "C0000002"],
            "customer_name": ["  alice smith  ", "BOB JONES"],
            "customer_email": ["alice@example.com", "bob@example.com"],
            "product_id": ["P001", "P002"],
            "product_name": ["  Widget  ", "Gadget"],
            "category": ["electronics", "Electronics"],
            "quantity": ["2", "3"],
            "unit_price": ["10.00", "20.00"],
            "discount": ["0.10", "20%"],
            "payment_method": ["cc", "Credit Card"],
            "country": ["usa", "United States"],
            "order_status": ["completed", "canceled"],
        }
    )


def test_load_raw_data(tmp_path: Path) -> None:
    """load_raw_data reads a CSV and returns strings."""
    path = tmp_path / "raw.csv"
    path.write_text("order_id\nORD-1\nORD-2\n")
    df = load_raw_data(path)
    assert list(df["order_id"]) == ["ORD-1", "ORD-2"]


def test_clean_data_reconciles_counts(valid_raw_df: pd.DataFrame) -> None:
    """Cleaned + quarantined equals raw row count for fully valid data."""
    cleaned, quarantined, _log = clean_data(valid_raw_df)
    assert len(cleaned) + len(quarantined) == len(valid_raw_df)


def test_clean_data_standardizes_categories(valid_raw_df: pd.DataFrame) -> None:
    """Category variants are mapped to canonical values."""
    cleaned, _quarantined, _log = clean_data(valid_raw_df)
    assert all(cat == "Electronics" for cat in cleaned["category"])


def test_clean_data_calculates_total_amount(valid_raw_df: pd.DataFrame) -> None:
    """total_amount is calculated and rounded correctly."""
    cleaned, _quarantined, _log = clean_data(valid_raw_df)
    assert "total_amount" in cleaned.columns
    assert cleaned.loc[0, "total_amount"] == pytest.approx(18.00, abs=0.01)


def test_clean_data_quarantines_invalid_rows() -> None:
    """Rows with invalid quantity or price are quarantined."""
    df = pd.DataFrame(
        {
            "row_id": ["R1", "R2", "R3"],
            "order_id": ["ORD1", "ORD2", "ORD3"],
            "order_date": ["2024-01-01", "2024-01-02", "2024-01-03"],
            "customer_id": ["C1", "C2", "C3"],
            "customer_name": ["Alice", "Bob", "Carol"],
            "customer_email": ["a@example.com", "b@example.com", "c@example.com"],
            "product_id": ["P1", "P2", "P3"],
            "product_name": ["Widget", "Gadget", "Thing"],
            "category": ["Electronics", "Electronics", "Electronics"],
            "quantity": ["2", "-1", "5"],
            "unit_price": ["10.00", "20.00", "bad"],
            "discount": ["0.0", "0.0", "0.0"],
            "payment_method": ["Credit Card", "Credit Card", "Credit Card"],
            "country": ["United States", "United States", "United States"],
            "order_status": ["completed", "completed", "completed"],
        }
    )
    cleaned, quarantined, _log = clean_data(df)
    assert len(cleaned) + len(quarantined) == 3
    assert len(quarantined) == 2
    reasons = "; ".join(quarantined["quarantine_reason"].tolist())
    assert "invalid_quantity" in reasons
    assert "invalid_unit_price" in reasons


def test_clean_data_quarantines_duplicates() -> None:
    """Duplicate business keys are quarantined."""
    df = pd.DataFrame(
        {
            "row_id": ["R1", "R2"],
            "order_id": ["ORD1", "ORD1"],
            "order_date": ["2024-01-01", "2024-01-01"],
            "customer_id": ["C1", "C1"],
            "customer_name": ["Alice", "Alice"],
            "customer_email": ["a@example.com", "a@example.com"],
            "product_id": ["P1", "P1"],
            "product_name": ["Widget", "Widget"],
            "category": ["Electronics", "Electronics"],
            "quantity": ["1", "1"],
            "unit_price": ["10.00", "10.00"],
            "discount": ["0.0", "0.0"],
            "payment_method": ["Credit Card", "Credit Card"],
            "country": ["United States", "United States"],
            "order_status": ["completed", "completed"],
        }
    )
    cleaned, quarantined, _log = clean_data(df)
    assert len(cleaned) == 1
    assert len(quarantined) == 1
    assert "duplicate_business_key" in quarantined.iloc[0]["quarantine_reason"]


def test_save_cleaned_data_writes_files(tmp_path: Path, valid_raw_df: pd.DataFrame) -> None:
    """save_cleaned_data persists CSV and Excel files."""
    cleaned, quarantined, _log = clean_data(valid_raw_df)
    save_cleaned_data(
        cleaned,
        quarantined,
        csv_cleaned=tmp_path / "cleaned.csv",
        excel_cleaned=tmp_path / "cleaned.xlsx",
        csv_quarantine=tmp_path / "quarantine.csv",
        excel_quarantine=tmp_path / "quarantine.xlsx",
    )
    assert (tmp_path / "cleaned.csv").exists()
    assert (tmp_path / "cleaned.xlsx").exists()
    assert (tmp_path / "quarantine.csv").exists()
    assert (tmp_path / "quarantine.xlsx").exists()


def test_main_cli(tmp_path: Path, valid_raw_df: pd.DataFrame) -> None:
    """The CLI entry point writes cleaned and quarantined outputs."""
    from src.cleaning import main

    raw_path = tmp_path / "raw.csv"
    valid_raw_df.to_csv(raw_path, index=False)
    cleaned_csv = tmp_path / "cleaned.csv"
    cleaned_xlsx = tmp_path / "cleaned.xlsx"
    q_csv = tmp_path / "quarantine.csv"
    q_xlsx = tmp_path / "quarantine.xlsx"
    args = [
        "cleaning",
        "--input", str(raw_path),
        "--cleaned-csv", str(cleaned_csv),
        "--cleaned-xlsx", str(cleaned_xlsx),
        "--quarantine-csv", str(q_csv),
        "--quarantine-xlsx", str(q_xlsx),
    ]
    with mock.patch("sys.argv", args):
        main()
    assert cleaned_csv.exists()
    assert q_csv.exists()


def test_map_country_uses_aliases() -> None:
    """Country aliases resolve to canonical names."""
    assert _map_country("usa") == "United States"
    assert _map_country("Deutschland") == "Germany"
    assert _map_country("brasil") == "Brazil"


def test_standardize_categories() -> None:
    """Category variants are normalized."""
    df = pd.DataFrame({"category": ["electronics", "ELECTRONICS", "Electrnics", "Unknown"]})
    result = _standardize_categories(df)
    assert list(result["category"]) == ["Electronics", "Electronics", "Electronics", "Unknown"]


def test_calculate_total_amount() -> None:
    """total_amount reflects quantity, price, and discount."""
    df = pd.DataFrame(
        {
            "quantity": [2, 1],
            "unit_price": [100.0, 50.0],
            "discount": [0.20, 0.0],
            "order_status": ["completed", "canceled"],
        }
    )
    result = _calculate_total_amount(df)
    assert result["total_amount"].tolist()[0] == 160.0
    assert result["is_revenue_realized"].tolist() == [True, False]
