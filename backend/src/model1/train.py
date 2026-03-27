from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import torch
from sklearn.metrics import accuracy_score, f1_score
from torch import nn
from torch.optim import AdamW
from torch.utils.data import DataLoader

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.config import MODEL1_CHECKPOINT_PATH, MODEL1_LABEL_MAP_PATH, MODEL1_TRAINING_HISTORY_PATH, PROCESSED_DATA_DIR, ensure_runtime_directories
from src.model1.model import ManifestImageDataset, build_classifier, save_checkpoint
from src.preprocessing.augment import build_eval_transforms, build_train_transforms


def mixup_data(images: torch.Tensor, labels: torch.Tensor, device: torch.device, alpha: float = 0.4) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor, float]:
    if alpha <= 0:
        return images, labels, labels, 1.0

    lam = float(np.random.beta(alpha, alpha))
    index = torch.randperm(images.size(0), device=device)
    mixed_images = (lam * images) + ((1.0 - lam) * images[index])
    return mixed_images, labels, labels[index], lam


def mixup_criterion(
    criterion: nn.Module,
    predictions: torch.Tensor,
    labels_a: torch.Tensor,
    labels_b: torch.Tensor,
    lam: float,
) -> torch.Tensor:
    return (lam * criterion(predictions, labels_a)) + ((1.0 - lam) * criterion(predictions, labels_b))


def evaluate_epoch(model: nn.Module, loader: DataLoader, criterion: nn.Module, device: torch.device) -> dict[str, float]:
    model.eval()
    losses: list[float] = []
    predictions: list[int] = []
    targets: list[int] = []

    with torch.no_grad():
        for images, labels in loader:
            images = images.to(device)
            labels = labels.to(device)
            logits = model(images)
            loss = criterion(logits, labels)
            losses.append(loss.item())
            predictions.extend(torch.argmax(logits, dim=1).cpu().tolist())
            targets.extend(labels.cpu().tolist())

    return {
        "loss": float(np.mean(losses)) if losses else 0.0,
        "accuracy": accuracy_score(targets, predictions),
        "f1_macro": f1_score(targets, predictions, average="macro")
    }


def train_model(
    manifest_path: Path,
    backbone: str = "efficientnet_b3",
    epochs: int = 10,
    batch_size: int = 16,
    learning_rate: float = 1e-4,
    num_workers: int = 0,
    pretrained: bool = True,
    mixup_alpha: float = 0.4,
) -> dict[str, object]:
    ensure_runtime_directories()
    dataframe = pd.read_csv(manifest_path)
    class_names = sorted(dataframe["label"].unique())
    label_map = {str(index): label for index, label in enumerate(class_names)}
    MODEL1_LABEL_MAP_PATH.write_text(json.dumps(label_map, indent=2), encoding="utf-8")

    train_dataset = ManifestImageDataset(manifest_path, "train", build_train_transforms())
    val_dataset = ManifestImageDataset(manifest_path, "val", build_eval_transforms())
    train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True, num_workers=num_workers)
    val_loader = DataLoader(val_dataset, batch_size=batch_size, shuffle=False, num_workers=num_workers)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = build_classifier(backbone=backbone, num_classes=len(class_names), pretrained=pretrained).to(device)

    train_frame = dataframe[dataframe["split"] == "train"]
    class_counts = (
        train_frame["label_index"]
        .value_counts()
        .sort_index()
        .reindex(range(len(class_names)), fill_value=0)
    )
    class_weights = len(train_frame) / np.maximum(class_counts.values.astype(np.float32), 1.0)
    criterion = nn.CrossEntropyLoss(weight=torch.tensor(class_weights, dtype=torch.float32, device=device))
    optimizer = AdamW(model.parameters(), lr=learning_rate, weight_decay=1e-4)

    best_val_f1 = -1.0
    history: list[dict[str, float]] = []
    for epoch in range(1, epochs + 1):
        model.train()
        running_losses: list[float] = []
        train_predictions: list[int] = []
        train_targets: list[int] = []
        weighted_correct = 0.0
        sample_count = 0

        for images, labels in train_loader:
            images = images.to(device)
            labels = labels.to(device)
            mixed_images, labels_a, labels_b, lam = mixup_data(images, labels, device, mixup_alpha)

            optimizer.zero_grad()
            logits = model(mixed_images)
            loss = mixup_criterion(criterion, logits, labels_a, labels_b, lam)
            loss.backward()
            optimizer.step()

            running_losses.append(loss.item())
            predicted_indices = torch.argmax(logits, dim=1)
            weighted_correct += float(
                (lam * (predicted_indices == labels_a).sum().item()) +
                ((1.0 - lam) * (predicted_indices == labels_b).sum().item())
            )
            sample_count += int(labels.size(0))
            train_predictions.extend(predicted_indices.detach().cpu().tolist())
            train_targets.extend(labels.detach().cpu().tolist())

        train_metrics = {
            "loss": float(np.mean(running_losses)) if running_losses else 0.0,
            "accuracy": (weighted_correct / sample_count) if sample_count else 0.0,
            "f1_macro": f1_score(train_targets, train_predictions, average="macro")
        }
        val_metrics = evaluate_epoch(model, val_loader, criterion, device)

        epoch_metrics = {
            "epoch": epoch,
            "train_loss": round(train_metrics["loss"], 4),
            "train_accuracy": round(train_metrics["accuracy"], 4),
            "train_f1_macro": round(train_metrics["f1_macro"], 4),
            "val_loss": round(val_metrics["loss"], 4),
            "val_accuracy": round(val_metrics["accuracy"], 4),
            "val_f1_macro": round(val_metrics["f1_macro"], 4)
        }
        history.append(epoch_metrics)
        print(json.dumps(epoch_metrics))

        if val_metrics["f1_macro"] > best_val_f1:
            best_val_f1 = float(val_metrics["f1_macro"])
            save_checkpoint(
                checkpoint_path=MODEL1_CHECKPOINT_PATH,
                model=model,
                backbone=backbone,
                class_names=class_names,
                epoch=epoch,
                best_val_f1=best_val_f1,
                history=history
            )

    MODEL1_TRAINING_HISTORY_PATH.write_text(json.dumps(history, indent=2), encoding="utf-8")
    return {
        "checkpoint_path": str(MODEL1_CHECKPOINT_PATH),
        "label_map_path": str(MODEL1_LABEL_MAP_PATH),
        "history_path": str(MODEL1_TRAINING_HISTORY_PATH),
        "best_val_f1": round(best_val_f1, 4),
        "backbone": backbone,
        "mixup_alpha": mixup_alpha,
    }


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Train the image-based disease classifier.")
    parser.add_argument("--manifest", default=str(PROCESSED_DATA_DIR / "manifest.csv"))
    parser.add_argument("--backbone", default="efficientnet_b3", choices=["efficientnet_b3", "mobilenet_v3", "resnet50"])
    parser.add_argument("--epochs", type=int, default=10)
    parser.add_argument("--batch-size", type=int, default=16)
    parser.add_argument("--lr", type=float, default=1e-4)
    parser.add_argument("--num-workers", type=int, default=0)
    parser.add_argument("--mixup-alpha", type=float, default=0.4)
    parser.add_argument("--no-pretrained", action="store_true")
    return parser


def main() -> None:
    args = build_arg_parser().parse_args()
    results = train_model(
        manifest_path=Path(args.manifest),
        backbone=args.backbone,
        epochs=args.epochs,
        batch_size=args.batch_size,
        learning_rate=args.lr,
        num_workers=args.num_workers,
        pretrained=not args.no_pretrained,
        mixup_alpha=args.mixup_alpha,
    )
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
