"""Baseline TF-IDF + Logistic Regression pipeline for ScamShield BD."""

from __future__ import annotations

import random
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.multiclass import OneVsRestClassifier

# Ensure project root is on sys.path when run as `python src/train_baseline.py`
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from src.normalize import is_noise_only, normalize  # noqa: E402

SEED = 42
TECHNIQUE_CODES = ("T1", "T2", "T3", "T4", "T5", "T6")
NUM_CLASSES = 6
CHUNK_SIZE = 50_000


def set_seed(seed: int = SEED) -> None:
    """Fix random seeds for reproducibility."""
    random.seed(seed)
    np.random.seed(seed)


def encode_techniques(series: pd.Series) -> np.ndarray:
    """Convert pipe-delimited technique strings into a (N, 6) binary matrix."""
    y = np.zeros((len(series), len(TECHNIQUE_CODES)), dtype=np.int32)
    code_to_idx = {code: idx for idx, code in enumerate(TECHNIQUE_CODES)}
    for row_idx, val in enumerate(series.fillna("NONE")):
        text = str(val).strip()
        if text == "NONE" or not text:
            continue
        for token in text.split("|"):
            token = token.strip()
            if token in code_to_idx:
                y[row_idx, code_to_idx[token]] = 1
    return y


def align_proba(probs: np.ndarray, classes: np.ndarray, num_classes: int = NUM_CLASSES) -> np.ndarray:
    """Align predict_proba output to a fixed (N, num_classes) array."""
    aligned = np.zeros((probs.shape[0], num_classes), dtype=np.float64)
    for col_idx, cls in enumerate(classes):
        cls_int = int(cls)
        if 0 <= cls_int < num_classes:
            aligned[:, cls_int] = probs[:, col_idx]
    return aligned


def train_models(
    train_df: pd.DataFrame,
) -> tuple[TfidfVectorizer, LogisticRegression, LogisticRegression, OneVsRestClassifier]:
    """Fit char n-gram TF-IDF and linear models strictly on training data."""
    train_texts = [normalize(t) for t in train_df["text"].fillna("")]

    vectorizer = TfidfVectorizer(
        analyzer="char_wb",
        ngram_range=(2, 5),
        sublinear_tf=True,
        min_df=2,
    )
    X_train = vectorizer.fit_transform(train_texts)

    y_label = train_df["label"].astype(int).to_numpy()
    y_action = train_df["action"].astype(int).to_numpy()
    y_tech = encode_techniques(train_df["techniques"])

    label_clf = LogisticRegression(
        max_iter=1000,
        class_weight="balanced",
        random_state=SEED,
    )
    label_clf.fit(X_train, y_label)

    action_clf = LogisticRegression(
        max_iter=1000,
        class_weight="balanced",
        random_state=SEED,
    )
    action_clf.fit(X_train, y_action)

    tech_clf = OneVsRestClassifier(
        LogisticRegression(
            max_iter=1000,
            class_weight="balanced",
            random_state=SEED,
        )
    )
    tech_clf.fit(X_train, y_tech)

    return vectorizer, label_clf, action_clf, tech_clf


def postprocess_chunk(
    raw_texts: list[str],
    label_probs: np.ndarray,
    action_probs: np.ndarray,
    tech_probs: np.ndarray,
    tech_threshold: float = 0.5,
) -> tuple[list[int], list[str], list[int], list[float]]:
    """Apply ScamShield BD consistency rules and extract confidence."""
    labels: list[int] = []
    techniques: list[str] = []
    actions: list[int] = []
    confidences: list[float] = []

    for i, raw_text in enumerate(raw_texts):
        max_prob = float(np.clip(np.max(label_probs[i]), 0.0, 1.0))

        if is_noise_only(raw_text):
            labels.append(0)
            techniques.append("NONE")
            actions.append(0)
            confidences.append(round(max_prob, 4))
            continue

        pred_label = int(np.argmax(label_probs[i]))
        labels.append(pred_label)
        confidences.append(round(max_prob, 4))

        if pred_label in (0, 5):
            techniques.append("NONE")
            actions.append(0)
        else:
            pred_action = int(np.argmax(action_probs[i]))
            if pred_action == 0:
                pred_action = int(1 + np.argmax(action_probs[i, 1:]))
            actions.append(pred_action)

            active = [
                TECHNIQUE_CODES[j]
                for j in range(len(TECHNIQUE_CODES))
                if tech_probs[i, j] >= tech_threshold
            ]
            if not active:
                best_idx = int(np.argmax(tech_probs[i]))
                active = [TECHNIQUE_CODES[best_idx]]
            techniques.append("|".join(active))

    return labels, techniques, actions, confidences


def validate_submission(sub_path: Path, expected_rows: int) -> None:
    """Verify submission.csv adheres to all format and consistency rules."""
    df = pd.read_csv(sub_path)
    expected_cols = ["id", "label", "techniques", "action", "confidence"]
    assert list(df.columns) == expected_cols, f"Bad columns: {list(df.columns)}"
    assert len(df) == expected_rows, f"Expected {expected_rows} rows, got {len(df)}"
    assert not df.isna().any().any(), "Submission contains NaN values"
    assert df["id"].is_unique, "Duplicate IDs found"
    assert df["label"].between(0, 5).all(), "Invalid label values"
    assert df["action"].between(0, 5).all(), "Invalid action values"
    assert df["confidence"].between(0.0, 1.0).all(), "Confidence out of [0, 1]"
    assert (df["techniques"].astype(str).str.len() > 0).all(), "Empty techniques found"

    benign_mask = df["label"].isin([0, 5])
    assert (df.loc[benign_mask, "techniques"] == "NONE").all(), "Class 0/5 must have NONE"
    assert (df.loc[benign_mask, "action"] == 0).all(), "Class 0/5 must have action 0"

    scam_mask = df["label"].isin([1, 2, 3, 4])
    assert (df.loc[scam_mask, "techniques"] != "NONE").all(), "Class 1-4 cannot have NONE"
    assert (df.loc[scam_mask, "action"] != 0).all(), "Class 1-4 cannot have action 0"


def main() -> None:
    set_seed(SEED)
    t0 = time.perf_counter()

    sample_path = _PROJECT_ROOT / "data" / "sample.csv"
    test_path = _PROJECT_ROOT / "data" / "test.csv"
    sub_path = _PROJECT_ROOT / "submission.csv"

    print(f"Loading training data from {sample_path}...")
    train_df = pd.read_csv(sample_path)
    vectorizer, label_clf, action_clf, tech_clf = train_models(train_df)
    print(f"Trained baseline models on {len(train_df)} rows in {time.perf_counter() - t0:.2f}s.")

    # TEST DATA: inference only
    total_rows = 0
    first_chunk = True
    t_inf = time.perf_counter()

    for chunk in pd.read_csv(test_path, chunksize=CHUNK_SIZE):  # TEST DATA: inference only
        raw_texts = chunk["text"].fillna("").astype(str).tolist()
        norm_texts = [normalize(t) for t in raw_texts]

        X_chunk = vectorizer.transform(norm_texts)
        label_probs = align_proba(label_clf.predict_proba(X_chunk), label_clf.classes_)
        action_probs = align_proba(action_clf.predict_proba(X_chunk), action_clf.classes_)
        tech_probs = tech_clf.predict_proba(X_chunk)

        labels, techniques, actions, confidences = postprocess_chunk(
            raw_texts, label_probs, action_probs, tech_probs
        )

        out_chunk = pd.DataFrame(
            {
                "id": chunk["id"].to_numpy(),
                "label": labels,
                "techniques": techniques,
                "action": actions,
                "confidence": confidences,
            }
        )
        out_chunk.to_csv(sub_path, mode="w" if first_chunk else "a", header=first_chunk, index=False)
        first_chunk = False
        total_rows += len(chunk)
        print(f"Predicted {total_rows} rows ({time.perf_counter() - t_inf:.1f}s)...")

    validate_submission(sub_path, total_rows)
    print(f"Saved and validated {sub_path} ({total_rows} rows) in {time.perf_counter() - t0:.2f}s total.")


if __name__ == "__main__":
    main()
