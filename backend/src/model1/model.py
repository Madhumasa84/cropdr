from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd
import torch
from PIL import Image
from torch import nn
from torch.utils.data import Dataset
from torchvision import models


class ManifestImageDataset(Dataset):
    def __init__(self, manifest_path: Path, split: str, transform: Any) -> None:
        dataframe = pd.read_csv(manifest_path)
        filtered = dataframe[dataframe["split"] == split].reset_index(drop=True)
        if filtered.empty:
            raise ValueError(f"No rows found for split '{split}' in {manifest_path}.")
        self.dataframe = filtered
        self.transform = transform

    def __len__(self) -> int:
        return len(self.dataframe)

    def __getitem__(self, index: int) -> tuple[torch.Tensor, int]:
        row = self.dataframe.iloc[index]
        image = Image.open(row["image_path"]).convert("RGB")
        tensor = self.transform(image)
        return tensor, int(row["label_index"])


def load_label_map(label_map_path: Path) -> dict[int, str]:
    with label_map_path.open("r", encoding="utf-8") as file:
        payload = json.load(file)
    return {int(key): value for key, value in payload.items()}


def build_classifier(backbone: str, num_classes: int, pretrained: bool = True) -> nn.Module:
    backbone = backbone.lower()
    if backbone == "efficientnet_b3":
        weights = models.EfficientNet_B3_Weights.IMAGENET1K_V1 if pretrained else None
        model = models.efficientnet_b3(weights=weights)
        in_features = model.classifier[-1].in_features
        model.classifier[-1] = nn.Linear(in_features, num_classes)
        return model

    if backbone == "mobilenet_v3":
        weights = models.MobileNet_V3_Large_Weights.IMAGENET1K_V2 if pretrained else None
        model = models.mobilenet_v3_large(weights=weights)
        in_features = model.classifier[-1].in_features
        model.classifier[-1] = nn.Linear(in_features, num_classes)
        return model

    if backbone == "resnet50":
        weights = models.ResNet50_Weights.IMAGENET1K_V2 if pretrained else None
        model = models.resnet50(weights=weights)
        in_features = model.fc.in_features
        model.fc = nn.Linear(in_features, num_classes)
        return model

    raise ValueError("Unsupported backbone. Choose 'efficientnet_b3', 'mobilenet_v3', or 'resnet50'.")


def save_checkpoint(
    checkpoint_path: Path,
    model: nn.Module,
    backbone: str,
    class_names: list[str],
    epoch: int,
    best_val_f1: float,
    history: list[dict[str, float]]
) -> None:
    checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
    torch.save(
        {
            "model_state_dict": model.state_dict(),
            "backbone": backbone,
            "num_classes": len(class_names),
            "class_names": class_names,
            "epoch": epoch,
            "best_val_f1": best_val_f1,
            "history": history
        },
        checkpoint_path
    )


def load_model_from_checkpoint(checkpoint_path: Path, map_location: str | torch.device = "cpu") -> tuple[nn.Module, dict[str, Any]]:
    checkpoint = torch.load(checkpoint_path, map_location=map_location)
    model = build_classifier(
        backbone=checkpoint["backbone"],
        num_classes=int(checkpoint["num_classes"]),
        pretrained=False
    )
    model.load_state_dict(checkpoint["model_state_dict"])
    return model, checkpoint
