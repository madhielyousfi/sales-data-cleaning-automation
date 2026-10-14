"""Sales data cleaning engine and quarantine logic."""

from __future__ import annotations

import argparse
import logging
import re
from datetime import datetime
from functools import cache
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import pycountry

from src.generate_data import (
    CANONICAL_CATEGORIES,
    CANONICAL_PAYMENTS,
    CATEGORY_VARIANTS,
    PAYMENT_VARIANTS,
)

logger = logging.getLogger(__name__)

DATE_EARLIEST = datetime(2010, 1, 1)
MAX_DISCOUNT = 0.80

# Build reverse lookup dictionaries (lowercase variant -> canonical)
CATEGORY_MAP = {}
for _canonical, _variants in CATEGORY_VARIANTS.items():
    for _variant in _variants:
        CATEGORY_MAP[_variant.lower()] = _canonical

PAYMENT_MAP = {}
for _canonical, _variants in PAYMENT_VARIANTS.items():
    for _variant in _variants:
        PAYMENT_MAP[_variant.lower()] = _canonical

COUNTRY_ALIASES = {
    "usa": "United States",
    "us": "United States",
    "united states of america": "United States",
    "uk": "United Kingdom",
    "united kingdom": "United Kingdom",
    "deutschland": "Germany",
    "brasil": "Brazil",
    "fr": "France",
    "es": "Spain",
    "it": "Italy",
    "ca": "Canada",
    "au": "Australia",
    "in": "India",
    "cn": "China",
    "jp": "Japan",
}

EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def load_raw_data(path: Path) -> pd.DataFrame:
    """Load raw sales data from a CSV file."""
    return pd.read_csv(path, dtype=str)


def _mark_quarantine(df: pd.DataFrame, condition: pd.Series, reason: str) -> pd.DataFrame:
    """Append a quarantine reason to rows matching the condition."""
    if "quarantine_reason" not in df.columns:
        df["quarantine_reason"] = ""
    existing = df.loc[condition, "quarantine_reason"].astype(str)
    updated = existing.apply(lambda x: f"{x}; {reason}" if x and x != "nan" else reason)
    df.loc[condition, "quarantine_reason"] = updated
    return df


def _strip_strings(df: pd.DataFrame) -> pd.DataFrame:
    """Trim whitespace and collapse multiple spaces in all string columns."""
    string_cols = df.select_dtypes(include=["object", "string"]).columns
    for col in string_cols:
        df[col] = df[col].astype(str).str.strip().replace(r"\s+", " ", regex=True)
        df[col] = df[col].replace("nan", pd.NA)
    return df


def _replace_empties_with_na(df: pd.DataFrame) -> pd.DataFrame:
    """Treat empty strings as missing values."""
    df = df.replace(r"^\s*$", pd.NA, regex=True)
    return df


def _standardize_dates(df: pd.DataFrame) -> pd.DataFrame:
    """Parse order_date; rows with invalid/out-of-range dates are flagged."""
    parsed = pd.to_datetime(df["order_date"], errors="coerce", dayfirst=False)
    today = pd.Timestamp.now().normalize()
    invalid = parsed.isna() | (parsed < DATE_EARLIEST) | (parsed > today)
    df["order_date_parsed"] = parsed
    df = _mark_quarantine(df, invalid, "invalid_date")
    # Keep original string for quarantine file context; will replace later for cleaned rows.
    return df


def _normalize_names(df: pd.DataFrame) -> pd.DataFrame:
    """Title-case and clean customer and product names."""
    for col in ["customer_name", "product_name"]:
        if col in df.columns:
            df[col] = df[col].str.title()
    return df


def _standardize_categories(df: pd.DataFrame) -> pd.DataFrame:
    """Map category variants to canonical values."""
    def _map(value: Any) -> Any:
        if pd.isna(value):
            return value
        return CATEGORY_MAP.get(str(value).strip().lower(), str(value).strip())

    df["category"] = df["category"].apply(_map)
    unknown = ~df["category"].isin(CANONICAL_CATEGORIES) & df["category"].notna()
    df.loc[unknown, "data_quality_notes"] = "unknown_category"
    return df


def _standardize_payment_methods(df: pd.DataFrame) -> pd.DataFrame:
    """Map payment method variants to canonical values."""
    def _map(value: Any) -> Any:
        if pd.isna(value):
            return value
        return PAYMENT_MAP.get(str(value).strip().lower(), str(value).strip())

    df["payment_method"] = df["payment_method"].apply(_map)
    unknown = ~df["payment_method"].isin(CANONICAL_PAYMENTS) & df["payment_method"].notna()
    df.loc[unknown, "data_quality_notes"] = "unknown_payment_method"
    return df


@cache
def _map_country(value: str) -> str:
    """Normalize a single country name using aliases and pycountry."""
    key = value.strip().lower()
    if key in COUNTRY_ALIASES:
        return COUNTRY_ALIASES[key]
    try:
        country = pycountry.countries.search_fuzzy(value)[0]
        return country.name
    except (LookupError, AttributeError):
        return value.strip()


def _standardize_countries(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize country names using aliases and pycountry."""
    def _map(value: Any) -> Any:
        if pd.isna(value):
            return value
        return _map_country(str(value))

    df["country"] = df["country"].apply(_map)
    return df


def _convert_numeric_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Safely coerce quantity, unit_price, and discount to numeric."""
    df["quantity"] = pd.to_numeric(df["quantity"], errors="coerce")
    df["unit_price"] = pd.to_numeric(df["unit_price"], errors="coerce")
    # Discount may have been coerced already if string; preserve NaN for handling.
    df["discount"] = pd.to_numeric(df["discount"], errors="coerce")
    return df


def _process_discounts(df: pd.DataFrame) -> pd.DataFrame:
    """Convert percentage strings, cap values, and flag invalid discounts."""
    # Re-parse from string in case original column had '%' characters that to_numeric dropped.
    def _convert(value: Any) -> float:
        if pd.isna(value):
            return np.nan
        if isinstance(value, (int, float)):
            return float(value)
        text = str(value).strip().replace("%", "")
        try:
            val = float(text)
        except ValueError:
            return np.nan
        if 0 <= val <= 1:
            return val
        # Treat value > 1 as a percentage (e.g., 20 -> 0.20)
        return val / 100.0

    df["discount"] = df["discount"].apply(_convert)

    # Fill missing discounts with 0 in cleaned rows; invalid ones are quarantined below.
    df["discount"] = df["discount"].fillna(0.0)

    invalid = (df["discount"] < 0) | (df["discount"] > MAX_DISCOUNT)
    df = _mark_quarantine(df, invalid, "invalid_discount")
    return df


def _validate_business_rules(df: pd.DataFrame) -> pd.DataFrame:
    """Apply core business-rule validation and collect quarantine reasons."""
    # Missing critical identifiers
    df = _mark_quarantine(df, df["order_id"].isna(), "missing_order_id")
    df = _mark_quarantine(df, df["product_id"].isna(), "missing_product_id")
    df = _mark_quarantine(df, df["customer_id"].isna(), "missing_customer_id")

    # Unidentifiable customer
    no_email = df["customer_email"].isna() | (df["customer_email"] == "")
    no_name = df["customer_name"].isna()
    df = _mark_quarantine(df, no_email & no_name, "unidentifiable_customer")

    # Invalid numeric business values
    invalid_quantity = df["quantity"].isna() | (df["quantity"] <= 0)
    df = _mark_quarantine(df, invalid_quantity, "invalid_quantity")
    invalid_price = df["unit_price"].isna() | (df["unit_price"] <= 0)
    df = _mark_quarantine(df, invalid_price, "invalid_unit_price")

    return df


def _validate_emails(df: pd.DataFrame) -> pd.DataFrame:
    """Flag malformed emails without quarantining them."""
    valid = df["customer_email"].notna() & df["customer_email"].str.match(EMAIL_PATTERN, na=False)
    df["email_valid"] = valid
    return df


def _calculate_total_amount(df: pd.DataFrame) -> pd.DataFrame:
    """Calculate line total and revenue-realized flag."""
    df["total_amount"] = (df["quantity"] * df["unit_price"] * (1 - df["discount"])).round(2)
    df["is_revenue_realized"] = ~df["order_status"].isin(["canceled", "refunded"])
    return df


def _remove_duplicate_business_keys(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Keep first occurrence of each business key; quarantine the rest."""
    keys = ["order_id", "product_id", "order_date"]
    # Only consider rows not already quarantined for missing keys
    active = df["quarantine_reason"].isna() | (df["quarantine_reason"] == "")
    workable = df[active].copy()

    duplicates = workable.duplicated(subset=keys, keep="first")
    dup_mask = df.index.isin(workable[duplicates].index)
    df = _mark_quarantine(df, dup_mask, "duplicate_business_key")
    return df, dup_mask


def clean_data(
    raw_df: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame, list[dict[str, Any]]]:
    """Clean raw sales data and separate valid and quarantined records.

    Returns:
        A tuple of (cleaned DataFrame, quarantined DataFrame, cleaning log).
    """
    df = raw_df.copy()

    # Preliminary cleaning
    df = _strip_strings(df)
    df = _replace_empties_with_na(df)

    # Initialize audit columns after empty-string replacement so they are not nulled.
    df["quarantine_reason"] = ""
    df["data_quality_notes"] = ""

    # Cleaning steps
    df = _standardize_dates(df)
    df = _normalize_names(df)
    df = _standardize_categories(df)
    df = _standardize_payment_methods(df)
    df = _standardize_countries(df)
    df = _convert_numeric_columns(df)
    df = _process_discounts(df)
    df = _validate_emails(df)
    df = _validate_business_rules(df)

    # Duplicates use cleaned dates and order_id
    df["order_date"] = df["order_date_parsed"].dt.strftime("%Y-%m-%d")
    df, _ = _remove_duplicate_business_keys(df)

    # Final calculations
    df = _calculate_total_amount(df)

    # Split cleaned vs quarantine
    quarantine_mask = df["quarantine_reason"].ne("")
    cleaned = df[~quarantine_mask].copy()
    quarantined = df[quarantine_mask].copy()

    # Remove helper columns from cleaned output (keep audit columns minimal)
    cleaned = cleaned.drop(columns=["order_date_parsed"])
    quarantined = quarantined.drop(columns=["order_date_parsed"])

    log: list[dict[str, Any]] = [
        {"step": "load", "affected_rows": len(raw_df), "reason": "raw_rows"},
        {"step": "clean", "affected_rows": len(cleaned), "reason": "valid_rows"},
        {"step": "quarantine", "affected_rows": len(quarantined), "reason": "quarantined_rows"},
    ]

    logger.info("Cleaning complete: %d cleaned, %d quarantined", len(cleaned), len(quarantined))
    return cleaned, quarantined, log


def save_cleaned_data(
    cleaned: pd.DataFrame,
    quarantined: pd.DataFrame,
    *,
    csv_cleaned: Path,
    excel_cleaned: Path,
    csv_quarantine: Path,
    excel_quarantine: Path,
) -> None:
    """Persist cleaned and quarantined datasets to CSV and Excel."""
    csv_cleaned.parent.mkdir(parents=True, exist_ok=True)
    csv_quarantine.parent.mkdir(parents=True, exist_ok=True)

    cleaned.to_csv(csv_cleaned, index=False)
    cleaned.to_excel(excel_cleaned, index=False)
    quarantined.to_csv(csv_quarantine, index=False)
    quarantined.to_excel(excel_quarantine, index=False)


def main() -> None:
    """CLI entry point for cleaning raw sales data."""
    parser = argparse.ArgumentParser(description="Clean raw sales data.")
    parser.add_argument("--input", type=Path, default=Path("data/raw/raw_sales.csv"))
    cleaned_csv = Path("data/processed/cleaned_sales.csv")
    cleaned_xlsx = Path("data/processed/cleaned_sales.xlsx")
    q_csv = Path("data/quarantine/quarantined_sales.csv")
    q_xlsx = Path("data/quarantine/quarantined_sales.xlsx")
    parser.add_argument("--cleaned-csv", type=Path, default=cleaned_csv)
    parser.add_argument("--cleaned-xlsx", type=Path, default=cleaned_xlsx)
    parser.add_argument("--quarantine-csv", type=Path, default=q_csv)
    parser.add_argument("--quarantine-xlsx", type=Path, default=q_xlsx)
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)
    raw_df = load_raw_data(args.input)
    cleaned, quarantined, _log = clean_data(raw_df)
    save_cleaned_data(
        cleaned,
        quarantined,
        csv_cleaned=args.cleaned_csv,
        excel_cleaned=args.cleaned_xlsx,
        csv_quarantine=args.quarantine_csv,
        excel_quarantine=args.quarantine_xlsx,
    )
    print(f"Cleaned: {len(cleaned)} | Quarantined: {len(quarantined)}")


if __name__ == "__main__":
    main()
