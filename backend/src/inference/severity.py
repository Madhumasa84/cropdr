from __future__ import annotations

import cv2
import numpy as np
from PIL import Image


def estimate_lesion_ratio(image: Image.Image) -> float:
    rgb = np.array(image.convert("RGB"))
    hsv = cv2.cvtColor(rgb, cv2.COLOR_RGB2HSV)

    healthy_mask = cv2.inRange(hsv, (30, 30, 30), (90, 255, 255))
    non_background_mask = cv2.inRange(hsv, (10, 10, 10), (170, 255, 255))

    healthy_pixels = float(np.count_nonzero(healthy_mask))
    observed_pixels = float(max(np.count_nonzero(non_background_mask), 1))
    lesion_ratio = max(0.0, min(1.0, 1.0 - (healthy_pixels / observed_pixels)))
    return round(lesion_ratio, 4)


def estimate_severity(image: Image.Image, disease_name: str, confidence: float) -> dict[str, float | str]:
    lesion_ratio = estimate_lesion_ratio(image)
    disease_key = disease_name.lower().replace(" ", "_")

    if "healthy" in disease_key:
        severity = "LOW"
    elif lesion_ratio >= 0.45 or confidence >= 0.92:
        severity = "HIGH"
    elif lesion_ratio >= 0.20 or confidence >= 0.70:
        severity = "MEDIUM"
    else:
        severity = "LOW"

    return {
        "severity": severity,
        "lesion_ratio": lesion_ratio
    }
