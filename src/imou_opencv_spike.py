from __future__ import annotations

import os
import signal
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from threading import Thread
from queue import Queue, Empty

import cv2


@dataclass(slots=True)
class SpikeConfig:
    serial: str
    username: str
    password: str
    camera_type: str
    subtype: str
    rtsp_host: str
    rtsp_port: str
    rtsp_channel: str
    include_rtsp_auth: bool
    force_relay: bool
    startup_wait_sec: float
    reconnect_sleep_sec: float
    max_read_failures: int


def load_config() -> SpikeConfig:
    serial = os.getenv("IMOU_CAMERA_SN", "").strip()
    username = os.getenv("IMOU_CAMERA_USERNAME", "admin").strip()
    password = os.getenv("IMOU_CAMERA_PASSWORD", "").strip()
    camera_type = os.getenv("IMOU_CAMERA_TYPE", "0").strip()
    subtype = os.getenv("IMOU_RTSP_SUBTYPE", "0").strip()
    rtsp_host = os.getenv("IMOU_RTSP_HOST", "127.0.0.1").strip()
    rtsp_port = os.getenv("IMOU_RTSP_PORT", "554").strip()
    rtsp_channel = os.getenv("IMOU_RTSP_CHANNEL", "1").strip()
    include_rtsp_auth = os.getenv("IMOU_RTSP_INCLUDE_AUTH", "1").strip() == "1"
    force_relay = os.getenv("IMOU_FORCE_RELAY", "1").strip() == "1"
    startup_wait_sec = float(os.getenv("IMOU_STARTUP_WAIT_SEC", "90"))
    reconnect_sleep_sec = float(os.getenv("IMOU_RECONNECT_SLEEP_SEC", "2"))
    max_read_failures = int(os.getenv("IMOU_MAX_READ_FAILURES", "20"))

    if not serial:
        raise ValueError("Missing env IMOU_CAMERA_SN")
    if not password:
        raise ValueError("Missing env IMOU_CAMERA_PASSWORD")

    return SpikeConfig(
        serial=serial,
        username=username,
        password=password,
        camera_type=camera_type,
        subtype=subtype,
        rtsp_host=rtsp_host,
        rtsp_port=rtsp_port,
        rtsp_channel=rtsp_channel,
        include_rtsp_auth=include_rtsp_auth,
        force_relay=force_relay,
        startup_wait_sec=startup_wait_sec,
        reconnect_sleep_sec=reconnect_sleep_sec,
        max_read_failures=max_read_failures,
    )


def build_rtsp_url(cfg: SpikeConfig) -> str:
    if cfg.include_rtsp_auth:
        return (
            f"rtsp://{cfg.username}:{cfg.password}@{cfg.rtsp_host}:{cfg.rtsp_port}"
            f"/cam/realmonitor?channel={cfg.rtsp_channel}&subtype={cfg.subtype}"
        )
    return (
        f"rtsp://{cfg.rtsp_host}:{cfg.rtsp_port}"
        f"/cam/realmonitor?channel={cfg.rtsp_channel}&subtype={cfg.subtype}"
    )


def start_tunnel(cfg: SpikeConfig, repo_dir: Path) -> subprocess.Popen:
    main_py = repo_dir / "main.py"
    if not main_py.exists():
        raise FileNotFoundError(f"Tunnel script not found: {main_py}")

    cmd = [
        sys.executable,
        "-u",
        str(main_py),
    ]
    if cfg.force_relay:
        cmd.append("-r")
    cmd.extend(
        [
        "-t",
        cfg.camera_type,
        "-u",
        cfg.username,
        "-p",
        cfg.password,
        cfg.serial,
        ]
    )

    creationflags = 0
    if os.name == "nt":
        creationflags = subprocess.CREATE_NEW_PROCESS_GROUP

    return subprocess.Popen(
        cmd,
        cwd=str(repo_dir),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        creationflags=creationflags,
    )


def stop_process(proc: subprocess.Popen | None) -> None:
    if proc is None or proc.poll() is not None:
        return
    try:
        if os.name == "nt":
            proc.send_signal(signal.CTRL_BREAK_EVENT)
            time.sleep(1)
    except Exception:
        pass
    try:
        proc.terminate()
        proc.wait(timeout=5)
    except Exception:
        try:
            proc.kill()
        except Exception:
            pass


def open_capture(url: str) -> cv2.VideoCapture:
    os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "rtsp_transport;tcp"
    cap = cv2.VideoCapture(url, cv2.CAP_FFMPEG)
    try:
        cap.set(cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, 10000)
        cap.set(cv2.CAP_PROP_READ_TIMEOUT_MSEC, 10000)
    except Exception:
        pass
    return cap


def _pump_lines(proc: subprocess.Popen, q: Queue) -> None:
    if proc.stdout is None:
        return
    for line in proc.stdout:
        q.put(line.rstrip("\r\n"))


def wait_tunnel_ready(proc: subprocess.Popen, wait_sec: float) -> tuple[bool, list[str]]:
    q: Queue[str] = Queue()
    t = Thread(target=_pump_lines, args=(proc, q), daemon=True)
    t.start()

    deadline = time.time() + wait_sec
    seen: list[str] = []
    while time.time() < deadline:
        if proc.poll() is not None:
            break
        try:
            line = q.get(timeout=0.2)
            seen.append(line)
            print(f"[TUNNEL] {line}")
            if "Ready to connect" in line:
                return True, seen
        except Empty:
            continue
    return False, seen


def main() -> None:
    cfg = load_config()
    repo_dir = Path(os.getenv("DH_P2P_REPO_DIR", "")).resolve()
    if not str(repo_dir) or str(repo_dir) == ".":
        raise ValueError("Missing env DH_P2P_REPO_DIR")

    rtsp_url = build_rtsp_url(cfg)
    print("[INFO] Starting tunnel process...")
    tunnel = start_tunnel(cfg, repo_dir)
    ready, lines = wait_tunnel_ready(tunnel, cfg.startup_wait_sec)
    if not ready:
        stop_process(tunnel)
        tail = "\n".join(lines[-12:]) if lines else "(no tunnel output)"
        raise RuntimeError(
            "Tunnel not ready (did not reach 'Ready to connect').\n"
            "Likely peer/relay issue in dh-p2p PoC.\n"
            f"Recent tunnel log:\n{tail}"
        )

    print("[INFO] Opening RTSP:", rtsp_url.replace(cfg.password, "***"))
    cap = open_capture(rtsp_url)
    if not cap.isOpened():
        stop_process(tunnel)
        raise RuntimeError("Cannot open RTSP. Check SN/password/type/subtype.")

    print("[INFO] Stream connected. Press 'q' to exit.")
    read_failures = 0

    try:
        while True:
            if tunnel.poll() is not None:
                print("[WARN] Tunnel exited. Restarting...")
                stop_process(tunnel)
                tunnel = start_tunnel(cfg, repo_dir)
                ready, lines = wait_tunnel_ready(tunnel, cfg.startup_wait_sec)
                if not ready:
                    tail = "\n".join(lines[-12:]) if lines else "(no tunnel output)"
                    raise RuntimeError(
                        "Tunnel restart failed to become ready.\n"
                        f"Recent tunnel log:\n{tail}"
                    )
                cap.release()
                cap = open_capture(rtsp_url)
                read_failures = 0
                continue

            ok, frame = cap.read()
            if not ok:
                read_failures += 1
                print(f"[WARN] Frame read failed ({read_failures}/{cfg.max_read_failures})")
                time.sleep(cfg.reconnect_sleep_sec)
                cap.release()
                cap = open_capture(rtsp_url)
                if read_failures >= cfg.max_read_failures:
                    print("[WARN] Too many read failures, restarting tunnel...")
                    stop_process(tunnel)
                    tunnel = start_tunnel(cfg, repo_dir)
                    ready, lines = wait_tunnel_ready(tunnel, cfg.startup_wait_sec)
                    if not ready:
                        tail = "\n".join(lines[-12:]) if lines else "(no tunnel output)"
                        raise RuntimeError(
                            "Tunnel restart failed after read errors.\n"
                            f"Recent tunnel log:\n{tail}"
                        )
                    cap.release()
                    cap = open_capture(rtsp_url)
                    read_failures = 0
                continue

            read_failures = 0
            cv2.imshow("IMOU Remote Stream", frame)
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break
    finally:
        cap.release()
        cv2.destroyAllWindows()
        stop_process(tunnel)


if __name__ == "__main__":
    main()
