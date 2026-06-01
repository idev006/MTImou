from __future__ import annotations

import subprocess
import sys
from pathlib import Path

THIS_DIR = Path(__file__).resolve().parent
if str(THIS_DIR) not in sys.path:
    sys.path.insert(0, str(THIS_DIR))

from mtimou_v2.registry import enabled_cameras
from venv_guard import enforce_venv_python


CREATE_NEW_CONSOLE = getattr(subprocess, "CREATE_NEW_CONSOLE", 0)
ROOT_DIR = Path(__file__).resolve().parents[1]


def main() -> int:
    enforce_venv_python()
    camera_ids = [arg.strip() for arg in sys.argv[1:] if arg.strip()]
    if not camera_ids:
        camera_ids = [camera.camera_id for camera in enabled_cameras()]
    if not camera_ids:
        print("[ERROR] No cameras configured.")
        return 2

    for camera_id in camera_ids:
        subprocess.Popen(
            ["cmd.exe", "/c", str(ROOT_DIR / "run_camera_stable.bat"), camera_id],
            cwd=str(ROOT_DIR),
            creationflags=CREATE_NEW_CONSOLE,
        )
        print(f"[INFO] Launched split-view camera {camera_id}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
