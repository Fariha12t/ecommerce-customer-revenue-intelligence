"""Late-delivery risk model: which orders will arrive after the promised date?

Why this model
--------------
Late delivery is the strongest driver of bad reviews in this dataset, and it can
be predicted at the moment the customer checks out, so the business could act
(re-promise the date, pick a faster carrier, prioritise the order).

Prediction moment: order purchase time. Only information known then is used
(basket, weight/size, seller and customer location, distance, promised delivery
window, payment choice, calendar). Delivery timestamps and reviews are NOT used.

Usage::

    python -m src.ml.late_delivery
    python -m src.ml.late_delivery --no-mlflow

Outputs in ``reports/generated/ml_late/``: metrics.json, shap_summary.png,
shap_importance.csv, order_risk_scores.csv (for Power BI, join on order_id).

Extra raw files needed besides those used elsewhere:
``olist_sellers_dataset.csv`` and ``olist_geolocation_dataset.csv``.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import shap  # noqa: E402
from sklearn.impute import SimpleImputer  # noqa: E402
from sklearn.linear_model import LogisticRegression  # noqa: E402
from sklearn.metrics import average_precision_score, roc_auc_score  # noqa: E402
from sklearn.pipeline import make_pipeline  # noqa: E402
from sklearn.preprocessing import StandardScaler  # noqa: E402
from xgboost import XGBClassifier  # noqa: E402

from src.ml.features import _group_rare, load_raw  # noqa: E402

SEED = 42
TEST_FRACTION = 0.25
CATEGORICAL = ["main_category", "customer_state", "seller_state", "main_payment_type"]
PRODUCT_DIM_COLUMNS = {
    "product_weight_g",
    "product_length_cm",
    "product_height_cm",
    "product_width_cm",
}


def _read_extra(raw_dir: Path, filename: str, required: set[str]) -> pd.DataFrame:
    path = raw_dir / filename
    if not path.exists():
        raise FileNotFoundError(f"Missing {path}. Run `python scripts/download_olist.py` first.")
    df = pd.read_csv(path)
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"{filename} is missing columns: {sorted(missing)}")
    return df


def haversine_km(lat1, lng1, lat2, lng2) -> np.ndarray:
    lat1, lng1, lat2, lng2 = map(np.radians, (lat1, lng1, lat2, lng2))
    a = np.sin((lat2 - lat1) / 2) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin((lng2 - lng1) / 2) ** 2
    return 6371.0 * 2 * np.arcsin(np.sqrt(a))


def build_order_table(raw_dir: str | Path) -> pd.DataFrame:
    """One row per delivered order with purchase-time features and ``is_late``."""
    raw_dir = Path(raw_dir)
    t = load_raw(raw_dir)
    sellers = _read_extra(raw_dir, "olist_sellers_dataset.csv",
                          {"seller_id", "seller_zip_code_prefix", "seller_state"})
    geo = _read_extra(raw_dir, "olist_geolocation_dataset.csv",
                      {"geolocation_zip_code_prefix", "geolocation_lat", "geolocation_lng"})
    if not PRODUCT_DIM_COLUMNS <= set(t["products"].columns):
        raise ValueError(f"olist_products_dataset.csv needs columns {sorted(PRODUCT_DIM_COLUMNS)}")
    if "customer_zip_code_prefix" not in t["customers"].columns:
        raise ValueError("olist_customers_dataset.csv needs customer_zip_code_prefix")

    # ---- cohort and label -----------------------------------------------------
    o = t["orders"]
    o = o[
        (o["order_status"] == "delivered")
        & o["order_delivered_customer_date"].notna()
        & o["order_estimated_delivery_date"].notna()
        & o["order_purchase_timestamp"].notna()
    ].copy()
    o = o.merge(
        t["customers"][["customer_id", "customer_zip_code_prefix", "customer_state"]],
        on="customer_id",
        how="inner",
    )
    o["is_late"] = (o["order_delivered_customer_date"] > o["order_estimated_delivery_date"]).astype(int)
    o["estimated_days"] = (
        o["order_estimated_delivery_date"] - o["order_purchase_timestamp"]
    ).dt.total_seconds() / 86400

    # ---- items, products, sellers --------------------------------------------
    prods = t["products"].merge(t["translation"], on="product_category_name", how="left")
    prods["category"] = (
        prods["product_category_name_english"].fillna(prods["product_category_name"]).fillna("unknown")
    )
    prods["volume_cm3"] = (
        prods["product_length_cm"] * prods["product_height_cm"] * prods["product_width_cm"]
    )
    items = (
        t["items"]
        .merge(prods[["product_id", "category", "product_weight_g", "volume_cm3"]], on="product_id", how="left")
        .merge(sellers[["seller_id", "seller_zip_code_prefix", "seller_state"]], on="seller_id", how="left")
    )
    items["category"] = items["category"].fillna("unknown")

    main_seller = (
        items.sort_values(["order_id", "price"], ascending=[True, False])
        .drop_duplicates("order_id")[["order_id", "seller_zip_code_prefix", "seller_state"]]
    )
    agg = items.groupby("order_id").agg(
        n_items=("product_id", "size"),
        n_sellers=("seller_id", "nunique"),
        n_categories=("category", "nunique"),
        items_value=("price", "sum"),
        freight_value=("freight_value", "sum"),
        total_weight_g=("product_weight_g", lambda s: s.sum(min_count=1)),
        max_volume_cm3=("volume_cm3", "max"),
        main_category=("category", lambda s: s.mode().iat[0]),
    )
    agg["freight_ratio"] = agg["freight_value"] / (agg["items_value"] + agg["freight_value"]).replace(0, np.nan)

    pay = t["payments"].groupby("order_id").agg(
        max_installments=("payment_installments", "max"),
        main_payment_type=("payment_type", lambda s: s.mode().iat[0]),
    )

    # ---- distance between customer and (main) seller ---------------------------
    geo_avg = geo.groupby("geolocation_zip_code_prefix").agg(
        lat=("geolocation_lat", "mean"), lng=("geolocation_lng", "mean")
    )
    df = (
        o.merge(agg, left_on="order_id", right_index=True, how="inner")
        .merge(pay, left_on="order_id", right_index=True, how="left")
        .merge(main_seller, on="order_id", how="left")
    )
    cust_geo = geo_avg.rename(columns={"lat": "cust_lat", "lng": "cust_lng"})
    sell_geo = geo_avg.rename(columns={"lat": "sell_lat", "lng": "sell_lng"})
    df = df.merge(cust_geo, left_on="customer_zip_code_prefix", right_index=True, how="left")
    df = df.merge(sell_geo, left_on="seller_zip_code_prefix", right_index=True, how="left")
    df["distance_km"] = haversine_km(df["cust_lat"], df["cust_lng"], df["sell_lat"], df["sell_lng"])
    df["same_state"] = (df["customer_state"] == df["seller_state"]).astype(int)

    # ---- calendar + grouping ----------------------------------------------------
    p = df["order_purchase_timestamp"]
    df["purchase_hour"] = p.dt.hour
    df["purchase_dow"] = p.dt.day_of_week
    df["purchase_month"] = p.dt.month
    df["main_category"] = _group_rare(df["main_category"].fillna("unknown"))
    df["customer_state"] = _group_rare(df["customer_state"].fillna("unknown"))
    df["seller_state"] = _group_rare(df["seller_state"].fillna("unknown"))
    df["main_payment_type"] = df["main_payment_type"].fillna("unknown")

    keep = [
        "order_id", "order_purchase_timestamp", "is_late",
        "n_items", "n_sellers", "n_categories", "items_value", "freight_value", "freight_ratio",
        "total_weight_g", "max_volume_cm3", "estimated_days", "distance_km", "same_state",
        "max_installments", "purchase_hour", "purchase_dow", "purchase_month",
        *CATEGORICAL,
    ]
    return df[keep].reset_index(drop=True)


def to_model_matrix(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.Series]:
    y = df["is_late"]
    X = df.drop(columns=["order_id", "order_purchase_timestamp", "is_late"])
    X = pd.get_dummies(X, columns=CATEGORICAL, dtype=float)
    X.columns = [str(c).replace("[", "(").replace("]", ")").replace("<", "lt") for c in X.columns]
    return X, y


def time_split(df: pd.DataFrame, test_fraction: float = TEST_FRACTION):
    df = df.sort_values("order_purchase_timestamp").reset_index(drop=True)
    cut = int(len(df) * (1 - test_fraction))
    return df.iloc[:cut], df.iloc[cut:]


def capture_at(y_true: np.ndarray, score: np.ndarray, frac: float) -> float:
    """Share of all late orders found inside the top ``frac`` riskiest orders."""
    n_top = max(1, int(len(score) * frac))
    top = np.argsort(-score)[:n_top]
    total = y_true.sum()
    return float(y_true[top].sum() / total) if total > 0 else float("nan")


def evaluate(y_true, score) -> dict[str, float]:
    y_true = np.asarray(y_true)
    score = np.asarray(score)
    base = float(y_true.mean())
    n_top = max(1, int(len(score) * 0.10))
    top_rate = float(y_true[np.argsort(-score)[:n_top]].mean())
    return {
        "roc_auc": float(roc_auc_score(y_true, score)),
        "pr_auc": float(average_precision_score(y_true, score)),
        "base_late_rate": base,
        "top_decile_late_rate": top_rate,
        "top_decile_lift": top_rate / base if base > 0 else float("nan"),
        "late_orders_captured_in_top_20pct": capture_at(y_true, score, 0.20),
    }


def run(raw_dir: str, out_dir: str, use_mlflow: bool) -> dict:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)

    orders = build_order_table(raw_dir)
    if orders["is_late"].nunique() < 2:
        raise RuntimeError("Only one class present in is_late; check the data.")
    train_df, test_df = time_split(orders)
    X_train, y_train = to_model_matrix(train_df)
    X_test, y_test = to_model_matrix(test_df)
    X_test = X_test.reindex(columns=X_train.columns, fill_value=0.0)

    xgb = XGBClassifier(
        n_estimators=400, max_depth=5, learning_rate=0.05, subsample=0.8, colsample_bytree=0.8,
        min_child_weight=10, reg_lambda=5.0, eval_metric="aucpr", random_state=SEED, n_jobs=-1,
    )
    xgb.fit(X_train, y_train)
    logit = make_pipeline(
        SimpleImputer(strategy="median"), StandardScaler(),
        LogisticRegression(max_iter=1000, class_weight="balanced", random_state=SEED),
    )
    logit.fit(X_train, y_train)

    metrics = {
        "n_orders": int(len(orders)),
        "n_train": int(len(train_df)),
        "n_test": int(len(test_df)),
        "test_period_start": str(test_df["order_purchase_timestamp"].min().date()),
        "xgboost": evaluate(y_test, xgb.predict_proba(X_test)[:, 1]),
        "logistic_baseline": evaluate(y_test, logit.predict_proba(X_test)[:, 1]),
    }

    sample = X_test.sample(min(2000, len(X_test)), random_state=SEED)
    sv = shap.TreeExplainer(xgb).shap_values(sample)
    shap.summary_plot(sv, sample, show=False, max_display=15)
    plt.tight_layout()
    plt.savefig(out / "shap_summary.png", dpi=150, bbox_inches="tight")
    plt.close()
    importance = (
        pd.DataFrame({"feature": sample.columns, "mean_abs_shap": np.abs(sv).mean(axis=0)})
        .sort_values("mean_abs_shap", ascending=False)
        .reset_index(drop=True)
    )
    importance.to_csv(out / "shap_importance.csv", index=False)

    X_all, _ = to_model_matrix(orders)
    X_all = X_all.reindex(columns=X_train.columns, fill_value=0.0)
    cutoff = test_df["order_purchase_timestamp"].min()
    scores = orders[["order_id", "order_purchase_timestamp", "is_late"]].copy()
    scores["late_probability"] = xgb.predict_proba(X_all)[:, 1]
    scores["split"] = np.where(scores["order_purchase_timestamp"] >= cutoff, "test", "train")
    pct = scores["late_probability"].rank(pct=True)
    scores["risk_band"] = np.select([pct >= 0.90, pct >= 0.70], ["High", "Medium"], default="Low")
    scores.to_csv(out / "order_risk_scores.csv", index=False)
    (out / "metrics.json").write_text(json.dumps(metrics, indent=2))

    if use_mlflow:
        try:
            import mlflow

            mlflow.set_experiment("late-delivery-risk")
            with mlflow.start_run():
                mlflow.log_params({"model": "xgboost", "seed": SEED})
                for name in ("xgboost", "logistic_baseline"):
                    for k, v in metrics[name].items():
                        mlflow.log_metric(f"{name}_{k}", v)
                mlflow.log_artifacts(str(out))
        except ImportError:
            print("mlflow not installed; skipping experiment tracking.")

    print(json.dumps(metrics, indent=2))
    print("\nTop drivers (mean |SHAP|):")
    print(importance.head(8).to_string(index=False))
    return metrics


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    p.add_argument("--raw-dir", default="data/raw")
    p.add_argument("--out-dir", default="reports/generated/ml_late")
    p.add_argument("--no-mlflow", action="store_true")
    a = p.parse_args()
    run(a.raw_dir, a.out_dir, use_mlflow=not a.no_mlflow)


if __name__ == "__main__":
    main()
