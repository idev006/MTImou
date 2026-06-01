from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from urllib.parse import quote

from venv_guard import enforce_venv_python


def main() -> int:
    enforce_venv_python()

    host = os.getenv("IMOU_PUBLIC_RTSP_HOST", "").strip()
    port = os.getenv("IMOU_PUBLIC_RTSP_PORT", "45554").strip()
    user = os.getenv("IMOU_CAMERA_USERNAME", "admin").strip()
    password = os.getenv("IMOU_CAMERA_PASSWORD", "").strip()
    channel = os.getenv("IMOU_PUBLIC_RTSP_CHANNEL", "1").strip()
    subtype = os.getenv("IMOU_PUBLIC_RTSP_SUBTYPE", "0").strip()
    ffmpeg_bin_dir = os.getenv("FFMPEG_BIN_DIR", r"F:\ffmpeg\bin").strip()
    autoexit_sec = os.getenv("IMOU_DIRECT_TEST_SECONDS", "").strip()

    if not host:
        print("Missing IMOU_PUBLIC_RTSP_HOST")
        return 2
    if not password:
        print("Missing IMOU_CAMERA_PASSWORD")
        return 2

    ffplay = Path(ffmpeg_bin_dir) / "ffplay.exe"
    if not ffplay.exists():
        print(f"Missing ffplay: {ffplay}")
        return 2

    safe_password = quote(password, safe="")
    url = (
        f"rtsp://{user}:{safe_password}@{host}:{port}"
        f"/cam/realmonitor?channel={channel}&subtype={subtype}"
    )
    safe_url = url.replace(safe_password, "***")

    cmd = [
        str(ffplay),
        "-rtsp_transport",
        "tcp",
        "-fflags",
        "nobuffer",
        "-flags",
        "low_delay",
        "-analyzeduration",
        "2000000",
        "-probesize",
        "1000000",
    ]
    if autoexit_sec:
        cmd.extend(["-t", autoexit_sec, "-autoexit"])
    cmd.append(url)

    print(f"[INFO] Runtime python: {sys.executable}")
    print(f"[INFO] Opening direct public RTSP: {safe_url}")
    print(f"[INFO] ffplay path: {ffplay}")
    subprocess.run(cmd, check=False)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
