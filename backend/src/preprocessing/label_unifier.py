from __future__ import annotations

import argparse
import json
import random
import re
import sys
from pathlib import Path

import pandas as pd
from PIL import Image

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.preprocessing.augment import IMAGE_SIZE, enhance_image

SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}

CROP_ALIASES = {
    "bell pepper": "Pepper_Bell",
    "pepper bell": "Pepper_Bell",
    "capsicum": "Pepper_Bell",
    "chili": "Chilli",
    "chilli": "Chilli",
    "ground nut": "Groundnut",
    "soy bean": "Soybean"
}

DISEASE_ALIASES = {
    "early blight": "Early_Blight",
    "late blight": "Late_Blight",
    "leaf mold": "Leaf_Mold",
    "leaf curl virus": "Leaf_Curl_Virus",
    "yellow leaf curl virus": "Leaf_Curl_Virus",
    "bacterial spot": "Bacterial_Spot",
    "bacterial leaf blight": "Bacterial_Leaf_Blight",
    "powdery mildew": "Powdery_Mildew",
    "black rot": "Black_Rot",
    "septoria leaf spot": "Septoria_Leaf_Spot",
    "mosaic virus": "Mosaic_Virus",
    "target spot": "Target_Spot",
    "tikka leaf spot": "Tikka_Leaf_Spot",
    "northern leaf blight": "Northern_Leaf_Blight",
    "southern leaf blight": "Southern_Leaf_Blight",
    "common rust": "Rust",
    "leaf rust": "Leaf_Rust",
    "healthy": "Healthy"
}


def slug_to_title(value: str) -> str:
    return "_".join(part.capitalize() for part in value.split("_") if part)


def normalize_crop_name(raw_label: str) -> str:
    normalized = raw_label.replace("___", " ").replace("_", " ").replace("-", " ").lower()
    normalized = re.sub(r"\s+", " ", normalized).strip()
    for alias, crop_name in CROP_ALIASES.items():
        if normalized.startswith(alias):
            return crop_name
    first_token = normalized.split(" ")[0]
    return slug_to_title(first_token)


def normalize_disease_name(raw_label: str) -> str:
    normalized = raw_label.replace("___", " ").replace("_", " ").replace("-", " ").lower()
    normalized = re.sub(r"\s+", " ", normalized).strip()
    for alias, disease_name in DISEASE_ALIASES.items():
        if alias in normalized:
            return disease_name

    tokens = normalized.split(" ")
    if len(tokens) > 1:
        inferred = "_".join(token.capitalize() for token in tokens[1:])
        return inferred or "Healthy"
    return "Healthy"


def normalize_label(raw_label: str) -> tuple[str, str, str]:
    crop = normalize_crop_name(raw_label)
    disease = normalize_disease_name(raw_label)
    if disease == "Healthy":
        canonical = f"{crop}___Healthy"
    else:
        canonical = f"{crop}___{disease}"
    return canonical, crop, disease


def discover_images(dataset_dir: Path) -> list[tuple[Path, str]]:
    discovered: list[tuple[Path, str]] = []
    for path in dataset_dir.rglob("*"):
        if path.is_file() and path.suffix.lower() in SUPPORTED_EXTENSIONS:
            label_name = path.parent.name
            discovered.append((path, label_name))
    return discovered


def assign_splits(labels: list[str], seed: int = 42) -> list[str]:
    rng = random.Random(seed)
    indices = list(range(len(labels)))
    rng.shuffle(indices)

    split_lookup = ["train"] * len(labels)
    label_to_indices: dict[str, list[int]] = {}
    for index, label in enumerate(labels):
        label_to_indices.setdefault(label, []).append(index)

    for _, label_indices in label_to_indices.items():
        rng.shuffle(label_indices)
        total = len(label_indices)
        val_count = max(1, int(total * 0.1)) if total >= 10 else (1 if total >= 3 else 0)
        test_count = max(1, int(total * 0.1)) if total >= 10 else (1 if total >= 5 else 0)
        for idx in label_indices[:val_count]:
            split_lookup[idx] = "val"
        for idx in label_indices[val_count : val_count + test_count]:
            split_lookup[idx] = "test"
    return split_lookup


def process_and_merge_datasets(dataset_dirs: list[Path], output_dir: Path, seed: int = 42) -> pd.DataFrame:
    images_dir = output_dir / "images"
    images_dir.mkdir(parents=True, exist_ok=True)

    records: list[dict[str, object]] = []
    for dataset_dir in dataset_dirs:
        dataset_name = dataset_dir.name
        for source_path, raw_label in discover_images(dataset_dir):
            canonical_label, crop, disease = normalize_label(raw_label)
            label_dir = images_dir / canonical_label
            label_dir.mkdir(parents=True, exist_ok=True)

            output_name = f"{dataset_name}_{source_path.parent.name}_{source_path.stem}.jpg".replace(" ", "_")
            output_path = label_dir / output_name
            with Image.open(source_path) as image:
                enhanced = enhance_image(image.convert("RGB"))
                enhanced.resize(IMAGE_SIZE).save(output_path, quality=95)

            records.append(
                {
                    "image_path": str(output_path.resolve()),
                    "label": canonical_label,
                    "crop": crop,
                    "disease": disease,
                    "dataset": dataset_name
                }
            )

    if not records:
        raise ValueError("No images were found in the provided dataset folders.")

    dataframe = pd.DataFrame(records)
    class_names = sorted(dataframe["label"].unique())
    label_map = {label: index for index, label in enumerate(class_names)}
    dataframe["label_index"] = dataframe["label"].map(label_map)
    dataframe["split"] = assign_splits(dataframe["label"].tolist(), seed=seed)

    output_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = output_dir / "manifest.csv"
    dataframe.to_csv(manifest_path, index=False)

    label_map_path = output_dir / "label_map.json"
    with label_map_path.open("w", encoding="utf-8") as file:
        json.dump({str(index): label for label, index in label_map.items()}, file, indent=2)
    return dataframe


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Merge PlantVillage, PlantDoc, and regional datasets into a unified manifest.")
    parser.add_argument("--datasets", nargs="+", required=True, help="List of dataset root folders.")
    parser.add_argument("--output-dir", required=True, help="Directory for processed images and manifest.csv")
    parser.add_argument("--seed", type=int, default=42)
    return parser


def main() -> None:
    args = build_arg_parser().parse_args()
    dataframe = process_and_merge_datasets(
        dataset_dirs=[Path(item) for item in args.datasets],
        output_dir=Path(args.output_dir),
        seed=args.seed
    )
    print(f"Processed {len(dataframe)} images into {Path(args.output_dir) / 'manifest.csv'}")


if __name__ == "__main__":
    main()
