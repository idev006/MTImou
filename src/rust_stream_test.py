from __future__ import annotations

import os
import socket
import subprocess
import threading
import time
from pathlib import Path

import cv2


def first_env(*names: str, default: str = "") -> str:
    for name in names:
        value = os.getenv(name, "").strip()
        if value:
            return value
    return default


def as_bool(value: str) -> bool:
    return value.strip().lower() in {"1", "true", "yes", "on"}


def pick_bind_port() -> int:
    fixed = first_env("IMOU_LOCAL_RTSP_PORT", "IMOU_RTSP_PORT")
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
    tunnel_mode = first_env("IMOU_TUNNEL_MODE", default="").lower()
    if not tunnel_mode and as_bool(first_env("IMOU_FORCE_RELAY")):
        tunnel_mode = "relay"
    if not tunnel_mode:
        tunnel_mode = "relay"

    if not serial:
        print("Missing IMOU_CAMERA_SN")
        return 2

    exe = repo_dir / "target" / "release" / "dh-p2p.exe"
    if not exe.exists():
        print("Missing rust binary:", exe)
        return 2

    log = repo_dir.parent / "rust_run.log"
    if log.exists():
        log.unlink()

    bind_port = pick_bind_port()
    mode_args = ["--relay"] if tunnel_mode == "relay" else []
    cmd = [str(exe), *mode_args, "--port", f"127.0.0.1:{bind_port}:554", serial]
    print("[INFO] Launch:", " ".join(cmd))
    proc = subprocess.Popen(
        cmd,
        cwd=str(repo_dir),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )

    ready = False
    deadline = time.time() + 90
    lines: list[str] = []
    lock = threading.Lock()

    def pump() -> None:
        nonlocal ready
        if proc.stdout is None:
            return
        for raw in proc.stdout:
            line = raw.rstrip("\r\n")
            with lock:
                lines.append(line)
            print("[RUST]", line)
            if "Ready to connect!" in line:
                ready = True

    t = threading.Thread(target=pump, daemon=True)
    t.start()

    while time.time() < deadline and proc.poll() is None and not ready:
        time.sleep(0.2)

    if not ready:
        print("[ERROR] Rust tunnel not ready.")
        if proc.poll() is None:
            proc.terminate()
        return 1

    os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "rtsp_transport;tcp"
    subtype_order = ["0", "1"]
    if preferred_subtype in {"0", "1"}:
        subtype_order = [preferred_subtype, "1" if preferred_subtype == "0" else "0"]

    urls = [
        f"rtsp://{user}:{pwd}@{rtsp_host}:{bind_port}/cam/realmonitor?channel={rtsp_channel}&subtype={subtype_order[0]}",
        f"rtsp://{rtsp_host}:{bind_port}/cam/realmonitor?channel={rtsp_channel}&subtype={subtype_order[0]}",
        f"rtsp://{user}:{pwd}@{rtsp_host}:{bind_port}/cam/realmonitor?channel={rtsp_channel}&subtype={subtype_order[1]}",
        f"rtsp://{rtsp_host}:{bind_port}/cam/realmonitor?channel={rtsp_channel}&subtype={subtype_order[1]}",
    ]

    ok = False
    try:
        for url in urls:
            print("[INFO] TRY", url.replace(pwd, "***") if pwd else url)
            cap = cv2.VideoCapture(url, cv2.CAP_FFMPEG)
            t0 = time.time()
            frames = 0
            while time.time() - t0 < 30:
                ret, _frame = cap.read()
                if ret:
                    frames += 1
                    if frames >= 3:
                        print("[SUCCESS] Stream works via Rust tunnel.")
                        ok = True
                        break
                time.sleep(0.2)
            cap.release()
            if ok:
                break
    finally:
        # Print last tunnel lines for diagnostics.
        with lock:
            tail = lines[-80:]
        print("[INFO] Rust tunnel tail:")
        for line in tail:
            print("[RUST-TAIL]", line)

        if proc.poll() is None:
            proc.terminate()
            time.sleep(1)
            if proc.poll() is None:
                proc.kill()

    if not ok:
        print("[ERROR] No frames received via Rust tunnel.")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
