from __future__ import annotations

import argparse
import io
import json
import sys
from functools import lru_cache
from pathlib import Path
from typing import Any

import numpy as np
import onnxruntime as ort
from PIL import Image, ImageOps

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.config import MODEL1_LABEL_MAP_PATH, MODEL1_ONNX_PATH
from src.inference.severity import estimate_severity
from src.preprocessing.augment import IMAGENET_MEAN, IMAGENET_STD, IMAGE_SIZE, enhance_image


@lru_cache(maxsize=1)
def load_session(model_path: str = str(MODEL1_ONNX_PATH)) -> ort.InferenceSession:
    if not Path(model_path).exists():
        raise FileNotFoundError(f"ONNX model not found at {model_path}")
    return ort.InferenceSession(model_path, providers=["CPUExecutionProvider"])


@lru_cache(maxsize=1)
def load_label_map(label_map_path: str = str(MODEL1_LABEL_MAP_PATH)) -> dict[int, str]:
    if not Path(label_map_path).exists():
        raise FileNotFoundError(f"Label map not found at {label_map_path}")
    payload = json.loads(Path(label_map_path).read_text(encoding="utf-8"))
    return {int(key): value for key, value in payload.items()}


def _image_to_batch(image: Image.Image) -> np.ndarray:
    resized = image.resize(IMAGE_SIZE, Image.Resampling.BILINEAR)
    array = np.asarray(resized, dtype=np.float32) / 255.0
    array = (array - np.array(IMAGENET_MEAN, dtype=np.float32)) / np.array(IMAGENET_STD, dtype=np.float32)
    return np.transpose(array, (2, 0, 1))[None, ...].astype(np.float32)


def _center_crop_variant(image: Image.Image, resize_to: int, crop_to: int) -> Image.Image:
    resized = image.resize((resize_to, resize_to), Image.Resampling.BILINEAR)
    margin = max((resize_to - crop_to) // 2, 0)
    cropped = resized.crop((margin, margin, margin + crop_to, margin + crop_to))
    return cropped.resize(IMAGE_SIZE, Image.Resampling.BILINEAR)


def build_tta_variants(image: Image.Image) -> list[Image.Image]:
    enhanced = enhance_image(image.convert("RGB"))
    rotated = enhanced.rotate(10, resample=Image.Resampling.BILINEAR, expand=True)
    return [
        enhanced.resize(IMAGE_SIZE, Image.Resampling.BILINEAR),
        _center_crop_variant(enhanced, resize_to=256, crop_to=224),
        ImageOps.mirror(enhanced).resize(IMAGE_SIZE, Image.Resampling.BILINEAR),
        ImageOps.flip(enhanced).resize(IMAGE_SIZE, Image.Resampling.BILINEAR),
        ImageOps.fit(rotated, IMAGE_SIZE, method=Image.Resampling.BILINEAR),
    ]


def softmax(logits: np.ndarray) -> np.ndarray:
    shifted = logits - np.max(logits, axis=1, keepdims=True)
    exp_values = np.exp(shifted)
    return exp_values / np.sum(exp_values, axis=1, keepdims=True)


def parse_label(label: str) -> tuple[str, str]:
    if "___" in label:
        crop, disease = label.split("___", 1)
    else:
        crop, disease = "Unknown", label
    return crop.replace("_", " "), disease.replace("_", " ")


def predict_with_tta(session: ort.InferenceSession, image: Image.Image) -> tuple[np.ndarray, Image.Image]:
    variants = build_tta_variants(image)
    probabilities: list[np.ndarray] = []
    for variant in variants:
        logits = session.run(["logits"], {"input": _image_to_batch(variant)})[0]
        probabilities.append(softmax(logits)[0])
    averaged_probabilities = np.mean(np.stack(probabilities, axis=0), axis=0)
    return averaged_probabilities, variants[0]


def predict_image(
    image_input: Image.Image | bytes | Path | str,
    model_path: Path = MODEL1_ONNX_PATH,
    label_map_path: Path = MODEL1_LABEL_MAP_PATH,
    top_k: int = 3
) -> dict[str, Any]:
    if isinstance(image_input, (str, Path)):
        image = Image.open(image_input).convert("RGB")
    elif isinstance(image_input, bytes):
        image = Image.open(io.BytesIO(image_input)).convert("RGB")
    else:
        image = image_input.convert("RGB")

    session = load_session(str(model_path))
    label_map = load_label_map(str(label_map_path))
    probabilities, scored_image = predict_with_tta(session, image)

    ranked_indices = np.argsort(probabilities)[::-1][:top_k]
    predicted_index = int(ranked_indices[0])
    predicted_label = label_map[predicted_index]
    crop, disease = parse_label(predicted_label)
    confidence = float(probabilities[predicted_index])
    severity = estimate_severity(scored_image, disease, confidence)

    return {
        "crop": crop,
        "disease": disease,
        "label": predicted_label,
        "confidence": round(confidence, 4),
        "severity": severity["severity"],
        "lesion_ratio": severity["lesion_ratio"],
        "top_predictions": [
            {
                "label": label_map[int(index)],
                "confidence": round(float(probabilities[int(index)]), 4)
            }
            for index in ranked_indices
        ]
    }


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run ONNX image inference on a crop leaf image.")
    parser.add_argument("--image", required=True)
    parser.add_argument("--top-k", type=int, default=3)
    return parser


def main() -> None:
    args = build_arg_parser().parse_args()
    result = predict_image(Path(args.image), top_k=args.top_k)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
