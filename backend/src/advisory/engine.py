from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from src.model3.rule_engine import normalize_crop_name, parse_prediction_date

KNOWLEDGE_BASE_PATH = Path(__file__).with_name("knowledge_base.json")


@lru_cache(maxsize=1)
def load_knowledge_base() -> dict[str, Any]:
    with KNOWLEDGE_BASE_PATH.open("r", encoding="utf-8") as file:
        return json.load(file)


def _normalize_disease_key(disease: str) -> str:
    return disease.strip().replace(" ", "_")


def _severity_to_priority(severity: str) -> str:
    normalized = severity.upper()
    if normalized == "HIGH":
        return "Immediate action within 24 to 48 hours."
    if normalized == "MEDIUM":
        return "Act within the next 3 to 4 days and keep close watch."
    return "Monitor and act if symptoms expand."


def _select_entry(crop: str, disease: str) -> dict[str, list[str]]:
    knowledge_base = load_knowledge_base()
    try:
        canonical_crop = normalize_crop_name(crop, knowledge_base)
    except Exception:
        canonical_crop = crop.title()

    crop_entries = knowledge_base.get(canonical_crop, {})
    disease_key = _normalize_disease_key(disease)
    entry = crop_entries.get(disease_key)
    if entry:
        return entry
    return knowledge_base["generic"]["fallback"]


def build_advisory(
    crop: str,
    disease: str,
    severity: str = "LOW",
    location: str = "Unknown",
    confidence: float | None = None,
    prediction_date: str | None = None,
    risk_level: str | None = None
) -> dict[str, Any]:
    entry = _select_entry(crop, disease)
    resolved_date = parse_prediction_date(prediction_date).isoformat()
    risk_text = risk_level or severity
    return {
        "crop": crop,
        "disease": disease,
        "location": location,
        "prediction_date": resolved_date,
        "severity": severity.upper(),
        "risk_level": risk_text.upper(),
        "confidence": round(float(confidence), 4) if confidence is not None else None,
        "treatment": entry["treatment"],
        "fertilizer": entry["fertilizer"],
        "prevention": entry["prevention"],
        "next_step": _severity_to_priority(severity),
        "farmer_message": (
            f"{disease} risk for {crop} in {location} is currently {risk_text.upper()}. "
            "Confirm field symptoms before using any curative chemical."
        )
    }


def merge_risk_advisories(
    crop: str,
    location: str,
    prediction_date: str,
    risks: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    return [
        build_advisory(
            crop=crop,
            disease=risk["disease"],
            severity=risk.get("risk_level", "LOW"),
            location=location,
            confidence=risk.get("confidence"),
            prediction_date=prediction_date,
            risk_level=risk.get("risk_level")
        )
        for risk in risks
    ]
