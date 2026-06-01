from __future__ import annotations

import os
import sys
from pathlib import Path

THIS_DIR = Path(__file__).resolve().parent
if str(THIS_DIR) not in sys.path:
    sys.path.insert(0, str(THIS_DIR))

from mtimou_v2.multi_viewer import run_multi_camera
from venv_guard import enforce_venv_python


def main() -> int:
    enforce_venv_python()
    camera_ids = [arg for arg in sys.argv[1:] if not arg.startswith("--")]
    root = Path(__file__).resolve().parents[1]
    log_path = Path(os.getenv("IMOU_MULTI_LOG_PATH", str(root / "logs" / "multi_camera_latest.log")))
    window_name = os.getenv("IMOU_MULTI_WINDOW_NAME", "IMOU Multi Camera")
    return run_multi_camera(camera_ids or None, log_path=log_path, window_name=window_name)


if __name__ == "__main__":
    raise SystemExit(main())
