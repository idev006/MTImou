from __future__ import annotations

import locale
import sys


def candidate_encodings() -> list[str]:
    candidates = [
        "utf-8-sig",
        "utf-8",
        locale.getpreferredencoding(False),
        sys.getfilesystemencoding(),
        "mbcs",
        "cp1252",
    ]
    seen: set[str] = set()
    ordered: list[str] = []
    for candidate in candidates:
        normalized = (candidate or "").strip()
        if not normalized:
            continue
        key = normalized.lower()
        if key in seen:
            continue
        seen.add(key)
        ordered.append(normalized)
    return ordered


def decode_text_bytes(data: bytes) -> str:
    if not data:
        return ""
    for encoding in candidate_encodings():
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8", errors="replace")

