from __future__ import annotations

import time

import cv2

from mtimou_v2.logging_utils import make_logger
from mtimou_v2.models import CameraConfig
from mtimou_v2.registry import target_modes_summary
from mtimou_v2.settings import viewer_runtime_settings
from mtimou_v2.viewer_common import blank_canvas, build_stream_state, overlay_style, reopen_stream


def run_single_camera(camera: CameraConfig, *, log_path, window_name: str) -> int:
    settings = viewer_runtime_settings(log_path=log_path, window_name=window_name)
    log = make_logger(settings.log_path)
    style = overlay_style()

    state = build_stream_state(camera, settings, camera_count=1)
    log(f"[INFO] Camera={camera.camera_id} name={camera.name}")
    log(f"[INFO] Candidate targets: {', '.join(target_modes_summary(camera))}")
    log(f"[INFO] Preferred mode={settings.preferred_mode}")
    log("[INFO] Runtime failover enabled: the viewer will re-evaluate LAN/DDNS/public during reconnects.")
    log(f"[INFO] Mode={state.mode} subtype={state.camera.subtype} Opening direct RTSP: {state.safe_url}")
    log(
        f"[INFO] Health guard: restart if no frame for {settings.restart_idle_sec:.1f}s "
        f"first-frame-timeout={settings.first_frame_timeout_sec:.1f}s"
    )
    if settings.test_seconds > 0:
        log(f"[INFO] Auto-exit test mode after {settings.test_seconds:.1f}s")
    log("[INFO] Press 'q' to exit.")

    cv2.namedWindow(settings.window_name, cv2.WINDOW_NORMAL)
    started = time.monotonic()

    try:
        while True:
            now = time.monotonic()
            if settings.test_seconds > 0 and now - started >= settings.test_seconds:
                log("[INFO] Test duration reached, exiting viewer.")
                break

            if state.cap is None or not state.cap.isOpened():
                reopen_stream(state, settings, log, "capture-not-open", camera_count=1)
                if state.cap is None:
                    canvas = blank_canvas()
                    cv2.putText(canvas, "Reconnect failed. Press q to exit.", (20, 50), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 255), 2, cv2.LINE_AA)
                    cv2.imshow(settings.window_name, canvas)
                    if (cv2.waitKey(max(50, settings.wait_key_ms)) & 0xFF) == ord("q"):
                        break
                    continue

            ok, frame = state.cap.read() if state.cap is not None else (False, None)
            now = time.monotonic()
            if ok and frame is not None:
                state.frame_count += 1
                state.last_ok = now
                elapsed = max(now - state.started, 1e-6)
                fps = state.frame_count / elapsed
                cv2.putText(frame, f"frames={state.frame_count} fps~{fps:.1f}", (16, 28), cv2.FONT_HERSHEY_SIMPLEX, style["meta_scale"], (80, 255, 120), style["meta_thickness"], cv2.LINE_AA)
                cv2.putText(frame, f"reconnects={state.reconnects} failovers={state.failovers}", (16, 52), cv2.FONT_HERSHEY_SIMPLEX, style["small_scale"], (255, 220, 80), style["small_thickness"], cv2.LINE_AA)
                cv2.imshow(settings.window_name, frame)
            else:
                idle = now - state.last_ok
                canvas = blank_canvas()
                cv2.putText(canvas, f"No frame for {idle:.1f}s", (16, 38), cv2.FONT_HERSHEY_SIMPLEX, style["meta_scale"], (0, 0, 255), style["meta_thickness"], cv2.LINE_AA)
                cv2.putText(canvas, f"reconnects={state.reconnects} failovers={state.failovers}", (16, 62), cv2.FONT_HERSHEY_SIMPLEX, style["small_scale"], (255, 220, 80), style["small_thickness"], cv2.LINE_AA)
                cv2.putText(canvas, "Waiting for stream recovery...", (16, 86), cv2.FONT_HERSHEY_SIMPLEX, style["small_scale"], (220, 220, 220), style["small_thickness"], cv2.LINE_AA)
                cv2.imshow(settings.window_name, canvas)
                if idle >= settings.restart_idle_sec:
                    reopen_stream(state, settings, log, f"idle={idle:.1f}s", camera_count=1)

            if (cv2.waitKey(settings.wait_key_ms) & 0xFF) == ord("q"):
                break
    finally:
        if state.cap is not None:
            state.cap.release()
        cv2.destroyAllWindows()
        elapsed = max(time.monotonic() - started, 1e-6)
        avg_fps = state.frame_count / elapsed
        log(
            f"[SUMMARY] mode={state.mode} frames={state.frame_count} avg_fps={avg_fps:.2f} "
            f"reconnects={state.reconnects} failovers={state.failovers} uptime_sec={elapsed:.1f} log={settings.log_path}"
        )

    return 0
