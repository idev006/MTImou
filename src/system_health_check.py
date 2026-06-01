from __future__ import annotations

import os
import socket
import sys
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from urllib.parse import quote

import cv2

from camera_registry import CameraConfig, enabled_cameras, get_camera, pick_target
from venv_guard import enforce_venv_python


ROOT_DIR = Path(__file__).resolve().parents[1]


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


def make_logger(log_path: Path):
    log_path.parent.mkdir(parents=True, exist_ok=True)

    def _log(message: str) -> None:
        line = f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} {message}"
        print(message)
        with log_path.open("a", encoding="utf-8") as fh:
            fh.write(line + "\n")

    return _log


def resolve_host(host: str) -> str:
    try:
        return socket.gethostbyname(host)
    except Exception:
        return ""


def probe_tcp(host: str, port: int, timeout_sec: float) -> bool:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(timeout_sec)
    try:
        sock.connect((host, port))
        return True
    except Exception:
        return False
    finally:
        sock.close()


def open_capture(url: str, transport: str) -> cv2.VideoCapture:
    os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = f"rtsp_transport;{transport}"
    return cv2.VideoCapture(url, cv2.CAP_FFMPEG)


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


def target_for_mode(camera: CameraConfig, mode: str):
    if mode == "auto":
        return pick_target(camera, preferred_mode="auto")
    if mode == "lan":
        return pick_target(camera, preferred_mode="lan")
    if mode == "ddns":
        return pick_target(camera, preferred_mode="ddns")
    if mode == "public":
        return pick_target(camera, preferred_mode="public")
    raise ValueError(f"Unsupported mode: {mode}")


def camera_url(camera: CameraConfig, host: str, port: int) -> tuple[str, str]:
    safe_password = quote(camera.password, safe="")
    url = (
        f"rtsp://{camera.username}:{safe_password}@{host}:{port}"
        f"/cam/realmonitor?channel={camera.channel}&subtype={camera.subtype}"
    )
    return url, url.replace(safe_password, "***")


def main() -> int:
    enforce_venv_python()

    args = [arg for arg in sys.argv[1:] if not arg.startswith("--")]
    cameras = [get_camera(arg) for arg in args] if args else enabled_cameras()
    if not cameras:
        print("[ERROR] No cameras configured.")
        return 2

    modes_raw = os.getenv("IMOU_HEALTH_MODES", "lan,ddns,public")
    modes = [part.strip().lower() for part in modes_raw.split(",") if part.strip()]
    required_modes_raw = os.getenv("IMOU_HEALTH_REQUIRED_MODES", modes_raw)
    required_modes = {part.strip().lower() for part in required_modes_raw.split(",") if part.strip()}
    tcp_timeout = float(os.getenv("IMOU_HEALTH_TCP_TIMEOUT_SEC", "2.0"))
    frame_timeout = float(os.getenv("IMOU_HEALTH_FRAME_TIMEOUT_SEC", "5.0"))
    log_path = Path(os.getenv("IMOU_HEALTH_LOG_PATH", str(ROOT_DIR / "logs" / "system_health_check_latest.log")))
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
                results.append(
                    CheckResult(
                        camera_id=camera.camera_id,
                        mode=mode,
                        host="",
                        port=0,
                        resolved_ip="",
                        tcp_ok=False,
                        frame_ok=False,
                        note=note,
                    )
                )
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
                url, safe_url = camera_url(camera, target.host, target.port)
                log(f"[INFO] camera={camera.camera_id} mode={mode} target={target.host}:{target.port} url={safe_url}")
                frame_ok = rtsp_first_frame(url, camera.transport, timeout_sec=frame_timeout)
                note = "ok" if frame_ok else "first-frame-timeout"

            results.append(
                CheckResult(
                    camera_id=camera.camera_id,
                    mode=mode,
                    host=target.host,
                    port=target.port,
                    resolved_ip=resolved_ip,
                    tcp_ok=tcp_ok,
                    frame_ok=frame_ok,
                    note=note,
                )
            )

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
    log(
        f"[SUMMARY] ok={ok_results}/{total_results} "
        f"hard_failures={hard_failures} log={log_path}"
    )
    return 0 if hard_failures == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
