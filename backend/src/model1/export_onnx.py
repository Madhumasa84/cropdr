from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import torch

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.config import MODEL1_CHECKPOINT_PATH, MODEL1_LABEL_MAP_PATH, MODEL1_ONNX_PATH
from src.model1.model import load_model_from_checkpoint


def export_to_onnx(checkpoint_path: Path = MODEL1_CHECKPOINT_PATH, output_path: Path = MODEL1_ONNX_PATH) -> dict[str, object]:
    model, checkpoint = load_model_from_checkpoint(checkpoint_path)
    model.eval()
    dummy_input = torch.randn(1, 3, 224, 224)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    torch.onnx.export(
        model,
        dummy_input,
        str(output_path),
        input_names=["input"],
        output_names=["logits"],
        dynamic_axes={"input": {0: "batch_size"}, "logits": {0: "batch_size"}},
        opset_version=13
    )

    if not MODEL1_LABEL_MAP_PATH.exists():
        label_map = {str(index): label for index, label in enumerate(checkpoint["class_names"])}
        MODEL1_LABEL_MAP_PATH.write_text(json.dumps(label_map, indent=2), encoding="utf-8")

    return {
        "onnx_path": str(output_path),
        "label_map_path": str(MODEL1_LABEL_MAP_PATH),
        "num_classes": checkpoint["num_classes"]
    }


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Export the image classifier to ONNX.")
    parser.add_argument("--checkpoint", default=str(MODEL1_CHECKPOINT_PATH))
    parser.add_argument("--output", default=str(MODEL1_ONNX_PATH))
    return parser


def main() -> None:
    args = build_arg_parser().parse_args()
    print(json.dumps(export_to_onnx(Path(args.checkpoint), Path(args.output)), indent=2))


if __name__ == "__main__":
    main()
