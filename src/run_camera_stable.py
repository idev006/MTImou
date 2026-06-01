from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from camera_registry import get_camera, target_modes_summary
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

    preferred_mode = os.getenv("IMOU_TARGET_MODE", "auto").strip().lower()
    root = Path(__file__).resolve().parents[1]
    log_name = f"direct_{camera.camera_id}_latest.log"
    env = os.environ.copy()
    env["IMOU_CAMERA_ID"] = camera.camera_id
    env["IMOU_DIRECT_WINDOW_NAME"] = camera.name
    env["IMOU_DIRECT_LOG_PATH"] = str(root / "logs" / log_name)

    print(f"[INFO] Camera={camera.camera_id} name={camera.name}")
    print(f"[INFO] Candidate targets: {', '.join(target_modes_summary(camera))}")
    print(f"[INFO] Preferred mode={preferred_mode}")
    print("[INFO] Runtime failover enabled: the viewer will re-evaluate LAN/DDNS/public during reconnects.")
    viewer = root / "src" / "direct_rtsp_opencv.py"
    result = subprocess.run([sys.executable, str(viewer)], env=env, check=False)
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
