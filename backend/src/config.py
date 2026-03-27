from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

BACKEND_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = BACKEND_ROOT / "data"
MODELS_DIR = BACKEND_ROOT / "models"
SRC_DIR = BACKEND_ROOT / "src"
ENV_PATH = BACKEND_ROOT / ".env"

load_dotenv(ENV_PATH, override=False)

RAW_DATA_DIR = DATA_DIR / "raw"
PROCESSED_DATA_DIR = DATA_DIR / "processed"
MODEL1_CHECKPOINT_PATH = MODELS_DIR / "model1_best.pth"
MODEL1_ONNX_PATH = MODELS_DIR / "model1.onnx"
MODEL1_LABEL_MAP_PATH = MODELS_DIR / "model1_label_map.json"
MODEL1_TRAINING_HISTORY_PATH = MODELS_DIR / "model1_training_history.json"
MODEL1_EVALUATION_PATH = MODELS_DIR / "model1_evaluation.json"
MODEL1_CONFUSION_MATRIX_PATH = MODELS_DIR / "model1_confusion_matrix.csv"
MODEL1_FIELD_EVALUATION_PATH = MODELS_DIR / "field_evaluation_report.json"
MODEL1_FIELD_CONFUSION_MATRIX_PATH = MODELS_DIR / "field_confusion_matrix.png"
MODEL3_TRAINING_DATA_PATH = PROCESSED_DATA_DIR / "weather_training_data.csv"
MODEL3_RAW_DATA_PATH = RAW_DATA_DIR / "nasa_power_raw.csv"
MODEL3_MODEL_PATH = MODELS_DIR / "weather_risk_model.pkl"
MODEL3_METADATA_PATH = MODELS_DIR / "weather_risk_model_metadata.json"
CROP_REGION_MAP_PATH = DATA_DIR / "crop_region_map.json"


def ensure_runtime_directories() -> None:
    RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)
    PROCESSED_DATA_DIR.mkdir(parents=True, exist_ok=True)
    MODELS_DIR.mkdir(parents=True, exist_ok=True)


def get_env(name: str, default: str | None = None) -> str | None:
    value = os.getenv(name, default)
    return value.strip() if isinstance(value, str) else value
