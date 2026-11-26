"""Confidence calibration via Temperature Scaling on validation logits."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import torch
import torch.nn as nn
import torch.optim as optim
from sklearn.metrics import brier_score_loss

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from src.normalize import is_noise_only  # noqa: E402

SEED = 42
np.random.seed(SEED)
torch.manual_seed(SEED)

CLIP_MIN = 0.08
CLIP_MAX = 0.92
NOISE_CONFIDENCE = 0.85


class ModelWithTemperature(nn.Module):
    """Single-parameter temperature scaling wrapper for classification logits."""

    def __init__(self, init_temp: float = 1.0) -> None:
        super().__init__()
        self.temperature = nn.Parameter(torch.ones(1) * init_temp)

    def forward(self, logits: torch.Tensor) -> torch.Tensor:
        temp = torch.clamp(self.temperature, min=1e-3)
        return logits / temp


def _softmax(logits: np.ndarray) -> np.ndarray:
    shifted = logits - np.max(logits, axis=-1, keepdims=True)
    exp_x = np.exp(shifted)
    return exp_x / np.sum(exp_x, axis=-1, keepdims=True)


def fit_temperature(val_logits: np.ndarray, val_labels: np.ndarray) -> float:
    """Fit positive scalar temperature T minimizing NLL on validation logits."""
    logits_t = torch.tensor(val_logits, dtype=torch.float32)
    labels_t = torch.tensor(val_labels, dtype=torch.long)

    model = ModelWithTemperature(init_temp=1.0)
    criterion = nn.CrossEntropyLoss()
    optimizer = optim.LBFGS([model.temperature], lr=0.05, max_iter=50)

    def _closure() -> torch.Tensor:
        optimizer.zero_grad()
        loss = criterion(model(logits_t), labels_t)
        loss.backward()
        return loss

    optimizer.step(_closure)
    with torch.no_grad():
        model.temperature.clamp_(min=0.05, max=10.0)

    return float(model.temperature.item())


def calibrate_confidence(
    logits: np.ndarray,
    temperature: float,
    is_noise_mask: np.ndarray | None = None,
) -> np.ndarray:
    """Scale logits by T, apply softmax, clip to [0.08, 0.92], and set noise rows to 0.85."""
    scaled_logits = logits / max(float(temperature), 1e-3)
    probs = _softmax(scaled_logits)
    confidences = np.max(probs, axis=-1)
    confidences = np.clip(confidences, CLIP_MIN, CLIP_MAX)

    if is_noise_mask is not None:
        mask = np.asarray(is_noise_mask, dtype=bool)
        confidences = np.where(mask, NOISE_CONFIDENCE, confidences)

    return confidences.astype(np.float64)


def evaluate_calibration(
    true_labels: np.ndarray,
    pred_labels: np.ndarray,
    confidences: np.ndarray,
) -> dict[str, float]:
    """Compute Brier score and calibration score (1 - Brier)."""
    correct = (np.asarray(true_labels) == np.asarray(pred_labels)).astype(int)
    brier = float(brier_score_loss(correct, np.clip(confidences, 0.0, 1.0)))
    return {
        "brier": brier,
        "calibration_score": 1.0 - brier,
    }


if __name__ == "__main__":
    val_df = pd.read_csv(_PROJECT_ROOT / "data" / "val.csv")
    logits_data = np.load(_PROJECT_ROOT / "outputs" / "val_logits.npz")
    val_logits = logits_data["logits_label"]

    true_labels = val_df["label"].astype(int).to_numpy()
    pred_labels = np.argmax(val_logits, axis=-1)
    noise_mask = np.array([is_noise_only(t) for t in val_df["text"].fillna("")], dtype=bool)

    # Before scaling (T = 1.0, raw max softmax probability)
    raw_conf = np.max(_softmax(val_logits), axis=-1)
    before_metrics = evaluate_calibration(true_labels, pred_labels, raw_conf)

    # Fit optimal temperature
    fitted_temp = fit_temperature(val_logits, true_labels)
    cal_conf = calibrate_confidence(val_logits, fitted_temp, is_noise_mask=noise_mask)
    after_metrics = evaluate_calibration(true_labels, pred_labels, cal_conf)

    params_path = _PROJECT_ROOT / "models" / "calibration_params.json"
    os.makedirs(params_path.parent, exist_ok=True)
    with open(params_path, "w", encoding="utf-8") as f:
        json.dump(
            {
                "temperature": round(fitted_temp, 6),
                "clip_min": CLIP_MIN,
                "clip_max": CLIP_MAX,
                "noise_confidence": NOISE_CONFIDENCE,
            },
            f,
            indent=2,
        )

    print(f"Fitted temperature: {fitted_temp:.4f}")
    print(f"Before scaling (T=1.0): brier={before_metrics['brier']:.4f}, calibration={before_metrics['calibration_score']:.4f}")
    print(f"After  scaling (T={fitted_temp:.4f}): brier={after_metrics['brier']:.4f}, calibration={after_metrics['calibration_score']:.4f}")
    print(f"Saved calibration parameters to {params_path}")
