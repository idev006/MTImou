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
    ffplay_analyzeduration: str
    ffplay_probesize: str
    strict_subtype: bool


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
    ffplay_analyzeduration = os.getenv("IMOU_FFPLAY_ANALYZEDURATION", "2000000").strip()
    ffplay_probesize = os.getenv("IMOU_FFPLAY_PROBESIZE", "1000000").strip()
    strict_subtype = os.getenv("IMOU_STRICT_SUBTYPE", "1").strip() == "1"

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
        ffplay_analyzeduration=ffplay_analyzeduration,
        ffplay_probesize=ffplay_probesize,
        strict_subtype=strict_subtype,
    )


def build_rtsp_url(cfg: ViewerConfig) -> str:
    password = quote(cfg.password, safe="")
    return (
        f"rtsp://{cfg.username}:{password}@{cfg.rtsp_host}:{cfg.rtsp_port}"
        f"/cam/realmonitor?channel={cfg.rtsp_channel}&subtype={cfg.subtype}"
    )


def build_candidate_urls(cfg: ViewerConfig) -> list[str]:
    password = quote(cfg.password, safe="")
    subtype_order = ["0", "1"]
    if cfg.subtype in {"0", "1"}:
        if cfg.strict_subtype:
            subtype_order = [cfg.subtype]
        else:
            subtype_order = [cfg.subtype, "1" if cfg.subtype == "0" else "0"]
    # Prefer sub stream (often H.264) to improve decoder compatibility.
    subtype_order = sorted(set(subtype_order), key=lambda s: 0 if s == "1" else 1)
    urls: list[str] = []
    for subtype in subtype_order:
        urls.append(
            f"rtsp://{cfg.username}:{password}@{cfg.rtsp_host}:{cfg.rtsp_port}"
            f"/cam/realmonitor?channel={cfg.rtsp_channel}&subtype={subtype}"
        )
    return urls


def has_video_stream(ffprobe: Path, url: str, timeout_sec: int = 10) -> bool:
    cmd = [
        str(ffprobe),
        "-v",
        "error",
        "-rtsp_transport",
        "tcp",
        "-i",
        url,
        "-show_streams",
        "-show_entries",
        "stream=codec_name,width,height",
        "-select_streams",
        "v:0",
        "-of",
        "default=noprint_wrappers=1:nokey=0",
    ]
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout_sec)
    except subprocess.TimeoutExpired:
        return False
    if p.returncode != 0 or not p.stdout.strip():
        return False
    width = 0
    height = 0
    for line in p.stdout.splitlines():
        if line.startswith("width="):
            try:
                width = int(line.split("=", 1)[1].strip())
            except ValueError:
                width = 0
        elif line.startswith("height="):
            try:
                height = int(line.split("=", 1)[1].strip())
            except ValueError:
                height = 0
    return width > 0 and height > 0


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

    ffprobe = Path(cfg.ffmpeg_bin_dir) / "ffprobe.exe"
    rtsp_url = build_rtsp_url(cfg)
    candidate_urls = build_candidate_urls(cfg)
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

    selected_url = rtsp_url
    if ffprobe.exists():
        for url in candidate_urls:
            masked_probe = url.replace(cfg.password, "***")
            print("[INFO] Probe URL:", masked_probe)
            if has_video_stream(ffprobe, url):
                selected_url = url
                break

    masked = selected_url.replace(cfg.password, "***")
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
                cfg.ffplay_analyzeduration,
                "-probesize",
                cfg.ffplay_probesize,
                selected_url,
            ]
        )
    finally:
        stop_process(tunnel)


if __name__ == "__main__":
    raise SystemExit(main())
