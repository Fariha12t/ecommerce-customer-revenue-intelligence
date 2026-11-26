import pandas as pd
import pytest

from src.ml.features import (
    GRACE_DAYS,
    build_customer_table,
    load_raw,
    to_model_matrix,
)


@pytest.fixture(scope="module")
def table(raw_dir):
    return build_customer_table(load_raw(raw_dir), horizon_days=180)


def test_one_row_per_customer(table):
    assert table["customer_unique_id"].is_unique


def test_label_is_binary_with_both_classes(table):
    assert set(table["repeat_purchase"].unique()) == {0, 1}


def test_censored_customers_removed(raw_dir, table):
    tables = load_raw(raw_dir)
    data_end = tables["orders"]["order_purchase_timestamp"].max()
    assert (table["prediction_time"] + pd.Timedelta(days=180) <= data_end).all()


def test_no_label_leakage_features_are_pre_prediction(raw_dir, table):
    """Label must only count orders strictly after the prediction time."""
    tables = load_raw(raw_dir)
    orders = tables["orders"].merge(tables["customers"], on="customer_id")
    row = table[table["repeat_purchase"] == 1].iloc[0]
    later = orders[
        (orders["customer_unique_id"] == row["customer_unique_id"])
        & (orders["order_purchase_timestamp"] > row["prediction_time"])
        & (orders["order_purchase_timestamp"] <= row["prediction_time"] + pd.Timedelta(days=180))
    ]
    assert len(later) >= 1


def test_prediction_time_is_delivery_plus_grace(raw_dir, table):
    tables = load_raw(raw_dir)
    orders = tables["orders"].merge(tables["customers"], on="customer_id")
    d = orders[orders["order_status"] == "delivered"].sort_values("order_purchase_timestamp")
    first = d.drop_duplicates("customer_unique_id").set_index("customer_unique_id")
    sample = table.head(20)
    expected = first.loc[sample["customer_unique_id"], "order_delivered_customer_date"] + pd.Timedelta(
        days=GRACE_DAYS
    )
    assert (sample["prediction_time"].values == expected.values).all()


def test_missing_file_gives_clear_error(tmp_path):
    with pytest.raises(FileNotFoundError, match="download_olist"):
        load_raw(tmp_path)


def test_model_matrix_has_no_identifiers_or_label(table):
    X, y = to_model_matrix(table)
    assert "repeat_purchase" not in X.columns
    assert "customer_unique_id" not in X.columns
    assert len(X) == len(y)
    assert X.select_dtypes(exclude="number").empty
