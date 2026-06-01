from __future__ import annotations

import os
import sys
import time
from pathlib import Path
from urllib.parse import quote

import cv2

from venv_guard import enforce_venv_python


def main() -> int:
    enforce_venv_python()

    host = os.getenv("IMOU_PUBLIC_RTSP_HOST", "").strip()
    port = os.getenv("IMOU_PUBLIC_RTSP_PORT", "45554").strip()
    user = os.getenv("IMOU_CAMERA_USERNAME", "admin").strip()
    password = os.getenv("IMOU_CAMERA_PASSWORD", "").strip()
    channel = os.getenv("IMOU_PUBLIC_RTSP_CHANNEL", "1").strip()
    subtype = os.getenv("IMOU_PUBLIC_RTSP_SUBTYPE", "0").strip()
    transport = os.getenv("IMOU_DIRECT_RTSP_TRANSPORT", "tcp").strip().lower()
    window_name = os.getenv("IMOU_DIRECT_WINDOW_NAME", "IMOU Direct Public RTSP").strip()

    if not host:
        print("Missing IMOU_PUBLIC_RTSP_HOST")
        return 2
    if not password:
        print("Missing IMOU_CAMERA_PASSWORD")
        return 2

    safe_password = quote(password, safe="")
    url = (
        f"rtsp://{user}:{safe_password}@{host}:{port}"
        f"/cam/realmonitor?channel={channel}&subtype={subtype}"
    )
    safe_url = url.replace(safe_password, "***")

    os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = f"rtsp_transport;{transport}"
    cap = cv2.VideoCapture(url, cv2.CAP_FFMPEG)
    if not cap.isOpened():
        print(f"[ERROR] Failed to open stream: {safe_url}")
        return 1

    print(f"[INFO] Runtime python: {sys.executable}")
    print(f"[INFO] Opening direct public RTSP: {safe_url}")
    print("[INFO] Press 'q' to exit.")

    cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
    frame_count = 0
    started = time.monotonic()
    last_ok = started

    try:
        while True:
            ok, frame = cap.read()
            now = time.monotonic()
            if ok and frame is not None:
                frame_count += 1
                last_ok = now
                elapsed = max(now - started, 1e-6)
                fps = frame_count / elapsed
                cv2.putText(
                    frame,
                    f"frames={frame_count} fps~{fps:.1f}",
                    (20, 35),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.9,
                    (80, 255, 120),
                    2,
                    cv2.LINE_AA,
                )
                cv2.imshow(window_name, frame)
            else:
                idle = now - last_ok
                canvas = cv2.imread(str(Path(__file__).resolve().parents[1] / "image.png"))
                if canvas is None:
                    canvas = 255 * (cv2.UMat(720, 1280, cv2.CV_8UC3).get())
                cv2.putText(
                    canvas,
                    f"No frame for {idle:.1f}s",
                    (20, 50),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    1.0,
                    (0, 0, 255),
                    2,
                    cv2.LINE_AA,
                )
                cv2.imshow(window_name, canvas)

            if (cv2.waitKey(20) & 0xFF) == ord("q"):
                break
    finally:
        cap.release()
        cv2.destroyAllWindows()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
