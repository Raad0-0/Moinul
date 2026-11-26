"""Group-based leakage-free validation split and competition metric evaluation."""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import brier_score_loss, f1_score
from sklearn.model_selection import GroupShuffleSplit

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

SEED = 42
TECHNIQUE_CODES = ("T1", "T2", "T3", "T4", "T5", "T6")
ALL_CLASSES = [0, 1, 2, 3, 4, 5]


def _resolve_path(path_str: str) -> Path:
    path = Path(path_str)
    return path if path.is_absolute() else _PROJECT_ROOT / path


def _encode_techniques(series: pd.Series) -> np.ndarray:
    """Convert pipe-delimited technique strings ('T1|T2' or 'NONE') to a (N, 6) binary matrix."""
    y = np.zeros((len(series), len(TECHNIQUE_CODES)), dtype=np.int32)
    code_to_idx = {code: idx for idx, code in enumerate(TECHNIQUE_CODES)}
    for i, val in enumerate(series.fillna("NONE")):
        text = str(val).strip()
        if not text or text == "NONE":
            continue
        for tok in text.split("|"):
            tok = tok.strip()
            if tok in code_to_idx:
                y[i, code_to_idx[tok]] = 1
    return y


def create_split(
    input_path: str = "data/augmented_train.csv",
    train_out: str = "data/train.csv",
    val_out: str = "data/val.csv",
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Split dataset by `group` using GroupShuffleSplit so no group leaks into validation."""
    df = pd.read_csv(_resolve_path(input_path))
    expected_classes = set(ALL_CLASSES)

    train_df: pd.DataFrame | None = None
    val_df: pd.DataFrame | None = None

    for offset in range(100):
        splitter = GroupShuffleSplit(n_splits=1, test_size=0.2, random_state=SEED + offset)
        train_idx, val_idx = next(splitter.split(df, df["label"], groups=df["group"]))
        cand_train = df.iloc[train_idx].reset_index(drop=True)
        cand_val = df.iloc[val_idx].reset_index(drop=True)

        if (
            set(cand_train["label"].unique()) >= expected_classes
            and set(cand_val["label"].unique()) >= expected_classes
        ):
            train_df, val_df = cand_train, cand_val
            if offset > 0:
                print(f"Adjusted GroupShuffleSplit seed to {SEED + offset} to cover all 6 classes.")
            break

    if train_df is None or val_df is None:
        raise RuntimeError("Could not find a group split with all 6 classes in both train and val.")

    train_path = _resolve_path(train_out)
    val_path = _resolve_path(val_out)
    train_df.to_csv(train_path, index=False)
    val_df.to_csv(val_path, index=False)

    print(f"Saved train ({len(train_df)} rows, {train_df['group'].nunique()} groups) -> {train_path}")
    print(f"Saved val   ({len(val_df)} rows, {val_df['group'].nunique()} groups) -> {val_path}")
    print("\nTrain class distribution:")
    print(train_df["label"].value_counts().sort_index())
    print("\nVal class distribution:")
    print(val_df["label"].value_counts().sort_index())

    return train_df, val_df


def evaluate_predictions(df_true: pd.DataFrame, df_pred: pd.DataFrame) -> dict[str, float]:
    """Compute Task A/B/C macro F1, Calibration (1 - Brier), and validation proxy score S."""
    y_true_label = df_true["label"].astype(int).to_numpy()
    y_pred_label = df_pred["label"].astype(int).to_numpy()

    f_a = float(
        f1_score(y_true_label, y_pred_label, labels=ALL_CLASSES, average="macro", zero_division=0)
    )

    y_true_tech = _encode_techniques(df_true["techniques"])
    y_pred_tech = _encode_techniques(df_pred["techniques"])
    f_b = float(f1_score(y_true_tech, y_pred_tech, average="macro", zero_division=0))

    y_true_action = df_true["action"].astype(int).to_numpy()
    y_pred_action = df_pred["action"].astype(int).to_numpy()
    f_c = float(
        f1_score(y_true_action, y_pred_action, labels=ALL_CLASSES, average="macro", zero_division=0)
    )

    correct = (y_pred_label == y_true_label).astype(np.float64)
    conf = np.clip(df_pred["confidence"].to_numpy(dtype=np.float64), 0.0, 1.0)
    brier = float(brier_score_loss(correct, conf))
    calibration = 1.0 - brier

    # Validation proxy allocating 30% hidden subset weight to F_A
    composite_s = 0.40 * f_a + 0.15 * f_b + 0.10 * f_c + 0.05 * calibration + 0.30 * f_a

    return {
        "F_A": f_a,
        "F_B": f_b,
        "F_C": f_c,
        "Brier": brier,
        "Calibration": calibration,
        "S": composite_s,
    }


if __name__ == "__main__":
    train_df, val_df = create_split()

    # Verify zero group leakage
    overlap = set(train_df["group"]).intersection(set(val_df["group"]))
    assert len(overlap) == 0, f"Group leakage detected: {overlap}"
    print(f"\nGroup leakage check passed: 0 overlapping groups.")

    # Dummy assertion tests on evaluate_predictions
    dummy_true = pd.DataFrame(
        {
            "label": [0, 1, 2, 3, 4, 5],
            "techniques": ["NONE", "T1|T2|T5", "T4|T3", "T6", "T1|T3", "NONE"],
            "action": [0, 1, 3, 4, 2, 5],
        }
    )
    dummy_perfect = dummy_true.copy()
    dummy_perfect["confidence"] = [1.0, 1.0, 1.0, 1.0, 1.0, 1.0]
    perfect_metrics = evaluate_predictions(dummy_true, dummy_perfect)
    assert np.isclose(perfect_metrics["S"], 1.0), f"Expected S=1.0, got {perfect_metrics}"

    dummy_imperfect = dummy_true.copy()
    dummy_imperfect.loc[0, "label"] = 1
    dummy_imperfect["confidence"] = [0.8, 0.9, 0.9, 0.9, 0.9, 0.9]
    imperfect_metrics = evaluate_predictions(dummy_true, dummy_imperfect)
    assert 0.0 <= imperfect_metrics["S"] < 1.0, f"Expected S < 1.0, got {imperfect_metrics}"

    print("Evaluation unit tests passed:", perfect_metrics)
