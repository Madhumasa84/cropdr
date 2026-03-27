from __future__ import annotations

import argparse
import json
from datetime import date, datetime
from functools import lru_cache
from pathlib import Path
from typing import Any

DISEASE_MAP_PATH = Path(__file__).with_name("disease_weather_map.json")

CROP_STAGE_CALENDAR: dict[str, dict[str, list[int]]] = {
    "Tomato": {"Nursery": [6, 7], "Vegetative": [8, 9], "Flowering": [10, 11], "Fruiting": [12, 1, 2], "Harvest": [3, 4]},
    "Rice": {"Nursery": [6], "Tillering": [7, 8], "Panicle_Initiation": [9], "Flowering": [10], "Grain_Filling": [11]},
    "Wheat": {"Germination": [11], "Tillering": [12, 1], "Jointing": [2], "Flowering": [3], "Grain_Filling": [4]},
    "Cotton": {"Sowing": [6], "Vegetative": [7, 8], "Squaring": [9], "Flowering": [10, 11], "Boll_Development": [12, 1]},
    "Maize": {"Germination": [6, 7], "Vegetative": [7, 8], "Tasseling": [8, 9], "Silking": [9], "Grain_Filling": [10, 11]},
    "Groundnut": {"Germination": [6, 7], "Vegetative": [7, 8], "Flowering": [8, 9], "Pegging": [9, 10], "Pod_Development": [10, 11]},
    "Potato": {"Sprouting": [10, 11], "Vegetative": [11, 12], "Tuber_Initiation": [12, 1], "Tuber_Bulking": [1, 2], "Maturity": [3]},
    "Chilli": {"Nursery": [6, 7], "Vegetative": [8, 9], "Flowering": [10, 11], "Fruiting": [12, 1, 2], "Harvest": [3, 4]},
    "Sugarcane": {"Germination": [2, 3], "Tillering": [4, 5, 6], "Grand_Growth": [7, 8, 9], "Maturity": [10, 11, 12, 1]},
    "Soybean": {"Germination": [6], "Vegetative": [7], "Flowering": [8], "Pod_Development": [9], "Seed_Filling": [10]}
}


@lru_cache(maxsize=1)
def load_knowledge_base() -> dict[str, Any]:
    with DISEASE_MAP_PATH.open("r", encoding="utf-8") as file:
        return json.load(file)


def parse_prediction_date(value: str | date | None) -> date:
    if value is None:
        return date.today()
    if isinstance(value, date):
        return value
    return datetime.fromisoformat(str(value)).date()


def normalize_crop_name(crop: str, knowledge_base: dict[str, Any] | None = None) -> str:
    if not crop:
        raise ValueError("Crop is required.")
    kb = knowledge_base or load_knowledge_base()
    lookup = {name.lower(): name for name in kb.keys()}
    key = crop.strip().lower()
    if key not in lookup:
        raise ValueError(f"Unsupported crop '{crop}'. Supported crops: {', '.join(sorted(kb.keys()))}")
    return lookup[key]


def infer_crop_stage(crop: str, month: int) -> str:
    for stage_name, months in CROP_STAGE_CALENDAR.get(crop, {}).items():
        if month in months:
            return stage_name
    return "General"


def _score_min(actual: float, threshold: float) -> float:
    if actual >= threshold:
        return 1.0
    tolerance = max(1.0, abs(threshold) * 0.20)
    return max(0.0, 1.0 - ((threshold - actual) / tolerance))


def _score_max(actual: float, threshold: float) -> float:
    if actual <= threshold:
        return 1.0
    tolerance = max(1.0, abs(threshold) * 0.20)
    return max(0.0, 1.0 - ((actual - threshold) / tolerance))


def _cyclic_month_distance(month_a: int, month_b: int) -> int:
    delta = abs(month_a - month_b)
    return min(delta, 12 - delta)


def _clean_weather_summary(weather_summary: dict[str, Any]) -> dict[str, float]:
    required_keys = ("temp_avg", "humidity_avg", "rainfall_7day_mm")
    missing = [key for key in required_keys if key not in weather_summary]
    if missing:
        raise ValueError(f"Weather summary missing fields: {', '.join(missing)}")
    return {
        "temp_avg": float(weather_summary["temp_avg"]),
        "humidity_avg": float(weather_summary["humidity_avg"]),
        "rainfall_7day_mm": float(weather_summary["rainfall_7day_mm"])
    }


def _determine_risk_level(confidence: float) -> str:
    if confidence >= 0.80:
        return "HIGH"
    if confidence >= 0.60:
        return "MEDIUM"
    if confidence >= 0.45:
        return "LOW"
    return "VERY_LOW"


def score_disease_rule(rule: dict[str, Any], weather_summary: dict[str, Any], month: int, crop_stage: str) -> dict[str, Any]:
    weather = _clean_weather_summary(weather_summary)
    conditions = rule.get("conditions", {})

    condition_scores: list[float] = []
    if "temp_min" in conditions:
        condition_scores.append(_score_min(weather["temp_avg"], float(conditions["temp_min"])))
    if "temp_max" in conditions:
        condition_scores.append(_score_max(weather["temp_avg"], float(conditions["temp_max"])))
    if "humidity_min" in conditions:
        condition_scores.append(_score_min(weather["humidity_avg"], float(conditions["humidity_min"])))
    if "humidity_max" in conditions:
        condition_scores.append(_score_max(weather["humidity_avg"], float(conditions["humidity_max"])))
    if "rainfall_mm_7day_min" in conditions:
        condition_scores.append(_score_min(weather["rainfall_7day_mm"], float(conditions["rainfall_mm_7day_min"])))
    if "rainfall_mm_7day_max" in conditions:
        condition_scores.append(_score_max(weather["rainfall_7day_mm"], float(conditions["rainfall_mm_7day_max"])))

    condition_score = sum(condition_scores) / len(condition_scores) if condition_scores else 0.0
    risk_months = [int(item) for item in rule.get("risk_months", [])]
    if month in risk_months:
        month_score = 1.0
    elif risk_months and min(_cyclic_month_distance(month, item) for item in risk_months) == 1:
        month_score = 0.55
    else:
        month_score = 0.15

    valid_stages = list(rule.get("crop_stages", []))
    if not valid_stages or crop_stage in valid_stages:
        stage_score = 1.0
    elif crop_stage == "General":
        stage_score = 0.60
    else:
        stage_score = 0.25

    confidence = round((0.65 * condition_score) + (0.20 * month_score) + (0.15 * stage_score), 2)
    return {
        "confidence": confidence,
        "risk_level": _determine_risk_level(confidence),
        "condition_score": round(condition_score, 2),
        "month_score": round(month_score, 2),
        "stage_score": round(stage_score, 2)
    }


def predict_weather_risk(
    crop: str,
    location: str,
    weather_summary: dict[str, Any],
    prediction_date: str | date | None = None,
    crop_stage: str | None = None,
    top_k: int = 5
) -> dict[str, Any]:
    knowledge_base = load_knowledge_base()
    canonical_crop = normalize_crop_name(crop, knowledge_base)
    prediction_day = parse_prediction_date(prediction_date)
    resolved_stage = crop_stage or infer_crop_stage(canonical_crop, prediction_day.month)
    cleaned_weather = _clean_weather_summary(weather_summary)

    scored_risks: list[dict[str, Any]] = []
    for disease_key, rule in knowledge_base[canonical_crop].items():
        score = score_disease_rule(rule, cleaned_weather, prediction_day.month, resolved_stage)
        scored_risks.append(
            {
                "disease": disease_key.replace("_", " "),
                "risk_level": score["risk_level"],
                "confidence": score["confidence"],
                "prevention_tip": rule["prevention"],
                "urgency_days": int(rule["urgency_days"])
            }
        )

    scored_risks.sort(key=lambda item: item["confidence"], reverse=True)
    risks = [item for item in scored_risks if item["confidence"] >= 0.45][:top_k]
    if not risks and scored_risks:
        fallback = dict(scored_risks[0])
        fallback["risk_level"] = "LOW"
        risks = [fallback]

    return {
        "crop": canonical_crop,
        "location": location,
        "prediction_date": prediction_day.isoformat(),
        "weather_summary": {
            "temp_avg": round(cleaned_weather["temp_avg"], 1),
            "humidity_avg": round(cleaned_weather["humidity_avg"], 1),
            "rainfall_7day_mm": round(cleaned_weather["rainfall_7day_mm"], 1)
        },
        "crop_stage": resolved_stage,
        "risks": risks,
        "model_version": "rule_engine_v1"
    }


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Rule-based crop disease weather risk prediction.")
    parser.add_argument("--crop", default="Tomato")
    parser.add_argument("--location", default="Chennai, Tamil Nadu")
    parser.add_argument("--temp", type=float, default=27.4)
    parser.add_argument("--humidity", type=float, default=88.0)
    parser.add_argument("--rainfall", type=float, default=14.2)
    parser.add_argument("--prediction-date", default=None)
    parser.add_argument("--crop-stage", default=None)
    parser.add_argument("--top-k", type=int, default=5)
    return parser


def main() -> None:
    args = build_arg_parser().parse_args()
    result = predict_weather_risk(
        crop=args.crop,
        location=args.location,
        weather_summary={
            "temp_avg": args.temp,
            "humidity_avg": args.humidity,
            "rainfall_7day_mm": args.rainfall
        },
        prediction_date=args.prediction_date,
        crop_stage=args.crop_stage,
        top_k=args.top_k
    )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
