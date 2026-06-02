from __future__ import annotations

import os
import sys
from pathlib import Path

THIS_DIR = Path(__file__).resolve().parent
if str(THIS_DIR) not in sys.path:
    sys.path.insert(0, str(THIS_DIR))

from mtimou_v2.source_capability import run_source_capability_check
from venv_guard import enforce_venv_python


ROOT_DIR = Path(__file__).resolve().parents[1]


def main() -> int:
    enforce_venv_python()
    camera_ids = [arg for arg in sys.argv[1:] if not arg.startswith("--")]
    mode = os.getenv("IMOU_SOURCE_CAPABILITY_MODE", "public")
    duration_sec = float(os.getenv("IMOU_SOURCE_CAPABILITY_DURATION_SEC", "10"))
    log_path = Path(
        os.getenv(
            "IMOU_SOURCE_CAPABILITY_LOG_PATH",
            str(ROOT_DIR / "logs" / "source_capability_latest.log"),
        )
    )
    return run_source_capability_check(
        camera_ids=camera_ids or None,
        mode=mode,
        duration_sec=duration_sec,
        log_path=log_path,
    )


if __name__ == "__main__":
    raise SystemExit(main())
