from __future__ import annotations

import re
from pathlib import Path

_WHITESPACE_RE = re.compile(r"\s+")
_SAFE_TOKEN_RE = re.compile(r"[^A-Za-z0-9._-]+")


def normalize_whitespace(text: str) -> str:
    return _WHITESPACE_RE.sub(" ", text).strip()


def sanitize_path_token(value: str, *, fallback: str = "unknown") -> str:
    ascii_value = value.encode("ascii", "ignore").decode().strip().lower()
    cleaned = _SAFE_TOKEN_RE.sub("-", ascii_value).strip(".-")
    return cleaned or fallback


def sanitize_filename(filename: str, *, fallback_stem: str = "document") -> str:
    original = Path(filename or "")
    stem = sanitize_path_token(original.stem or fallback_stem, fallback=fallback_stem)
    suffix = sanitize_path_token(original.suffix.lstrip("."), fallback="")
    return f"{stem}.{suffix}" if suffix else stem
