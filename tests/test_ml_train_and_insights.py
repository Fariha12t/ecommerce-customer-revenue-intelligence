import json

import numpy as np

from src.insights import compute_findings, to_markdown
from src.ml.features import load_raw
from src.ml.train import run, top_decile_lift


def test_top_decile_lift_perfect_ranking():
    y = np.array([1] * 10 + [0] * 90)
    score = np.array([1.0] * 10 + [0.0] * 90)
    out = top_decile_lift(y, score)
    assert out["top_decile_repeat_rate"] == 1.0
    assert out["top_decile_lift"] == 10.0


def test_training_end_to_end(raw_dir, tmp_path):
    metrics = run(str(raw_dir), str(tmp_path), horizon=180, use_mlflow=False)
    # the fixture has a planted signal, so the model should beat random
    assert metrics["xgboost"]["roc_auc"] > 0.55
    for name in ("metrics.json", "shap_summary.png", "shap_importance.csv", "customer_scores.csv"):
        assert (tmp_path / name).exists()
    saved = json.loads((tmp_path / "metrics.json").read_text())
    assert saved["n_train"] + saved["n_test"] == saved["n_customers"]


def test_insights_numbers_are_sane(raw_dir):
    f = compute_findings(load_raw(raw_dir))
    assert 0 < f["repeat_customer_rate"] < 1
    assert 0.2 <= f["top20_customers_value_share"] <= 1
    assert f["aov"] > 0
    md = to_markdown(f)
    assert "Key findings" in md and "Suggested action" in md
