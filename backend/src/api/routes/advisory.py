from __future__ import annotations

from fastapi import APIRouter, HTTPException

from src.advisory.engine import build_advisory, merge_risk_advisories
from src.api.schemas import AdvisoryRequest

router = APIRouter()


@router.post("")
def advisory(payload: AdvisoryRequest) -> dict[str, object]:
    try:
        if payload.risks:
            advisories = merge_risk_advisories(
                crop=payload.crop,
                location=payload.location,
                prediction_date=payload.prediction_date.isoformat() if payload.prediction_date else None,
                risks=[risk.model_dump() for risk in payload.risks]
            )
            return {
                "crop": payload.crop,
                "location": payload.location,
                "prediction_date": payload.prediction_date.isoformat() if payload.prediction_date else None,
                "advisories": advisories
            }

        if not payload.disease:
            raise ValueError("Provide either a disease or a list of weather risks.")

        return build_advisory(
            crop=payload.crop,
            disease=payload.disease,
            severity=payload.severity,
            location=payload.location,
            confidence=payload.confidence,
            prediction_date=payload.prediction_date.isoformat() if payload.prediction_date else None,
            risk_level=payload.risk_level
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Advisory generation failed: {exc}") from exc
