"""Adversarial text corruption and noise injection for ScamShield BD."""

from __future__ import annotations

import random
import re
import sys
from pathlib import Path

import pandas as pd

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

SEED = 42

LOOKALIKE_MAP: dict[str, str] = {
    "a": "а",
    "e": "е",
    "o": "о",
    "p": "р",
    "c": "с",
    "x": "х",
    "A": "А",
    "E": "Е",
    "O": "О",
    "P": "Р",
    "C": "С",
    "X": "Х",
}

SENSITIVE_WORDS = [
    "bKash",
    "Nagad",
    "OTP",
    "PIN",
    "parcel",
    "account",
    "verify",
    "link",
    "taka",
]

SENSITIVE_MISSPELLINGS: dict[str, list[str]] = {
    "bkash": ["bkaash", "b-kash", "bk@sh"],
    "nagad": ["nagaad", "n@gad", "ngad"],
    "otp": ["ootp", "0tp", "o-t-p"],
    "pin": ["p1n", "piin", "p-i-n"],
    "parcel": ["parcl", "paarcel", "parcelll"],
    "account": ["accnt", "accoount", "acount"],
    "verify": ["verfy", "verifiy", "v3rify"],
    "link": ["l1nk", "liink", "lnk"],
    "taka": ["tka", "taaka", "t@ka"],
}

ZERO_WIDTH_CHARS = ["\u200B", "\u200C", "\u200D", "\uFEFF"]
SCAM_EMOJIS = ["🔥", "💰", "🎁", "⚠️", "❗", "👉"]
GIBBERISH_TOKENS = ["wkrjfejejrn", "zzqwpo", "xkcdpl", "bcdfghj", "qwrtyps", "mnbvcxz"]

_SPEAKER_PREFIX_RE = re.compile(
    r"^(\s*(?:S:|R:|A:|B:|\[Sender\]|\[You\]|Caller:|You:)\s*)",
    re.IGNORECASE,
)


def _corrupt_sensitive_words(text: str, prob: float, rng: random.Random) -> str:
    """Deliberately misspell sensitive keywords with probability `prob`."""
    for word in SENSITIVE_WORDS:
        pattern = re.compile(rf"\b{re.escape(word)}\b", re.IGNORECASE)
        if pattern.search(text) and rng.random() < prob:
            replacement = rng.choice(SENSITIVE_MISSPELLINGS[word.lower()])
            text = pattern.sub(replacement, text, count=1)
    return text


def _corrupt_segment(segment: str, level: float, rng: random.Random) -> str:
    """Apply character, whitespace, emoji, and gibberish corruptions to a non-prefix segment."""
    if not segment.strip():
        return segment

    # Pick a random mix of active mutations based on level
    segment = _corrupt_sensitive_words(segment, prob=min(0.8, level * 1.5), rng=rng)

    out_chars: list[str] = []
    for ch in segment:
        # Random deletion on inner ASCII letters
        if ch.isascii() and ch.isalpha() and rng.random() < 0.06 * level:
            continue

        # Random case variation
        if ch.isascii() and ch.isalpha() and rng.random() < 0.30 * level:
            ch = ch.upper() if ch.islower() else ch.lower()

        # Lookalike swap
        if ch in LOOKALIKE_MAP and rng.random() < 0.25 * level:
            ch = LOOKALIKE_MAP[ch]

        out_chars.append(ch)

        # Character repetition (3-4x)
        if ch.isascii() and ch.isalpha() and rng.random() < 0.08 * level:
            out_chars.append(ch * rng.randint(2, 3))

        # Zero-width insertion between letters
        if ch.isalpha() and rng.random() < 0.12 * level:
            out_chars.append(rng.choice(ZERO_WIDTH_CHARS))

        # Random space insertion
        if ch.isalpha() and rng.random() < 0.05 * level:
            out_chars.append(" ")

    corrupted = "".join(out_chars)

    # Occasionally remove existing spaces between words
    if rng.random() < 0.5 * level:
        words = corrupted.split(" ")
        if len(words) > 2:
            idx = rng.randint(0, len(words) - 2)
            words[idx] = words[idx] + words[idx + 1]
            del words[idx + 1]
        corrupted = " ".join(words)

    # Inject scam emojis
    if rng.random() < min(0.9, level * 1.8):
        tokens = corrupted.split(" ")
        pos = rng.randint(0, len(tokens))
        tokens.insert(pos, rng.choice(SCAM_EMOJIS))
        corrupted = " ".join(tokens)

    # Inject meaningless gibberish token
    if rng.random() < min(0.8, level * 1.4):
        tokens = corrupted.split(" ")
        pos = rng.randint(0, len(tokens))
        tokens.insert(pos, rng.choice(GIBBERISH_TOKENS))
        corrupted = " ".join(tokens)

    return corrupted


def corrupt(text: str, level: float = 0.3, rng: random.Random | None = None) -> str:
    """Apply adversarial corruptions while keeping '|||' and speaker prefixes intact."""
    if not isinstance(text, str) or not text:
        return "" if text is None else str(text)

    level = max(0.0, min(1.0, float(level)))
    if level == 0.0:
        return text

    local_rng = rng if rng is not None else random.Random(SEED)

    turns = text.split("|||")
    corrupted_turns: list[str] = []
    for turn in turns:
        match = _SPEAKER_PREFIX_RE.match(turn)
        if match:
            prefix = match.group(1)
            body = turn[len(prefix) :]
            corrupted_turns.append(prefix + _corrupt_segment(body, level, local_rng))
        else:
            corrupted_turns.append(_corrupt_segment(turn, level, local_rng))

    return " ||| ".join(t.strip() for t in corrupted_turns)


def generate_noise_only(n_samples: int = 60, rng: random.Random | None = None) -> list[dict]:
    """Generate noise-only records strictly labeled 0 / NONE / 0."""
    local_rng = rng if rng is not None else random.Random(SEED)
    consonants = "bcdfghjklmnpqrstvwxz"
    rows: list[dict] = []

    for i in range(n_samples):
        mode = i % 3
        if mode == 0:
            # Random consonant-cluster tokens
            words = [
                "".join(local_rng.choice(consonants) for _ in range(local_rng.randint(5, 11)))
                for _ in range(local_rng.randint(1, 3))
            ]
            text = " ".join(words)
        elif mode == 1:
            # Keyboard smash + gibberish
            base = local_rng.choice(["lkjsdfoiu xcvbnm", "zzqpwoeiru", "asdfghjkl qwert", "zxcvbnm"])
            text = f"{base} {local_rng.choice(GIBBERISH_TOKENS)}"
        else:
            # Zero-width + emoji + punctuation noise
            zw = "".join(local_rng.choice(ZERO_WIDTH_CHARS) for _ in range(local_rng.randint(2, 5)))
            em = "".join(local_rng.choice(SCAM_EMOJIS) for _ in range(local_rng.randint(1, 3)))
            text = f"{zw}{em} !!!"

        rows.append(
            {
                "scenario_id": "noise_only",
                "group": "noise",
                "text": text,
                "label": 0,
                "techniques": "NONE",
                "action": 0,
            }
        )
    return rows


def augment_dataset(
    input_path: Path,
    output_path: Path,
    corrupt_frac: float = 0.25,
    n_noise: int = 60,
    seed: int = SEED,
) -> pd.DataFrame:
    """Combine original synthetic data, ~25% corrupted copies, and noise-only samples."""
    rng = random.Random(seed)
    df = pd.read_csv(input_path)

    # Stratified sample across classes
    sampled_parts = []
    for _, cls_df in df.groupby("label", sort=True):
        n_sample = max(1, int(round(len(cls_df) * corrupt_frac)))
        sampled_parts.append(cls_df.sample(n=n_sample, random_state=seed))
    sampled_df = pd.concat(sampled_parts, ignore_index=True)

    corrupted_rows: list[dict] = []
    for row in sampled_df.itertuples(index=False):
        corrupted_rows.append(
            {
                "scenario_id": row.scenario_id,
                "group": row.group,
                "text": corrupt(str(row.text), level=0.35, rng=rng),
                "label": int(row.label),
                "techniques": row.techniques,
                "action": int(row.action),
            }
        )

    noise_rows = generate_noise_only(n_samples=n_noise, rng=rng)
    combined = pd.concat(
        [df, pd.DataFrame(corrupted_rows), pd.DataFrame(noise_rows)],
        ignore_index=True,
    )
    combined = combined.sample(frac=1.0, random_state=seed).reset_index(drop=True)
    combined = combined[["scenario_id", "group", "text", "label", "techniques", "action"]]
    combined.to_csv(output_path, index=False)
    return combined


if __name__ == "__main__":
    in_path = _PROJECT_ROOT / "data" / "synthetic_train.csv"
    out_path = _PROJECT_ROOT / "data" / "augmented_train.csv"

    aug_df = augment_dataset(in_path, out_path, corrupt_frac=0.25, n_noise=60, seed=SEED)

    assert not aug_df.isna().any().any(), "Augmented dataset contains NaNs!"

    # Show sample corruptions
    demo_rng = random.Random(SEED)
    samples = [
        "bKash Helpline: Share your OTP within 1 hour at hxxps://bkash-claim[.]top",
        "S: Hello ||| R: What reward? ||| S: Send Tk 500 to verify your parcel.",
    ]
    print("Sample corruptions:")
    for s in samples:
        print("  ORIG:", s)
        print("  CORR:", corrupt(s, level=0.35, rng=demo_rng))

    print(f"\nSaved {len(aug_df)} rows to {out_path}")
    print("Class distribution:")
    print(aug_df["label"].value_counts().sort_index())
