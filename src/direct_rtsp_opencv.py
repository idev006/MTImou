from __future__ import annotations

import os
import sys
import time
from pathlib import Path
from urllib.parse import quote
from datetime import datetime

import cv2
import numpy as np

from venv_guard import enforce_venv_python


def blank_canvas() -> np.ndarray:
    return np.zeros((720, 1280, 3), dtype=np.uint8)


def open_capture(url: str, transport: str) -> cv2.VideoCapture:
    os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = f"rtsp_transport;{transport}"
    return cv2.VideoCapture(url, cv2.CAP_FFMPEG)


def make_logger(log_path: Path):
    log_path.parent.mkdir(parents=True, exist_ok=True)

    def _log(message: str) -> None:
        line = f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} {message}"
        print(message)
        with log_path.open("a", encoding="utf-8") as fh:
            fh.write(line + "\n")

    return _log


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
    restart_idle_sec = float(os.getenv("IMOU_DIRECT_NO_FRAME_RESTART_SEC", "8"))
    reconnect_sleep_sec = float(os.getenv("IMOU_DIRECT_RECONNECT_SLEEP_SEC", "1.5"))
    first_frame_timeout_sec = float(os.getenv("IMOU_DIRECT_FIRST_FRAME_TIMEOUT_SEC", "6"))
    test_seconds = float(os.getenv("IMOU_DIRECT_TEST_SECONDS", "0") or "0")
    mode_label = os.getenv("IMOU_DIRECT_MODE_LABEL", "public").strip()
    log_path = Path(
        os.getenv(
            "IMOU_DIRECT_LOG_PATH",
            str(Path(__file__).resolve().parents[1] / "logs" / "direct_public_latest.log"),
        )
    )
    log = make_logger(log_path)

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

    log(f"[INFO] Runtime python: {sys.executable}")
    log(f"[INFO] Mode={mode_label} Opening direct RTSP: {safe_url}")
    log(
        f"[INFO] Health guard: restart if no frame for {restart_idle_sec:.1f}s "
        f"first-frame-timeout={first_frame_timeout_sec:.1f}s"
    )
    if test_seconds > 0:
        log(f"[INFO] Auto-exit test mode after {test_seconds:.1f}s")
    log("[INFO] Press 'q' to exit.")

    cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
    frame_count = 0
    started = time.monotonic()
    last_ok = started
    reconnects = 0
    cap: cv2.VideoCapture | None = None

    def reopen(reason: str) -> cv2.VideoCapture | None:
        nonlocal reconnects, last_ok
        reconnects += 1
        log(f"[WARN] Reopening stream ({reason}) attempt #{reconnects}")
        if cap is not None:
            cap.release()
        time.sleep(reconnect_sleep_sec)
        new_cap = open_capture(url, transport)
        if not new_cap.isOpened():
            log(f"[WARN] Reopen failed: {safe_url}")
            return None
        probe_start = time.monotonic()
        while time.monotonic() - probe_start < first_frame_timeout_sec:
            ok, frame = new_cap.read()
            if ok and frame is not None:
                last_ok = time.monotonic()
                log("[INFO] Reopen success.")
                return new_cap
            if (cv2.waitKey(20) & 0xFF) == ord("q"):
                new_cap.release()
                return None
        log("[WARN] Reopen got no first frame in time.")
        new_cap.release()
        return None

    cap = open_capture(url, transport)
    if not cap.isOpened():
        log(f"[ERROR] Failed to open stream: {safe_url}")
        return 1

    try:
        while True:
            now = time.monotonic()
            if test_seconds > 0 and now - started >= test_seconds:
                log("[INFO] Test duration reached, exiting viewer.")
                break
            if cap is None or not cap.isOpened():
                cap = reopen("capture-not-open")
                if cap is None:
                    canvas = blank_canvas()
                    cv2.putText(
                        canvas,
                        "Reconnect failed. Press q to exit.",
                        (20, 50),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        1.0,
                        (0, 0, 255),
                        2,
                        cv2.LINE_AA,
                    )
                    cv2.imshow(window_name, canvas)
                    if (cv2.waitKey(250) & 0xFF) == ord("q"):
                        break
                    continue

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
                cv2.putText(
                    frame,
                    f"reconnects={reconnects}",
                    (20, 70),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.8,
                    (255, 220, 80),
                    2,
                    cv2.LINE_AA,
                )
                cv2.imshow(window_name, frame)
            else:
                idle = now - last_ok
                canvas = blank_canvas()
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
                cv2.putText(
                    canvas,
                    f"reconnects={reconnects}",
                    (20, 90),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.9,
                    (255, 220, 80),
                    2,
                    cv2.LINE_AA,
                )
                cv2.putText(
                    canvas,
                    "Waiting for stream recovery...",
                    (20, 130),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.9,
                    (220, 220, 220),
                    2,
                    cv2.LINE_AA,
                )
                cv2.imshow(window_name, canvas)
                if idle >= restart_idle_sec:
                    cap = reopen(f"idle={idle:.1f}s")

            if (cv2.waitKey(20) & 0xFF) == ord("q"):
                break
    finally:
        if cap is not None:
            cap.release()
        cv2.destroyAllWindows()
        elapsed = max(time.monotonic() - started, 1e-6)
        avg_fps = frame_count / elapsed
        log(
            f"[SUMMARY] mode={mode_label} frames={frame_count} avg_fps={avg_fps:.2f} "
            f"reconnects={reconnects} uptime_sec={elapsed:.1f} log={log_path}"
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
