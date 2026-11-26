"""Builds a small, deterministic dataset with the exact Olist schema for tests/CI."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

STATES = ["SP", "RJ", "MG", "RS", "PR", "BA", "SC"]
CATEGORIES = [("beleza_saude", "health_beauty"), ("esporte_lazer", "sports_leisure"),
              ("informatica_acessorios", "computers_accessories"), ("moveis_decoracao", "furniture_decor")]
PAY_TYPES = ["credit_card", "boleto", "voucher", "debit_card"]
N_SELLERS = 15
N_ZIP_SUFFIX = 15


def _zip(state_idx: int, suffix: int) -> int:
    return 1000 + state_idx * 1000 + suffix


def make_mini_olist(out_dir: str | Path, n_customers: int = 4000, seed: int = 7) -> Path:
    rng = np.random.default_rng(seed)
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)

    start = pd.Timestamp("2017-01-01")
    span_days = 600  # data ends ~mid 2018

    customers, orders, items, pays, reviews = [], [], [], [], []
    oid = 0
    cid = 0
    n_products = 40
    products = pd.DataFrame(
        {
            "product_id": [f"p{i}" for i in range(n_products)],
            "product_category_name": [CATEGORIES[i % 4][0] for i in range(n_products)],
            "product_weight_g": rng.gamma(2, 500, n_products).round(0),
            "product_length_cm": rng.integers(10, 60, n_products),
            "product_height_cm": rng.integers(5, 40, n_products),
            "product_width_cm": rng.integers(10, 50, n_products),
        }
    )
    products.loc[0, "product_category_name"] = np.nan
    products.loc[1, "product_weight_g"] = np.nan

    for u in range(n_customers):
        uid = f"u{u}"
        first_purchase = start + pd.Timedelta(days=int(rng.integers(0, span_days - 60)),
                                              hours=int(rng.integers(0, 24)))
        cust_state_idx = u % len(STATES)
        main_seller = int(rng.integers(0, N_SELLERS))
        cross_state = (main_seller % len(STATES)) != cust_state_idx
        # planted signal 1: cross-state shipments are late far more often
        late = rng.random() < (0.30 if cross_state else 0.06)
        score_first = int(rng.choice([1, 2], p=[0.6, 0.4])) if late else int(rng.choice([3, 4, 5], p=[0.1, 0.3, 0.6]))
        # planted signal 2: happy, on-time customers return more often
        p_repeat = 0.04 + (0.10 if score_first >= 4 else 0) - (0.02 if late else 0)
        n_orders = 1 + (rng.random() < p_repeat) + (rng.random() < p_repeat / 4)
        purchase = first_purchase
        for k in range(int(n_orders)):
            cid += 1
            oid += 1
            customers.append({"customer_id": f"c{cid}", "customer_unique_id": uid,
                              "customer_zip_code_prefix": _zip(cust_state_idx, u % N_ZIP_SUFFIX),
                              "customer_state": STATES[cust_state_idx]})
            est = purchase + pd.Timedelta(days=15)
            deliv = est + pd.Timedelta(days=int(rng.integers(3, 12))) if (late and k == 0) \
                else purchase + pd.Timedelta(days=int(rng.integers(5, 14)))
            status = "delivered" if rng.random() > 0.03 else "canceled"
            orders.append({
                "order_id": f"o{oid}", "customer_id": f"c{cid}", "order_status": status,
                "order_purchase_timestamp": purchase,
                "order_delivered_customer_date": deliv if status == "delivered" else pd.NaT,
                "order_estimated_delivery_date": est,
            })
            for _ in range(int(rng.integers(1, 4))):
                seller = main_seller if k == 0 else int(rng.integers(0, N_SELLERS))
                items.append({"order_id": f"o{oid}", "product_id": f"p{int(rng.integers(0, n_products))}",
                              "seller_id": f"s{seller}",
                              "price": float(rng.gamma(3, 40)), "freight_value": float(rng.gamma(2, 8))})
            pays.append({"order_id": f"o{oid}", "payment_type": str(rng.choice(PAY_TYPES)),
                         "payment_installments": int(rng.integers(1, 8)),
                         "payment_value": float(rng.gamma(3, 60))})
            if status == "delivered":
                reviews.append({"order_id": f"o{oid}", "review_score": score_first if k == 0 else 5,
                                "review_answer_timestamp": deliv + pd.Timedelta(days=int(rng.integers(0, 5)))})
            purchase = purchase + pd.Timedelta(days=int(rng.integers(20, 120)))

    sellers = pd.DataFrame(
        {
            "seller_id": [f"s{i}" for i in range(N_SELLERS)],
            "seller_zip_code_prefix": [_zip(i % len(STATES), i) for i in range(N_SELLERS)],
            "seller_state": [STATES[i % len(STATES)] for i in range(N_SELLERS)],
        }
    )
    geo_rows = []
    for s in range(len(STATES)):
        for j in range(N_ZIP_SUFFIX):
            for _ in range(2):  # duplicate rows per prefix, like the real file
                geo_rows.append({
                    "geolocation_zip_code_prefix": _zip(s, j),
                    "geolocation_lat": -23.0 + s * 2.0 + j * 0.01 + rng.normal(0, 0.005),
                    "geolocation_lng": -46.0 + s * 1.5 + j * 0.01 + rng.normal(0, 0.005),
                    "geolocation_city": "x",
                    "geolocation_state": STATES[s],
                })

    pd.DataFrame(customers).to_csv(out / "olist_customers_dataset.csv", index=False)
    pd.DataFrame(orders).to_csv(out / "olist_orders_dataset.csv", index=False)
    pd.DataFrame(items).to_csv(out / "olist_order_items_dataset.csv", index=False)
    pd.DataFrame(pays).to_csv(out / "olist_order_payments_dataset.csv", index=False)
    pd.DataFrame(reviews).to_csv(out / "olist_order_reviews_dataset.csv", index=False)
    products.to_csv(out / "olist_products_dataset.csv", index=False)
    sellers.to_csv(out / "olist_sellers_dataset.csv", index=False)
    pd.DataFrame(geo_rows).to_csv(out / "olist_geolocation_dataset.csv", index=False)
    pd.DataFrame(CATEGORIES, columns=["product_category_name", "product_category_name_english"]).to_csv(
        out / "product_category_name_translation.csv", index=False
    )
    return out
