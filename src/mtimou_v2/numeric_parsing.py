from __future__ import annotations

import os


def normalize_decimal_text(raw: str) -> str:
    text = raw.strip()
    if not text:
        return text
    if "," in text and "." not in text:
        return text.replace(",", ".")
    return text


def parse_float_text(raw: str, default: float) -> float:
    text = normalize_decimal_text(raw)
    if not text:
        return default
    try:
        return float(text)
    except ValueError:
        return default


def parse_int_text(raw: str, default: int) -> int:
    text = normalize_decimal_text(raw)
    if not text:
        return default
    try:
        return int(float(text))
    except ValueError:
        return default


def parse_env_float(name: str, default: float) -> float:
    return parse_float_text(os.getenv(name, ""), default)


def parse_env_int(name: str, default: int) -> int:
    return parse_int_text(os.getenv(name, ""), default)

