from __future__ import annotations

import os
import time

import cv2


def main() -> int:
    ip = os.getenv("IMOU_CAMERA_IP", "").strip()
    user = os.getenv("IMOU_CAMERA_USERNAME", "admin").strip()
    pwd = os.getenv("IMOU_CAMERA_PASSWORD", "").strip()
    port = os.getenv("IMOU_CAMERA_RTSP_PORT", "554").strip()

    if not ip:
        print("Missing IMOU_CAMERA_IP")
        return 2
    if not pwd:
        print("Missing IMOU_CAMERA_PASSWORD")
        return 2

    os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "rtsp_transport;tcp"
    urls = [
        f"rtsp://{user}:{pwd}@{ip}:{port}/cam/realmonitor?channel=1&subtype=0",
        f"rtsp://{user}:{pwd}@{ip}:{port}/cam/realmonitor?channel=1&subtype=1",
        f"rtsp://{user}:{pwd}@{ip}:{port}/cam/realmonitor?channel=1&subtype=0&unicast=true&proto=Onvif",
    ]

    for url in urls:
        safe = url.replace(pwd, "***")
        print("[INFO] TRY", safe)
        cap = cv2.VideoCapture(url, cv2.CAP_FFMPEG)
        if not cap.isOpened():
            cap.release()
            continue

        count = 0
        start = time.time()
        while time.time() - start < 20:
            ok, _frame = cap.read()
            if ok:
                count += 1
                if count >= 3:
                    print("[SUCCESS] LAN RTSP works:", safe)
                    cap.release()
                    return 0
            time.sleep(0.2)

        cap.release()

    print("[ERROR] LAN RTSP failed for tested URLs")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())

