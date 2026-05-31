from __future__ import annotations

import os
import time

import cv2


def first_env(*names: str, default: str = "") -> str:
    for name in names:
        value = os.getenv(name, "").strip()
        if value:
            return value
    return default


def main() -> int:
    ip = first_env("IMOU_CAMERA_IP")
    user = first_env("IMOU_CAMERA_USERNAME", default="admin")
    pwd = first_env("IMOU_CAMERA_PASSWORD")
    port = first_env("IMOU_CAMERA_RTSP_PORT", default="554")
    channel = first_env("IMOU_RTSP_CHANNEL", default="1")
    subtype = first_env("IMOU_RTSP_SUBTYPE", default="0")
    target_frames = int(first_env("IMOU_RECEIVER_TARGET_FRAMES", default="60"))

    if not ip:
        print("Missing IMOU_CAMERA_IP")
        return 2
    if not pwd:
        print("Missing IMOU_CAMERA_PASSWORD")
        return 2

    url = (
        f"rtsp://{user}:{pwd}@{ip}:{port}/cam/realmonitor?"
        f"channel={channel}&subtype={subtype}"
    )
    print("[INFO] Opening:", url.replace(pwd, "***"))

    os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "rtsp_transport;tcp"
    cap = cv2.VideoCapture(url, cv2.CAP_FFMPEG)
    if not cap.isOpened():
        print("[ERROR] Cannot open RTSP stream")
        return 1

    frames = 0
    start = time.time()
    while frames < target_frames:
        ok, _frame = cap.read()
        if not ok:
            print("[WARN] Frame read failed")
            time.sleep(0.1)
            continue
        frames += 1

    elapsed = max(time.time() - start, 0.001)
    fps = frames / elapsed
    print(f"[SUCCESS] Received {frames} frames in {elapsed:.2f}s ({fps:.2f} fps)")
    cap.release()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
