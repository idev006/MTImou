from __future__ import annotations

import os
import sys
from pathlib import Path

THIS_DIR = Path(__file__).resolve().parent
if str(THIS_DIR) not in sys.path:
    sys.path.insert(0, str(THIS_DIR))

from mtimou_v2.registry import get_camera
from mtimou_v2.single_viewer import run_single_camera
from venv_guard import enforce_venv_python


def main() -> int:
    enforce_venv_python()
    if len(sys.argv) < 2:
        print("Usage: run_camera_stable.py <camera-id>")
        return 2

    camera_id = sys.argv[1].strip()
    camera = get_camera(camera_id)
    if not camera.password:
        print(f"[ERROR] Missing password for {camera.camera_id}.")
        return 2

    root = Path(__file__).resolve().parents[1]
    log_path = root / "logs" / f"direct_{camera.camera_id}_latest.log"
    window_name = os.getenv("IMOU_DIRECT_WINDOW_NAME", camera.name).strip() or camera.name
    return run_single_camera(camera, log_path=log_path, window_name=window_name)


if __name__ == "__main__":
    raise SystemExit(main())
