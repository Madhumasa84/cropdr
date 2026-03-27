from __future__ import annotations

import argparse
import json
import pickle
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import accuracy_score, precision_score, recall_score, roc_auc_score
from sklearn.model_selection import train_test_split

from src.config import MODEL3_METADATA_PATH, MODEL3_MODEL_PATH, MODEL3_TRAINING_DATA_PATH, ensure_runtime_directories

FEATURES_USED = [
    "crop",
    "disease",
    "crop_stage",
    "city",
    "state",
    "month",
    "temp_avg",
    "humidity_avg",
    "rainfall_7day_mm",
    "temp_avg_3d",
    "humidity_avg_3d",
    "temp_trend_3d",
    "humidity_trend_3d",
    "is_monsoon"
]

CATEGORICAL_COLUMNS = ["crop", "disease", "crop_stage", "city", "state"]


def build_model(target_series: pd.Series) -> tuple[Any, str]:
    positive_count = int(target_series.sum())
    negative_count = int((1 - target_series).sum())
    scale_pos_weight = max(1.0, negative_count / max(1, positive_count))
    try:
        from xgboost import XGBClassifier

        model = XGBClassifier(
            n_estimators=250,
            max_depth=5,
            learning_rate=0.05,
            subsample=0.9,
            colsample_bytree=0.9,
            objective="binary:logistic",
            eval_metric="logloss",
            random_state=42,
            scale_pos_weight=scale_pos_weight
        )
        return model, "xgboost"
    except ImportError:
        return HistGradientBoostingClassifier(max_depth=5, learning_rate=0.05, random_state=42), "hist_gradient_boosting"


def train_model(input_path: Path = MODEL3_TRAINING_DATA_PATH, output_path: Path = MODEL3_MODEL_PATH) -> dict[str, Any]:
    ensure_runtime_directories()
    if not input_path.exists():
        raise FileNotFoundError(f"Training data not found at {input_path}. Run 02_feature_engineering.py first.")

    dataframe = pd.read_csv(input_path)
    if dataframe["target"].nunique() < 2:
        raise ValueError("Training data must contain both positive and negative classes.")

    feature_frame = pd.get_dummies(dataframe[FEATURES_USED], columns=CATEGORICAL_COLUMNS)
    target = dataframe["target"].astype(int)
    train_x, test_x, train_y, test_y = train_test_split(
        feature_frame,
        target,
        test_size=0.20,
        random_state=42,
        stratify=target
    )

    model, model_family = build_model(train_y)
    model.fit(train_x, train_y)
    predicted = model.predict(test_x)
    probabilities = model.predict_proba(test_x)[:, 1] if hasattr(model, "predict_proba") else predicted

    metrics = {
        "accuracy": round(float(accuracy_score(test_y, predicted)), 4),
        "precision": round(float(precision_score(test_y, predicted, zero_division=0)), 4),
        "recall": round(float(recall_score(test_y, predicted, zero_division=0)), 4),
        "roc_auc": round(float(roc_auc_score(test_y, probabilities)), 4)
    }

    artifact = {
        "model": model,
        "model_family": model_family,
        "feature_columns": list(feature_frame.columns),
        "categorical_columns": CATEGORICAL_COLUMNS,
        "features_used": FEATURES_USED,
        "metrics": metrics,
        "created_at": datetime.utcnow().isoformat(),
        "training_rows": int(len(dataframe))
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("wb") as file:
        pickle.dump(artifact, file)

    with MODEL3_METADATA_PATH.open("w", encoding="utf-8") as file:
        json.dump(
            {
                "model_family": artifact["model_family"],
                "metrics": artifact["metrics"],
                "training_rows": artifact["training_rows"],
                "created_at": artifact["created_at"],
                "feature_columns": artifact["feature_columns"]
            },
            file,
            indent=2
        )

    return artifact


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Train the weather risk ML model.")
    parser.add_argument("--input", default=str(MODEL3_TRAINING_DATA_PATH))
    parser.add_argument("--output", default=str(MODEL3_MODEL_PATH))
    return parser


def main() -> None:
    args = build_arg_parser().parse_args()
    artifact = train_model(Path(args.input), Path(args.output))
    print(json.dumps({"model_family": artifact["model_family"], "metrics": artifact["metrics"]}, indent=2))


if __name__ == "__main__":
    main()
