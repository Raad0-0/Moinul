"""Text normalization and noise detection utilities for ScamShield BD."""

from __future__ import annotations

import re
import unicodedata

# Zero-width characters to strip
_ZERO_WIDTH_RE = re.compile(r"[\u200b\u200c\u200d\ufeff]")

# Common emoji and symbol ranges (preserves ASCII, Latin, Bangla \u0980-\u09FF, and '|')
_EMOJI_RE = re.compile(
    r"[\U0001F300-\U0001FAFF\U00002600-\U000027BF\U0001F000-\U0001F2FF\uFE00-\uFE0F]"
)

# Cyrillic and Greek lookalikes mapped to Latin equivalents
_LOOKALIKE_MAP: dict[str, str] = {
    # Cyrillic uppercase
    "А": "A",
    "В": "B",
    "С": "C",
    "Е": "E",
    "Ё": "E",
    "Н": "H",
    "І": "I",
    "Ї": "I",
    "Ј": "J",
    "К": "K",
    "М": "M",
    "О": "O",
    "Р": "P",
    "Ѕ": "S",
    "Т": "T",
    "У": "Y",
    "Х": "X",
    "Ү": "Y",
    # Cyrillic lowercase
    "а": "a",
    "в": "b",
    "с": "c",
    "е": "e",
    "ё": "e",
    "н": "h",
    "і": "i",
    "ї": "i",
    "ј": "j",
    "к": "k",
    "м": "m",
    "о": "o",
    "р": "p",
    "ѕ": "s",
    "т": "t",
    "у": "y",
    "х": "x",
    "ү": "y",
    "һ": "h",
    "ԁ": "d",
    "ԛ": "q",
    "ԝ": "w",
    # Greek uppercase
    "Α": "A",
    "Β": "B",
    "Ε": "E",
    "Ζ": "Z",
    "Η": "H",
    "Ι": "I",
    "Κ": "K",
    "Μ": "M",
    "Ν": "N",
    "Ο": "O",
    "Ρ": "P",
    "Τ": "T",
    "Υ": "Y",
    "Χ": "X",
    # Greek lowercase
    "α": "a",
    "β": "b",
    "ε": "e",
    "ζ": "z",
    "η": "h",
    "ι": "i",
    "κ": "k",
    "μ": "m",
    "ν": "n",
    "ο": "o",
    "ρ": "p",
    "ς": "c",
    "τ": "t",
    "υ": "u",
    "χ": "x",
}
_LOOKALIKE_TRANS = str.maketrans(_LOOKALIKE_MAP)

# Defanged and standard URLs (stops before whitespace or '|' delimiter)
_URL_RE = re.compile(
    r"(?i)(?:(?:hxxps?|https?|ftp)://[^\s|]+|www\.[^\s|]+|[a-z0-9-]+(?:\[\.\]|\.)(?:com|org|net|top|xyz|info|bd|me|io|co|uk|in|app|site|online|club|vip|link|click|shop)(?:\[\.\][a-z0-9-]+)*(?:/[^\s|]*)?)"
)

# Masked and standard Bangladeshi phone numbers (e.g. 01XXXXXXXXX, +8801XXXXXXXXX)
_PHONE_RE = re.compile(r"(?i)(?<!\w)(?:\+?88)?01[3-9x*#][0-9x*#]{8}(?!\w)")

# Collapse 3+ repeated non-digit, non-whitespace, non-pipe characters to 2
_REPEAT_CHAR_RE = re.compile(r"([^\d\s|])\1{2,}")

# Gibberish ASCII tokens: >=5 chars with no vowels, or >=7 chars with 5+ consecutive consonants
_GIBBERISH_NO_VOWEL_RE = re.compile(r"\b[b-df-hj-np-tv-xz]{5,}\b", re.IGNORECASE)
_GIBBERISH_CONSONANT_CLUSTER_RE = re.compile(
    r"\b[a-z]*[b-df-hj-np-tv-xz]{5,}[a-z]*\b", re.IGNORECASE
)

_WHITESPACE_RE = re.compile(r"\s+")

_BANGLA_LETTER_RE = re.compile(r"[\u0985-\u09B9\u09DC-\u09DF]")
_ASCII_WORD_RE = re.compile(r"[a-z]+")
_VOWEL_RE = re.compile(r"[aeiouy]")

_KNOWN_SHORT_ACRONYMS = frozenset(
    {
        "ok",
        "hi",
        "no",
        "go",
        "id",
        "tk",
        "bd",
        "cv",
        "pm",
        "am",
        "hr",
        "sc",
        "gp",
        "sms",
        "otp",
        "pin",
        "nid",
        "cvv",
        "kyc",
        "sim",
        "app",
        "url",
        "mfs",
        "atm",
    }
)


def _strip_gibberish_tokens(text: str) -> str:
    """Remove long vowel-less or consonant-heavy gibberish ASCII tokens."""
    tokens = text.split(" ")
    kept: list[str] = []
    for tok in tokens:
        if not tok:
            continue
        if tok in ("<URL>", "<PHONE>", "|||"):
            kept.append(tok)
            continue
        core = tok.strip(".,!?;:\"'()[]{}")
        if core.isascii() and core.isalpha():
            if len(core) >= 5 and _GIBBERISH_NO_VOWEL_RE.fullmatch(core):
                continue
            if len(core) >= 7 and _GIBBERISH_CONSONANT_CLUSTER_RE.fullmatch(core):
                continue
        kept.append(tok)
    return " ".join(kept)


def normalize(text: str) -> str:
    """Normalize SMS/chat text while preserving Bangla script, '|||', and speaker markers.

    Steps:
    1. Strip zero-width characters (U+200B, U+200C, U+200D, U+FEFF).
    2. Apply Unicode NFKC normalization.
    3. Map Cyrillic and Greek lookalikes to Latin characters.
    4. Remove emojis.
    5. Replace defanged URLs with '<URL>' and masked phones with '<PHONE>'.
    6. Collapse 3+ consecutive repeated characters (excluding digits, spaces, '|') to 2.
    7. Lowercase English characters (preserving '<URL>' and '<PHONE>' tokens).
    8. Remove gibberish consonant-heavy tokens and collapse whitespace.
    """
    if not isinstance(text, str):
        text = "" if text is None else str(text)

    # 1. Strip zero-width characters
    text = _ZERO_WIDTH_RE.sub("", text)

    # 2. Unicode NFKC normalization
    text = unicodedata.normalize("NFKC", text)

    # 3. Map Cyrillic and Greek lookalikes to Latin
    text = text.translate(_LOOKALIKE_TRANS)

    # 4. Remove emojis
    text = _EMOJI_RE.sub(" ", text)

    # 5. Replace defanged URLs and masked phone numbers with placeholders
    #    Use temporary ASCII-safe markers so lowercasing does not alter them.
    text = _URL_RE.sub(" __URL_TOKEN__ ", text)
    text = _PHONE_RE.sub(" __PHONE_TOKEN__ ", text)

    # 6. Collapse repeated characters (3+ -> 2), preserving digits and '|||'
    text = _REPEAT_CHAR_RE.sub(r"\1\1", text)

    # 7. Lowercase English characters (Bangla script is uncased and unaffected)
    text = text.lower()
    text = text.replace("__url_token__", "<URL>").replace("__phone_token__", "<PHONE>")

    # 8. Collapse whitespace and strip gibberish tokens
    text = _WHITESPACE_RE.sub(" ", text).strip()
    text = _strip_gibberish_tokens(text)
    text = _WHITESPACE_RE.sub(" ", text).strip()
    return text


def is_noise_only(text: str) -> bool:
    """Return True if text has no meaningful Bangla, English/Banglish words, URLs, or phones."""
    cleaned = normalize(text)
    if not cleaned:
        return True

    if "<URL>" in cleaned or "<PHONE>" in cleaned:
        return False

    # Meaningful Bangla script check (at least 2 Bangla letters)
    if len(_BANGLA_LETTER_RE.findall(cleaned)) >= 2:
        return False

    # Check ASCII alphabetic tokens for meaningful words or known abbreviations
    for word in _ASCII_WORD_RE.findall(cleaned):
        if word in _KNOWN_SHORT_ACRONYMS:
            return False
        if len(word) >= 2 and _VOWEL_RE.search(word) and len(set(word)) > 1:
            return False

    return True


if __name__ == "__main__":
    # 1. Cyrillic & Greek lookalike replacement
    cyrillic_sample = "bKаsh аccоunt еxpired, рlease сheck"
    norm_cyr = normalize(cyrillic_sample)
    assert "bkash account expired, please check" == norm_cyr, f"Got: {norm_cyr}"

    # 2. Defanged link and phone replacement
    defanged_sample = "Pay via bKash 01XXXXXXXXX at hxxps://sap-fee[.]top/pay"
    norm_def = normalize(defanged_sample)
    assert "<PHONE>" in norm_def and "<URL>" in norm_def, f"Got: {norm_def}"
    assert "01xxxxxxxxx" not in norm_def and "hxxps" not in norm_def, f"Got: {norm_def}"

    # 3. Bangla preservation + zero-width stripping
    bangla_sample = "ঘরে\u200b বসে প্রতিদিন ২০০০\u200c টাকা আয় করুন।"
    norm_bn = normalize(bangla_sample)
    assert norm_bn == "ঘরে বসে প্রতিদিন ২০০০ টাকা আয় করুন।", f"Got: {norm_bn}"

    # 4. Repeated character collapse + delimiter/speaker preservation
    conv_sample = "S: Helloooo Facccebook ||| R: Okaaaay 5000 tk"
    norm_conv = normalize(conv_sample)
    assert norm_conv == "s: helloo faccebook ||| r: okaay 5000 tk", f"Got: {norm_conv}"

    # 5. Noise-only detection
    assert is_noise_only("") is True
    assert is_noise_only("\u200b\u200c\u200d\ufeff") is True
    assert is_noise_only("wkrjfejejrn xkcdpl bcdfgh") is True
    assert is_noise_only("🔥🎉!!!") is True
    assert is_noise_only("Apnar OTP 482913") is False
    assert is_noise_only("আপনার অ্যাকাউন্ট যাচাই করুন") is False

    print("All normalize.py unit tests passed!")
