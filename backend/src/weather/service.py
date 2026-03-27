from __future__ import annotations

import json
from functools import lru_cache
from typing import Any

from src.config import CROP_REGION_MAP_PATH


@lru_cache(maxsize=1)
def load_crop_region_map() -> dict[str, list[str]]:
    with CROP_REGION_MAP_PATH.open("r", encoding="utf-8") as file:
        return json.load(file)


def suggest_crops_for_location(location: str) -> list[str]:
    region_map = load_crop_region_map()
    normalized = location.strip().lower()
    for state_name, crops in region_map.items():
        if state_name.lower() in normalized:
            return crops
    return sorted({crop for values in region_map.values() for crop in values})


def weather_payload_to_summary(payload: dict[str, Any]) -> dict[str, float]:
    summary = payload.get("weather_summary", payload)
    return {
        "temp_avg": float(summary["temp_avg"]),
        "humidity_avg": float(summary["humidity_avg"]),
        "rainfall_7day_mm": float(summary["rainfall_7day_mm"])
    }
