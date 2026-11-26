"""Leakage-safe customer feature table for repeat-purchase prediction.

Prediction moment
-----------------
For every customer (``customer_unique_id``) we look at their FIRST delivered
order and "stand" at ``prediction_time = delivered_customer_date + GRACE_DAYS``.
Everything used as a feature is known by that moment:

* basket, price, freight, payment and product attributes of the first order
* delivery speed / lateness of the first order
* the review score of the first order (only if it was answered before
  ``prediction_time``; otherwise NaN)
* calendar and geography of the first order

Label
-----
``repeat_purchase = 1`` if the customer places another order with
``order_purchase_timestamp`` in ``(prediction_time, prediction_time + horizon]``.

Customers whose observation window would extend past the end of the dataset
are dropped (right-censoring), otherwise they would be wrongly labelled 0.

Expected raw files (standard Olist names, in ``data/raw``)::

    olist_customers_dataset.csv        olist_order_items_dataset.csv
    olist_orders_dataset.csv           olist_order_payments_dataset.csv
    olist_order_reviews_dataset.csv    olist_products_dataset.csv
    product_category_name_translation.csv
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

GRACE_DAYS = 7
DEFAULT_HORIZON_DAYS = 180
TOP_N_LEVELS = 10

FILES = {
    "customers": "olist_customers_dataset.csv",
    "orders": "olist_orders_dataset.csv",
    "items": "olist_order_items_dataset.csv",
    "payments": "olist_order_payments_dataset.csv",
    "reviews": "olist_order_reviews_dataset.csv",
    "products": "olist_products_dataset.csv",
    "translation": "product_category_name_translation.csv",
}

REQUIRED_COLUMNS = {
    "customers": {"customer_id", "customer_unique_id", "customer_state"},
    "orders": {
        "order_id",
        "customer_id",
        "order_status",
        "order_purchase_timestamp",
        "order_delivered_customer_date",
        "order_estimated_delivery_date",
    },
    "items": {"order_id", "product_id", "seller_id", "price", "freight_value"},
    "payments": {"order_id", "payment_type", "payment_installments", "payment_value"},
    "reviews": {"order_id", "review_score", "review_answer_timestamp"},
    "products": {"product_id", "product_category_name"},
    "translation": {"product_category_name", "product_category_name_english"},
}

DATE_COLUMNS = {
    "orders": [
        "order_purchase_timestamp",
        "order_delivered_customer_date",
        "order_estimated_delivery_date",
    ],
    "reviews": ["review_answer_timestamp"],
}


def load_raw(raw_dir: str | Path) -> dict[str, pd.DataFrame]:
    """Read the Olist CSVs, validate columns and parse dates."""
    raw_dir = Path(raw_dir)
    tables: dict[str, pd.DataFrame] = {}
    for key, filename in FILES.items():
        path = raw_dir / filename
        if not path.exists():
            raise FileNotFoundError(
                f"Missing {path}. Run `python scripts/download_olist.py` first "
                "(or `make data-real`)."
            )
        df = pd.read_csv(path)
        missing = REQUIRED_COLUMNS[key] - set(df.columns)
        if missing:
            raise ValueError(f"{filename} is missing columns: {sorted(missing)}")
        for col in DATE_COLUMNS.get(key, []):
            df[col] = pd.to_datetime(df[col], errors="coerce")
        tables[key] = df
    return tables


def _group_rare(series: pd.Series, top_n: int = TOP_N_LEVELS) -> pd.Series:
    """Keep the ``top_n`` most frequent levels, bucket the rest as 'other'."""
    keep = series.value_counts().nlargest(top_n).index
    return series.where(series.isin(keep), "other")


def build_customer_table(
    tables: dict[str, pd.DataFrame],
    horizon_days: int = DEFAULT_HORIZON_DAYS,
) -> pd.DataFrame:
    """Return one row per customer with features, ``prediction_time`` and label."""
    customers = tables["customers"][["customer_id", "customer_unique_id", "customer_state"]]
    orders = tables["orders"].merge(customers, on="customer_id", how="inner")
    orders = orders.dropna(subset=["order_purchase_timestamp"])

    # ---- first delivered order per customer ---------------------------------
    delivered = orders[
        (orders["order_status"] == "delivered")
        & orders["order_delivered_customer_date"].notna()
    ].sort_values(["customer_unique_id", "order_purchase_timestamp", "order_id"])
    first = delivered.drop_duplicates("customer_unique_id", keep="first").copy()
    first["prediction_time"] = first["order_delivered_customer_date"] + pd.Timedelta(
        days=GRACE_DAYS
    )

    # ---- label: any later order (any status) inside the horizon -------------
    purchases = orders[["customer_unique_id", "order_purchase_timestamp"]].merge(
        first[["customer_unique_id", "prediction_time"]], on="customer_unique_id"
    )
    in_window = (
        purchases["order_purchase_timestamp"] > purchases["prediction_time"]
    ) & (
        purchases["order_purchase_timestamp"]
        <= purchases["prediction_time"] + pd.Timedelta(days=horizon_days)
    )
    repeaters = set(purchases.loc[in_window, "customer_unique_id"])
    first["repeat_purchase"] = first["customer_unique_id"].isin(repeaters).astype(int)

    # ---- right-censoring ------------------------------------------------------
    data_end = orders["order_purchase_timestamp"].max()
    first = first[first["prediction_time"] + pd.Timedelta(days=horizon_days) <= data_end]

    # ---- item-level features of the first order -------------------------------
    products = tables["products"].merge(
        tables["translation"], on="product_category_name", how="left"
    )
    products["category"] = (
        products["product_category_name_english"]
        .fillna(products["product_category_name"])
        .fillna("unknown")
    )
    items = tables["items"].merge(products[["product_id", "category"]], on="product_id", how="left")
    items["category"] = items["category"].fillna("unknown")
    item_agg = items.groupby("order_id").agg(
        n_items=("product_id", "size"),
        n_sellers=("seller_id", "nunique"),
        n_categories=("category", "nunique"),
        items_value=("price", "sum"),
        freight_value=("freight_value", "sum"),
        main_category=("category", lambda s: s.mode().iat[0]),
    )
    item_agg["freight_ratio"] = item_agg["freight_value"] / (
        item_agg["items_value"] + item_agg["freight_value"]
    ).replace(0, np.nan)

    # ---- payment features -----------------------------------------------------
    pay = tables["payments"]
    pay_agg = pay.groupby("order_id").agg(
        payment_total=("payment_value", "sum"),
        max_installments=("payment_installments", "max"),
        n_payment_methods=("payment_type", "nunique"),
        main_payment_type=("payment_type", lambda s: s.mode().iat[0]),
    )

    # ---- review (only if answered before prediction_time) ---------------------
    rev = tables["reviews"].merge(
        first[["order_id", "prediction_time"]], on="order_id", how="inner"
    )
    rev = rev[rev["review_answer_timestamp"] <= rev["prediction_time"]]
    rev_agg = rev.groupby("order_id").agg(review_score=("review_score", "mean"))

    df = (
        first.merge(item_agg, left_on="order_id", right_index=True, how="left")
        .merge(pay_agg, left_on="order_id", right_index=True, how="left")
        .merge(rev_agg, left_on="order_id", right_index=True, how="left")
    )

    # ---- delivery + calendar features -----------------------------------------
    purchase = df["order_purchase_timestamp"]
    delivered_at = df["order_delivered_customer_date"]
    df["delivery_days"] = (delivered_at - purchase).dt.total_seconds() / 86400
    df["delivery_delay_days"] = (
        delivered_at - df["order_estimated_delivery_date"]
    ).dt.total_seconds() / 86400
    df["is_late"] = (df["delivery_delay_days"] > 0).astype(int)
    df["purchase_hour"] = purchase.dt.hour
    df["purchase_dow"] = purchase.dt.day_of_week
    df["purchase_month"] = purchase.dt.month

    df["main_category"] = _group_rare(df["main_category"].fillna("unknown"))
    df["customer_state"] = _group_rare(df["customer_state"].fillna("unknown"))
    df["main_payment_type"] = df["main_payment_type"].fillna("unknown")

    keep = [
        "customer_unique_id",
        "prediction_time",
        "repeat_purchase",
        "n_items",
        "n_sellers",
        "n_categories",
        "items_value",
        "freight_value",
        "freight_ratio",
        "payment_total",
        "max_installments",
        "n_payment_methods",
        "review_score",
        "delivery_days",
        "delivery_delay_days",
        "is_late",
        "purchase_hour",
        "purchase_dow",
        "purchase_month",
        "main_category",
        "customer_state",
        "main_payment_type",
    ]
    return df[keep].reset_index(drop=True)


CATEGORICAL = ["main_category", "customer_state", "main_payment_type"]


def to_model_matrix(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.Series]:
    """One-hot encode categoricals; return (X, y)."""
    y = df["repeat_purchase"]
    X = df.drop(columns=["customer_unique_id", "prediction_time", "repeat_purchase"])
    X = pd.get_dummies(X, columns=CATEGORICAL, dtype=float)
    X.columns = [str(c).replace("[", "(").replace("]", ")").replace("<", "lt") for c in X.columns]
    return X, y
