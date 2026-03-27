from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

import pandas as pd

from src.config import MODEL3_RAW_DATA_PATH, MODEL3_TRAINING_DATA_PATH
from src.model3.rule_engine import infer_crop_stage, load_knowledge_base, score_disease_rule


def engineer_weather_features(raw_df: pd.DataFrame) -> pd.DataFrame:
    dataframe = raw_df.copy()
    dataframe["date"] = pd.to_datetime(dataframe["date"])
    dataframe = dataframe.sort_values(["city", "date"]).reset_index(drop=True)

    grouped = dataframe.groupby("city", group_keys=False)
    dataframe["temp_avg_3d"] = grouped["temp_c"].transform(lambda series: series.rolling(3, min_periods=1).mean())
    dataframe["humidity_avg_3d"] = grouped["humidity_pct"].transform(lambda series: series.rolling(3, min_periods=1).mean())
    dataframe["rainfall_7day_mm"] = grouped["rainfall_mm"].transform(lambda series: series.rolling(7, min_periods=1).sum())
    dataframe["temp_trend_3d"] = grouped["temp_c"].transform(lambda series: series.diff(3).fillna(0.0))
    dataframe["humidity_trend_3d"] = grouped["humidity_pct"].transform(lambda series: series.diff(3).fillna(0.0))
    dataframe["month"] = dataframe["date"].dt.month
    dataframe["is_monsoon"] = dataframe["month"].isin([6, 7, 8, 9]).astype(int)
    return dataframe


def build_training_dataset(weather_df: pd.DataFrame) -> pd.DataFrame:
    knowledge_base = load_knowledge_base()
    training_rows: list[dict[str, Any]] = []

    for row in weather_df.itertuples(index=False):
        weather_summary = {
            "temp_avg": float(row.temp_c),
            "humidity_avg": float(row.humidity_pct),
            "rainfall_7day_mm": float(row.rainfall_7day_mm)
        }

        for crop_name, disease_map in knowledge_base.items():
            crop_stage = infer_crop_stage(crop_name, int(row.month))
            for disease_name, rule in disease_map.items():
                scored = score_disease_rule(rule, weather_summary, int(row.month), crop_stage)
                training_rows.append(
                    {
                        "date": row.date.date().isoformat(),
                        "city": row.city,
                        "state": row.state,
                        "crop": crop_name,
                        "disease": disease_name,
                        "crop_stage": crop_stage,
                        "month": int(row.month),
                        "temp_avg": round(float(row.temp_c), 3),
                        "humidity_avg": round(float(row.humidity_pct), 3),
                        "rainfall_7day_mm": round(float(row.rainfall_7day_mm), 3),
                        "temp_avg_3d": round(float(row.temp_avg_3d), 3),
                        "humidity_avg_3d": round(float(row.humidity_avg_3d), 3),
                        "temp_trend_3d": round(float(row.temp_trend_3d), 3),
                        "humidity_trend_3d": round(float(row.humidity_trend_3d), 3),
                        "is_monsoon": int(row.is_monsoon),
                        "rule_confidence": float(scored["confidence"]),
                        "target": int(scored["confidence"] >= 0.68 and scored["risk_level"] in {"HIGH", "MEDIUM"})
                    }
                )

    if not training_rows:
        raise ValueError("No training rows were generated.")
    return pd.DataFrame(training_rows)


def build_features(input_path: Path = MODEL3_RAW_DATA_PATH, output_path: Path = MODEL3_TRAINING_DATA_PATH) -> pd.DataFrame:
    if not input_path.exists():
        raise FileNotFoundError(f"Raw NASA data not found at {input_path}. Run 01_fetch_nasa_data.py first.")

    raw_df = pd.read_csv(input_path)
    feature_df = engineer_weather_features(raw_df)
    training_df = build_training_dataset(feature_df)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    training_df.to_csv(output_path, index=False)
    return training_df


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate weather features from NASA POWER data.")
    parser.add_argument("--input", default=str(MODEL3_RAW_DATA_PATH))
    parser.add_argument("--output", default=str(MODEL3_TRAINING_DATA_PATH))
    return parser


def main() -> None:
    args = build_arg_parser().parse_args()
    dataframe = build_features(Path(args.input), Path(args.output))
    print(f"Saved {len(dataframe)} training rows to {args.output}")


if __name__ == "__main__":
    main()
