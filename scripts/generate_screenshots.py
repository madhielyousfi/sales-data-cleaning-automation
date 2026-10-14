"""Generate portfolio screenshots from cleaned data and reports."""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

RAW_PATH = Path("data/raw/raw_sales.csv")
CLEANED_PATH = Path("data/processed/cleaned_sales.csv")
REPORT_JSON = Path("reports/data_quality_report.json")
SCREENSHOTS = Path("docs/screenshots")


def _save_table(df: pd.DataFrame, title: str, path: Path, rows: int = 5) -> None:
    """Render a small DataFrame as an table image."""
    fig, ax = plt.subplots(figsize=(12, 3))
    ax.axis("tight")
    ax.axis("off")
    subset = df.head(rows)
    ax.table(
        cellText=subset.values,
        colLabels=subset.columns,
        cellLoc="left",
        loc="center",
    )
    ax.set_title(title, fontweight="bold", pad=20)
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)


def generate_raw_cleaned_previews() -> None:
    """Create before/after table screenshots."""
    raw = pd.read_csv(RAW_PATH)
    cleaned = pd.read_csv(CLEANED_PATH)

    raw_cols = [
        "order_id",
        "order_date",
        "customer_email",
        "category",
        "quantity",
        "unit_price",
        "discount",
        "order_status",
    ]
    _save_table(
        raw[raw_cols],
        "Raw Data Sample (before cleaning)",
        SCREENSHOTS / "01_raw_preview.png",
    )
    _save_table(
        cleaned[raw_cols + ["total_amount", "is_revenue_realized"]],
        "Cleaned Data Sample (after cleaning)",
        SCREENSHOTS / "02_cleaned_preview.png",
    )


def generate_quality_chart() -> None:
    """Create a bar chart of remaining quality issues."""
    import json

    data = json.loads(REPORT_JSON.read_text(encoding="utf-8"))
    checks = [c for c in data["checks"] if c["issue_count"] > 0]
    if not checks:
        return

    df = pd.DataFrame(checks)
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.bar(df["check_name"], df["issue_count"], color="#e15759")
    ax.set_xlabel("Quality Check")
    ax.set_ylabel("Issue Count")
    ax.set_title("Remaining Data Quality Issues After Cleaning")
    plt.xticks(rotation=45, ha="right")
    fig.tight_layout()
    fig.savefig(SCREENSHOTS / "03_quality_issues.png", dpi=150)
    plt.close(fig)


def generate_revenue_chart() -> None:
    """Create a revenue-by-category chart."""
    cleaned = pd.read_csv(CLEANED_PATH)
    revenue = (
        cleaned[cleaned["is_revenue_realized"]]
        .groupby("category")["total_amount"]
        .sum()
        .sort_values(ascending=False)
    )
    fig, ax = plt.subplots(figsize=(10, 5))
    revenue.plot(kind="bar", ax=ax, color="#4e79a7")
    ax.set_xlabel("Category")
    ax.set_ylabel("Revenue (USD)")
    ax.set_title("Revenue by Product Category")
    fig.tight_layout()
    fig.savefig(SCREENSHOTS / "04_revenue_by_category.png", dpi=150)
    plt.close(fig)


def main() -> None:
    """Generate all portfolio screenshots."""
    generate_raw_cleaned_previews()
    generate_quality_chart()
    generate_revenue_chart()
    print(f"Screenshots saved to {SCREENSHOTS}")


if __name__ == "__main__":
    main()
