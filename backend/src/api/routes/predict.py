from __future__ import annotations

from datetime import date

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from src.advisory.engine import build_advisory
from src.api.schemas import ImagePredictionResponse
from src.inference.predict import predict_image
from src.model2.bridge import build_treatment_recommendation

router = APIRouter()


@router.post("/image", response_model=ImagePredictionResponse)
async def image_prediction(
    file: UploadFile = File(...),
    crop: str | None = Form(default=None),
    location: str = Form(default="Unknown")
) -> dict[str, object]:
    try:
        image_bytes = await file.read()
        prediction = predict_image(image_bytes)
        detected_crop = str(prediction["crop"])
        requested_crop = crop.strip() if crop else None
        resolved_crop = detected_crop
        advisory = build_advisory(
            crop=resolved_crop,
            disease=prediction["disease"],
            severity=prediction["severity"],
            location=location,
            confidence=prediction["confidence"],
            prediction_date=date.today().isoformat()
        )
        treatment = build_treatment_recommendation(
            crop=resolved_crop,
            disease=prediction["disease"],
            severity=prediction["severity"],
            confidence=prediction["confidence"],
            advisory=advisory,
            model1_payload=prediction,
        )
        prediction["treatment"] = treatment
        prediction["advisory"] = advisory
        prediction["metadata"] = {
            "filename": file.filename,
            "content_type": file.content_type,
            "requested_crop": requested_crop,
            "detected_crop": detected_crop,
            "crop_mismatch": bool(
                requested_crop and requested_crop.casefold() != detected_crop.casefold()
            ),
        }
        return prediction
    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=503,
            detail="ONNX model not found. Train Model 1 and run export_onnx.py before calling this endpoint."
        ) from exc
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Image prediction failed: {exc}") from exc
