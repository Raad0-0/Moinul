"""Multi-task multilingual transformer training script for ScamShield BD."""

from __future__ import annotations

import argparse
import random
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from sklearn.utils.class_weight import compute_class_weight
from torch.utils.data import DataLoader, Dataset
from tqdm import tqdm
from transformers import (
    AutoConfig,
    AutoModel,
    AutoTokenizer,
    DataCollatorWithPadding,
    get_linear_schedule_with_warmup,
)

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from src.normalize import is_noise_only, normalize  # noqa: E402
from src.split import evaluate_predictions  # noqa: E402

SEED = 42
TECHNIQUE_CODES = ("T1", "T2", "T3", "T4", "T5", "T6")
NUM_CLASSES = 6


def set_seed(seed: int = SEED) -> None:
    """Fix all random seeds for reproducibility."""
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def encode_techniques(series: pd.Series) -> np.ndarray:
    """Convert pipe-delimited technique strings ('T1|T2' or 'NONE') to (N, 6) float32 array."""
    y = np.zeros((len(series), len(TECHNIQUE_CODES)), dtype=np.float32)
    code_to_idx = {code: idx for idx, code in enumerate(TECHNIQUE_CODES)}
    for i, val in enumerate(series.fillna("NONE")):
        text = str(val).strip()
        if not text or text == "NONE":
            continue
        for tok in text.split("|"):
            tok = tok.strip()
            if tok in code_to_idx:
                y[i, code_to_idx[tok]] = 1.0
    return y


def compute_balanced_weights(targets: np.ndarray, num_classes: int = NUM_CLASSES) -> torch.Tensor:
    """Compute balanced class weights for CrossEntropyLoss."""
    present = np.unique(targets)
    weights = np.ones(num_classes, dtype=np.float32)
    if len(present) > 0:
        computed = compute_class_weight("balanced", classes=present, y=targets)
        for cls, w in zip(present, computed):
            weights[int(cls)] = float(w)
    return torch.tensor(weights, dtype=torch.float32)


class ScamDataset(Dataset):
    """Dataset for multi-task scam, technique, and action classification."""

    def __init__(self, df: pd.DataFrame, tokenizer, max_length: int = 256) -> None:
        self.raw_texts = df["text"].fillna("").astype(str).tolist()
        self.norm_texts = [normalize(t) for t in self.raw_texts]
        self.labels = df["label"].astype(int).to_numpy()
        self.actions = df["action"].astype(int).to_numpy()
        self.techniques = encode_techniques(df["techniques"])
        self.encodings = tokenizer(
            self.norm_texts,
            truncation=True,
            max_length=max_length,
            padding=False,
        )

    def __len__(self) -> int:
        return len(self.labels)

    def __getitem__(self, idx: int) -> dict:
        return {
            "input_ids": self.encodings["input_ids"][idx],
            "attention_mask": self.encodings["attention_mask"][idx],
            "label": int(self.labels[idx]),
            "technique": self.techniques[idx].tolist(),
            "action": int(self.actions[idx]),
        }


def make_collate_fn(tokenizer):
    """Create a dynamic-padding collate function preserving multi-task targets."""
    pad_collator = DataCollatorWithPadding(tokenizer=tokenizer, return_tensors="pt")

    def collate_fn(batch: list[dict]) -> dict[str, torch.Tensor]:
        features = [
            {"input_ids": item["input_ids"], "attention_mask": item["attention_mask"]}
            for item in batch
        ]
        padded = pad_collator(features)
        padded["labels"] = torch.tensor([item["label"] for item in batch], dtype=torch.long)
        padded["techniques"] = torch.tensor(
            [item["technique"] for item in batch], dtype=torch.float32
        )
        padded["actions"] = torch.tensor([item["action"] for item in batch], dtype=torch.long)
        return padded

    return collate_fn


class MultiTaskModel(nn.Module):
    """Shared multilingual transformer encoder with 3 classification heads."""

    def __init__(
        self,
        model_name: str = "xlm-roberta-base",
        dropout_p: float = 0.2,
        from_config_only: bool = False,
    ) -> None:
        super().__init__()
        if from_config_only:
            config = AutoConfig.from_pretrained(model_name)
            self.encoder = AutoModel.from_config(config)
        else:
            self.encoder = AutoModel.from_pretrained(model_name)
        hidden_size = self.encoder.config.hidden_size
        self.dropout = nn.Dropout(dropout_p)
        self.head_label = nn.Linear(hidden_size, NUM_CLASSES)
        self.head_tech = nn.Linear(hidden_size, len(TECHNIQUE_CODES))
        self.head_action = nn.Linear(hidden_size, NUM_CLASSES)

    def forward(
        self, input_ids: torch.Tensor, attention_mask: torch.Tensor
    ) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        outputs = self.encoder(input_ids=input_ids, attention_mask=attention_mask)
        cls_hidden = self.dropout(outputs.last_hidden_state[:, 0, :])
        logits_label = self.head_label(cls_hidden)
        logits_tech = self.head_tech(cls_hidden)
        logits_action = self.head_action(cls_hidden)
        return logits_label, logits_tech, logits_action


def logits_to_preds_df(
    raw_texts: list[str],
    logits_label: np.ndarray,
    logits_tech: np.ndarray,
    logits_action: np.ndarray,
    tech_threshold: float = 0.5,
) -> pd.DataFrame:
    """Convert raw multi-task logits into a DataFrame adhering to ScamShield rules."""
    exp_l = np.exp(logits_label - np.max(logits_label, axis=1, keepdims=True))
    probs_label = exp_l / np.sum(exp_l, axis=1, keepdims=True)

    exp_a = np.exp(logits_action - np.max(logits_action, axis=1, keepdims=True))
    probs_action = exp_a / np.sum(exp_a, axis=1, keepdims=True)

    probs_tech = 1.0 / (1.0 + np.exp(-np.clip(logits_tech, -30.0, 30.0)))

    pred_labels: list[int] = []
    pred_techs: list[str] = []
    pred_actions: list[int] = []
    confidences: list[float] = []

    for i, raw_text in enumerate(raw_texts):
        max_conf = float(np.clip(np.max(probs_label[i]), 0.0, 1.0))

        if is_noise_only(raw_text):
            pred_labels.append(0)
            pred_techs.append("NONE")
            pred_actions.append(0)
            confidences.append(round(max_conf, 4))
            continue

        lbl = int(np.argmax(probs_label[i]))
        pred_labels.append(lbl)
        confidences.append(round(max_conf, 4))

        if lbl in (0, 5):
            pred_techs.append("NONE")
            pred_actions.append(0)
        else:
            act = int(np.argmax(probs_action[i]))
            if act == 0:
                act = int(1 + np.argmax(probs_action[i, 1:]))
            pred_actions.append(act)

            active = [
                TECHNIQUE_CODES[j]
                for j in range(len(TECHNIQUE_CODES))
                if probs_tech[i, j] >= tech_threshold
            ]
            if not active:
                active = [TECHNIQUE_CODES[int(np.argmax(probs_tech[i]))]]
            pred_techs.append("|".join(active))

    return pd.DataFrame(
        {
            "label": pred_labels,
            "techniques": pred_techs,
            "action": pred_actions,
            "confidence": confidences,
        }
    )


@torch.no_grad()
def evaluate_model(
    model: MultiTaskModel,
    val_loader: DataLoader,
    val_df: pd.DataFrame,
    device: torch.device,
) -> tuple[dict[str, float], pd.DataFrame, dict[str, np.ndarray]]:
    """Run validation inference and return metrics, predictions DataFrame, and raw logits."""
    model.eval()
    all_l, all_t, all_a = [], [], []
    for batch in val_loader:
        input_ids = batch["input_ids"].to(device)
        attention_mask = batch["attention_mask"].to(device)
        logits_l, logits_t, logits_a = model(input_ids=input_ids, attention_mask=attention_mask)
        all_l.append(logits_l.cpu().numpy())
        all_t.append(logits_t.cpu().numpy())
        all_a.append(logits_a.cpu().numpy())

    logits_label = np.concatenate(all_l, axis=0)
    logits_tech = np.concatenate(all_t, axis=0)
    logits_action = np.concatenate(all_a, axis=0)

    preds_df = logits_to_preds_df(
        val_df["text"].fillna("").astype(str).tolist(),
        logits_label,
        logits_tech,
        logits_action,
    )
    metrics = evaluate_predictions(val_df, preds_df)
    logits_dict = {
        "logits_label": logits_label,
        "logits_tech": logits_tech,
        "logits_action": logits_action,
    }
    return metrics, preds_df, logits_dict


def train(args: argparse.Namespace) -> None:
    """Train the multi-task transformer and save best checkpoint and validation logits."""
    set_seed(SEED)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    use_amp = device.type == "cuda"

    best_model_dir = _PROJECT_ROOT / "models" / "best_model"
    outputs_dir = _PROJECT_ROOT / "outputs"
    best_model_dir.mkdir(parents=True, exist_ok=True)
    outputs_dir.mkdir(parents=True, exist_ok=True)

    train_df = pd.read_csv(_PROJECT_ROOT / args.train_path)
    val_df = pd.read_csv(_PROJECT_ROOT / args.val_path)

    tokenizer = AutoTokenizer.from_pretrained(args.model_name)
    train_ds = ScamDataset(train_df, tokenizer, max_length=args.max_length)
    val_ds = ScamDataset(val_df, tokenizer, max_length=args.max_length)

    collate_fn = make_collate_fn(tokenizer)
    train_loader = DataLoader(
        train_ds, batch_size=args.batch_size, shuffle=True, collate_fn=collate_fn
    )
    val_loader = DataLoader(
        val_ds, batch_size=args.batch_size, shuffle=False, collate_fn=collate_fn
    )

    model = MultiTaskModel(args.model_name).to(device)

    label_weights = compute_balanced_weights(train_ds.labels).to(device)
    action_weights = compute_balanced_weights(train_ds.actions).to(device)
    loss_fn_label = nn.CrossEntropyLoss(weight=label_weights)
    loss_fn_tech = nn.BCEWithLogitsLoss()
    loss_fn_action = nn.CrossEntropyLoss(weight=action_weights)

    optimizer = torch.optim.AdamW(model.parameters(), lr=args.lr, weight_decay=args.weight_decay)
    total_steps = len(train_loader) * args.epochs
    warmup_steps = max(1, int(0.1 * total_steps))
    scheduler = get_linear_schedule_with_warmup(
        optimizer, num_warmup_steps=warmup_steps, num_training_steps=total_steps
    )
    scaler = torch.amp.GradScaler("cuda", enabled=use_amp)

    best_fa = -1.0
    print(f"Training {args.model_name} on {device} (AMP={use_amp}) for {args.epochs} epochs...")

    for epoch in range(1, args.epochs + 1):
        model.train()
        running_loss = 0.0

        progress = tqdm(train_loader, desc=f"Epoch {epoch}/{args.epochs}", leave=False)
        for batch in progress:
            optimizer.zero_grad(set_to_none=True)
            input_ids = batch["input_ids"].to(device)
            attention_mask = batch["attention_mask"].to(device)
            y_l = batch["labels"].to(device)
            y_t = batch["techniques"].to(device)
            y_a = batch["actions"].to(device)

            with torch.amp.autocast("cuda", enabled=use_amp):
                logits_l, logits_t, logits_a = model(input_ids=input_ids, attention_mask=attention_mask)
                loss_l = loss_fn_label(logits_l, y_l)
                loss_t = loss_fn_tech(logits_t, y_t)
                loss_a = loss_fn_action(logits_a, y_a)
                loss = 1.0 * loss_l + 0.5 * loss_t + 0.5 * loss_a

            scaler.scale(loss).backward()
            scaler.step(optimizer)
            scaler.update()
            scheduler.step()

            running_loss += float(loss.item())
            progress.set_postfix(loss=f"{loss.item():.4f}")

        avg_loss = running_loss / max(1, len(train_loader))
        metrics, val_preds_df, val_logits = evaluate_model(model, val_loader, val_df, device)
        print(
            f"Epoch {epoch}/{args.epochs} | loss={avg_loss:.4f} | "
            f"F_A={metrics['F_A']:.4f} | F_B={metrics['F_B']:.4f} | "
            f"F_C={metrics['F_C']:.4f} | Cal={metrics['Calibration']:.4f} | S={metrics['S']:.4f}"
        )

        if metrics["F_A"] > best_fa:
            best_fa = metrics["F_A"]
            tokenizer.save_pretrained(best_model_dir)
            model.encoder.config.save_pretrained(best_model_dir)
            torch.save(model.state_dict(), best_model_dir / "multitask_weights.pt")
            val_preds_df.to_csv(outputs_dir / "val_preds.csv", index=False)
            np.savez(outputs_dir / "val_logits.npz", **val_logits)
            print(f"  -> Saved new best model (F_A={best_fa:.4f}) to {best_model_dir}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Train multi-task transformer for ScamShield BD.")
    parser.add_argument("--model_name", type=str, default="xlm-roberta-base")
    parser.add_argument("--train_path", type=str, default="data/train.csv")
    parser.add_argument("--val_path", type=str, default="data/val.csv")
    parser.add_argument("--max_length", type=int, default=256)
    parser.add_argument("--batch_size", type=int, default=16)
    parser.add_argument("--lr", type=float, default=2e-5)
    parser.add_argument("--epochs", type=int, default=3)
    parser.add_argument("--weight_decay", type=float, default=0.01)
    return parser.parse_args()


if __name__ == "__main__":
    train(parse_args())
