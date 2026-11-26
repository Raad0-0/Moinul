"""500k-row inference, calibration, post-processing, and submission verification for ScamShield BD."""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
import torch
from torch.utils.data import DataLoader, Dataset
from transformers import AutoTokenizer, DataCollatorWithPadding

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from src.calibrate import calibrate_confidence  # noqa: E402
from src.normalize import is_noise_only, normalize  # noqa: E402
from src.postprocess import apply_postprocessing  # noqa: E402
from src.train_transformer import MultiTaskModel  # noqa: E402

VALID_TECHNIQUES = {"T1", "T2", "T3", "T4", "T5", "T6"}


def _resolve_path(path_str: str) -> Path:
    path = Path(path_str)
    return path if path.is_absolute() else _PROJECT_ROOT / path


def _softmax(logits: np.ndarray) -> np.ndarray:
    shifted = logits - np.max(logits, axis=-1, keepdims=True)
    exp_x = np.exp(shifted)
    return exp_x / np.sum(exp_x, axis=-1, keepdims=True)


def _sigmoid(logits: np.ndarray) -> np.ndarray:
    return 1.0 / (1.0 + np.exp(-np.clip(logits, -30.0, 30.0)))


class InferenceDataset(Dataset):
    """PyTorch Dataset that tokenizes normalized texts for inference."""

    def __init__(self, texts: list[str], tokenizer, max_length: int = 256) -> None:
        self.texts = texts
        self.tokenizer = tokenizer
        self.max_length = max_length

    def __len__(self) -> int:
        return len(self.texts)

    def __getitem__(self, idx: int) -> dict[str, list[int]]:
        return self.tokenizer(
            self.texts[idx],
            truncation=True,
            max_length=self.max_length,
            padding=False,
        )


def _run_dataloader_inference(
    texts: list[str],
    model: MultiTaskModel,
    tokenizer,
    device: torch.device,
    batch_size: int,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Shared DataLoader inference loop with throughput benchmarking and progress logging."""
    dataset = InferenceDataset(texts, tokenizer, max_length=256)
    collator = DataCollatorWithPadding(tokenizer=tokenizer, return_tensors="pt")
    loader = DataLoader(
        dataset,
        batch_size=batch_size,
        shuffle=False,
        collate_fn=collator,
        pin_memory=torch.cuda.is_available(),
        num_workers=2,
    )

    all_logits_a: list[np.ndarray] = []
    all_logits_b: list[np.ndarray] = []
    all_logits_c: list[np.ndarray] = []

    use_amp = device.type == "cuda"
    processed = 0
    benchmarked = False
    next_log = 50_000
    t_start = time.perf_counter()

    with torch.inference_mode():
        for batch in loader:
            input_ids = batch["input_ids"].to(device, non_blocking=True)
            attention_mask = batch["attention_mask"].to(device, non_blocking=True)

            with torch.amp.autocast("cuda", enabled=use_amp):
                logits_a, logits_b, logits_c = model(input_ids=input_ids, attention_mask=attention_mask)

            all_logits_a.append(logits_a.float().cpu().numpy())
            all_logits_b.append(logits_b.float().cpu().numpy())
            all_logits_c.append(logits_c.float().cpu().numpy())

            processed += input_ids.size(0)
            elapsed = time.perf_counter() - t_start

            if not benchmarked and processed >= min(5_000, len(texts)):
                rate = processed / max(elapsed, 1e-6)
                eta_min = (len(texts) / max(rate, 1e-6)) / 60.0
                print(
                    f"[Benchmark] {processed} samples in {elapsed:.2f}s "
                    f"({rate:.1f} samples/s, est. total {eta_min:.1f} min)"
                )
                benchmarked = True

            if processed >= next_log:
                print(f"[Progress] {processed}/{len(texts)} samples ({elapsed:.1f}s)")
                next_log += 50_000

    logits_A = np.concatenate(all_logits_a, axis=0)
    probs_B = _sigmoid(np.concatenate(all_logits_b, axis=0))
    probs_C = _softmax(np.concatenate(all_logits_c, axis=0))
    return logits_A, probs_B, probs_C


def run_direct_inference(
    texts: list[str],
    model: MultiTaskModel,
    tokenizer,
    device: torch.device,
    batch_size: int,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Method 1: Direct sequential batch inference over all rows."""
    print(f"Running direct inference on {len(texts)} texts (batch_size={batch_size}, device={device})...")
    return _run_dataloader_inference(texts, model, tokenizer, device, batch_size)


def run_dedup_inference(
    test_df: pd.DataFrame,
    model: MultiTaskModel,
    tokenizer,
    device: torch.device,
    batch_size: int,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Method 2: Deduplicated fast inference over unique normalized texts."""
    codes, uniques = pd.factorize(test_df["clean_text"], sort=False)
    unique_texts = uniques.tolist()
    print(
        f"Running dedup inference on {len(unique_texts)} unique texts "
        f"(out of {len(test_df)}, batch_size={batch_size}, device={device})..."
    )
    u_logits_A, u_probs_B, u_probs_C = _run_dataloader_inference(
        unique_texts, model, tokenizer, device, batch_size
    )
    return u_logits_A[codes], u_probs_B[codes], u_probs_C[codes]


def verify_submission(sub_df: pd.DataFrame, test_df: pd.DataFrame) -> None:
    """Enforce strict competition submission schema and value assertions."""
    expected_cols = ["id", "label", "techniques", "action", "confidence"]
    assert list(sub_df.columns) == expected_cols, f"Bad columns: {list(sub_df.columns)}"
    assert len(sub_df) == len(test_df), f"Row count mismatch: {len(sub_df)} != {len(test_df)}"
    assert not sub_df.isna().any().any(), "Submission contains NaN/null values"

    sample_sub_path = _PROJECT_ROOT / "data" / "sample_submission.csv"
    if sample_sub_path.exists() and len(sub_df) == 500_000:
        sample_sub = pd.read_csv(sample_sub_path, usecols=["id"])
        assert len(sub_df) == 500_000, f"Expected 500,000 rows, got {len(sub_df)}"
        assert (sub_df["id"].to_numpy() == sample_sub["id"].to_numpy()).all(), (
            "IDs do not match sample_submission.csv"
        )

    assert sub_df["label"].isin([0, 1, 2, 3, 4, 5]).all(), "Labels out of 0..5"
    assert sub_df["action"].isin([0, 1, 2, 3, 4, 5]).all(), "Actions out of 0..5"
    assert sub_df["confidence"].between(0.0, 1.0).all(), "Confidence out of [0.0, 1.0]"

    for val in sub_df["techniques"]:
        assert isinstance(val, str) and len(val) > 0, "Empty technique string"
        if val != "NONE":
            parts = val.split("|")
            assert all(p in VALID_TECHNIQUES for p in parts), f"Invalid technique code: {val}"

    benign = sub_df["label"].isin([0, 5])
    assert (sub_df.loc[benign, "techniques"] == "NONE").all(), "Class 0/5 must have NONE"
    assert (sub_df.loc[benign, "action"] == 0).all(), "Class 0/5 must have action 0"

    scam = sub_df["label"].isin([1, 2, 3, 4])
    assert (sub_df.loc[scam, "techniques"] != "NONE").all(), "Class 1-4 cannot have NONE"
    assert (sub_df.loc[scam, "action"] != 0).all(), "Class 1-4 cannot have action 0"


def parse_args() -> argparse.Namespace:
    default_bs = 256 if torch.cuda.is_available() else 64
    parser = argparse.ArgumentParser(description="Run ScamShield BD inference and generate submission.csv.")
    parser.add_argument("--mode", choices=["direct", "dedup"], default="direct")
    parser.add_argument("--batch_size", type=int, default=default_bs)
    parser.add_argument("--test_path", type=str, default="data/test.csv")
    parser.add_argument("--output_path", type=str, default="submission.csv")
    parser.add_argument("--model_dir", type=str, default="models/best_model")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    t0 = time.perf_counter()
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    test_path = _resolve_path(args.test_path)
    output_path = _resolve_path(args.output_path)
    model_dir = _resolve_path(args.model_dir)

    print(f"Loading test data from {test_path}...")
    test_df = pd.read_csv(test_path)  # TEST DATA: inference only
    raw_texts = test_df["text"].fillna("").astype(str).tolist()
    test_df["clean_text"] = [normalize(t) for t in raw_texts]
    is_noise_mask = np.array([is_noise_only(t) for t in raw_texts], dtype=bool)

    print(f"Loading model and tokenizer from {model_dir}...")
    tokenizer = AutoTokenizer.from_pretrained(str(model_dir))
    model = MultiTaskModel(str(model_dir), from_config_only=True)
    weights_path = model_dir / "multitask_weights.pt"
    state_dict = torch.load(weights_path, map_location=device, weights_only=True)
    model.load_state_dict(state_dict)
    model.to(device).eval()

    if args.mode == "dedup":
        logits_A, probs_B, probs_C = run_dedup_inference(
            test_df, model, tokenizer, device, args.batch_size
        )
    else:
        logits_A, probs_B, probs_C = run_direct_inference(
            test_df["clean_text"].tolist(), model, tokenizer, device, args.batch_size
        )

    # Load tuned thresholds and calibration temperature if available
    thresh_path = _PROJECT_ROOT / "models" / "technique_thresholds.json"
    thresholds = None
    if thresh_path.exists():
        with open(thresh_path, "r", encoding="utf-8") as f:
            thresholds = json.load(f)

    cal_path = _PROJECT_ROOT / "models" / "calibration_params.json"
    temperature = 1.0
    if cal_path.exists():
        with open(cal_path, "r", encoding="utf-8") as f:
            temperature = float(json.load(f).get("temperature", 1.0))

    probs_A = _softmax(logits_A)
    sub_df = apply_postprocessing(test_df, probs_A, probs_B, probs_C, thresholds=thresholds)
    cal_conf = calibrate_confidence(logits_A, temperature, is_noise_mask=is_noise_mask)
    sub_df["confidence"] = np.round(cal_conf, 4)

    verify_submission(sub_df, test_df)
    sub_df.to_csv(output_path, index=False)
    print(f"Saved and verified {output_path} ({len(sub_df)} rows) in {time.perf_counter() - t0:.2f}s.")


if __name__ == "__main__":
    main()
