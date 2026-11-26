"""Generate headline business findings from Olist-schema raw data.

Usage::

    python -m src.insights

Writes ``reports/generated/key_findings.md`` and ``key_findings.json`` with
numbers computed from YOUR data, so the README never contains invented claims.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from src.ml.features import load_raw


def compute_findings(tables: dict[str, pd.DataFrame]) -> dict:
    customers = tables["customers"][["customer_id", "customer_unique_id", "customer_state"]]
    orders = tables["orders"].merge(customers, on="customer_id", how="inner")
    delivered = orders[orders["order_status"] == "delivered"].copy()

    items = tables["items"].merge(delivered[["order_id", "customer_unique_id", "customer_state",
                                             "order_purchase_timestamp"]], on="order_id")
    items["gmv"] = items["price"] + items["freight_value"]

    products = tables["products"].merge(tables["translation"], on="product_category_name", how="left")
    products["category"] = (
        products["product_category_name_english"].fillna(products["product_category_name"]).fillna("unknown")
    )
    items = items.merge(products[["product_id", "category"]], on="product_id", how="left")
    items["category"] = items["category"].fillna("unknown")

    total_gmv = float(items["gmv"].sum())
    n_orders = int(delivered["order_id"].nunique())
    n_customers = int(delivered["customer_unique_id"].nunique())

    # --- repeat behaviour ------------------------------------------------------
    orders_per_customer = delivered.groupby("customer_unique_id")["order_id"].nunique()
    repeat_rate = float((orders_per_customer >= 2).mean())

    # --- revenue concentration -------------------------------------------------
    cust_gmv = items.groupby("customer_unique_id")["gmv"].sum().sort_values(ascending=False)
    top20_n = max(1, int(round(len(cust_gmv) * 0.20)))
    top20_share = float(cust_gmv.head(top20_n).sum() / cust_gmv.sum())

    cat_gmv = items.groupby("category")["gmv"].sum().sort_values(ascending=False)
    top5_cat = [(c, float(v / total_gmv)) for c, v in cat_gmv.head(5).items()]

    state_gmv = items.groupby("customer_state")["gmv"].sum().sort_values(ascending=False)
    top3_state = [(s, float(v / total_gmv)) for s, v in state_gmv.head(3).items()]

    freight_share = float(items["freight_value"].sum() / total_gmv)

    # --- monthly trend ----------------------------------------------------------
    items["month"] = items["order_purchase_timestamp"].dt.to_period("M")
    monthly = items.groupby("month")["gmv"].sum()
    peak_month = str(monthly.idxmax())
    peak_value = float(monthly.max())
    yoy = None
    years = sorted(monthly.index.year.unique())
    if len(years) >= 2:
        last, prev = years[-1], years[-2]
        last_months = {p.month for p in monthly.index if p.year == last}
        prev_months = {p.month for p in monthly.index if p.year == prev}
        common = sorted(last_months & prev_months)
        if common:
            a = sum(v for p, v in monthly.items() if p.year == last and p.month in common)
            b = sum(v for p, v in monthly.items() if p.year == prev and p.month in common)
            if b > 0:
                yoy = {"year": int(last), "vs_year": int(prev),
                       "months": [int(m) for m in common], "growth": float(a / b - 1)}

    # --- delivery vs satisfaction ------------------------------------------------
    d = delivered.dropna(subset=["order_delivered_customer_date", "order_estimated_delivery_date"]).copy()
    d["late"] = d["order_delivered_customer_date"] > d["order_estimated_delivery_date"]
    rv = tables["reviews"].groupby("order_id")["review_score"].mean().rename("score")
    d = d.merge(rv, left_on="order_id", right_index=True, how="inner")
    late_rate = float(d["late"].mean()) if len(d) else float("nan")
    score_late = float(d.loc[d["late"], "score"].mean()) if d["late"].any() else float("nan")
    score_ontime = float(d.loc[~d["late"], "score"].mean()) if (~d["late"]).any() else float("nan")

    return {
        "period_start": str(delivered["order_purchase_timestamp"].min().date()),
        "period_end": str(delivered["order_purchase_timestamp"].max().date()),
        "delivered_orders": n_orders,
        "unique_customers": n_customers,
        "gross_order_item_value": total_gmv,
        "aov": total_gmv / n_orders,
        "repeat_customer_rate": repeat_rate,
        "top20_customers_value_share": top20_share,
        "top5_categories_share": top5_cat,
        "top3_states_share": top3_state,
        "freight_share_of_value": freight_share,
        "peak_month": peak_month,
        "peak_month_value": peak_value,
        "yoy": yoy,
        "late_delivery_rate": late_rate,
        "review_score_late": score_late,
        "review_score_on_time": score_ontime,
    }


def to_markdown(f: dict) -> str:
    pct = lambda x: f"{x * 100:.1f}%"  # noqa: E731
    money = lambda x: f"{x:,.0f}"  # noqa: E731
    lines = [
        "# Key findings (auto-generated)",
        "",
        f"Data window: {f['period_start']} to {f['period_end']} · "
        f"{f['delivered_orders']:,} delivered orders · {f['unique_customers']:,} unique customers · "
        f"gross order-item value {money(f['gross_order_item_value'])} · AOV {f['aov']:.2f}",
        "",
        "| # | Finding | Evidence | Suggested action |",
        "|---|---------|----------|------------------|",
        f"| 1 | Repeat-purchase rate | Only {pct(f['repeat_customer_rate'])} of customers "
        f"placed 2+ delivered orders | Focus on the second purchase: post-delivery offers, "
        f"review-triggered coupons |",
        f"| 2 | Customer value concentration | Top 20% of customers = {pct(f['top20_customers_value_share'])} "
        f"of gross order-item value | Protect and grow the high-value segment (RFM 'Champions') |",
        "| 3 | Category concentration (top 5 by value share) | " + ", ".join(f"{c} {pct(s)}" for c, s in f["top5_categories_share"])
        + " | Prioritise inventory and marketing on these categories |",
        "| 4 | Geographic concentration (top 3 states) | " + ", ".join(f"{s} {pct(v)}" for s, v in f["top3_states_share"])
        + " | Expand logistics or seller supply in under-served states |",
        f"| 5 | Freight share of order value | Freight = {pct(f['freight_share_of_value'])} "
        f"of gross order-item value | Test free-shipping thresholds and regional fulfilment |",
        f"| 6 | Late delivery vs customer satisfaction | {pct(f['late_delivery_rate'])} of orders late; "
        f"avg review {f['review_score_late']:.2f} (late) vs {f['review_score_on_time']:.2f} (on time) "
        f"| Improve delivery-time estimates and carrier SLAs |",
        f"| 7 | Seasonality and growth | Peak month {f['peak_month']} ({money(f['peak_month_value'])})"
        + (
            f"; {f['yoy']['year']} vs {f['yoy']['vs_year']} (same months) {pct(f['yoy']['growth'])}"
            if f["yoy"]
            else ""
        )
        + " | Plan campaigns and capacity around peak periods |",
        "",
        "_All numbers are computed from the data in `data/raw`. Describe them as findings from "
        "that dataset only. Gross order-item value = price + freight for delivered orders._",
    ]
    return "\n".join(lines) + "\n"


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--raw-dir", default="data/raw")
    p.add_argument("--out-dir", default="reports/generated")
    a = p.parse_args()
    out = Path(a.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    findings = compute_findings(load_raw(a.raw_dir))
    (out / "key_findings.json").write_text(json.dumps(findings, indent=2, default=float))
    (out / "key_findings.md").write_text(to_markdown(findings), encoding="utf-8")
    print((out / "key_findings.md").read_text(encoding="utf-8"))


if __name__ == "__main__":
    main()
