import json

import numpy as np
import pandas as pd
import pytest

from src.ml.features import load_raw
from src.ml.late_delivery import (
    build_order_table,
    capture_at,
    haversine_km,
    run,
    to_model_matrix,
)

FORBIDDEN = {"order_delivered_customer_date", "review_score", "delivery_days", "delivery_delay_days"}


@pytest.fixture(scope="module")
def orders(raw_dir):
    return build_order_table(raw_dir)


def test_one_row_per_order(orders):
    assert orders["order_id"].is_unique


def test_label_matches_raw_dates(raw_dir, orders):
    o = load_raw(raw_dir)["orders"].set_index("order_id")
    sample = orders.head(50)
    expected = (
        o.loc[sample["order_id"], "order_delivered_customer_date"]
        > o.loc[sample["order_id"], "order_estimated_delivery_date"]
    ).astype(int)
    assert (sample["is_late"].values == expected.values).all()


def test_no_post_purchase_information_in_features(orders):
    X, _ = to_model_matrix(orders)
    assert not (FORBIDDEN & set(X.columns))
    assert "is_late" not in X.columns


def test_distance_is_positive_and_cross_state_is_farther(orders):
    d = orders.dropna(subset=["distance_km"])
    assert (d["distance_km"] >= 0).all()
    assert d.loc[d["same_state"] == 0, "distance_km"].mean() > d.loc[d["same_state"] == 1, "distance_km"].mean()


def test_haversine_known_distance():
    # Sao Paulo to Rio de Janeiro is roughly 360 km
    km = haversine_km(np.array([-23.55]), np.array([-46.63]), np.array([-22.91]), np.array([-43.17]))[0]
    assert 340 < km < 380


def test_capture_at():
    y = np.array([1, 1, 0, 0, 0, 0, 0, 0, 0, 0])
    s = np.array([0.9, 0.8, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1])
    assert capture_at(y, s, 0.2) == 1.0


def test_training_end_to_end(raw_dir, tmp_path):
    metrics = run(str(raw_dir), str(tmp_path), use_mlflow=False)
    assert metrics["xgboost"]["roc_auc"] > 0.60  # planted cross-state signal
    for name in ("metrics.json", "shap_summary.png", "shap_importance.csv", "order_risk_scores.csv"):
        assert (tmp_path / name).exists()
    scores = pd.read_csv(tmp_path / "order_risk_scores.csv")
    assert set(scores["risk_band"]) <= {"High", "Medium", "Low"}
    saved = json.loads((tmp_path / "metrics.json").read_text())
    assert saved["n_train"] + saved["n_test"] == saved["n_orders"]
