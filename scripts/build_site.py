"""Build embedded data for the static GitHub Pages site from pipeline outputs."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
REPORTS = ROOT / "reports"
DATA = ROOT / "data"
OUT = ROOT / "assets" / "site-data.js"


def _read_csv(name: str) -> pd.DataFrame:
    return pd.read_csv(REPORTS / name)


def _round2(value: object) -> float:
    try:
        return round(float(str(value)), 2)
    except (TypeError, ValueError):
        return 0.0


def build() -> dict[str, object]:
    """Collect all site data from reports and quarantine files."""
    raw = pd.read_csv(DATA / "raw" / "raw_sales.csv", usecols=["row_id"])
    cleaned = pd.read_csv(DATA / "processed" / "cleaned_sales.csv", usecols=["row_id"])
    quarantine = pd.read_csv(DATA / "quarantine" / "quarantined_sales.csv")

    quality = json.loads((REPORTS / "data_quality_report.json").read_text())
    monthly = _read_csv("monthly_sales_trends.csv")
    category = _read_csv("revenue_by_category.csv")
    country = _read_csv("revenue_by_country.csv")
    products = _read_csv("top_selling_products.csv")
    summary = _read_csv("summary_metrics.csv")
    aov = _read_csv("average_order_value.csv")
    total_sales = _read_csv("total_sales.csv")

    reasons = (
        quarantine["quarantine_reason"]
        .astype(str)
        .str.split(";")
        .explode()
        .str.strip()
    )
    reasons = reasons[reasons.ne("") & reasons.ne("nan")]
    breakdown = reasons.value_counts().rename_axis("reason").reset_index(name="count")

    sample_cols = [
        "order_id", "order_date", "product_name", "category",
        "quantity", "unit_price", "quarantine_reason",
    ]
    sample = quarantine[sample_cols].head(100).fillna("").to_dict(orient="records")

    return {
        "generated_at": quality.get("generated_at", ""),
        "kpis": {
            "raw": int(len(raw)),
            "cleaned": int(len(cleaned)),
            "quarantined": int(len(quarantine)),
            "revenue": _round2(total_sales.iloc[0]["value"]),
            "aov": _round2(aov.iloc[0]["value"]),
        },
        "quality": [
            {"check": str(r["check_name"]), "issues": int(r["issue_count"])}
            for r in quality["checks"]
        ],
        "monthly": [
            {"month": str(r["month"])[:7], "revenue": _round2(r["revenue"])}
            for _, r in monthly.iterrows()
        ],
        "category": [
            {"category": str(r["category"]), "revenue": _round2(r["revenue"])}
            for _, r in category.iterrows()
        ],
        "country": [
            {"country": str(r["country"]), "revenue": _round2(r["revenue"])}
            for _, r in country.head(15).iterrows()
        ],
        "products": [
            {
                "product": str(r["product_name"]),
                "quantity": int(float(r["total_quantity"])),
                "revenue": _round2(r["revenue"]),
            }
            for _, r in products.iterrows()
        ],
        "summary": [
            {"metric": str(r["metric"]), "value": str(r["value"])}
            for _, r in summary.iterrows()
        ],
        "quarantine_reasons": [
            {"reason": str(r["reason"]), "count": int(r["count"])}
            for _, r in breakdown.iterrows()
        ],
        "quarantine_sample": sample,
        "quarantine_sample_size": int(len(quarantine)),
    }


def main() -> None:
    """CLI entry point: write assets/site-data.js."""
    parser = argparse.ArgumentParser(description="Build static site data.")
    parser.add_argument("--output", type=Path, default=OUT)
    args = parser.parse_args()
    payload = "window.SITE_DATA = " + json.dumps(build(), ensure_ascii=False) + ";\n"
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(payload, encoding="utf-8")
    print(f"Wrote {args.output} ({len(payload) // 1024} KB)")


if __name__ == "__main__":
    main()
