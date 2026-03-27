from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns
import torch
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix, f1_score
from torch.utils.data import DataLoader
from torchvision import datasets

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.config import (
    MODEL1_CHECKPOINT_PATH,
    MODEL1_CONFUSION_MATRIX_PATH,
    MODEL1_EVALUATION_PATH,
    MODEL1_FIELD_CONFUSION_MATRIX_PATH,
    MODEL1_FIELD_EVALUATION_PATH,
    MODEL1_LABEL_MAP_PATH,
    PROCESSED_DATA_DIR,
)
from src.model1.model import ManifestImageDataset, load_model_from_checkpoint
from src.preprocessing.augment import build_eval_transforms


def evaluate_model(manifest_path: Path, checkpoint_path: Path = MODEL1_CHECKPOINT_PATH, batch_size: int = 16) -> dict[str, object]:
    model, checkpoint = load_model_from_checkpoint(checkpoint_path)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = model.to(device)
    model.eval()

    dataframe = pd.read_csv(manifest_path)
    split_name = "test" if (dataframe["split"] == "test").any() else "val"
    dataset = ManifestImageDataset(manifest_path, split_name, build_eval_transforms())
    loader = DataLoader(dataset, batch_size=batch_size, shuffle=False, num_workers=0)

    predictions: list[int] = []
    targets: list[int] = []
    with torch.no_grad():
        for images, labels in loader:
            images = images.to(device)
            logits = model(images)
            predictions.extend(torch.argmax(logits, dim=1).cpu().tolist())
            targets.extend(labels.tolist())

    labels = list(range(len(checkpoint["class_names"])))
    report = classification_report(
        targets,
        predictions,
        labels=labels,
        target_names=checkpoint["class_names"],
        zero_division=0,
        output_dict=True,
    )

    confusion = confusion_matrix(targets, predictions, labels=labels)
    confusion_frame = pd.DataFrame(confusion, index=checkpoint["class_names"], columns=checkpoint["class_names"])
    confusion_frame.to_csv(MODEL1_CONFUSION_MATRIX_PATH)

    evaluation = {
        "split": split_name,
        "accuracy": round(accuracy_score(targets, predictions), 4),
        "f1_macro": round(f1_score(targets, predictions, average="macro", zero_division=0), 4),
        "confusion_matrix_path": str(MODEL1_CONFUSION_MATRIX_PATH),
        "classification_report": report,
    }
    MODEL1_EVALUATION_PATH.write_text(json.dumps(evaluation, indent=2), encoding="utf-8")
    return evaluation


def _normalize_label(value: str) -> str:
    return value.strip().lower().replace(" ", "_")


def evaluate_on_field_data(
    field_data_dir: Path,
    checkpoint_path: Path = MODEL1_CHECKPOINT_PATH,
    label_map_path: Path = MODEL1_LABEL_MAP_PATH,
    batch_size: int = 32,
) -> dict[str, object]:
    model, _ = load_model_from_checkpoint(checkpoint_path)
    with label_map_path.open("r", encoding="utf-8") as file:
        label_map_raw = json.load(file)
    label_map = {int(key): value for key, value in label_map_raw.items()}

    transform = build_eval_transforms()
    dataset = datasets.ImageFolder(str(field_data_dir), transform=transform)
    loader = DataLoader(dataset, batch_size=batch_size, shuffle=False, num_workers=0)

    model_label_lookup = {_normalize_label(label): index for index, label in label_map.items()}
    dataset_index_to_model_index: dict[int, int] = {}
    for class_name, dataset_index in dataset.class_to_idx.items():
        normalized_name = _normalize_label(class_name)
        if normalized_name not in model_label_lookup:
            raise ValueError(
                f"Field class '{class_name}' is missing from the model label map. "
                "Ensure the folder names match the training labels."
            )
        dataset_index_to_model_index[dataset_index] = model_label_lookup[normalized_name]

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = model.to(device)
    model.eval()
    all_preds: list[int] = []
    all_labels: list[int] = []

    with torch.no_grad():
        for images, labels in loader:
            images = images.to(device)
            outputs = model(images)
            predictions = outputs.argmax(dim=1).cpu().tolist()
            mapped_labels = [dataset_index_to_model_index[int(label)] for label in labels.tolist()]
            all_preds.extend(predictions)
            all_labels.extend(mapped_labels)

    ordered_labels = sorted(label_map.keys())
    class_names = [label_map[index] for index in ordered_labels]
    report = classification_report(
        all_labels,
        all_preds,
        labels=ordered_labels,
        target_names=class_names,
        zero_division=0,
        output_dict=True,
    )
    confusion = confusion_matrix(all_labels, all_preds, labels=ordered_labels)

    plt.figure(figsize=(16, 14))
    sns.heatmap(
        confusion,
        annot=True,
        fmt="d",
        cmap="Greens",
        xticklabels=class_names,
        yticklabels=class_names,
    )
    plt.title("Field Evaluation - Confusion Matrix")
    plt.ylabel("True Label")
    plt.xlabel("Predicted Label")
    plt.tight_layout()
    plt.savefig(MODEL1_FIELD_CONFUSION_MATRIX_PATH, dpi=120)
    plt.close()

    summary = {
        "overall_accuracy": round(accuracy_score(all_labels, all_preds) * 100, 2),
        "macro_f1": round(report["macro avg"]["f1-score"] * 100, 2),
        "weighted_f1": round(report["weighted avg"]["f1-score"] * 100, 2),
        "per_class": report,
        "evaluation_set": str(field_data_dir),
        "note": "Evaluated on held-out field images - model was NOT trained on these",
        "confusion_matrix_path": str(MODEL1_FIELD_CONFUSION_MATRIX_PATH),
    }
    MODEL1_FIELD_EVALUATION_PATH.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Evaluate the image disease classifier.")
    parser.add_argument("--manifest", default=str(PROCESSED_DATA_DIR / "manifest.csv"))
    parser.add_argument("--checkpoint", default=str(MODEL1_CHECKPOINT_PATH))
    parser.add_argument("--label-map", default=str(MODEL1_LABEL_MAP_PATH))
    parser.add_argument("--field-data-dir", default=None, help="Optional held-out field dataset laid out as ImageFolder.")
    parser.add_argument("--batch-size", type=int, default=16)
    return parser


def main() -> None:
    args = build_arg_parser().parse_args()
    results: dict[str, object] = {
        "validation": evaluate_model(Path(args.manifest), Path(args.checkpoint), args.batch_size)
    }
    if args.field_data_dir:
        results["field_evaluation"] = evaluate_on_field_data(
            field_data_dir=Path(args.field_data_dir),
            checkpoint_path=Path(args.checkpoint),
            label_map_path=Path(args.label_map),
            batch_size=args.batch_size,
        )
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
