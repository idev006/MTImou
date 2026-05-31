from __future__ import annotations

import os
import signal
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from queue import Empty, Queue
from threading import Thread
from urllib.parse import quote


@dataclass(slots=True)
class ViewerConfig:
    serial: str
    username: str
    password: str
    camera_type: str
    subtype: str
    rtsp_host: str
    rtsp_port: str
    rtsp_channel: str
    force_relay: bool
    startup_wait_sec: float
    ffmpeg_bin_dir: str


def load_config() -> ViewerConfig:
    serial = os.getenv("IMOU_CAMERA_SN", "").strip()
    username = os.getenv("IMOU_CAMERA_USERNAME", "admin").strip()
    password = os.getenv("IMOU_CAMERA_PASSWORD", "").strip()
    camera_type = os.getenv("IMOU_CAMERA_TYPE", "1").strip()
    subtype = os.getenv("IMOU_RTSP_SUBTYPE", "0").strip()
    rtsp_host = os.getenv("IMOU_RTSP_HOST", "127.0.0.1").strip()
    rtsp_port = os.getenv("IMOU_RTSP_PORT", "554").strip()
    rtsp_channel = os.getenv("IMOU_RTSP_CHANNEL", "1").strip()
    force_relay = os.getenv("IMOU_FORCE_RELAY", "1").strip() == "1"
    startup_wait_sec = float(os.getenv("IMOU_STARTUP_WAIT_SEC", "90"))
    ffmpeg_bin_dir = os.getenv("FFMPEG_BIN_DIR", r"F:\ffmpeg\bin").strip()

    if not serial:
        raise ValueError("Missing env IMOU_CAMERA_SN")
    if not password:
        raise ValueError("Missing env IMOU_CAMERA_PASSWORD")

    return ViewerConfig(
        serial=serial,
        username=username,
        password=password,
        camera_type=camera_type,
        subtype=subtype,
        rtsp_host=rtsp_host,
        rtsp_port=rtsp_port,
        rtsp_channel=rtsp_channel,
        force_relay=force_relay,
        startup_wait_sec=startup_wait_sec,
        ffmpeg_bin_dir=ffmpeg_bin_dir,
    )


def build_rtsp_url(cfg: ViewerConfig) -> str:
    password = quote(cfg.password, safe="")
    return (
        f"rtsp://{cfg.username}:{password}@{cfg.rtsp_host}:{cfg.rtsp_port}"
        f"/cam/realmonitor?channel={cfg.rtsp_channel}&subtype={cfg.subtype}"
    )


def start_tunnel(cfg: ViewerConfig, repo_dir: Path) -> subprocess.Popen:
    main_py = repo_dir / "main.py"
    if not main_py.exists():
        raise FileNotFoundError(f"Tunnel script not found: {main_py}")

    cmd = [sys.executable, "-u", str(main_py)]
    if cfg.force_relay:
        cmd.append("-r")
    cmd.extend(["-t", cfg.camera_type, "-u", cfg.username, "-p", cfg.password, cfg.serial])

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
            time.sleep(0.5)
    except Exception:
        pass
    try:
        proc.terminate()
        proc.wait(timeout=3)
    except Exception:
        try:
            proc.kill()
        except Exception:
            pass


def _pump_lines(proc: subprocess.Popen, q: Queue[str]) -> None:
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


def main() -> int:
    cfg = load_config()
    repo_dir = Path(os.getenv("DH_P2P_REPO_DIR", "")).resolve()
    if not str(repo_dir) or str(repo_dir) == ".":
        raise ValueError("Missing env DH_P2P_REPO_DIR")

    ffplay = Path(cfg.ffmpeg_bin_dir) / "ffplay.exe"
    if not ffplay.exists():
        raise FileNotFoundError(f"ffplay not found: {ffplay}")

    rtsp_url = build_rtsp_url(cfg)
    print("[INFO] Starting tunnel...")
    tunnel = start_tunnel(cfg, repo_dir)
    ready, lines = wait_tunnel_ready(tunnel, cfg.startup_wait_sec)
    if not ready:
        stop_process(tunnel)
        tail = "\n".join(lines[-12:]) if lines else "(no tunnel output)"
        raise RuntimeError(
            "Tunnel not ready (did not reach 'Ready to connect').\n"
            f"Recent tunnel log:\n{tail}"
        )

    masked = rtsp_url.replace(cfg.password, "***")
    print("[INFO] Launching ffplay:", masked)
    print("[INFO] Close ffplay window or press q in ffplay to stop.")

    try:
        return subprocess.call(
            [
                str(ffplay),
                "-loglevel",
                "warning",
                "-rtsp_transport",
                "tcp",
                "-fflags",
                "nobuffer",
                "-flags",
                "low_delay",
                "-analyzeduration",
                "0",
                "-probesize",
                "32",
                rtsp_url,
            ]
        )
    finally:
        stop_process(tunnel)


if __name__ == "__main__":
    raise SystemExit(main())

