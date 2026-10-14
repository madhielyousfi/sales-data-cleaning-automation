"""Smoke tests for the Streamlit app helpers."""

from __future__ import annotations

from io import BytesIO

import pandas as pd

import app
from src.cleaning import clean_data


def _raw_frame() -> pd.DataFrame:
    """Build a tiny raw frame with one valid and one invalid row."""
    return pd.DataFrame(
        {
            "row_id": ["R1", "R2"],
            "order_id": ["ORD-0000001", "ORD-0000002"],
            "order_date": ["2024-01-01", "2024-01-02"],
            "customer_id": ["C0000001", "C0000002"],
            "customer_name": ["Alice", "Bob"],
            "customer_email": ["alice@example.com", "bob@example.com"],
            "product_id": ["P001", "P002"],
            "product_name": ["Widget", "Gadget"],
            "category": ["Electronics", "Books"],
            "quantity": [2, -1],
            "unit_price": [10.0, 5.0],
            "discount": [0.1, 0.0],
            "payment_method": ["Credit Card", "Cash"],
            "country": ["United States", "France"],
            "order_status": ["completed", "completed"],
        }
    )


def test_run_pipeline_reconciles() -> None:
    """Pipeline keeps the valid row and quarantines the bad quantity."""
    cleaned, quarantined, _log = clean_data(_raw_frame())
    assert len(cleaned) == 1
    assert len(quarantined) == 1
    assert "invalid_quantity" in str(quarantined.iloc[0]["quarantine_reason"])
    assert float(cleaned.iloc[0]["total_amount"]) == 18.0


def test_quarantine_breakdown_counts() -> None:
    """Breakdown explodes multi-reason rows into per-reason counts."""
    quarantined = pd.DataFrame(
        {"quarantine_reason": ["invalid_quantity; invalid_date", "invalid_quantity"]}
    )
    breakdown = app._quarantine_breakdown(quarantined)  # noqa: SLF001
    counts = dict(zip(breakdown["reason"], breakdown["count"], strict=True))
    assert counts == {"invalid_quantity": 2, "invalid_date": 1}


def test_quarantine_breakdown_empty() -> None:
    """Empty quarantine yields an empty breakdown frame."""
    breakdown = app._quarantine_breakdown(pd.DataFrame())  # noqa: SLF001
    assert breakdown.empty


def test_to_excel_bytes_roundtrip() -> None:
    """Excel bytes are a readable workbook with the same columns."""
    df = _raw_frame()
    payload = app._to_excel_bytes(df)  # noqa: SLF001
    assert payload[:2] == b"PK"
    restored = pd.read_excel(BytesIO(payload), engine="openpyxl")
    assert list(restored.columns) == list(df.columns)
    assert len(restored) == len(df)


def test_quality_with_status_runs() -> None:
    """DuckDB checks run on pipeline output and report all check names."""
    cleaned, _, _log = clean_data(_raw_frame())
    quality_df, analytics = app._quality_with_status(cleaned)  # noqa: SLF001
    assert len(quality_df) == 8
    assert set(quality_df["status"]) <= {"Pass", "Review"}
    assert len(analytics) == 7
