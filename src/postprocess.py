"""Post-processing, consistency rules, priority overrides, and threshold tuning for ScamShield BD."""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import f1_score

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from src.normalize import is_noise_only, normalize  # noqa: E402
from src.split import _encode_techniques, evaluate_predictions  # noqa: E402

TECHNIQUE_CODES = ["T1", "T2", "T3", "T4", "T5", "T6"]
PRIORITY_ORDER = [1, 2, 4, 3, 5, 0]

_CREDENTIAL_RE = re.compile(
    r"(?:\b(?:otp|pin|cvv|password|nid|passcode|card\s*number|expiry)\b|ওটিপি|পিন|পাসওয়ার্ড|এনআইডি|কার্ড)",
    re.IGNORECASE,
)
_DO_NOT_SHARE_RE = re.compile(
    r"(?:do\s*not\s*share|never\s*share|don['’]?t\s*share|kauke\s*bolben\s*na|kauke\s*diben\s*na|"
    r"কারো\s*সাথে\s*শেয়ার\s*করবেন\s*না|শেয়ার\s*করবেন\s*না|কখনোই\s*ওটিপি\s*চায়\s*না)",
    re.IGNORECASE,
)
_ORG_ROLE_RE = re.compile(
    r"(?:\b(?:bkash|nagad|rocket|upay|gp|grameenphone|robi|banglalink|daraz|pathao|"
    r"steadfast|sa\s*paribahan|bdjobs|dbbl|city\s*bank|bank|helpline|support|"
    r"customer\s*care|agent|officer|head\s*office|customs|cargo|govt|government|"
    r"ministry|police|telecom|merchant|freelancer\s*portal|hr|company)\b|"
    r"বিকাশ|নগদ|রকেট|উপায়|গ্রামীণফোন|রবি|দারাজ|পাঠাও|কাস্টমস|হেল্পলাইন|অফিস|ব্যাংক|এজেন্ট|কর্তৃপক্ষ)",
    re.IGNORECASE,
)


def _softmax(logits: np.ndarray) -> np.ndarray:
    shifted = logits - np.max(logits, axis=1, keepdims=True)
    exp_x = np.exp(shifted)
    return exp_x / np.sum(exp_x, axis=1, keepdims=True)


def _sigmoid(logits: np.ndarray) -> np.ndarray:
    return 1.0 / (1.0 + np.exp(-np.clip(logits, -30.0, 30.0)))


def tune_technique_thresholds(
    probs_B: np.ndarray,
    y_true_B: np.ndarray,
    save_path: str | Path = "models/technique_thresholds.json",
) -> dict[str, float]:
    """Grid-search per-technique thresholds (0.20..0.70, step 0.05) to maximize F1."""
    grid = [round(float(t), 2) for t in np.arange(0.20, 0.701, 0.05)]
    best_thresholds: dict[str, float] = {}

    for j, code in enumerate(TECHNIQUE_CODES):
        best_t = 0.50
        best_f1 = -1.0
        y_col = y_true_B[:, j]
        p_col = probs_B[:, j]

        for t in grid:
            preds = (p_col >= t).astype(np.int32)
            score = float(f1_score(y_col, preds, zero_division=0))
            if score > best_f1:
                best_f1 = score
                best_t = t
        best_thresholds[code] = best_t

    out_path = Path(save_path)
    if not out_path.is_absolute():
        out_path = _PROJECT_ROOT / out_path
    os.makedirs(out_path.parent, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(best_thresholds, f, indent=2)

    return best_thresholds


def apply_postprocessing(
    df: pd.DataFrame,
    probs_A: np.ndarray,
    probs_B: np.ndarray,
    probs_C: np.ndarray,
    thresholds: dict[str, float] | None = None,
) -> pd.DataFrame:
    """Enforce ScamShield BD rules, priority overrides, and label-technique-action consistency."""
    if thresholds is None:
        thresholds = {code: 0.50 for code in TECHNIQUE_CODES}

    ids = df["id"].to_numpy() if "id" in df.columns else np.arange(len(df))
    texts = df["text"].fillna("").astype(str).tolist()

    out_labels: list[int] = []
    out_techs: list[str] = []
    out_actions: list[int] = []
    out_confs: list[float] = []

    for i, raw_text in enumerate(texts):
        # a. Noise-only check
        if is_noise_only(raw_text):
            out_labels.append(0)
            out_techs.append("NONE")
            out_actions.append(0)
            out_confs.append(0.85)
            continue

        pred_label = int(np.argmax(probs_A[i]))
        conf = float(np.clip(np.max(probs_A[i]), 0.0, 1.0))

        # b. Priority Override (OTP / Credential rule -> Class 1)
        has_cred = bool(_CREDENTIAL_RE.search(raw_text))
        is_warning = bool(_DO_NOT_SHARE_RE.search(raw_text))
        scam_mass = float(np.sum(probs_A[i, 1:5]))
        if has_cred and not is_warning:
            if pred_label in (1, 2, 3, 4) or probs_B[i, 1] >= 0.40 or scam_mass >= 0.45:
                pred_label = 1
                conf = float(np.clip(max(conf, probs_A[i, 1]), 0.0, 1.0))

        # c. Hard consistency constraints
        if pred_label in (0, 5):
            out_labels.append(pred_label)
            out_techs.append("NONE")
            out_actions.append(0)
            out_confs.append(round(conf, 4))
            continue

        # Class 1..4: Technique thresholding + T1 sanity check
        active = [
            code
            for j, code in enumerate(TECHNIQUE_CODES)
            if probs_B[i, j] >= thresholds.get(code, 0.50)
        ]

        # e. T1 sanity check: keep T1 only if an organization/brand/role is claimed
        if "T1" in active and not _ORG_ROLE_RE.search(raw_text):
            active = [c for c in active if c != "T1"]

        # d. Class 1..4 cannot have NONE
        if not active:
            if _ORG_ROLE_RE.search(raw_text):
                best_j = int(np.argmax(probs_B[i]))
            else:
                best_j = int(1 + np.argmax(probs_B[i, 1:]))
            active = [TECHNIQUE_CODES[best_j]]

        # d. Class 1..4 action cannot be 0
        pred_action = int(np.argmax(probs_C[i]))
        if pred_action == 0:
            pred_action = int(1 + np.argmax(probs_C[i, 1:]))

        out_labels.append(pred_label)
        out_techs.append("|".join(active))
        out_actions.append(pred_action)
        out_confs.append(round(conf, 4))

    return pd.DataFrame(
        {
            "id": ids,
            "label": out_labels,
            "techniques": out_techs,
            "action": out_actions,
            "confidence": out_confs,
        }
    )


def _raw_preds_df(probs_A: np.ndarray, probs_B: np.ndarray, probs_C: np.ndarray) -> pd.DataFrame:
    """Build un-postprocessed predictions for before/after comparison."""
    labels = np.argmax(probs_A, axis=1).astype(int)
    actions = np.argmax(probs_C, axis=1).astype(int)
    confs = np.round(np.clip(np.max(probs_A, axis=1), 0.0, 1.0), 4)
    techs: list[str] = []
    for i in range(len(labels)):
        active = [TECHNIQUE_CODES[j] for j in range(6) if probs_B[i, j] >= 0.50]
        techs.append("|".join(active) if active else "NONE")
    return pd.DataFrame(
        {"label": labels, "techniques": techs, "action": actions, "confidence": confs}
    )


if __name__ == "__main__":
    val_df = pd.read_csv(_PROJECT_ROOT / "data" / "val.csv")
    logits_path = _PROJECT_ROOT / "outputs" / "val_logits.npz"

    if logits_path.exists():
        print(f"Loading validation logits from {logits_path}...")
        data = np.load(logits_path)
        probs_A = _softmax(data["logits_label"])
        probs_B = _sigmoid(data["logits_tech"])
        probs_C = _softmax(data["logits_action"])
    else:
        print("outputs/val_logits.npz not found; using TF-IDF baseline on data/train.csv for validation check...")
        from src.train_baseline import align_proba, train_models

        train_df = pd.read_csv(_PROJECT_ROOT / "data" / "train.csv")
        vec, l_clf, a_clf, t_clf = train_models(train_df)
        X_val = vec.transform([normalize(t) for t in val_df["text"].fillna("")])
        probs_A = align_proba(l_clf.predict_proba(X_val), l_clf.classes_)
        probs_B = t_clf.predict_proba(X_val)
        probs_C = align_proba(a_clf.predict_proba(X_val), a_clf.classes_)

    y_true_B = _encode_techniques(val_df["techniques"])
    thresholds = tune_technique_thresholds(probs_B, y_true_B)
    print("Tuned technique thresholds:", thresholds)

    raw_df = _raw_preds_df(probs_A, probs_B, probs_C)
    post_df = apply_postprocessing(val_df, probs_A, probs_B, probs_C, thresholds=thresholds)

    before = evaluate_predictions(val_df, raw_df)
    after = evaluate_predictions(val_df, post_df)

    print("\nValidation Metrics BEFORE post-processing:", {k: round(v, 4) for k, v in before.items()})
    print("Validation Metrics AFTER  post-processing:", {k: round(v, 4) for k, v in after.items()})
    print(f"Composite Score Delta (S): {after['S'] - before['S']:+.4f}")
