from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd
import requests

from src.config import MODEL3_RAW_DATA_PATH, ensure_runtime_directories

NASA_POWER_URL = "https://power.larc.nasa.gov/api/temporal/daily/point"

DEFAULT_CITY_CATALOG: list[dict[str, Any]] = [
    {"city": "Chennai", "state": "Tamil Nadu", "latitude": 13.0827, "longitude": 80.2707},
    {"city": "Bengaluru", "state": "Karnataka", "latitude": 12.9716, "longitude": 77.5946},
    {"city": "Hyderabad", "state": "Telangana", "latitude": 17.3850, "longitude": 78.4867},
    {"city": "Mumbai", "state": "Maharashtra", "latitude": 19.0760, "longitude": 72.8777},
    {"city": "Pune", "state": "Maharashtra", "latitude": 18.5204, "longitude": 73.8567},
    {"city": "Ahmedabad", "state": "Gujarat", "latitude": 23.0225, "longitude": 72.5714},
    {"city": "Jaipur", "state": "Rajasthan", "latitude": 26.9124, "longitude": 75.7873},
    {"city": "Lucknow", "state": "Uttar Pradesh", "latitude": 26.8467, "longitude": 80.9462},
    {"city": "Bhopal", "state": "Madhya Pradesh", "latitude": 23.2599, "longitude": 77.4126},
    {"city": "Kolkata", "state": "West Bengal", "latitude": 22.5726, "longitude": 88.3639}
]


def fetch_city_weather(city_record: dict[str, Any], start_date: str, end_date: str) -> list[dict[str, Any]]:
    response = requests.get(
        NASA_POWER_URL,
        params={
            "parameters": "T2M,RH2M,PRECTOTCORR",
            "community": "AG",
            "longitude": city_record["longitude"],
            "latitude": city_record["latitude"],
            "start": start_date,
            "end": end_date,
            "format": "JSON"
        },
        timeout=60
    )
    response.raise_for_status()
    payload = response.json()

    parameters = payload["properties"]["parameter"]
    temp_map = parameters["T2M"]
    humidity_map = parameters["RH2M"]
    rainfall_map = parameters["PRECTOTCORR"]

    rows: list[dict[str, Any]] = []
    for date_key in sorted(temp_map.keys()):
        values = (temp_map.get(date_key), humidity_map.get(date_key), rainfall_map.get(date_key))
        if any(value in (-999, -999.0, None) for value in values):
            continue
        rows.append(
            {
                "date": datetime.strptime(date_key, "%Y%m%d").date().isoformat(),
                "city": city_record["city"],
                "state": city_record["state"],
                "latitude": city_record["latitude"],
                "longitude": city_record["longitude"],
                "temp_c": round(float(temp_map[date_key]), 2),
                "humidity_pct": round(float(humidity_map[date_key]), 2),
                "rainfall_mm": round(float(rainfall_map[date_key]), 2)
            }
        )
    return rows


def fetch_nasa_power_dataset(start_date: str, end_date: str, output_path: Path = MODEL3_RAW_DATA_PATH) -> pd.DataFrame:
    ensure_runtime_directories()
    all_rows: list[dict[str, Any]] = []
    for city_record in DEFAULT_CITY_CATALOG:
        print(f"Fetching NASA POWER data for {city_record['city']}, {city_record['state']}...")
        all_rows.extend(fetch_city_weather(city_record, start_date=start_date, end_date=end_date))

    if not all_rows:
        raise ValueError("NASA POWER returned no rows.")

    dataframe = pd.DataFrame(all_rows).sort_values(["city", "date"]).reset_index(drop=True)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    dataframe.to_csv(output_path, index=False)
    return dataframe


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Download historical weather from NASA POWER.")
    parser.add_argument("--start", default="20190101")
    parser.add_argument("--end", default=datetime.now().strftime("%Y%m%d"))
    parser.add_argument("--output", default=str(MODEL3_RAW_DATA_PATH))
    return parser


def main() -> None:
    args = build_arg_parser().parse_args()
    dataframe = fetch_nasa_power_dataset(args.start, args.end, Path(args.output))
    print(f"Saved {len(dataframe)} rows to {args.output}")


if __name__ == "__main__":
    main()
