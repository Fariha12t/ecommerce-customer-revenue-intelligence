import pandas as pd


def test_revenue_includes_freight():
    df = pd.DataFrame({"price": [10.0, 20.0], "freight_value": [2.0, 3.0]})
    assert (df.price + df.freight_value).sum() == 35.0

def test_repeat_customer_definition():
    orders = pd.DataFrame({
        "customer_unique_id": ["A", "A", "B"],
        "order_id": ["1", "2", "3"]
    })
    counts = orders.groupby("customer_unique_id").order_id.nunique()
    assert int((counts >= 2).sum()) == 1
