from __future__ import annotations

import os
import sys
import time

from camera_registry import enabled_cameras, get_camera
from system_health_check import camera_url, probe_tcp, resolve_host, rtsp_first_frame, target_for_mode
from venv_guard import enforce_venv_python


def main() -> int:
    enforce_venv_python()
    camera_ids = [arg for arg in sys.argv[1:] if not arg.startswith("--")]
    cameras = [get_camera(camera_id) for camera_id in camera_ids] if camera_ids else enabled_cameras()
    if not cameras:
        print("[ERROR] No cameras configured.")
        return 2

    modes_raw = os.getenv("IMOU_RESILIENCE_MODES", "lan,ddns,public")
    modes = [part.strip().lower() for part in modes_raw.split(",") if part.strip()]
    cycles = int(os.getenv("IMOU_RESILIENCE_CYCLES", "3"))
    sleep_sec = float(os.getenv("IMOU_RESILIENCE_SLEEP_SEC", "1.5"))
    tcp_timeout = float(os.getenv("IMOU_HEALTH_TCP_TIMEOUT_SEC", "2.0"))
    frame_timeout = float(os.getenv("IMOU_HEALTH_FRAME_TIMEOUT_SEC", "5.0"))

    hard_failures = 0
    for cycle in range(1, cycles + 1):
        print(f"[INFO] Resilience cycle {cycle}/{cycles}")
        for camera in cameras:
            for mode in modes:
                try:
                    target = target_for_mode(camera, mode)
                except RuntimeError as exc:
                    hard_failures += 1
                    print(f"[FAIL] camera={camera.camera_id} mode={mode} note={exc}")
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
                    print(f"[INFO] camera={camera.camera_id} mode={mode} target={target.host}:{target.port} url={safe_url}")
                    frame_ok = rtsp_first_frame(url, camera.transport, timeout_sec=frame_timeout)
                    note = "ok" if frame_ok else "first-frame-timeout"

                status = "PASS" if tcp_ok and frame_ok else "FAIL"
                print(
                    f"[{status}] camera={camera.camera_id} mode={mode} "
                    f"host={target.host} port={target.port} resolved_ip={resolved_ip or '-'} "
                    f"tcp_ok={tcp_ok} frame_ok={frame_ok} note={note}"
                )
                if not (tcp_ok and frame_ok):
                    hard_failures += 1

        if cycle < cycles:
            time.sleep(sleep_sec)

    print(f"[SUMMARY] hard_failures={hard_failures} cycles={cycles}")
    return 0 if hard_failures == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
