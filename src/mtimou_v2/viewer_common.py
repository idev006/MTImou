from __future__ import annotations

from dataclasses import replace
import math
import threading
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


def overlay_style(*, single_view: bool = False) -> dict[str, float | int]:
    import os

    prefix = "IMOU_SINGLE_OVERLAY_" if single_view else "IMOU_MULTI_OVERLAY_"
    default_title_scale = "0.92" if single_view else "0.62"
    default_meta_scale = "0.82" if single_view else "0.54"
    default_small_scale = "0.72" if single_view else "0.50"
    default_title_thickness = "2"
    default_meta_thickness = "2" if single_view else "1"
    default_small_thickness = "2" if single_view else "1"

    def env_value(name: str, default: str) -> str:
        return os.getenv(f"{prefix}{name}", os.getenv(f"IMOU_OVERLAY_{name}", default))

    return {
        "title_scale": float(env_value("TITLE_SCALE", default_title_scale)),
        "meta_scale": float(env_value("META_SCALE", default_meta_scale)),
        "small_scale": float(env_value("SMALL_SCALE", default_small_scale)),
        "title_thickness": int(env_value("TITLE_THICKNESS", default_title_thickness)),
        "meta_thickness": int(env_value("META_THICKNESS", default_meta_thickness)),
        "small_thickness": int(env_value("SMALL_THICKNESS", default_small_thickness)),
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


class CameraReaderWorker(threading.Thread):
    def __init__(self, state, settings, log, *, camera_count: int) -> None:
        super().__init__(daemon=True)
        self.state = state
        self.settings = settings
        self.log = log
        self.camera_count = camera_count
        self.stop_event = threading.Event()

    def run(self) -> None:
        state = self.state
        while not self.stop_event.is_set():
            now = time.monotonic()
            if not state.camera.password:
                state.status_text = "missing password"
                time.sleep(0.2)
                continue

            if (state.cap is None or not state.cap.isOpened()) and now >= state.next_retry_ts:
                reopen_stream(state, self.settings, self.log, "capture-not-open", camera_count=self.camera_count)
                if state.cap is None or not state.cap.isOpened():
                    time.sleep(0.05)
                    continue

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
                continue

            idle = now - state.last_ok
            if idle >= self.settings.restart_idle_sec and now >= state.next_retry_ts:
                state.status_text = f"idle {idle:.1f}s"
                reopen_stream(state, self.settings, self.log, f"idle={idle:.1f}s", camera_count=self.camera_count)
            else:
                state.status_text = f"waiting {idle:.1f}s"
                time.sleep(0.01)

        if state.cap is not None:
            state.cap.release()

    def stop(self) -> None:
        self.stop_event.set()


def effective_camera_profile(
    camera: CameraConfig,
    *,
    target_mode: str,
    camera_count: int,
    settings: ViewerRuntimeSettings,
) -> CameraConfig:
    subtype = camera.subtype
    if target_mode in {"ddns", "public"}:
        if camera_count > 1:
            subtype = camera.remote_wall_subtype or settings.remote_multi_subtype or subtype
        else:
            subtype = camera.remote_focus_subtype or settings.remote_single_subtype or subtype
    if subtype == camera.subtype:
        return camera
    return replace(camera, subtype=subtype)


def build_stream_state(camera: CameraConfig, settings: ViewerRuntimeSettings, *, camera_count: int = 1) -> StreamState:
    target = pick_target(camera, preferred_mode=settings.preferred_mode, timeout_sec=settings.target_probe_timeout_sec)
    runtime_camera = effective_camera_profile(camera, target_mode=target.mode, camera_count=camera_count, settings=settings)
    url, safe_url = build_rtsp_url(runtime_camera, target)
    cap = open_capture(url, runtime_camera.transport) if runtime_camera.password else None
    now = time.monotonic()
    return StreamState(
        camera=runtime_camera,
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
    *,
    camera_count: int = 1,
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
    runtime_camera = effective_camera_profile(state.camera, target_mode=target.mode, camera_count=camera_count, settings=settings)
    state.camera = runtime_camera
    state.url, state.safe_url = build_rtsp_url(runtime_camera, target)

    state.cap = open_capture(state.url, runtime_camera.transport) if runtime_camera.password else None
    state.next_retry_ts = time.monotonic() + settings.reconnect_sleep_sec
    if state.cap is None or not state.cap.isOpened():
        state.status_text = "open failed"
        log(f"[WARN] Reopen failed: {state.camera.camera_id}")
        return
    state.status_text = f"reconnected subtype={runtime_camera.subtype}"
    log(
        f"[INFO] Reopen opened capture: {state.camera.camera_id} "
        f"mode={state.mode} target={state.host}:{state.port} subtype={runtime_camera.subtype}"
    )
