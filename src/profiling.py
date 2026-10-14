"""Generate a profiling snapshot of raw sales data."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd


def profile_dataframe(df: pd.DataFrame) -> dict[str, object]:
    """Return a profiling dictionary for a sales DataFrame."""
    total_rows = len(df)
    total_cols = len(df.columns)
    memory_mb = df.memory_usage(deep=True).sum() / (1024 * 1024)

    nulls = df.isna().sum().to_dict()
    nulls = {k: int(v) for k, v in nulls.items()}

    # Count empty strings as missing for string columns
    empty_counts: dict[str, int] = {}
    for col in df.columns:
        if df[col].dtype == object:
            empty_counts[col] = int((df[col] == "").sum())

    # Numeric columns — will be object type in raw data, so skip real min/max here
    # and focus on string lengths / top values.
    top_values: dict[str, dict[str, int]] = {}
    for col in df.columns:
        top_values[col] = df[col].value_counts().head(5).to_dict()
        top_values[col] = {str(k): int(v) for k, v in top_values[col].items()}

    business_key = ["order_id", "product_id", "order_date"]
    duplicate_keys = 0
    if all(col in df.columns for col in business_key):
        duplicate_keys = int(df.duplicated(subset=business_key).sum())

    return {
        "total_rows": total_rows,
        "total_columns": total_cols,
        "memory_mb": round(memory_mb, 2),
        "columns": df.columns.tolist(),
        "dtypes": {k: str(v) for k, v in df.dtypes.to_dict().items()},
        "null_counts": nulls,
        "empty_string_counts": empty_counts,
        "duplicate_business_keys": duplicate_keys,
        "top_values": top_values,
    }


def save_profile(df: pd.DataFrame, output_path: Path) -> None:
    """Profile a DataFrame and write the result as JSON."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    profile = profile_dataframe(df)
    with output_path.open("w", encoding="utf-8") as f:
        json.dump(profile, f, indent=2, default=str)


def main() -> None:
    """CLI entry point for profiling raw sales data."""
    parser = argparse.ArgumentParser(description="Profile raw sales data.")
    parser.add_argument("--input", type=Path, default=Path("data/raw/raw_sales.csv"))
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("reports/profiling_snapshot.json"),
    )
    args = parser.parse_args()

    df = pd.read_csv(args.input)
    save_profile(df, args.output)
    print(f"Profiling report written to {args.output}")


if __name__ == "__main__":
    main()
