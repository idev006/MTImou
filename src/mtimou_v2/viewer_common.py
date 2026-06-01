from __future__ import annotations

import math
import time

import cv2
import numpy as np

from mtimou_v2.models import CameraConfig, CameraTarget, StreamState, ViewerRuntimeSettings
from mtimou_v2.rtsp import build_rtsp_url, open_capture
from mtimou_v2.targets import pick_target


def blank_tile(width: int = 640, height: int = 360) -> np.ndarray:
    return np.zeros((height, width, 3), dtype=np.uint8)


def blank_canvas() -> np.ndarray:
    return np.zeros((720, 1280, 3), dtype=np.uint8)


def overlay_style() -> dict[str, float | int]:
    import os

    return {
        "title_scale": float(os.getenv("IMOU_OVERLAY_TITLE_SCALE", "0.62")),
        "meta_scale": float(os.getenv("IMOU_OVERLAY_META_SCALE", "0.54")),
        "small_scale": float(os.getenv("IMOU_OVERLAY_SMALL_SCALE", "0.50")),
        "title_thickness": int(os.getenv("IMOU_OVERLAY_TITLE_THICKNESS", "2")),
        "meta_thickness": int(os.getenv("IMOU_OVERLAY_META_THICKNESS", "1")),
        "small_thickness": int(os.getenv("IMOU_OVERLAY_SMALL_THICKNESS", "1")),
    }


def choose_grid_cols(camera_count: int) -> int:
    import os

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


def build_stream_state(camera: CameraConfig, settings: ViewerRuntimeSettings) -> StreamState:
    target = pick_target(camera, preferred_mode=settings.preferred_mode, timeout_sec=settings.target_probe_timeout_sec)
    url, safe_url = build_rtsp_url(camera, target)
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


def reopen_stream(
    state: StreamState,
    settings: ViewerRuntimeSettings,
    log,
    reason: str,
) -> None:
    state.reconnects += 1
    log(f"[WARN] Reopening {state.camera.camera_id} ({reason}) attempt #{state.reconnects}")
    if state.cap is not None:
        state.cap.release()

    try:
        target = pick_target(
            state.camera,
            preferred_mode=settings.preferred_mode,
            timeout_sec=settings.target_probe_timeout_sec,
        )
    except RuntimeError as exc:
        state.cap = None
        state.status_text = str(exc)
        state.next_retry_ts = time.monotonic() + settings.reconnect_sleep_sec
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
    state.url, state.safe_url = build_rtsp_url(state.camera, target)

    state.cap = open_capture(state.url, state.camera.transport) if state.camera.password else None
    state.next_retry_ts = time.monotonic() + settings.reconnect_sleep_sec
    if state.cap is None or not state.cap.isOpened():
        state.status_text = "open failed"
        log(f"[WARN] Reopen failed: {state.camera.camera_id}")
        return
    state.status_text = "reconnected"
    log(f"[INFO] Reopen opened capture: {state.camera.camera_id} mode={state.mode} target={state.host}:{state.port}")

