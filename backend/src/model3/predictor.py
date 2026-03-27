from __future__ import annotations

import argparse
import json
import pickle
from functools import lru_cache
from typing import Any

import pandas as pd

from src.config import MODEL3_MODEL_PATH
from src.model3.live_weather import fetch_live_weather
from src.model3.rule_engine import infer_crop_stage, load_knowledge_base, normalize_crop_name, parse_prediction_date, predict_weather_risk as rule_predict


@lru_cache(maxsize=1)
def load_model_artifact() -> dict[str, Any] | None:
    if not MODEL3_MODEL_PATH.exists():
        return None
    with MODEL3_MODEL_PATH.open("rb") as file:
        return pickle.load(file)


def map_confidence_to_level(confidence: float) -> str:
    if confidence >= 0.80:
        return "HIGH"
    if confidence >= 0.60:
        return "MEDIUM"
    return "LOW"


def split_location(location: str) -> tuple[str, str]:
    parts = [segment.strip() for segment in location.split(",") if segment.strip()]
    city = parts[0] if parts else "Unknown"
    state = parts[1] if len(parts) > 1 else "Unknown"
    return city, state


def build_fallback_weather_payload(location: str, prediction_date: Any = None) -> dict[str, Any]:
    prediction_day = parse_prediction_date(prediction_date)
    month = prediction_day.month
    normalized_location = location.strip() if location.strip() else "Unknown"
    lowered_location = normalized_location.lower()

    if month in {3, 4, 5}:
        temp_avg = 31.0
        humidity_avg = 62.0
        rainfall_7day_mm = 4.0
        description = "hot and mostly dry"
    elif month in {6, 7, 8, 9}:
        temp_avg = 27.5
        humidity_avg = 84.0
        rainfall_7day_mm = 26.0
        description = "humid with monsoon conditions"
    elif month in {10, 11}:
        temp_avg = 26.0
        humidity_avg = 78.0
        rainfall_7day_mm = 16.0
        description = "humid with scattered rain"
    else:
        temp_avg = 23.0
        humidity_avg = 68.0
        rainfall_7day_mm = 6.0
        description = "mild and mostly dry"

    if any(keyword in lowered_location for keyword in ("chennai", "tamil nadu", "kerala", "coastal", "andhra")):
        humidity_avg += 8.0
        rainfall_7day_mm += 2.0
    if any(keyword in lowered_location for keyword in ("punjab", "haryana", "rajasthan", "delhi")):
        temp_avg += 2.0
        humidity_avg -= 8.0
        rainfall_7day_mm = max(0.0, rainfall_7day_mm - 3.0)
    if any(keyword in lowered_location for keyword in ("assam", "meghalaya", "odisha", "west bengal")):
        humidity_avg += 6.0
        rainfall_7day_mm += 6.0

    return {
        "location": normalized_location,
        "coordinates": None,
        "observation_time": prediction_day.isoformat(),
        "weather_summary": {
            "temp_avg": round(temp_avg, 1),
            "humidity_avg": round(max(35.0, min(humidity_avg, 95.0)), 1),
            "rainfall_7day_mm": round(max(0.0, rainfall_7day_mm), 1),
        },
        "current_snapshot": {
            "temp": round(temp_avg - 1.5, 1),
            "humidity": round(max(35.0, min(humidity_avg + 5.0, 98.0)), 1),
            "description": description,
        },
        "forecast_points": 0,
        "source": "seasonal_fallback_v1",
    }


def build_candidate_frame(
    crop: str,
    location: str,
    weather_summary: dict[str, Any],
    prediction_date: Any,
    crop_stage: str | None = None
) -> pd.DataFrame:
    knowledge_base = load_knowledge_base()
    canonical_crop = normalize_crop_name(crop, knowledge_base)
    prediction_day = parse_prediction_date(prediction_date)
    resolved_stage = crop_stage or infer_crop_stage(canonical_crop, prediction_day.month)
    city, state = split_location(location)

    rows: list[dict[str, Any]] = []
    for disease_name, disease_rule in knowledge_base[canonical_crop].items():
        rows.append(
            {
                "crop": canonical_crop,
                "disease": disease_name,
                "crop_stage": resolved_stage,
                "city": city,
                "state": state,
                "month": prediction_day.month,
                "temp_avg": float(weather_summary["temp_avg"]),
                "humidity_avg": float(weather_summary["humidity_avg"]),
                "rainfall_7day_mm": float(weather_summary["rainfall_7day_mm"]),
                "temp_avg_3d": float(weather_summary["temp_avg"]),
                "humidity_avg_3d": float(weather_summary["humidity_avg"]),
                "temp_trend_3d": 0.0,
                "humidity_trend_3d": 0.0,
                "is_monsoon": int(prediction_day.month in [6, 7, 8, 9]),
                "prevention_tip": disease_rule["prevention"],
                "urgency_days": int(disease_rule["urgency_days"])
            }
        )
    return pd.DataFrame(rows)


def ml_predict_weather_risk(
    crop: str,
    location: str,
    weather_summary: dict[str, Any],
    prediction_date: Any = None,
    crop_stage: str | None = None,
    top_k: int = 5
) -> dict[str, Any]:
    artifact = load_model_artifact()
    if artifact is None:
        raise FileNotFoundError("Trained weather risk model is not available.")

    knowledge_base = load_knowledge_base()
    canonical_crop = normalize_crop_name(crop, knowledge_base)
    prediction_day = parse_prediction_date(prediction_date)
    resolved_stage = crop_stage or infer_crop_stage(canonical_crop, prediction_day.month)
    candidate_frame = build_candidate_frame(crop, location, weather_summary, prediction_day, resolved_stage)

    encoded = pd.get_dummies(candidate_frame[artifact["features_used"]], columns=artifact["categorical_columns"])
    encoded = encoded.reindex(columns=artifact["feature_columns"], fill_value=0)
    model = artifact["model"]
    probabilities = model.predict_proba(encoded)[:, 1] if hasattr(model, "predict_proba") else model.predict(encoded)

    risks: list[dict[str, Any]] = []
    for row, probability in zip(candidate_frame.to_dict(orient="records"), probabilities):
        confidence = round(float(probability), 2)
        if confidence < 0.45:
            continue
        risks.append(
            {
                "disease": row["disease"].replace("_", " "),
                "risk_level": map_confidence_to_level(confidence),
                "confidence": confidence,
                "prevention_tip": row["prevention_tip"],
                "urgency_days": row["urgency_days"]
            }
        )

    risks.sort(key=lambda item: item["confidence"], reverse=True)
    return {
        "crop": canonical_crop,
        "location": location,
        "prediction_date": prediction_day.isoformat(),
        "weather_summary": {
            "temp_avg": round(float(weather_summary["temp_avg"]), 1),
            "humidity_avg": round(float(weather_summary["humidity_avg"]), 1),
            "rainfall_7day_mm": round(float(weather_summary["rainfall_7day_mm"]), 1)
        },
        "crop_stage": resolved_stage,
        "risks": risks[:top_k],
        "model_version": f"{artifact['model_family']}_v1"
    }


def predict_weather_risk(
    crop: str,
    location: str = "Unknown",
    latitude: float | None = None,
    longitude: float | None = None,
    weather_summary: dict[str, Any] | None = None,
    prediction_date: Any = None,
    crop_stage: str | None = None,
    api_key: str | None = None,
    top_k: int = 5
) -> dict[str, Any]:
    live_weather_payload: dict[str, Any] | None = None
    if weather_summary is None:
        requested_location = location
        if requested_location and requested_location.strip().lower() in {"unknown", "current location"}:
            requested_location = "Chennai, Tamil Nadu"
        try:
            live_weather_payload = fetch_live_weather(
                latitude=latitude,
                longitude=longitude,
                location=requested_location,
                api_key=api_key,
            )
        except Exception:
            live_weather_payload = build_fallback_weather_payload(
                location=requested_location or location or "Chennai, Tamil Nadu",
                prediction_date=prediction_date,
            )
        weather_summary = live_weather_payload["weather_summary"]
        location = live_weather_payload["location"]

    try:
        prediction = ml_predict_weather_risk(
            crop=crop,
            location=location,
            weather_summary=weather_summary,
            prediction_date=prediction_date,
            crop_stage=crop_stage,
            top_k=top_k
        )
        if prediction["risks"]:
            result = prediction
        else:
            result = None
    except Exception:
        result = None

    if result is None:
        result = rule_predict(
            crop=crop,
            location=location,
            weather_summary=weather_summary,
            prediction_date=prediction_date,
            crop_stage=crop_stage,
            top_k=top_k
        )

    if live_weather_payload is not None:
        result["current_snapshot"] = live_weather_payload.get("current_snapshot")
        result["coordinates"] = live_weather_payload.get("coordinates")
        result["source"] = live_weather_payload.get("source")

    return result


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Unified weather risk predictor.")
    parser.add_argument("--crop", required=True)
    parser.add_argument("--location", default="Unknown")
    parser.add_argument("--lat", type=float, default=None)
    parser.add_argument("--lon", type=float, default=None)
    parser.add_argument("--temp", type=float, default=None)
    parser.add_argument("--humidity", type=float, default=None)
    parser.add_argument("--rainfall", type=float, default=None)
    parser.add_argument("--prediction-date", default=None)
    parser.add_argument("--crop-stage", default=None)
    parser.add_argument("--api-key", default=None)
    parser.add_argument("--top-k", type=int, default=5)
    return parser


def main() -> None:
    args = build_arg_parser().parse_args()
    manual_weather = None
    if args.temp is not None and args.humidity is not None and args.rainfall is not None:
        manual_weather = {
            "temp_avg": args.temp,
            "humidity_avg": args.humidity,
            "rainfall_7day_mm": args.rainfall
        }

    result = predict_weather_risk(
        crop=args.crop,
        location=args.location,
        latitude=args.lat,
        longitude=args.lon,
        weather_summary=manual_weather,
        prediction_date=args.prediction_date,
        crop_stage=args.crop_stage,
        api_key=args.api_key,
        top_k=args.top_k
    )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
