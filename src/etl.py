"""Clean Olist source files and create analytics-ready CSV tables."""
from pathlib import Path
import pandas as pd
import numpy as np
from src.config import RAW_DIR, PROCESSED_DIR, FILES

DATE_COLUMNS = {
    "orders": ["order_purchase_timestamp", "order_approved_at",
               "order_delivered_carrier_date", "order_delivered_customer_date",
               "order_estimated_delivery_date"],
    "reviews": ["review_creation_date", "review_answer_timestamp"],
}

def read_source(key: str) -> pd.DataFrame:
    path = RAW_DIR / FILES[key]
    if not path.exists():
        raise FileNotFoundError(
            f"Missing {path.name}. Download the Olist dataset and place it in {RAW_DIR}"
        )
    return pd.read_csv(path)

def clean_sources():
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    data = {key: read_source(key) for key in FILES}

    for key, cols in DATE_COLUMNS.items():
        for col in cols:
            if col in data[key]:
                data[key][col] = pd.to_datetime(data[key][col], errors="coerce")

    # Remove exact duplicate source records.
    for key, df in data.items():
        data[key] = df.drop_duplicates().copy()

    # Standardise text dimensions and make missing categories explicit.
    products = data["products"].copy()
    products["product_category_name"] = (
        products["product_category_name"].fillna("Unknown").astype(str).str.strip()
    )
    translation = data["category_translation"].drop_duplicates(
        subset=["product_category_name"]
    )
    products = products.merge(translation, on="product_category_name", how="left")
    products["product_category_name_english"] = (
        products["product_category_name_english"]
        .fillna(products["product_category_name"])
        .replace({"": "Unknown"})
    )

    # Keep only valid order-item records with non-negative monetary values.
    items = data["items"].copy()
    items["price"] = pd.to_numeric(items["price"], errors="coerce")
    items["freight_value"] = pd.to_numeric(items["freight_value"], errors="coerce")
    items = items.dropna(subset=["order_id", "product_id", "price", "freight_value"])
    items = items[(items["price"] >= 0) & (items["freight_value"] >= 0)]

    # Source entity tables.
    outputs = {
        "orders": data["orders"],
        "order_items": items,
        "payments": data["payments"],
        "reviews": data["reviews"],
        "customers": data["customers"],
        "products": products,
        "sellers": data["sellers"],
    }

    for name, df in outputs.items():
        df.to_csv(PROCESSED_DIR / f"{name}.csv", index=False)

    # Safe one-row-per-order aggregates avoid fan-out when combining source tables.
    item_agg = items.groupby("order_id", as_index=False).agg(
        item_revenue=("price", "sum"),
        freight_revenue=("freight_value", "sum"),
        item_count=("order_item_id", "count"),
    )
    item_agg["gross_item_value"] = item_agg["item_revenue"] + item_agg["freight_revenue"]

    payment_agg = data["payments"].groupby("order_id", as_index=False).agg(
        payment_value=("payment_value", "sum"),
        payment_count=("payment_sequential", "count"),
    )
    order_fact = data["orders"].merge(item_agg, on="order_id", how="left")
    order_fact = order_fact.merge(payment_agg, on="order_id", how="left")
    order_fact = order_fact.merge(
        data["customers"][["customer_id", "customer_unique_id",
                           "customer_city", "customer_state"]],
        on="customer_id", how="left"
    )
    order_fact.to_csv(PROCESSED_DIR / "fact_orders.csv", index=False)

    item_fact = items.merge(
        data["orders"][["order_id", "customer_id", "order_status",
                        "order_purchase_timestamp"]], on="order_id", how="left"
    )
    item_fact = item_fact.merge(
        data["customers"][["customer_id", "customer_unique_id",
                           "customer_city", "customer_state"]], on="customer_id", how="left"
    )
    item_fact = item_fact.merge(
        products[["product_id", "product_category_name_english"]],
        on="product_id", how="left"
    )
    item_fact = item_fact.merge(
        data["sellers"][["seller_id", "seller_city", "seller_state"]],
        on="seller_id", how="left"
    )
    item_fact["revenue_including_freight"] = item_fact["price"] + item_fact["freight_value"]
    item_fact.to_csv(PROCESSED_DIR / "fact_order_items.csv", index=False)

    print(f"ETL complete. Processed files saved to: {PROCESSED_DIR}")
    print(f"Orders: {len(data['orders']):,} | Order items: {len(items):,} | Customers: {len(data['customers']):,}")

if __name__ == "__main__":
    clean_sources()
