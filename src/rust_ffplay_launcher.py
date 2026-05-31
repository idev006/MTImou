from __future__ import annotations

import os
import queue
import socket
import subprocess
import threading
import time
from pathlib import Path


def first_env(*names: str, default: str = "") -> str:
    for name in names:
        value = os.getenv(name, "").strip()
        if value:
            return value
    return default


def as_bool(value: str) -> bool:
    return value.strip().lower() in {"1", "true", "yes", "on"}


def start_output_pump(proc: subprocess.Popen, prefix: str) -> queue.Queue[str]:
    line_q: queue.Queue[str] = queue.Queue()

    def _pump() -> None:
        if proc.stdout is None:
            return
        for raw in proc.stdout:
            line_q.put(raw.rstrip("\r\n"))

    t = threading.Thread(target=_pump, daemon=True, name=f"{prefix}-pump")
    t.start()
    return line_q


def wait_rust_ready(
    proc: subprocess.Popen, line_q: queue.Queue[str], timeout_sec: int = 120
) -> bool:
    start = time.time()
    while time.time() - start < timeout_sec and proc.poll() is None:
        try:
            line = line_q.get(timeout=0.2)
        except queue.Empty:
            continue
        print("[RUST]", line)
        if "Ready to connect!" in line:
            return True
    return False


def has_video_stream(ffprobe: Path, url: str, transport: str) -> bool:
    cmd = [
        str(ffprobe),
        "-v",
        "error",
        "-rtsp_transport",
        transport,
        "-rw_timeout",
        "12000000",
        "-i",
        url,
        "-show_streams",
        "-select_streams",
        "v:0",
        "-of",
        "compact",
    ]
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=20)
    except subprocess.TimeoutExpired:
        return False
    return p.returncode == 0 and bool(p.stdout.strip())


def pick_bind_port() -> int:
    fixed = first_env("IMOU_LOCAL_RTSP_PORT")
    if fixed:
        return int(fixed)

    candidates = [18554, 19554, 20554, 17554, 1554]
    for port in candidates:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            sock.bind(("127.0.0.1", port))
            return port
        except OSError:
            pass
        finally:
            sock.close()
    raise RuntimeError("No available local RTSP port found")


def main() -> int:
    repo_dir = Path(
        os.getenv("DH_P2P_REPO_DIR", r"F:\programming\python\MTImou\dh-p2p").strip()
    )
    serial = os.getenv("IMOU_CAMERA_SN", "").strip()
    user = os.getenv("IMOU_CAMERA_USERNAME", "admin").strip()
    pwd = os.getenv("IMOU_CAMERA_PASSWORD", "").strip()
    rtsp_host = first_env("IMOU_RTSP_HOST", default="127.0.0.1")
    rtsp_channel = first_env("IMOU_RTSP_CHANNEL", default="1")
    preferred_subtype = first_env("IMOU_RTSP_SUBTYPE", default="")
    max_attempts = int(os.getenv("IMOU_SESSION_RETRIES", "5"))
    ready_timeout_sec = int(os.getenv("IMOU_RUST_READY_TIMEOUT_SEC", "60"))
    tunnel_mode = first_env("IMOU_TUNNEL_MODE", default="").lower()
    if not tunnel_mode and as_bool(first_env("IMOU_FORCE_RELAY")):
        tunnel_mode = "relay"
    if not tunnel_mode:
        tunnel_mode = "auto"

    ffmpeg_bin_dir = first_env("FFMPEG_BIN_DIR", default=r"F:\ffmpeg\bin")
    ffplay = Path(ffmpeg_bin_dir) / "ffplay.exe"
    ffprobe = Path(ffmpeg_bin_dir) / "ffprobe.exe"
    exe = repo_dir / "target" / "release" / "dh-p2p.exe"

    if not serial:
        print("Missing IMOU_CAMERA_SN")
        return 2
    if not pwd:
        print("Missing IMOU_CAMERA_PASSWORD")
        return 2
    if not exe.exists():
        print("Missing rust binary:", exe)
        return 2
    if not ffplay.exists():
        print("Missing ffplay:", ffplay)
        return 2
    if not ffprobe.exists():
        print("Missing ffprobe:", ffprobe)
        return 2

    if tunnel_mode not in {"auto", "direct", "relay"}:
        print("Invalid IMOU_TUNNEL_MODE. Use auto/direct/relay")
        return 2

    mode_plan = []
    if tunnel_mode == "auto":
        mode_plan = [("direct", []), ("relay", ["--relay"])]
    elif tunnel_mode == "direct":
        mode_plan = [("direct", [])]
    else:
        mode_plan = [("relay", ["--relay"])]

    for attempt in range(1, max_attempts + 1):
        bind_port = pick_bind_port()
        print(f"[INFO] Using local RTSP port: {bind_port}")
        subtype_order = ["0", "1"]
        if preferred_subtype in {"0", "1"}:
            subtype_order = [preferred_subtype, "1" if preferred_subtype == "0" else "0"]
        url_paths = [
            f"/cam/realmonitor?channel={rtsp_channel}&subtype={subtype_order[0]}",
            f"/cam/realmonitor?channel={rtsp_channel}&subtype={subtype_order[1]}",
            f"/cam/realmonitor?channel={rtsp_channel}&subtype={subtype_order[0]}&unicast=true&proto=Onvif",
            f"/cam/realmonitor?channel={rtsp_channel}&subtype={subtype_order[1]}&unicast=true&proto=Onvif",
        ]
        urls = [f"rtsp://{user}:{pwd}@{rtsp_host}:{bind_port}{path}" for path in url_paths]
        transports = ["tcp", "udp"]
        print(f"[INFO] Session attempt {attempt}/{max_attempts}")
        for mode_name, mode_args in mode_plan:
            print(f"[INFO] Tunnel mode: {mode_name}")
            rust = subprocess.Popen(
                [
                    str(exe),
                    *mode_args,
                    "--port",
                    f"127.0.0.1:{bind_port}:554",
                    serial,
                ],
                cwd=str(repo_dir),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
            )
            rust_q = start_output_pump(rust, "rust-ffplay")

            if not wait_rust_ready(rust, rust_q, timeout_sec=ready_timeout_sec):
                print("[WARN] Rust tunnel not ready in this mode")
                if rust.poll() is None:
                    rust.terminate()
                continue

            selected_url = ""
            selected_transport = "tcp"
            for transport in transports:
                for url in urls:
                    print(
                        "[INFO] Probe:",
                        url.replace(pwd, "***"),
                        f"(transport={transport})",
                    )
                    if has_video_stream(ffprobe, url, transport):
                        selected_url = url
                        selected_transport = transport
                        break
                if selected_url:
                    break

            if not selected_url:
                print("[WARN] No video stream detected in this mode.")
                if rust.poll() is None:
                    rust.terminate()
                    time.sleep(1)
                    if rust.poll() is None:
                        rust.kill()
                continue

            print("[INFO] Launch ffplay:", selected_url.replace(pwd, "***"))
            rc = subprocess.call(
                [
                    str(ffplay),
                    "-rtsp_transport",
                    selected_transport,
                    "-fflags",
                    "nobuffer",
                    "-flags",
                    "low_delay",
                    selected_url,
                ]
            )
            if rust.poll() is None:
                rust.terminate()
                time.sleep(1)
                if rust.poll() is None:
                    rust.kill()
            return rc

    print("[ERROR] Could not establish a streamable session after retries.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
