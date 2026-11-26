"""Generate reproducible business KPIs, RFM segments and cohort retention."""
import numpy as np
import pandas as pd

from src.config import PROCESSED_DIR, REPORT_DIR


def run_analytics():
    orders = pd.read_csv(PROCESSED_DIR / "orders.csv", parse_dates=["order_purchase_timestamp"])
    customers = pd.read_csv(PROCESSED_DIR / "customers.csv")
    items = pd.read_csv(PROCESSED_DIR / "fact_order_items.csv",
                        parse_dates=["order_purchase_timestamp"])

    delivered = orders[orders["order_status"].eq("delivered")].copy()
    delivered_items = items[items["order_status"].eq("delivered")].copy()
    delivered_items["revenue_including_freight"] = (
        delivered_items["price"].fillna(0) + delivered_items["freight_value"].fillna(0)
    )

    # Executive KPIs: aggregate item-level revenue separately from order count.
    revenue = delivered_items["revenue_including_freight"].sum()
    order_count = delivered["order_id"].nunique()
    kpis = pd.DataFrame([{
        "delivered_orders": order_count,
        "gross_value_including_freight": round(revenue, 2),
        "average_order_value": round(revenue / order_count, 2) if order_count else 0,
        "unique_customers": delivered["customer_id"].nunique(),
        "repeat_customers": 0,
        "repeat_customer_rate_pct": 0.0,
    }])

    customer_orders = delivered[["order_id", "customer_id", "order_purchase_timestamp"]].merge(
        customers[["customer_id", "customer_unique_id", "customer_state", "customer_city"]],
        on="customer_id", how="left"
    )
    frequency = customer_orders.groupby("customer_unique_id")["order_id"].nunique()
    repeat_count = int((frequency >= 2).sum())
    unique_count = int(frequency.shape[0])
    kpis.loc[0, "repeat_customers"] = repeat_count
    kpis.loc[0, "repeat_customer_rate_pct"] = round(
        repeat_count / unique_count * 100, 2
    ) if unique_count else 0
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    kpis.to_csv(REPORT_DIR / "executive_kpis.csv", index=False)

    # Monthly revenue and order trends.
    monthly = delivered_items.dropna(subset=["order_purchase_timestamp"]).copy()
    monthly["month"] = monthly["order_purchase_timestamp"].dt.to_period("M").astype(str)
    monthly_revenue = monthly.groupby("month", as_index=False).agg(
        revenue=("revenue_including_freight", "sum"),
        orders=("order_id", "nunique"),
        units=("order_item_id", "count"),
    )
    monthly_revenue["revenue_mom_pct"] = monthly_revenue["revenue"].pct_change().mul(100).round(2)
    monthly_revenue.to_csv(REPORT_DIR / "monthly_performance.csv", index=False)

    # Category contribution.
    category = delivered_items.groupby("product_category_name_english", dropna=False).agg(
        revenue=("revenue_including_freight", "sum"),
        orders=("order_id", "nunique"),
        units=("order_item_id", "count"),
    ).reset_index().sort_values("revenue", ascending=False)
    category.to_csv(REPORT_DIR / "category_performance.csv", index=False)

    # Geographic performance at customer-state level.
    geo = delivered_items.groupby("customer_state", dropna=False).agg(
        revenue=("revenue_including_freight", "sum"),
        orders=("order_id", "nunique"),
        customers=("customer_unique_id", "nunique"),
    ).reset_index().sort_values("revenue", ascending=False)
    geo.to_csv(REPORT_DIR / "state_performance.csv", index=False)

    # RFM at customer_unique_id grain, using delivered orders only.
    valid = delivered_items.dropna(subset=["order_purchase_timestamp"]).copy()
    customer_rev = valid.groupby("customer_unique_id").agg(
        last_purchase=("order_purchase_timestamp", "max"),
        frequency=("order_id", "nunique"),
        monetary=("revenue_including_freight", "sum"),
    ).reset_index()
    if not customer_rev.empty:
        snapshot = valid["order_purchase_timestamp"].max() + pd.Timedelta(days=1)
        customer_rev["recency_days"] = (snapshot - customer_rev["last_purchase"]).dt.days
        # qcut can fail when many customers have identical values; rank first for stable bins.
        customer_rev["r_score"] = pd.qcut(
            customer_rev["recency_days"].rank(method="first"), 5, labels=[5,4,3,2,1]
        ).astype(int)
        customer_rev["f_score"] = pd.qcut(
            customer_rev["frequency"].rank(method="first"), 5, labels=[1,2,3,4,5]
        ).astype(int)
        customer_rev["m_score"] = pd.qcut(
            customer_rev["monetary"].rank(method="first"), 5, labels=[1,2,3,4,5]
        ).astype(int)
        customer_rev["rfm_score"] = (
            customer_rev["r_score"].astype(str)
            + customer_rev["f_score"].astype(str)
            + customer_rev["m_score"].astype(str)
        )
        customer_rev["segment"] = np.select(
            [
                (customer_rev.r_score >= 4) & (customer_rev.f_score >= 4),
                (customer_rev.r_score >= 3) & (customer_rev.f_score >= 3),
                (customer_rev.r_score <= 2) & (customer_rev.f_score >= 3),
                (customer_rev.r_score <= 2) & (customer_rev.f_score <= 2),
            ],
            ["Champions", "Loyal customers", "At risk", "Hibernating"],
            default="Potential / developing"
        )
    customer_rev.to_csv(REPORT_DIR / "customer_rfm.csv", index=False)

    # Cohort retention by first delivered purchase month.
    cohort_base = customer_orders.dropna(subset=["order_purchase_timestamp"]).copy()
    cohort_base["order_month"] = cohort_base["order_purchase_timestamp"].dt.to_period("M")
    first_month = cohort_base.groupby("customer_unique_id")["order_month"].min().rename("cohort_month")
    cohort_base = cohort_base.join(first_month, on="customer_unique_id")
    cohort_base["cohort_index"] = (
        (cohort_base["order_month"].dt.year - cohort_base["cohort_month"].dt.year) * 12
        + cohort_base["order_month"].dt.month - cohort_base["cohort_month"].dt.month + 1
    )
    cohort_counts = cohort_base.groupby(
        ["cohort_month", "cohort_index"]
    )["customer_unique_id"].nunique().reset_index(name="customers")
    cohort_pivot = cohort_counts.pivot(
        index="cohort_month", columns="cohort_index", values="customers"
    )
    cohort_sizes = cohort_pivot.iloc[:, 0]
    retention = cohort_pivot.divide(cohort_sizes, axis=0).round(4)
    retention.to_csv(REPORT_DIR / "cohort_retention.csv")

    print("Analytics complete. Outputs saved to reports/generated/")

if __name__ == "__main__":
    run_analytics()
