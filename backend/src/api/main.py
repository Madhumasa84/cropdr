from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.routes import advisory, predict, weather

app = FastAPI(
    title="Crop Disease Prediction Platform API",
    version="1.0.0",
    description="Phase 1 backend for image disease detection, weather-based disease risk, and advisory delivery."
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

app.include_router(predict.router, prefix="/predict", tags=["Prediction"])
app.include_router(weather.router, prefix="/predict", tags=["Weather"])
app.include_router(advisory.router, prefix="/advisory", tags=["Advisory"])


@app.get("/")
def root() -> dict[str, object]:
    return {
        "service": "crop_disease_platform",
        "status": "ok",
        "docs": "/docs",
        "endpoints": [
            "/predict/image",
            "/predict/weather-risk",
            "/advisory"
        ]
    }


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
