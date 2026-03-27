from __future__ import annotations

from datetime import date
from typing import Any

from pydantic import AliasChoices, BaseModel, Field


class WeatherSummaryInput(BaseModel):
    temp_avg: float = Field(..., description="Average temperature in Celsius.")
    humidity_avg: float = Field(..., ge=0, le=100, description="Average humidity percentage.")
    rainfall_7day_mm: float = Field(..., ge=0, description="Rainfall across the last 7 days in millimeters.")


class WeatherCurrentSnapshot(BaseModel):
    temp: float | None = None
    humidity: float | None = None
    description: str | None = None


class Coordinates(BaseModel):
    latitude: float
    longitude: float


class RiskItem(BaseModel):
    disease: str
    risk_level: str
    confidence: float
    prevention_tip: str
    urgency_days: int


class WeatherRiskRequest(BaseModel):
    crop: str
    location: str | None = Field(
        default=None,
        validation_alias=AliasChoices("location", "city"),
    )
    latitude: float | None = Field(
        default=None,
        validation_alias=AliasChoices("latitude", "lat"),
    )
    longitude: float | None = Field(
        default=None,
        validation_alias=AliasChoices("longitude", "lon"),
    )
    prediction_date: date | None = None
    crop_stage: str | None = None
    weather_summary: WeatherSummaryInput | None = None
    api_key: str | None = None
    top_k: int = Field(default=5, ge=1, le=10)


class WeatherRiskResponse(BaseModel):
    crop: str
    location: str
    prediction_date: str
    weather_summary: dict[str, float]
    crop_stage: str
    risks: list[RiskItem]
    model_version: str
    current_snapshot: WeatherCurrentSnapshot | None = None
    coordinates: Coordinates | None = None
    source: str | None = None


class PredictionCandidate(BaseModel):
    label: str
    confidence: float


class TreatmentResponse(BaseModel):
    chemical: str
    organic: str
    dosage: str
    frequency: str
    prevention: list[str]
    source: str | None = None


class AdvisoryResponse(BaseModel):
    crop: str
    disease: str
    location: str
    prediction_date: str
    severity: str
    risk_level: str
    confidence: float | None = None
    treatment: list[str]
    fertilizer: list[str]
    prevention: list[str]
    next_step: str
    farmer_message: str


class AdvisoryRequest(BaseModel):
    crop: str
    disease: str | None = None
    severity: str = "LOW"
    location: str = "Unknown"
    confidence: float | None = None
    prediction_date: date | None = None
    risk_level: str | None = None
    risks: list[RiskItem] | None = None


class ImagePredictionResponse(BaseModel):
    crop: str
    disease: str
    label: str
    confidence: float
    severity: str
    lesion_ratio: float
    treatment: TreatmentResponse
    top_predictions: list[PredictionCandidate]
    advisory: AdvisoryResponse | None = None
    metadata: dict[str, Any] | None = None
