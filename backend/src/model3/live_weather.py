from __future__ import annotations

import argparse
import json
import statistics
from typing import Any

import requests

from src.config import get_env

OPENWEATHER_FORECAST_URL = "https://api.openweathermap.org/data/2.5/forecast"
OPENWEATHER_GEOCODE_URL = "https://api.openweathermap.org/geo/1.0/direct"
PLACEHOLDER_KEYS = {"", "YOUR_OPENWEATHER_API_KEY", "your_openweathermap_api_key_here"}
REQUEST_TIMEOUT_SECONDS = 10


def resolve_api_key(api_key: str | None = None) -> str:
    resolved = (api_key or get_env("OPENWEATHERMAP_API_KEY") or "").strip()
    if resolved in PLACEHOLDER_KEYS:
        raise ValueError(
            "OpenWeatherMap API key is missing. Set OPENWEATHERMAP_API_KEY in .env or pass --api-key."
        )
    return resolved


def geocode_location(location: str, api_key: str | None = None) -> tuple[float, float, str]:
    resolved_key = resolve_api_key(api_key)
    response = requests.get(
        OPENWEATHER_GEOCODE_URL,
        params={"q": location, "limit": 1, "appid": resolved_key},
        timeout=REQUEST_TIMEOUT_SECONDS
    )
    response.raise_for_status()
    payload = response.json()
    if not payload:
        raise ValueError(f"Could not geocode location '{location}'.")
    item = payload[0]
    label_parts = [item.get("name"), item.get("state"), item.get("country")]
    return float(item["lat"]), float(item["lon"]), ", ".join(part for part in label_parts if part)


def fetch_live_weather(
    latitude: float | None = None,
    longitude: float | None = None,
    location: str | None = None,
    api_key: str | None = None,
    units: str = "metric"
) -> dict[str, Any]:
    if latitude is None or longitude is None:
        if not location:
            raise ValueError("Provide either latitude and longitude or a location string.")
        latitude, longitude, location = geocode_location(location, api_key=api_key)

    resolved_key = resolve_api_key(api_key)
    response = requests.get(
        OPENWEATHER_FORECAST_URL,
        params={"lat": latitude, "lon": longitude, "appid": resolved_key, "units": units},
        timeout=REQUEST_TIMEOUT_SECONDS
    )
    response.raise_for_status()
    payload = response.json()

    forecast_rows = payload.get("list", [])
    if not forecast_rows:
        raise ValueError("OpenWeatherMap returned no forecast rows.")

    temperatures = [float(item["main"]["temp"]) for item in forecast_rows if "main" in item]
    humidities = [float(item["main"]["humidity"]) for item in forecast_rows if "main" in item]
    rainfall_total = sum(float(item.get("rain", {}).get("3h", 0.0)) for item in forecast_rows)
    first_row = forecast_rows[0]
    city_info = payload.get("city", {})
    location_parts = [city_info.get("name"), city_info.get("country")]
    resolved_location = location or ", ".join(part for part in location_parts if part) or f"{latitude}, {longitude}"

    return {
        "location": resolved_location,
        "coordinates": {"latitude": latitude, "longitude": longitude},
        "observation_time": first_row.get("dt_txt"),
        "weather_summary": {
            "temp_avg": round(statistics.mean(temperatures), 1),
            "humidity_avg": round(statistics.mean(humidities), 1),
            "rainfall_7day_mm": round(rainfall_total, 1)
        },
        "current_snapshot": {
            "temp": round(float(first_row["main"]["temp"]), 1),
            "humidity": round(float(first_row["main"]["humidity"]), 1),
            "description": first_row.get("weather", [{}])[0].get("description", "unknown")
        },
        "forecast_points": len(forecast_rows),
        "source": "OpenWeatherMap 5-day forecast"
    }


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Fetch live weather from OpenWeatherMap.")
    parser.add_argument("--lat", type=float, default=None)
    parser.add_argument("--lon", type=float, default=None)
    parser.add_argument("--location", default=None)
    parser.add_argument("--api-key", default=None)
    parser.add_argument("--units", default="metric", choices=["metric", "imperial", "standard"])
    return parser


def main() -> None:
    args = build_arg_parser().parse_args()
    payload = fetch_live_weather(
        latitude=args.lat,
        longitude=args.lon,
        location=args.location,
        api_key=args.api_key,
        units=args.units
    )
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
