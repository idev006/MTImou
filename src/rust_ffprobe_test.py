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


def probe_video_stream(
    ffprobe: Path, url: str, transport: str, rw_timeout_us: str, timeout_sec: int
) -> tuple[bool, str]:
    cmd = [
        str(ffprobe),
        "-v",
        "error",
        "-rtsp_transport",
        transport,
        "-rw_timeout",
        rw_timeout_us,
        "-i",
        url,
        "-show_streams",
        "-select_streams",
        "v:0",
        "-of",
        "compact",
    ]
    try:
        probe = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout_sec)
    except subprocess.TimeoutExpired:
        return False, "ffprobe timeout on this URL"

    if probe.returncode == 0 and probe.stdout.strip():
        return True, probe.stdout.strip()

    if probe.stderr:
        return False, probe.stderr.strip().splitlines()[-1]

    return False, "ffprobe returned no stream info"


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
    ffmpeg_bin_dir = first_env("FFMPEG_BIN_DIR", default=r"F:\ffmpeg\bin")
    ffprobe = Path(ffmpeg_bin_dir) / "ffprobe.exe"
    exe = repo_dir / "target" / "release" / "dh-p2p.exe"
    max_attempts = int(os.getenv("IMOU_PROBE_ATTEMPTS", "3"))
    probe_timeout_sec = int(os.getenv("IMOU_PROBE_TIMEOUT_SEC", "35"))
    rw_timeout_us = os.getenv("IMOU_PROBE_RW_TIMEOUT_US", "15000000")
    rust_ready_timeout_sec = int(os.getenv("IMOU_RUST_READY_TIMEOUT_SEC", "60"))
    tunnel_mode = first_env("IMOU_TUNNEL_MODE", default="").lower()
    if not tunnel_mode and as_bool(first_env("IMOU_FORCE_RELAY")):
        tunnel_mode = "relay"
    if not tunnel_mode:
        tunnel_mode = "auto"

    if not serial:
        print("Missing IMOU_CAMERA_SN")
        return 2
    if not pwd:
        print("Missing IMOU_CAMERA_PASSWORD")
        return 2
    if not exe.exists():
        print("Missing dh-p2p rust binary:", exe)
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
        urls = [
            f"rtsp://{user}:{pwd}@{rtsp_host}:{bind_port}/cam/realmonitor?channel={rtsp_channel}&subtype={subtype_order[0]}",
            f"rtsp://{user}:{pwd}@{rtsp_host}:{bind_port}/cam/realmonitor?channel={rtsp_channel}&subtype={subtype_order[1]}",
            f"rtsp://{user}:{pwd}@{rtsp_host}:{bind_port}/cam/realmonitor?channel={rtsp_channel}&subtype={subtype_order[0]}&unicast=true&proto=Onvif",
            f"rtsp://{user}:{pwd}@{rtsp_host}:{bind_port}/cam/realmonitor?channel={rtsp_channel}&subtype={subtype_order[1]}&unicast=true&proto=Onvif",
        ]
        transports = ["tcp", "udp"]
        print(f"[INFO] Rust session attempt {attempt}/{max_attempts}")
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
            rust_q = start_output_pump(rust, "rust-probe")

            ready = False
            start = time.time()
            while time.time() - start < rust_ready_timeout_sec and rust.poll() is None:
                try:
                    line = rust_q.get(timeout=0.2)
                except queue.Empty:
                    continue
                print("[RUST]", line)
                if "Ready to connect!" in line:
                    ready = True
                    break

            if not ready:
                if rust.poll() is None:
                    rust.terminate()
                    time.sleep(1)
                    if rust.poll() is None:
                        rust.kill()
                print("[WARN] Rust tunnel not ready in this mode")
                continue
            success_out = ""
            success_url = ""
            for transport in transports:
                for url in urls:
                    print(
                        "[INFO] Running ffprobe on",
                        url.replace(pwd, "***"),
                        f"(transport={transport})",
                    )
                    ok, detail = probe_video_stream(
                        ffprobe, url, transport, rw_timeout_us, probe_timeout_sec
                    )
                    if ok:
                        success_out = detail
                        success_url = url
                        break
                    print("[WARN]", detail.replace(pwd, "***"))
                if success_out:
                    break

            if rust.poll() is None:
                rust.terminate()
                time.sleep(1)
                if rust.poll() is None:
                    rust.kill()

            if success_out:
                print("[SUCCESS] ffprobe found video stream")
                print("[SUCCESS] URL:", success_url.replace(pwd, "***"))
                print(success_out)
                return 0

    print(
        f"[ERROR] ffprobe could not find stream with tested URLs in {max_attempts} attempts"
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
