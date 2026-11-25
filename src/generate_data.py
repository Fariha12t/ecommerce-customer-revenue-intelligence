
"""Generate synthetic e-commerce data without Kaggle."""
import numpy as np
import pandas as pd
from src.config import RAW_DIR


def generate(seed=42, n_orders=2500):
    rng = np.random.default_rng(seed)
    RAW_DIR.mkdir(parents=True, exist_ok=True)

    states = ["SP", "RJ", "MG", "RS", "PR", "SC", "BA", "DF"]
    cities = ["Sao Paulo", "Rio de Janeiro", "Belo Horizonte",
              "Curitiba", "Porto Alegre", "Salvador", "Brasilia"]
    categories = ["electronics", "fashion", "beauty", "sports",
                  "home_and_garden", "toys", "books", "health"]

    n_customers, n_products, n_sellers = 1500, 180, 45

    customers = pd.DataFrame({
        "customer_id": [f"C{i:05d}" for i in range(n_customers)],
        "customer_unique_id": [f"U{i:05d}" for i in range(n_customers)],
        "customer_zip_code_prefix": rng.integers(1000, 99999, n_customers),
        "customer_city": rng.choice(cities, n_customers),
        "customer_state": rng.choice(states, n_customers)
    })

    products = pd.DataFrame({
        "product_id": [f"P{i:04d}" for i in range(n_products)],
        "product_category_name": rng.choice(categories, n_products),
        "product_name_lenght": rng.integers(10, 60, n_products),
        "product_description_lenght": rng.integers(50, 1500, n_products),
        "product_photos_qty": rng.integers(1, 6, n_products),
        "product_weight_g": rng.integers(100, 12000, n_products),
        "product_length_cm": rng.integers(5, 100, n_products),
        "product_height_cm": rng.integers(2, 80, n_products),
        "product_width_cm": rng.integers(5, 80, n_products)
    })

    sellers = pd.DataFrame({
        "seller_id": [f"S{i:03d}" for i in range(n_sellers)],
        "seller_zip_code_prefix": rng.integers(1000, 99999, n_sellers),
        "seller_city": rng.choice(cities, n_sellers),
        "seller_state": rng.choice(states, n_sellers)
    })

    customer_indices = rng.integers(0, n_customers, n_orders)
    order_ids = [f"O{i:06d}" for i in range(n_orders)]

    purchase = (
        pd.Timestamp("2023-01-01")
        + pd.to_timedelta(rng.integers(0, 730, n_orders), unit="D")
        + pd.to_timedelta(rng.integers(0, 86400, n_orders), unit="s")
    )

    approved = purchase + pd.to_timedelta(
        rng.integers(1, 180, n_orders), unit="m"
    )
    delivered = approved + pd.to_timedelta(
        rng.integers(1, 12, n_orders), unit="D"
    )

    orders = pd.DataFrame({
        "order_id": order_ids,
        "customer_id": customers.iloc[customer_indices]["customer_id"].to_numpy(),
        "order_status": rng.choice(
            ["delivered", "shipped", "canceled"],
            n_orders, p=[0.88, 0.07, 0.05]
        ),
        "order_purchase_timestamp": purchase,
        "order_approved_at": approved,
        "order_delivered_carrier_date": approved + pd.Timedelta(days=2),
        "order_delivered_customer_date": delivered,
        "order_estimated_delivery_date": delivered + pd.Timedelta(days=4)
    })

    item_rows = []

    for order_id in order_ids:
        for sequence in range(1, int(rng.integers(2, 4))):
            product = int(rng.integers(n_products))
            seller = int(rng.integers(n_sellers))

            item_rows.append({
                "order_id": order_id,
                "order_item_id": sequence,
                "product_id": products.iloc[product]["product_id"],
                "seller_id": sellers.iloc[seller]["seller_id"],
                "price": round(float(rng.lognormal(3.3, 0.65)), 2),
                "freight_value": round(float(rng.uniform(3, 35)), 2)
            })

    items = pd.DataFrame(item_rows)

    payments = pd.DataFrame({
        "order_id": order_ids,
        "payment_sequential": 1,
        "payment_type": rng.choice(
            ["credit_card", "debit_card", "voucher", "boleto"], n_orders
        ),
        "payment_installments": rng.integers(1, 7, n_orders),
        "payment_value": [
            round(float(
                items.loc[items.order_id == oid, ["price", "freight_value"]]
                .sum().sum()
            ), 2)
            for oid in order_ids
        ]
    })

    reviews = pd.DataFrame({
        "review_id": [f"R{i:06d}" for i in range(n_orders)],
        "order_id": order_ids,
        "review_score": rng.integers(1, 6, n_orders),
        "review_comment_title": "",
        "review_comment_message": "",
        "review_creation_date": purchase + pd.Timedelta(days=14),
        "review_answer_timestamp": purchase + pd.Timedelta(days=15)
    })

    translations = pd.DataFrame({
        "product_category_name": categories,
        "product_category_name_english": [
            category.replace("_", " ") for category in categories
        ]
    })

    datasets = {
        "olist_orders_dataset.csv": orders,
        "olist_order_items_dataset.csv": items,
        "olist_order_payments_dataset.csv": payments,
        "olist_order_reviews_dataset.csv": reviews,
        "olist_customers_dataset.csv": customers,
        "olist_products_dataset.csv": products,
        "olist_sellers_dataset.csv": sellers,
        "product_category_name_translation.csv": translations
    }

    for filename, dataframe in datasets.items():
        dataframe.to_csv(RAW_DIR / filename, index=False)

    print("SUCCESS! Synthetic e-commerce data generated.")
    print(f"Orders: {len(orders):,}")
    print(f"Customers: {len(customers):,}")
    print(f"Products: {len(products):,}")
    print(f"Order items: {len(items):,}")
    print(f"Files saved in: {RAW_DIR}")


if __name__ == "__main__":
    generate()
