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
    camera_id = os.getenv("IMOU_CAMERA_ID", "").strip()
    if camera_id:
        camera = get_camera(camera_id)
        root = Path(__file__).resolve().parents[1]
        log_path = Path(os.getenv("IMOU_DIRECT_LOG_PATH", str(root / "logs" / f"direct_{camera.camera_id}_latest.log")))
        window_name = os.getenv("IMOU_DIRECT_WINDOW_NAME", camera.name).strip() or camera.name
        return run_single_camera(camera, log_path=log_path, window_name=window_name)

    print("[ERROR] direct_rtsp_opencv.py now expects IMOU_CAMERA_ID for production use.")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
