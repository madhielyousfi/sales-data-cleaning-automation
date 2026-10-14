"""Tests for the synthetic sales data generator."""

from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest import mock

import pandas as pd
import pytest

from src.generate_data import generate_sales_data

REQUIRED_COLUMNS = {
    "row_id",
    "order_id",
    "order_date",
    "customer_id",
    "customer_name",
    "customer_email",
    "product_id",
    "product_name",
    "category",
    "quantity",
    "unit_price",
    "discount",
    "payment_method",
    "country",
    "order_status",
}


@pytest.fixture()
def sample_df() -> pd.DataFrame:
    """Default generated DataFrame for tests."""
    return generate_sales_data(rows=1_000, seed=42)


def test_generate_sales_data_has_required_columns(sample_df: pd.DataFrame) -> None:
    """Generated data contains all expected columns."""
    assert REQUIRED_COLUMNS.issubset(sample_df.columns)


def test_generate_sales_data_row_count() -> None:
    """Total rows equal base rows plus injected duplicate copies."""
    df = generate_sales_data(rows=1_000, seed=123)
    # 1_000 base + 150 duplicates injected by default
    assert len(df) == 1_150


def test_generate_sales_data_is_reproducible() -> None:
    """Identical seeds produce identical DataFrames."""
    df1 = generate_sales_data(rows=500, seed=42)
    df2 = generate_sales_data(rows=500, seed=42)
    pd.testing.assert_frame_equal(df1, df2)


def test_invalid_dates_injected(sample_df: pd.DataFrame) -> None:
    """Some order_date values are invalid or empty."""
    bad_dates = sample_df["order_date"].isin(["", "not-a-date"]) | sample_df["order_date"].str.contains("not-a-date", na=False)  # noqa: E501
    assert bad_dates.sum() > 0


def test_invalid_quantities_injected(sample_df: pd.DataFrame) -> None:
    """Some quantity values are non-numeric, negative, or zero."""
    def _bad(value: Any) -> bool:
        try:
            return int(value) <= 0
        except (ValueError, TypeError):
            return True

    bad = sample_df["quantity"].apply(_bad)
    assert bad.sum() > 0


def test_invalid_prices_injected(sample_df: pd.DataFrame) -> None:
    """Some unit_price values are non-numeric, negative, or zero."""
    def _bad(value: Any) -> bool:
        try:
            return float(value) <= 0
        except (ValueError, TypeError):
            return True

    bad = sample_df["unit_price"].apply(_bad)
    assert bad.sum() > 0


def test_bad_emails_injected(sample_df: pd.DataFrame) -> None:
    """Some emails are missing or malformed."""
    bad = sample_df["customer_email"].isin(["", "not-an-email", "missing@domain", "@nodomain.com"])
    assert bad.sum() > 0


def test_inconsistent_categories_injected(sample_df: pd.DataFrame) -> None:
    """Some categories are non-canonical variants."""
    from src.generate_data import CANONICAL_CATEGORIES

    non_canonical = ~sample_df["category"].isin(CANONICAL_CATEGORIES)
    assert non_canonical.sum() > 0


def test_main_generates_csv(tmp_path: Path) -> None:
    """The CLI entry point writes a CSV file."""
    from src.generate_data import main

    output = tmp_path / "raw_sales.csv"
    args = ["generate_data", "--rows", "50", "--seed", "1", "--output", str(output)]
    with mock.patch("sys.argv", args):
        main()
    assert output.exists()
    df = pd.read_csv(output)
    assert len(df) == 100  # 50 base + 50 duplicate copies capped by base size
