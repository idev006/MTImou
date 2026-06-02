from __future__ import annotations

import time

import cv2

from mtimou_v2.logging_utils import make_logger
from mtimou_v2.registry import enabled_cameras, get_camera
from mtimou_v2.settings import viewer_runtime_settings
from mtimou_v2.viewer_common import (
    CameraReaderWorker,
    blank_tile,
    build_stream_state,
    choose_grid_cols,
    compose_grid,
    overlay_style,
    reopen_stream,
)


def run_multi_camera(camera_ids: list[str] | None, *, log_path, window_name: str) -> int:
    cameras = [get_camera(camera_id) for camera_id in camera_ids] if camera_ids else enabled_cameras()
    if not cameras:
        print("[ERROR] No cameras configured.")
        return 2

    settings = viewer_runtime_settings(log_path=log_path, window_name=window_name)
    log = make_logger(settings.log_path)
    style = overlay_style(single_view=False)
    states = [build_stream_state(camera, settings, camera_count=len(cameras)) for camera in cameras]
    for state in states:
        log(
            f"[INFO] Camera={state.camera.camera_id} mode={state.mode} "
            f"target={state.host}:{state.port} subtype={state.camera.subtype} url={state.safe_url}"
        )
    grid_cols = choose_grid_cols(len(states))
    log(f"[INFO] Grid layout cameras={len(states)} cols={grid_cols}")

    workers = [CameraReaderWorker(state, settings, log, camera_count=len(states)) for state in states]
    for worker in workers:
        worker.start()

    cv2.namedWindow(settings.window_name, cv2.WINDOW_NORMAL)
    started = time.monotonic()

    try:
        while True:
            now = time.monotonic()
            if settings.test_seconds > 0 and now - started >= settings.test_seconds:
                log("[INFO] Test duration reached, exiting multi viewer.")
                break

            tiles = []
            for state in states:
                if not state.camera.password:
                    tile = blank_tile(settings.multi_tile_width, settings.multi_tile_height)
                    cv2.putText(tile, f"{state.camera.camera_id}: missing password", (16, 56), cv2.FONT_HERSHEY_SIMPLEX, style["title_scale"], (0, 0, 255), style["title_thickness"], cv2.LINE_AA)
                    tiles.append(tile)
                    continue

                if state.last_frame is not None:
                    elapsed = max(now - state.started, 1e-6)
                    fps = state.frame_count / elapsed
                    tile = cv2.resize(
                        state.last_frame,
                        (settings.multi_tile_width, settings.multi_tile_height),
                        interpolation=cv2.INTER_LINEAR,
                    )
                    cv2.putText(tile, f"{state.camera.name} [{state.mode}]", (10, 24), cv2.FONT_HERSHEY_SIMPLEX, style["title_scale"], (80, 255, 120), style["title_thickness"], cv2.LINE_AA)
                    cv2.putText(tile, f"frames={state.frame_count} fps~{fps:.1f}", (10, 46), cv2.FONT_HERSHEY_SIMPLEX, style["meta_scale"], (255, 220, 80), style["meta_thickness"], cv2.LINE_AA)
                    cv2.putText(tile, f"reconnects={state.reconnects} failovers={state.failovers}", (10, 66), cv2.FONT_HERSHEY_SIMPLEX, style["meta_scale"], (220, 220, 220), style["meta_thickness"], cv2.LINE_AA)
                else:
                    idle = now - state.last_ok
                    tile = blank_tile(settings.multi_tile_width, settings.multi_tile_height)
                    cv2.putText(tile, f"{state.camera.name} [{state.mode}]", (10, 24), cv2.FONT_HERSHEY_SIMPLEX, style["title_scale"], (80, 255, 120), style["title_thickness"], cv2.LINE_AA)
                    cv2.putText(tile, f"No frame for {idle:.1f}s", (10, 54), cv2.FONT_HERSHEY_SIMPLEX, style["title_scale"], (0, 0, 255), style["title_thickness"], cv2.LINE_AA)
                    cv2.putText(tile, f"reconnects={state.reconnects} failovers={state.failovers}", (10, 76), cv2.FONT_HERSHEY_SIMPLEX, style["meta_scale"], (220, 220, 220), style["meta_thickness"], cv2.LINE_AA)
                    if state.status_text:
                        cv2.putText(tile, f"status={state.status_text}", (10, 98), cv2.FONT_HERSHEY_SIMPLEX, style["small_scale"], (180, 180, 180), style["small_thickness"], cv2.LINE_AA)
                tiles.append(tile)

            grid = compose_grid(tiles, cols=grid_cols)
            cv2.imshow(settings.window_name, grid)
            if (cv2.waitKey(settings.wait_key_ms) & 0xFF) == ord("q"):
                break
    finally:
        for worker in workers:
            worker.stop()
        for worker in workers:
            worker.join(timeout=2.0)
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
