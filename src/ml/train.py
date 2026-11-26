"""Train and evaluate the repeat-purchase model.

Usage (from the repository root)::

    python -m src.ml.train                    # real/Olist data in data/raw
    python -m src.ml.train --horizon 90 --no-mlflow

Outputs go to ``reports/generated/ml/``:
    metrics.json, shap_summary.png, shap_importance.csv, customer_scores.csv
``customer_scores.csv`` can be imported into Power BI (join on customer_unique_id).
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

from src.ml.features import (  # noqa: E402
    DEFAULT_HORIZON_DAYS,
    build_customer_table,
    load_raw,
    to_model_matrix,
)

SEED = 42
TEST_FRACTION = 0.25


def time_split(df: pd.DataFrame, test_fraction: float = TEST_FRACTION):
    """Train on the earliest customers, test on the latest (no look-ahead)."""
    df = df.sort_values("prediction_time").reset_index(drop=True)
    cut = int(len(df) * (1 - test_fraction))
    return df.iloc[:cut], df.iloc[cut:]


def top_decile_lift(y_true: np.ndarray, score: np.ndarray) -> dict[str, float]:
    """Repeat rate among the top-scored 10% of customers vs overall."""
    n_top = max(1, int(len(score) * 0.10))
    order = np.argsort(-score)[:n_top]
    top_rate = float(np.mean(y_true[order]))
    base = float(np.mean(y_true))
    return {
        "top_decile_repeat_rate": top_rate,
        "base_repeat_rate": base,
        "top_decile_lift": top_rate / base if base > 0 else float("nan"),
    }


def evaluate(y_true, score) -> dict[str, float]:
    y_true = np.asarray(y_true)
    out = {
        "roc_auc": float(roc_auc_score(y_true, score)),
        "pr_auc": float(average_precision_score(y_true, score)),
    }
    out.update(top_decile_lift(y_true, np.asarray(score)))
    return out


def fit_models(X_train, y_train):
    # Heavily regularised: only ~1% positives, so a flexible model just memorises noise.
    xgb = XGBClassifier(
        n_estimators=200,
        max_depth=3,
        learning_rate=0.03,
        subsample=0.8,
        colsample_bytree=0.8,
        min_child_weight=20,
        reg_lambda=10.0,
        gamma=1.0,
        eval_metric="aucpr",
        random_state=SEED,
        n_jobs=-1,
    )
    xgb.fit(X_train, y_train)
    logit = make_pipeline(
        SimpleImputer(strategy="median"),
        StandardScaler(),
        LogisticRegression(max_iter=1000, class_weight="balanced", random_state=SEED),
    )
    logit.fit(X_train, y_train)
    return xgb, logit


def explain(model, X_test: pd.DataFrame, out_dir: Path) -> pd.DataFrame:
    sample = X_test.sample(min(2000, len(X_test)), random_state=SEED)
    shap_values = shap.TreeExplainer(model).shap_values(sample)
    shap.summary_plot(shap_values, sample, show=False, max_display=15)
    plt.tight_layout()
    plt.savefig(out_dir / "shap_summary.png", dpi=150, bbox_inches="tight")
    plt.close()
    importance = (
        pd.DataFrame(
            {"feature": sample.columns, "mean_abs_shap": np.abs(shap_values).mean(axis=0)}
        )
        .sort_values("mean_abs_shap", ascending=False)
        .reset_index(drop=True)
    )
    importance.to_csv(out_dir / "shap_importance.csv", index=False)
    return importance


def run(raw_dir: str, out_dir: str, horizon: int, use_mlflow: bool) -> dict:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)

    customers = build_customer_table(load_raw(raw_dir), horizon_days=horizon)
    if customers["repeat_purchase"].nunique() < 2:
        raise RuntimeError("Label has a single class; check the data or horizon.")
    train_df, test_df = time_split(customers)
    X_train, y_train = to_model_matrix(train_df)
    X_test, y_test = to_model_matrix(test_df)
    X_test = X_test.reindex(columns=X_train.columns, fill_value=0.0)

    xgb, logit = fit_models(X_train, y_train)
    metrics = {
        "horizon_days": horizon,
        "n_customers": int(len(customers)),
        "n_train": int(len(train_df)),
        "n_test": int(len(test_df)),
        "test_period_start": str(test_df["prediction_time"].min().date()),
        "xgboost": evaluate(y_test, xgb.predict_proba(X_test)[:, 1]),
        "logistic_baseline": evaluate(y_test, logit.predict_proba(X_test)[:, 1]),
    }
    importance = explain(xgb, X_test, out)

    # Score everyone (flagging the split) so the output can feed Power BI.
    X_all, _ = to_model_matrix(customers)
    X_all = X_all.reindex(columns=X_train.columns, fill_value=0.0)
    scores = customers[["customer_unique_id", "prediction_time", "repeat_purchase"]].copy()
    scores["repeat_probability"] = xgb.predict_proba(X_all)[:, 1]
    scores["split"] = np.where(scores["prediction_time"].isin(test_df["prediction_time"]), "test", "train")
    scores["score_decile"] = pd.qcut(
        scores["repeat_probability"].rank(method="first"), 10, labels=range(1, 11)
    ).astype(int)
    scores.to_csv(out / "customer_scores.csv", index=False)

    (out / "metrics.json").write_text(json.dumps(metrics, indent=2))

    if use_mlflow:
        try:
            import mlflow

            mlflow.set_experiment("repeat-purchase")
            with mlflow.start_run():
                mlflow.log_params({"horizon_days": horizon, "model": "xgboost", "seed": SEED})
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
    p.add_argument("--out-dir", default="reports/generated/ml")
    p.add_argument("--horizon", type=int, default=DEFAULT_HORIZON_DAYS)
    p.add_argument("--no-mlflow", action="store_true")
    a = p.parse_args()
    run(a.raw_dir, a.out_dir, a.horizon, use_mlflow=not a.no_mlflow)


if __name__ == "__main__":
    main()
