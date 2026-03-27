from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Any

import requests

from src.config import get_env

KNOWLEDGE_BASE_PATH = Path(__file__).resolve().parents[1] / "advisory" / "knowledge_base.json"
DOSAGE_PATTERN = re.compile(
    r"@\s*([0-9.]+\s*(?:g|kg|ml|l)(?:\s*/\s*(?:l|kg|ha|acre|plant))?)",
    re.IGNORECASE,
)
FREQUENCY_PATTERN = re.compile(r"(every\s+\d+(?:\s+to\s+\d+)?\s+days?)", re.IGNORECASE)
CHEMICAL_KEYWORDS = (
    "fungicide",
    "insecticide",
    "bactericide",
    "mancozeb",
    "chlorothalonil",
    "cymoxanil",
    "tricyclazole",
    "validamycin",
    "propiconazole",
    "tebuconazole",
    "sulphur",
    "copper",
)
ORGANIC_KEYWORDS = (
    "neem",
    "bio",
    "sticky trap",
    "mulch",
    "organic",
    "trichoderma",
)


@lru_cache(maxsize=1)
def load_knowledge_base() -> dict[str, Any]:
    with KNOWLEDGE_BASE_PATH.open("r", encoding="utf-8") as file:
        return json.load(file)


def _normalize_key(value: str) -> str:
    return value.strip().lower().replace(" ", "_")


def _find_matching_key(candidates: dict[str, Any], value: str) -> str | None:
    normalized = _normalize_key(value)
    for candidate in candidates.keys():
        if _normalize_key(candidate) == normalized:
            return candidate
    return None


def _lookup_entry(crop: str, disease: str) -> dict[str, Any]:
    knowledge_base = load_knowledge_base()
    crop_key = _find_matching_key(knowledge_base, crop)
    if crop_key is None:
        return knowledge_base["generic"]["fallback"]

    crop_entries = knowledge_base[crop_key]
    disease_key = _find_matching_key(crop_entries, disease)
    if disease_key is None:
        return knowledge_base["generic"]["fallback"]
    return crop_entries[disease_key]


def _extract_matching_line(lines: list[str], keywords: tuple[str, ...]) -> str | None:
    for line in lines:
        lowered = line.lower()
        if any(keyword in lowered for keyword in keywords):
            return line
    return None


def _extract_dosage(text: str | None) -> str:
    if not text:
        return "Follow the label rate recommended for this crop and disease."
    match = DOSAGE_PATTERN.search(text)
    return match.group(1).strip() if match else "Follow the label rate recommended for this crop and disease."


def _extract_frequency(text: str | None, severity: str) -> str:
    if text:
        match = FREQUENCY_PATTERN.search(text)
        if match:
            return match.group(1).capitalize()
    if severity.upper() == "HIGH":
        return "Repeat in 5 to 7 days if symptoms are active."
    if severity.upper() == "MEDIUM":
        return "Repeat in 7 days and reassess field spread."
    return "Monitor weekly and repeat only if symptoms appear."


def _default_organic_line(disease: str) -> str:
    if "healthy" in disease.lower():
        return "No organic treatment is needed right now; continue regular scouting."
    return "Neem oil spray or a Trichoderma-based bio-input can be used as a supportive organic option."


def _coerce_treatment_payload(payload: dict[str, Any], fallback_prevention: list[str], severity: str) -> dict[str, Any]:
    chemical = str(payload.get("chemical") or payload.get("chemical_treatment") or "").strip()
    organic = str(payload.get("organic") or payload.get("organic_treatment") or "").strip()
    dosage = str(payload.get("dosage") or "").strip()
    frequency = str(payload.get("frequency") or "").strip()
    prevention = payload.get("prevention") or fallback_prevention

    if isinstance(prevention, str):
        prevention = [prevention]

    return {
        "chemical": chemical or "Confirm the diagnosis before applying a crop-protection chemical.",
        "organic": organic or _default_organic_line(str(payload.get("disease", ""))),
        "dosage": dosage or "Follow the label rate recommended for this crop and disease.",
        "frequency": frequency or _extract_frequency(None, severity),
        "prevention": [str(item) for item in prevention] or fallback_prevention,
        "source": "external_model2",
    }


def predict_with_external_model(payload: dict[str, Any]) -> dict[str, Any]:
    endpoint = get_env("MODEL2_ENDPOINT")
    if not endpoint:
        raise RuntimeError("MODEL2_ENDPOINT is not configured.")

    response = requests.post(endpoint, json=payload, timeout=30)
    response.raise_for_status()
    return response.json()


def build_treatment_recommendation(
    crop: str,
    disease: str,
    severity: str,
    confidence: float | None = None,
    advisory: dict[str, Any] | None = None,
    model1_payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    advisory_payload = advisory or {}
    fallback_prevention = [str(item) for item in advisory_payload.get("prevention", [])]
    model2_payload = {
        "crop": crop,
        "disease": disease,
        "severity": severity,
        "confidence": confidence,
        "model1": model1_payload or {},
    }

    endpoint = get_env("MODEL2_ENDPOINT")
    if endpoint:
        try:
            external_payload = predict_with_external_model(model2_payload)
            return _coerce_treatment_payload(external_payload, fallback_prevention, severity)
        except Exception:
            pass

    entry = _lookup_entry(crop, disease)
    treatment_lines = [str(item) for item in entry.get("treatment", [])]
    prevention_lines = [str(item) for item in entry.get("prevention", [])] or fallback_prevention

    chemical_line = _extract_matching_line(treatment_lines, CHEMICAL_KEYWORDS) or (treatment_lines[0] if treatment_lines else "")
    organic_line = _extract_matching_line(treatment_lines, ORGANIC_KEYWORDS)
    if not organic_line:
        organic_line = _extract_matching_line(prevention_lines, ORGANIC_KEYWORDS) or _default_organic_line(disease)

    return {
        "chemical": chemical_line or "Confirm the diagnosis before applying a crop-protection chemical.",
        "organic": organic_line,
        "dosage": _extract_dosage(chemical_line or organic_line),
        "frequency": _extract_frequency(chemical_line or organic_line, severity),
        "prevention": prevention_lines,
        "source": "knowledge_base_fallback",
    }
