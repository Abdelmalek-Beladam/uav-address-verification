"""Normalisation of house numbers so that plate readings and official numbers compare.

Keys are lowercase: number followed by an optional suffix letter.
  "12" -> "12", "12 bis" / "12B" -> "12b", "12 ter" -> "12t", "17 A" -> "17a".
Unreadable or invalid readings normalise to None.
"""

from __future__ import annotations

import math
import re

SUFFIX_WORDS = {"BIS": "b", "TER": "t", "QUATER": "q", "QUINQUIES": "c"}
SUFFIX_DISPLAY = {"b": "bis", "t": "ter", "q": "quater"}
UNREADABLE_TOKENS = {"", "?", "??", "???", "UNREADABLE", "ILLISIBLE", "NA", "N/A", "NAN", "NONE", "NULL", "-"}

_PATTERN = re.compile(r"(\d{1,4})(BIS|TER|QUATER|QUINQUIES|[A-Z])?")
_KEY = re.compile(r"(\d+)([a-z]*)")


def normalize_number(raw) -> str | None:
    """Return the comparison key of a house number, or None if unreadable."""
    if raw is None:
        return None
    if isinstance(raw, float):
        if math.isnan(raw):
            return None
        if raw.is_integer():
            raw = int(raw)
    text = str(raw).strip().upper()
    if text in UNREADABLE_TOKENS:
        return None
    text = re.sub(r"[^0-9A-Z]", "", text)
    match = _PATTERN.fullmatch(text)
    if not match:
        return None
    number = int(match.group(1))
    suffix = match.group(2) or ""
    suffix = SUFFIX_WORDS.get(suffix, suffix.lower())
    return f"{number}{suffix}"


def split_key(key: str) -> tuple[int, str]:
    match = _KEY.fullmatch(key)
    if not match:
        raise ValueError(f"Invalid number key: {key!r}")
    return int(match.group(1)), match.group(2)


def base_number(key: str) -> int:
    return split_key(key)[0]


def display_number(key: str | None) -> str:
    """Human-readable form of a key: '12b' -> '12 bis', '17a' -> '17 A'."""
    if key is None:
        return "unreadable"
    number, suffix = split_key(key)
    if not suffix:
        return str(number)
    return f"{number} {SUFFIX_DISPLAY.get(suffix, suffix.upper())}"
