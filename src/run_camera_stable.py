from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from camera_registry import get_camera, pick_target, target_modes_summary
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
    target = pick_target(camera, preferred_mode=preferred_mode)
    root = Path(__file__).resolve().parents[1]
    log_name = f"direct_{camera.camera_id}_{target.mode}_latest.log"
    env = os.environ.copy()
    env["IMOU_PUBLIC_RTSP_HOST"] = target.host
    env["IMOU_PUBLIC_RTSP_PORT"] = str(target.port)
    env["IMOU_PUBLIC_RTSP_CHANNEL"] = camera.channel
    env["IMOU_PUBLIC_RTSP_SUBTYPE"] = camera.subtype
    env["IMOU_DIRECT_RTSP_TRANSPORT"] = camera.transport
    env["IMOU_DIRECT_MODE_LABEL"] = f"{camera.camera_id}:{target.mode}"
    env["IMOU_DIRECT_WINDOW_NAME"] = f"{camera.name} ({target.mode.upper()})"
    env["IMOU_DIRECT_LOG_PATH"] = str(root / "logs" / log_name)
    env["IMOU_CAMERA_USERNAME"] = camera.username
    env["IMOU_CAMERA_PASSWORD"] = camera.password

    print(f"[INFO] Camera={camera.camera_id} name={camera.name}")
    print(f"[INFO] Candidate targets: {', '.join(target_modes_summary(camera))}")
    print(f"[INFO] Preferred mode={preferred_mode}")
    print(f"[INFO] Selected mode={target.mode} target={target.host}:{target.port}")
    viewer = root / "src" / "direct_rtsp_opencv.py"
    result = subprocess.run([sys.executable, str(viewer)], env=env, check=False)
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
