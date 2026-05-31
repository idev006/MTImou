from __future__ import annotations

import os
import sys
from pathlib import Path


def _normalize_path(p: str) -> str:
    return os.path.normcase(os.path.normpath(str(Path(p).resolve())))


def expected_python_path() -> Path:
    env_expected = os.getenv("IMOU_REQUIRED_PYTHON", "").strip()
    if env_expected:
        return Path(env_expected)
    project_root = Path(__file__).resolve().parents[1]
    return project_root / ".venv" / "Scripts" / "python.exe"


def enforce_venv_python() -> None:
    expected = _normalize_path(str(expected_python_path()))
    actual = _normalize_path(sys.executable)
    if actual != expected:
        msg = (
            "[ERROR] Wrong Python interpreter.\n"
            f"Expected: {expected}\n"
            f"Actual:   {actual}\n"
            "Please run with F:\\programming\\python\\MTImou\\.venv\\Scripts\\python.exe"
        )
        raise RuntimeError(msg)
