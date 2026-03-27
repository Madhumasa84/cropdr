from __future__ import annotations

import argparse
from pathlib import Path

import cv2
import numpy as np
import pandas as pd
from PIL import Image
from torchvision import transforms

IMAGENET_MEAN = (0.485, 0.456, 0.406)
IMAGENET_STD = (0.229, 0.224, 0.225)
IMAGE_SIZE = (224, 224)


def enhance_image(image: Image.Image) -> Image.Image:
    """Apply light denoising and contrast improvement for field images."""
    rgb_array = np.array(image.convert("RGB"))
    bgr_array = cv2.cvtColor(rgb_array, cv2.COLOR_RGB2BGR)
    denoised = cv2.fastNlMeansDenoisingColored(bgr_array, None, 4, 4, 7, 21)

    lab = cv2.cvtColor(denoised, cv2.COLOR_BGR2LAB)
    l_channel, a_channel, b_channel = cv2.split(lab)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    enhanced_l = clahe.apply(l_channel)
    enhanced_lab = cv2.merge((enhanced_l, a_channel, b_channel))
    enhanced_bgr = cv2.cvtColor(enhanced_lab, cv2.COLOR_LAB2BGR)
    enhanced_rgb = cv2.cvtColor(enhanced_bgr, cv2.COLOR_BGR2RGB)
    return Image.fromarray(enhanced_rgb)


def build_train_transforms(image_size: tuple[int, int] = IMAGE_SIZE) -> transforms.Compose:
    return transforms.Compose(
        [
            transforms.RandomResizedCrop(image_size[0], scale=(0.85, 1.0)),
            transforms.RandomHorizontalFlip(),
            transforms.RandomVerticalFlip(p=0.1),
            transforms.RandomRotation(20),
            transforms.ColorJitter(brightness=0.15, contrast=0.15, saturation=0.15, hue=0.03),
            transforms.ToTensor(),
            transforms.Normalize(mean=IMAGENET_MEAN, std=IMAGENET_STD)
        ]
    )


def build_eval_transforms(image_size: tuple[int, int] = IMAGE_SIZE) -> transforms.Compose:
    return transforms.Compose(
        [
            transforms.Resize(image_size),
            transforms.ToTensor(),
            transforms.Normalize(mean=IMAGENET_MEAN, std=IMAGENET_STD)
        ]
    )


def save_augmented_dataset(
    manifest_path: Path,
    output_dir: Path,
    copies_per_image: int = 1,
    image_size: tuple[int, int] = IMAGE_SIZE
) -> pd.DataFrame:
    manifest = pd.read_csv(manifest_path)
    output_dir.mkdir(parents=True, exist_ok=True)
    augmentation = transforms.Compose(
        [
            transforms.Resize(image_size),
            transforms.RandomHorizontalFlip(),
            transforms.RandomRotation(15),
            transforms.ColorJitter(brightness=0.12, contrast=0.12, saturation=0.12)
        ]
    )

    rows: list[dict[str, object]] = []
    for row in manifest.itertuples(index=False):
        image = Image.open(row.image_path).convert("RGB")
        for copy_index in range(copies_per_image):
            augmented = augmentation(image)
            if isinstance(augmented, Image.Image):
                augmented_image = augmented
            else:
                augmented_image = transforms.ToPILImage()(augmented)

            split_dir = output_dir / str(row.split) / str(row.label)
            split_dir.mkdir(parents=True, exist_ok=True)
            output_path = split_dir / f"{Path(str(row.image_path)).stem}_aug_{copy_index}.jpg"
            augmented_image.save(output_path, quality=95)
            rows.append(
                {
                    "image_path": str(output_path),
                    "label": row.label,
                    "label_index": int(row.label_index),
                    "crop": row.crop,
                    "disease": row.disease,
                    "dataset": f"{row.dataset}_augmented",
                    "split": row.split
                }
            )

    augmented_manifest = pd.DataFrame(rows)
    augmented_manifest_path = output_dir / "augmented_manifest.csv"
    augmented_manifest.to_csv(augmented_manifest_path, index=False)
    return augmented_manifest


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Create offline augmented copies from a unified manifest.")
    parser.add_argument("--manifest", required=True, help="Path to manifest.csv from label_unifier.py")
    parser.add_argument("--output-dir", required=True, help="Directory to store augmented images")
    parser.add_argument("--copies-per-image", type=int, default=1)
    return parser


def main() -> None:
    args = build_arg_parser().parse_args()
    augmented = save_augmented_dataset(
        manifest_path=Path(args.manifest),
        output_dir=Path(args.output_dir),
        copies_per_image=args.copies_per_image
    )
    print(f"Saved {len(augmented)} augmented rows to {Path(args.output_dir) / 'augmented_manifest.csv'}")


if __name__ == "__main__":
    main()
