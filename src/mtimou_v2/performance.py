from __future__ import annotations

import time
from dataclasses import replace
from pathlib import Path

from mtimou_v2.logging_utils import make_logger
from mtimou_v2.registry import enabled_cameras, get_camera
from mtimou_v2.settings import viewer_runtime_settings
from mtimou_v2.viewer_common import CameraReaderWorker, build_stream_state


def run_performance_benchmark(
    *,
    camera_ids: list[str] | None,
    mode: str,
    duration_sec: float,
    warmup_sec: float,
    min_fps: float,
    log_path: Path,
) -> int:
    cameras = [get_camera(camera_id) for camera_id in camera_ids] if camera_ids else enabled_cameras()
    if not cameras:
        print("[ERROR] No cameras configured.")
        return 2

    settings = viewer_runtime_settings(log_path=log_path, window_name="MTImou Performance Benchmark")
    settings = replace(settings, preferred_mode=mode.strip().lower() or "public")
    log = make_logger(log_path)
    log(
        f"[INFO] Benchmark mode={settings.preferred_mode} duration_sec={duration_sec:.1f} "
        f"warmup_sec={warmup_sec:.1f} min_fps={min_fps:.2f} cameras={','.join(camera.camera_id for camera in cameras)}"
    )

    states = [build_stream_state(camera, settings, camera_count=len(cameras)) for camera in cameras]
    for state in states:
        log(
            f"[INFO] Camera={state.camera.camera_id} mode={state.mode} "
            f"target={state.host}:{state.port} subtype={state.camera.subtype} url={state.safe_url}"
        )

    workers = [CameraReaderWorker(state, settings, log, camera_count=len(states)) for state in states]
    for worker in workers:
        worker.start()

    started = time.monotonic()
    baseline: dict[str, tuple[int, float]] = {}
    hard_failures = 0

    try:
        if warmup_sec > 0:
            time.sleep(warmup_sec)
        baseline_ts = time.monotonic()
        for state in states:
            baseline[state.camera.camera_id] = (state.frame_count, baseline_ts)

        time.sleep(duration_sec)
    finally:
        for worker in workers:
            worker.stop()
        for worker in workers:
            worker.join(timeout=2.0)
        for state in states:
            if state.cap is not None:
                state.cap.release()

    finished = time.monotonic()
    for state in states:
        start_frames, start_ts = baseline.get(state.camera.camera_id, (0, started))
        elapsed = max(finished - start_ts, 1e-6)
        delta_frames = max(0, state.frame_count - start_frames)
        avg_fps = delta_frames / elapsed
        passed = avg_fps >= min_fps
        if not passed:
            hard_failures += 1
        log(
            f"[RESULT] camera={state.camera.camera_id} mode={state.mode} subtype={state.camera.subtype} "
            f"frames={delta_frames} avg_fps={avg_fps:.2f} threshold={min_fps:.2f} "
            f"reconnects={state.reconnects} failovers={state.failovers} passed={passed}"
        )

    log(f"[SUMMARY] cameras={len(states)} hard_failures={hard_failures} min_fps={min_fps:.2f} mode={settings.preferred_mode} log={log_path}")
    return 0 if hard_failures == 0 else 1
