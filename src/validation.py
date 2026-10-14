"""DuckDB SQL validation and analytics runner."""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

import duckdb
import pandas as pd

logger = logging.getLogger(__name__)


def _statements(sql: str) -> list[str]:
    """Split SQL text into individual non-empty statements."""
    parts = [part.strip() for part in sql.split(";")]
    return [part for part in parts if part]


def _substitute_path(sql: str, cleaned_path: Path) -> str:
    """Replace placeholder with the cleaned CSV path."""
    return sql.replace("{{cleaned_path}}", str(cleaned_path))


def run_quality_checks(
    cleaned_path: Path,
    sql_path: Path = Path("sql/quality_checks.sql"),
) -> pd.DataFrame:
    """Execute quality-check SQL and return a DataFrame of results."""
    sql = _substitute_path(sql_path.read_text(encoding="utf-8"), cleaned_path)
    logger.info("Running quality checks on %s", cleaned_path)
    with duckdb.connect() as conn:
        result = conn.execute(sql).fetchdf()
    return result


def run_analytics(
    cleaned_path: Path,
    sql_path: Path = Path("sql/sales_analytics.sql"),
) -> list[pd.DataFrame]:
    """Execute analytics SQL and return a list of result DataFrames."""
    sql = _substitute_path(sql_path.read_text(encoding="utf-8"), cleaned_path)
    results: list[pd.DataFrame] = []
    with duckdb.connect() as conn:
        for statement in _statements(sql):
            relation = conn.execute(statement)
            if statement.lstrip().upper().startswith("SELECT"):
                results.append(relation.fetchdf())
    return results


def save_analytics(
    analytics: list[pd.DataFrame],
    output_dir: Path,
) -> dict[str, Path]:
    """Persist analytics DataFrames to CSV files."""
    output_dir.mkdir(parents=True, exist_ok=True)
    saved: dict[str, Path] = {}
    names = [
        "total_valid_records",
        "total_sales",
        "monthly_sales_trends",
        "revenue_by_category",
        "revenue_by_country",
        "top_selling_products",
        "average_order_value",
    ]
    for name, df in zip(names, analytics, strict=True):
        path = output_dir / f"{name}.csv"
        df.to_csv(path, index=False)
        saved[name] = path
    return saved


def main() -> None:
    """CLI entry point for SQL validation and analytics."""
    parser = argparse.ArgumentParser(description="Validate cleaned data with DuckDB.")
    parser.add_argument("--cleaned", type=Path, default=Path("data/processed/cleaned_sales.csv"))
    parser.add_argument("--quality-checks", type=Path, default=Path("sql/quality_checks.sql"))
    parser.add_argument("--analytics", type=Path, default=Path("sql/sales_analytics.sql"))
    parser.add_argument("--output-dir", type=Path, default=Path("reports"))
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)
    quality = run_quality_checks(args.cleaned, args.quality_checks)
    analytics = run_analytics(args.cleaned, args.analytics)
    save_analytics(analytics, args.output_dir)
    logger.info("Quality checks: %s", quality.to_dict(orient="records"))


if __name__ == "__main__":
    main()
