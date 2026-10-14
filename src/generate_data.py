"""Generate reproducible synthetic e-commerce sales data with injected defects."""

from __future__ import annotations

import argparse
import random
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
from faker import Faker

DEFAULT_SEED = 42
DEFAULT_ROWS = 7_500
EARLIEST_DATE = datetime(2010, 1, 1)

CANONICAL_CATEGORIES = [
    "Electronics",
    "Clothing",
    "Home & Garden",
    "Sports",
    "Books",
    "Beauty",
    "Toys",
    "Food & Beverage",
]

CATEGORY_VARIANTS = {
    "Electronics": ["electronics", "ELECTRONICS", "Electrnics", "Elec"],
    "Clothing": ["clothing", "CLOTHING", "Cloth", "Clothes"],
    "Home & Garden": ["home & garden", "Home and Garden", "HomeGarden", "Garden"],
    "Sports": ["sports", "SPORTS", "Sporting"],
    "Books": ["books", "BOOKS", "Book"],
    "Beauty": ["beauty", "BEAUTY", "Beaut"],
    "Toys": ["toys", "TOYS", "Toy"],
    "Food & Beverage": ["food & beverage", "Food and Bev", "FoodBeverage"],
}

CANONICAL_PAYMENTS = [
    "Credit Card",
    "PayPal",
    "Bank Transfer",
    "Cash",
    "Crypto",
    "Other",
]

PAYMENT_VARIANTS = {
    "Credit Card": ["cc", "credit card", "CreditCard", "CC"],
    "PayPal": ["paypal", "Pay Pal", "pay pal"],
    "Bank Transfer": ["bank transfer", "BankTransfer", "wire"],
    "Cash": ["cash", "CASH"],
    "Crypto": ["crypto", "cryptocurrency", "bitcoin"],
    "Other": ["other", "OTH"],
}

STATUSES = ["completed", "canceled", "refunded", "pending"]
STATUS_WEIGHTS = [0.75, 0.10, 0.08, 0.07]

# fmt: off
PRODUCTS: list[dict[str, str | float]] = [
    {"product_id": "P001", "product_name": "Wireless Mouse", "category": "Electronics", "base_price": 29.99},  # noqa: E501
    {"product_id": "P002", "product_name": "Mechanical Keyboard", "category": "Electronics", "base_price": 89.99},  # noqa: E501
    {"product_id": "P003", "product_name": "USB-C Cable", "category": "Electronics", "base_price": 12.50},  # noqa: E501
    {"product_id": "P004", "product_name": "Webcam 1080p", "category": "Electronics", "base_price": 59.99},  # noqa: E501
    {"product_id": "P005", "product_name": "Laptop Stand", "category": "Electronics", "base_price": 34.99},  # noqa: E501
    {"product_id": "P006", "product_name": "Cotton T-Shirt", "category": "Clothing", "base_price": 19.99},  # noqa: E501
    {"product_id": "P007", "product_name": "Denim Jeans", "category": "Clothing", "base_price": 49.99},  # noqa: E501
    {"product_id": "P008", "product_name": "Running Shoes", "category": "Clothing", "base_price": 79.99},  # noqa: E501
    {"product_id": "P009", "product_name": "Wool Scarf", "category": "Clothing", "base_price": 24.99},  # noqa: E501
    {"product_id": "P010", "product_name": "Leather Belt", "category": "Clothing", "base_price": 34.99},  # noqa: E501
    {"product_id": "P011", "product_name": "Coffee Maker", "category": "Home & Garden", "base_price": 99.99},  # noqa: E501
    {"product_id": "P012", "product_name": "Vacuum Bottle", "category": "Home & Garden", "base_price": 22.99},  # noqa: E501
    {"product_id": "P013", "product_name": "Kitchen Towel Set", "category": "Home & Garden", "base_price": 15.99},  # noqa: E501
    {"product_id": "P014", "product_name": "LED Desk Lamp", "category": "Home & Garden", "base_price": 32.99},  # noqa: E501
    {"product_id": "P015", "product_name": "Throw Pillow", "category": "Home & Garden", "base_price": 18.99},  # noqa: E501
    {"product_id": "P016", "product_name": "Yoga Mat", "category": "Sports", "base_price": 29.99},  # noqa: E501
    {"product_id": "P017", "product_name": "Resistance Bands", "category": "Sports", "base_price": 19.99},  # noqa: E501
    {"product_id": "P018", "product_name": "Water Bottle", "category": "Sports", "base_price": 14.99},  # noqa: E501
    {"product_id": "P019", "product_name": "Dumbbell 5kg", "category": "Sports", "base_price": 24.99},  # noqa: E501
    {"product_id": "P020", "product_name": "Tennis Balls", "category": "Sports", "base_price": 9.99},  # noqa: E501
    {"product_id": "P021", "product_name": "Fiction Novel", "category": "Books", "base_price": 14.99},  # noqa: E501
    {"product_id": "P022", "product_name": "Cookbook", "category": "Books", "base_price": 24.99},  # noqa: E501
    {"product_id": "P023", "product_name": "Notebook", "category": "Books", "base_price": 6.99},  # noqa: E501
    {"product_id": "P024", "product_name": "Sketch Pad", "category": "Books", "base_price": 8.99},  # noqa: E501
    {"product_id": "P025", "product_name": "Desk Planner", "category": "Books", "base_price": 12.99},  # noqa: E501
    {"product_id": "P026", "product_name": "Face Moisturizer", "category": "Beauty", "base_price": 19.99},  # noqa: E501
    {"product_id": "P027", "product_name": "Lip Balm", "category": "Beauty", "base_price": 4.99},  # noqa: E501
    {"product_id": "P028", "product_name": "Shampoo", "category": "Beauty", "base_price": 9.99},  # noqa: E501
    {"product_id": "P029", "product_name": "Hand Cream", "category": "Beauty", "base_price": 7.99},  # noqa: E501
    {"product_id": "P030", "product_name": "Sunscreen SPF50", "category": "Beauty", "base_price": 14.99},  # noqa: E501
    {"product_id": "P031", "product_name": "Building Blocks", "category": "Toys", "base_price": 29.99},  # noqa: E501
    {"product_id": "P032", "product_name": "Plush Bear", "category": "Toys", "base_price": 19.99},  # noqa: E501
    {"product_id": "P033", "product_name": "Board Game", "category": "Toys", "base_price": 34.99},  # noqa: E501
    {"product_id": "P034", "product_name": "Puzzle 1000pc", "category": "Toys", "base_price": 16.99},  # noqa: E501
    {"product_id": "P035", "product_name": "Remote Car", "category": "Toys", "base_price": 39.99},  # noqa: E501
    {"product_id": "P036", "product_name": "Organic Coffee", "category": "Food & Beverage", "base_price": 14.99},  # noqa: E501
    {"product_id": "P037", "product_name": "Green Tea", "category": "Food & Beverage", "base_price": 9.99},  # noqa: E501
    {"product_id": "P038", "product_name": "Protein Bar", "category": "Food & Beverage", "base_price": 2.99},  # noqa: E501
    {"product_id": "P039", "product_name": "Sparkling Water", "category": "Food & Beverage", "base_price": 1.49},  # noqa: E501
    {"product_id": "P040", "product_name": "Oatmeal Cookies", "category": "Food & Beverage", "base_price": 4.99},  # noqa: E501
]
# fmt: on


def _random_date(rng: np.random.Generator, fake: Faker) -> datetime:  # noqa: ARG001
    """Return a random datetime within the last 4 years."""
    end = datetime.now()
    start = end - timedelta(days=4 * 365)
    delta = end - start
    seconds = rng.integers(0, int(delta.total_seconds()))
    return start + timedelta(seconds=int(seconds))


def _generate_base_rows(n: int, rng: np.random.Generator, fake: Faker) -> pd.DataFrame:
    """Generate clean baseline sales rows."""
    products_df = pd.DataFrame(PRODUCTS)
    product_indices = rng.integers(0, len(products_df), size=n)
    quantities = rng.integers(1, 10, size=n)
    # price varies around base price by -20% to +20%
    price_multipliers = rng.uniform(0.8, 1.2, size=n)
    unit_prices = (products_df.iloc[product_indices]["base_price"].values * price_multipliers).round(2)  # noqa: E501

    rows: list[dict[str, object]] = []
    for i in range(n):
        product = products_df.iloc[product_indices[i]]
        order_date = _random_date(rng, fake)
        rows.append(
            {
                "row_id": f"R{i+1:07d}",
                "order_id": f"ORD-{rng.integers(1, 1_000_000):07d}",
                "order_date": order_date.strftime("%Y-%m-%d"),
                "customer_id": f"C{rng.integers(1, 500_000):07d}",
                "customer_name": fake.name(),
                "customer_email": fake.email(),
                "product_id": product["product_id"],
                "product_name": product["product_name"],
                "category": product["category"],
                "quantity": int(quantities[i]),
                "unit_price": float(unit_prices[i]),
                "discount": float(round(rng.choice([0.0, 0.05, 0.10, 0.15, 0.20, 0.25]), 2)),
                "payment_method": rng.choice(CANONICAL_PAYMENTS),
                "country": fake.country(),
                "order_status": rng.choice(STATUSES, p=STATUS_WEIGHTS),
            }
        )

    return pd.DataFrame(rows)


def _inject_defects(df: pd.DataFrame, rng: np.random.Generator) -> pd.DataFrame:
    """Inject a reproducible mix of data quality defects."""
    df = df.copy()
    # Cast numeric columns to object so invalid values can be injected.
    df = df.astype({"quantity": object, "unit_price": object, "discount": object})
    n = len(df)

    def _pick_indices(count: int) -> list[int]:
        indices = rng.choice(n, size=min(count, n), replace=False)
        return [int(i) for i in indices]

    # 1. Duplicate order lines (~150 copies)
    dup_indices = _pick_indices(150)
    dup_rows = df.iloc[dup_indices].copy()
    df = pd.concat([df, dup_rows], ignore_index=True)

    # 2. Missing order_id (~100)
    for idx in _pick_indices(100):
        df.at[idx, "order_id"] = ""

    # 3. Invalid/missing dates (~120)
    invalid_date_values = ["", "not-a-date", "2024-13-45", "2010-00-00", "01/01/2024"]
    future_date = (datetime.now() + timedelta(days=int(rng.integers(1, 500)))).strftime("%Y-%m-%d")
    invalid_date_values.append(future_date)
    for idx in _pick_indices(120):
        df.at[idx, "order_date"] = rng.choice(invalid_date_values)

    # 4. Invalid quantities (~80)
    for idx in _pick_indices(80):
        df.at[idx, "quantity"] = rng.choice([-1, 0, "abc", "", "N/A"])

    # 5. Invalid unit prices (~80)
    for idx in _pick_indices(80):
        df.at[idx, "unit_price"] = rng.choice([-9.99, 0, "free", "", "N/A"])

    # 6. Malformed emails (~150)
    bad_emails = ["not-an-email", "missing@domain", "@nodomain.com", "spaces in@email.com", ""]
    for idx in _pick_indices(150):
        df.at[idx, "customer_email"] = rng.choice(bad_emails)

    # 7. Inconsistent categories (~200)
    for idx in _pick_indices(200):
        canonical = rng.choice(CANONICAL_CATEGORIES)
        variants = CATEGORY_VARIANTS[canonical]
        df.at[idx, "category"] = rng.choice(variants)

    # 8. Inconsistent payment methods (~150)
    for idx in _pick_indices(150):
        canonical = rng.choice(CANONICAL_PAYMENTS)
        variants = PAYMENT_VARIANTS[canonical]
        df.at[idx, "payment_method"] = rng.choice(variants)

    # 9. Missing customer or product names (~100)
    for idx in _pick_indices(100):
        column = rng.choice(["customer_name", "product_name"])
        df.at[idx, column] = ""

    # 10. Bad discount values (~60)
    for idx in _pick_indices(60):
        df.at[idx, "discount"] = rng.choice([-0.1, 1.5, "20%", "", "half"])

    # 11. Canceled/refunded rows already present in baseline due to status weights.

    # 12. Inconsistent country names (~100)
    country_variants = ["USA", "uk", "FR", "Deutschland", "United States of America", "brasil", ""]
    for idx in _pick_indices(100):
        df.at[idx, "country"] = rng.choice(country_variants)

    return df


def generate_sales_data(
    *,
    rows: int = DEFAULT_ROWS,
    seed: int = DEFAULT_SEED,
) -> pd.DataFrame:
    """Generate a reproducible synthetic sales dataset with injected defects."""
    rng = np.random.default_rng(seed)
    fake = Faker(seed=seed)
    Faker.seed(seed)
    random.seed(seed)

    df = _generate_base_rows(rows, rng, fake)
    df = _inject_defects(df, rng)
    # Shuffle so defects are not clustered at the bottom
    df = df.sample(frac=1, random_state=seed).reset_index(drop=True)
    return df


def save_raw_data(df: pd.DataFrame, output_path: Path) -> None:
    """Write raw sales data to CSV."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, index=False)


def main() -> None:
    """CLI entry point for generating synthetic sales data."""
    parser = argparse.ArgumentParser(description="Generate synthetic sales data.")
    parser.add_argument("--rows", type=int, default=DEFAULT_ROWS, help="Number of base rows.")
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED, help="Random seed.")
    parser.add_argument("--output", type=Path, default=Path("data/raw/raw_sales.csv"))
    args = parser.parse_args()

    df = generate_sales_data(rows=args.rows, seed=args.seed)
    save_raw_data(df, args.output)
    print(f"Generated {len(df)} rows at {args.output}")


if __name__ == "__main__":
    main()
