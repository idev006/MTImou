from __future__ import annotations

import sys
import time
from dataclasses import dataclass
from pathlib import Path

import cv2

from mtimou_v2.logging_utils import make_logger
from mtimou_v2.registry import enabled_cameras, get_camera
from mtimou_v2.rtsp import build_rtsp_url, open_capture
from mtimou_v2.targets import CameraTarget, pick_target, probe_tcp, resolve_host


@dataclass(slots=True)
class CheckResult:
    camera_id: str
    mode: str
    host: str
    port: int
    resolved_ip: str
    tcp_ok: bool
    frame_ok: bool
    note: str


def rtsp_first_frame(url: str, transport: str, timeout_sec: float) -> bool:
    cap = open_capture(url, transport)
    try:
        if not cap.isOpened():
            return False
        started = time.monotonic()
        while time.monotonic() - started < timeout_sec:
            ok, frame = cap.read()
            if ok and frame is not None:
                return True
            time.sleep(0.05)
        return False
    finally:
        cap.release()


def target_for_mode(camera, mode: str):
    if mode == "auto":
        return pick_target(camera, preferred_mode="auto")
    if mode == "lan":
        return pick_target(camera, preferred_mode="lan")
    if mode == "ddns":
        return pick_target(camera, preferred_mode="ddns")
    if mode == "public":
        return pick_target(camera, preferred_mode="public")
    raise ValueError(f"Unsupported mode: {mode}")


def run_health_check(*, modes: list[str], required_modes: set[str], tcp_timeout: float, frame_timeout: float, log_path: Path, camera_ids: list[str] | None = None) -> int:
    cameras = [get_camera(arg) for arg in camera_ids] if camera_ids else enabled_cameras()
    if not cameras:
        print("[ERROR] No cameras configured.")
        return 2

    log = make_logger(log_path)
    log(f"[INFO] Runtime python: {sys.executable}")
    log(f"[INFO] Health modes: {', '.join(modes)}")
    log(f"[INFO] Required modes: {', '.join(sorted(required_modes))}")
    log(f"[INFO] Cameras: {', '.join(camera.camera_id for camera in cameras)}")

    results: list[CheckResult] = []
    hard_failures = 0

    for camera in cameras:
        if not camera.password:
            hard_failures += 1
            log(f"[FAIL] camera={camera.camera_id} missing password")
            continue

        for mode in modes:
            try:
                target = target_for_mode(camera, mode)
            except RuntimeError as exc:
                note = str(exc)
                results.append(CheckResult(camera.camera_id, mode, "", 0, "", False, False, note))
                if mode in required_modes:
                    hard_failures += 1
                    log(f"[FAIL] camera={camera.camera_id} mode={mode} note={note}")
                else:
                    log(f"[WARN] camera={camera.camera_id} mode={mode} note={note}")
                continue

            resolved_ip = resolve_host(target.host)
            tcp_ok = probe_tcp(target.host, target.port, timeout_sec=tcp_timeout)
            frame_ok = False
            note = ""

            if not resolved_ip:
                note = "dns-unresolved"
            elif not tcp_ok:
                note = "tcp-connect-failed"
            else:
                url, safe_url = build_rtsp_url(camera, target)
                log(f"[INFO] camera={camera.camera_id} mode={mode} target={target.host}:{target.port} url={safe_url}")
                frame_ok = rtsp_first_frame(url, camera.transport, timeout_sec=frame_timeout)
                note = "ok" if frame_ok else "first-frame-timeout"

            results.append(CheckResult(camera.camera_id, mode, target.host, target.port, resolved_ip, tcp_ok, frame_ok, note))
            line = (
                f"[RESULT] camera={camera.camera_id} mode={mode} "
                f"host={target.host} port={target.port} resolved_ip={resolved_ip or '-'} "
                f"tcp_ok={tcp_ok} frame_ok={frame_ok} note={note}"
            )
            if mode in required_modes and (not tcp_ok or not frame_ok):
                hard_failures += 1
                log(line.replace("[RESULT]", "[FAIL]"))
            elif not tcp_ok or not frame_ok:
                log(line.replace("[RESULT]", "[WARN]"))
            else:
                log(line)

    ok_results = sum(1 for item in results if item.tcp_ok and item.frame_ok)
    total_results = len(results)
    log(f"[SUMMARY] ok={ok_results}/{total_results} hard_failures={hard_failures} log={log_path}")
    return 0 if hard_failures == 0 else 1

