from __future__ import annotations

from urllib.parse import quote

import cv2

from mtimou_v2.models import CameraConfig, CameraTarget


def open_capture(url: str, transport: str) -> cv2.VideoCapture:
    import os

    os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = f"rtsp_transport;{transport}|fflags;nobuffer|flags;low_delay"
    cap = cv2.VideoCapture(url, cv2.CAP_FFMPEG)
    try:
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
    except Exception:
        pass
    return cap


def build_rtsp_url(camera: CameraConfig, target: CameraTarget) -> tuple[str, str]:
    safe_password = quote(camera.password, safe="")
    url = (
        f"rtsp://{camera.username}:{safe_password}@{target.host}:{target.port}"
        f"/cam/realmonitor?channel={camera.channel}&subtype={camera.subtype}"
    )
    return url, url.replace(safe_password, "***")
