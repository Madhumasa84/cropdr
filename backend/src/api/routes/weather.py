from __future__ import annotations

from fastapi import APIRouter, HTTPException

from src.api.schemas import WeatherRiskRequest, WeatherRiskResponse
from src.model3.predictor import predict_weather_risk

router = APIRouter()


@router.post("/weather-risk", response_model=WeatherRiskResponse)
def weather_risk_prediction(payload: WeatherRiskRequest) -> dict[str, object]:
    try:
        weather_summary = payload.weather_summary.model_dump() if payload.weather_summary else None
        return predict_weather_risk(
            crop=payload.crop,
            location=payload.location,
            latitude=payload.latitude,
            longitude=payload.longitude,
            weather_summary=weather_summary,
            prediction_date=payload.prediction_date.isoformat() if payload.prediction_date else None,
            crop_stage=payload.crop_stage,
            api_key=payload.api_key,
            top_k=payload.top_k
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Weather risk prediction failed: {exc}") from exc
