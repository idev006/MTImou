from __future__ import annotations

import math
import os
import sys
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from urllib.parse import quote

import cv2
import numpy as np

from camera_registry import CameraConfig, CameraTarget, enabled_cameras, get_camera, pick_target
from venv_guard import enforce_venv_python


@dataclass(slots=True)
class StreamState:
    camera: CameraConfig
    mode: str
    host: str
    port: int
    url: str
    safe_url: str
    cap: cv2.VideoCapture | None
    frame_count: int = 0
    reconnects: int = 0
    failovers: int = 0
    started: float = 0.0
    last_ok: float = 0.0
    last_frame: np.ndarray | None = None
    next_retry_ts: float = 0.0
    status_text: str = ""
    target_key: tuple[str, str, int] | None = None


def make_logger(log_path: Path):
    log_path.parent.mkdir(parents=True, exist_ok=True)

    def _log(message: str) -> None:
        line = f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} {message}"
        print(message)
        with log_path.open("a", encoding="utf-8") as fh:
            fh.write(line + "\n")

    return _log


def blank_tile(width: int = 640, height: int = 360) -> np.ndarray:
    return np.zeros((height, width, 3), dtype=np.uint8)


def open_capture(url: str, transport: str) -> cv2.VideoCapture:
    os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = f"rtsp_transport;{transport}"
    return cv2.VideoCapture(url, cv2.CAP_FFMPEG)


def build_url(camera: CameraConfig, target: CameraTarget) -> tuple[str, str]:
    safe_password = quote(camera.password, safe="")
    url = (
        f"rtsp://{camera.username}:{safe_password}@{target.host}:{target.port}"
        f"/cam/realmonitor?channel={camera.channel}&subtype={camera.subtype}"
    )
    return url, url.replace(safe_password, "***")


def build_state(camera: CameraConfig, preferred_mode: str, target_probe_timeout_sec: float) -> StreamState:
    target = pick_target(camera, preferred_mode=preferred_mode, timeout_sec=target_probe_timeout_sec)
    url, safe_url = build_url(camera, target)
    cap = open_capture(url, camera.transport) if camera.password else None
    now = time.monotonic()
    return StreamState(
        camera=camera,
        mode=target.mode,
        host=target.host,
        port=target.port,
        url=url,
        safe_url=safe_url,
        cap=cap,
        started=now,
        last_ok=now,
        next_retry_ts=now,
        status_text="starting",
        target_key=(target.mode, target.host, target.port),
    )


def choose_grid_cols(camera_count: int) -> int:
    override = os.getenv("IMOU_MULTI_GRID_COLS", "auto").strip().lower()
    if override and override != "auto":
        try:
            return max(1, int(override))
        except ValueError:
            pass

    if camera_count <= 1:
        return 1
    if camera_count <= 4:
        return 2
    if camera_count <= 9:
        return 3
    return max(1, math.ceil(math.sqrt(camera_count)))


def compose_grid(frames: list[np.ndarray], cols: int = 2) -> np.ndarray:
    rows = math.ceil(len(frames) / cols)
    height = max(frame.shape[0] for frame in frames)
    width = max(frame.shape[1] for frame in frames)
    tiles: list[np.ndarray] = []
    for frame in frames:
        if frame.shape[:2] != (height, width):
            frame = cv2.resize(frame, (width, height), interpolation=cv2.INTER_AREA)
        tiles.append(frame)
    while len(tiles) < rows * cols:
        tiles.append(blank_tile(width, height))
    row_imgs = []
    for row in range(rows):
        row_imgs.append(np.hstack(tiles[row * cols : (row + 1) * cols]))
    return np.vstack(row_imgs)


def overlay_style() -> dict[str, float | int]:
    return {
        "title_scale": float(os.getenv("IMOU_OVERLAY_TITLE_SCALE", "0.62")),
        "meta_scale": float(os.getenv("IMOU_OVERLAY_META_SCALE", "0.54")),
        "small_scale": float(os.getenv("IMOU_OVERLAY_SMALL_SCALE", "0.50")),
        "title_thickness": int(os.getenv("IMOU_OVERLAY_TITLE_THICKNESS", "2")),
        "meta_thickness": int(os.getenv("IMOU_OVERLAY_META_THICKNESS", "1")),
        "small_thickness": int(os.getenv("IMOU_OVERLAY_SMALL_THICKNESS", "1")),
    }


def main() -> int:
    enforce_venv_python()
    args = sys.argv[1:]
    camera_ids = [arg for arg in args if not arg.startswith("--")]
    test_seconds = float(os.getenv("IMOU_DIRECT_TEST_SECONDS", "0") or "0")
    restart_idle_sec = float(os.getenv("IMOU_DIRECT_NO_FRAME_RESTART_SEC", "8"))
    reconnect_sleep_sec = float(os.getenv("IMOU_DIRECT_RECONNECT_SLEEP_SEC", "1.5"))
    first_frame_timeout_sec = float(os.getenv("IMOU_DIRECT_FIRST_FRAME_TIMEOUT_SEC", "6"))
    target_probe_timeout_sec = float(os.getenv("IMOU_TARGET_PROBE_TIMEOUT_SEC", "1.2"))
    preferred_mode = os.getenv("IMOU_TARGET_MODE", "auto").strip().lower()
    log_path = Path(os.getenv("IMOU_MULTI_LOG_PATH", str(Path(__file__).resolve().parents[1] / "logs" / "multi_camera_latest.log")))
    log = make_logger(log_path)

    cameras: list[CameraConfig]
    if camera_ids:
        cameras = [get_camera(camera_id) for camera_id in camera_ids]
    else:
        cameras = enabled_cameras()
    if not cameras:
        print("[ERROR] No cameras configured.")
        return 2

    states = [build_state(camera, preferred_mode=preferred_mode, target_probe_timeout_sec=target_probe_timeout_sec) for camera in cameras]
    style = overlay_style()
    for state in states:
        log(f"[INFO] Camera={state.camera.camera_id} mode={state.mode} target={state.host}:{state.port} url={state.safe_url}")
    grid_cols = choose_grid_cols(len(states))
    log(f"[INFO] Grid layout cameras={len(states)} cols={grid_cols}")

    window_name = os.getenv("IMOU_MULTI_WINDOW_NAME", "IMOU Multi Camera")
    cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
    started = time.monotonic()

    def reopen(state: StreamState, reason: str) -> None:
        state.reconnects += 1
        log(f"[WARN] Reopening {state.camera.camera_id} ({reason}) attempt #{state.reconnects}")
        if state.cap is not None:
            state.cap.release()

        try:
            target = pick_target(state.camera, preferred_mode=preferred_mode, timeout_sec=target_probe_timeout_sec)
        except RuntimeError as exc:
            state.cap = None
            state.status_text = str(exc)
            state.next_retry_ts = time.monotonic() + reconnect_sleep_sec
            log(f"[WARN] Reopen target resolve failed: {state.camera.camera_id} {exc}")
            return

        target_key = (target.mode, target.host, target.port)
        if state.target_key is not None and state.target_key != target_key:
            state.failovers += 1
            log(
                f"[WARN] Target failover camera={state.camera.camera_id} "
                f"from={state.target_key[0]}:{state.target_key[1]}:{state.target_key[2]} "
                f"to={target.mode}:{target.host}:{target.port}"
            )
        state.target_key = target_key
        state.mode = target.mode
        state.host = target.host
        state.port = target.port
        state.url, state.safe_url = build_url(state.camera, target)

        state.cap = open_capture(state.url, state.camera.transport) if state.camera.password else None
        state.next_retry_ts = time.monotonic() + reconnect_sleep_sec
        if state.cap is None or not state.cap.isOpened():
            state.status_text = "open failed"
            log(f"[WARN] Reopen failed: {state.camera.camera_id}")
            return
        state.status_text = "reconnected"
        log(f"[INFO] Reopen opened capture: {state.camera.camera_id} mode={state.mode} target={state.host}:{state.port}")

    try:
        while True:
            now = time.monotonic()
            if test_seconds > 0 and now - started >= test_seconds:
                log("[INFO] Test duration reached, exiting multi viewer.")
                break

            tiles: list[np.ndarray] = []
            for state in states:
                if not state.camera.password:
                    tile = blank_tile()
                    cv2.putText(tile, f"{state.camera.camera_id}: missing password", (16, 56), cv2.FONT_HERSHEY_SIMPLEX, style["title_scale"], (0, 0, 255), style["title_thickness"], cv2.LINE_AA)
                    tiles.append(tile)
                    continue

                if (state.cap is None or not state.cap.isOpened()) and now >= state.next_retry_ts:
                    reopen(state, "capture-not-open")

                ok = False
                frame = None
                if state.cap is not None and state.cap.isOpened():
                    ok, frame = state.cap.read()
                now = time.monotonic()
                if ok and frame is not None:
                    state.frame_count += 1
                    state.last_ok = now
                    state.last_frame = frame
                    state.status_text = "ok"
                    elapsed = max(now - state.started, 1e-6)
                    fps = state.frame_count / elapsed
                    tile = cv2.resize(frame, (640, 360), interpolation=cv2.INTER_AREA)
                    cv2.putText(tile, f"{state.camera.name} [{state.mode}]", (10, 24), cv2.FONT_HERSHEY_SIMPLEX, style["title_scale"], (80, 255, 120), style["title_thickness"], cv2.LINE_AA)
                    cv2.putText(tile, f"frames={state.frame_count} fps~{fps:.1f}", (10, 46), cv2.FONT_HERSHEY_SIMPLEX, style["meta_scale"], (255, 220, 80), style["meta_thickness"], cv2.LINE_AA)
                    cv2.putText(tile, f"reconnects={state.reconnects} failovers={state.failovers}", (10, 66), cv2.FONT_HERSHEY_SIMPLEX, style["meta_scale"], (220, 220, 220), style["meta_thickness"], cv2.LINE_AA)
                else:
                    idle = now - state.last_ok
                    tile = blank_tile()
                    cv2.putText(tile, f"{state.camera.name} [{state.mode}]", (10, 24), cv2.FONT_HERSHEY_SIMPLEX, style["title_scale"], (80, 255, 120), style["title_thickness"], cv2.LINE_AA)
                    cv2.putText(tile, f"No frame for {idle:.1f}s", (10, 54), cv2.FONT_HERSHEY_SIMPLEX, style["title_scale"], (0, 0, 255), style["title_thickness"], cv2.LINE_AA)
                    cv2.putText(tile, f"reconnects={state.reconnects} failovers={state.failovers}", (10, 76), cv2.FONT_HERSHEY_SIMPLEX, style["meta_scale"], (220, 220, 220), style["meta_thickness"], cv2.LINE_AA)
                    if state.status_text:
                        cv2.putText(tile, f"status={state.status_text}", (10, 98), cv2.FONT_HERSHEY_SIMPLEX, style["small_scale"], (180, 180, 180), style["small_thickness"], cv2.LINE_AA)
                    if idle >= restart_idle_sec and now >= state.next_retry_ts:
                        state.status_text = f"idle {idle:.1f}s"
                        reopen(state, f"idle={idle:.1f}s")
                tiles.append(tile)

            grid = compose_grid(tiles, cols=grid_cols)
            cv2.imshow(window_name, grid)
            if (cv2.waitKey(20) & 0xFF) == ord("q"):
                break
    finally:
        for state in states:
            if state.cap is not None:
                state.cap.release()
        cv2.destroyAllWindows()
        for state in states:
            elapsed = max(time.monotonic() - state.started, 1e-6)
            avg_fps = state.frame_count / elapsed
            log(
                f"[SUMMARY] camera={state.camera.camera_id} mode={state.mode} "
                f"frames={state.frame_count} avg_fps={avg_fps:.2f} reconnects={state.reconnects} "
                f"failovers={state.failovers} uptime_sec={elapsed:.1f}"
            )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
