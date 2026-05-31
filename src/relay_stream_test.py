from __future__ import annotations

import os
import subprocess
import sys
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


def build_urls(
    host: str,
    port: str,
    channel: str,
    username: str,
    password: str,
    preferred_subtype: str,
    include_auth: bool,
    try_anonymous: bool,
) -> list[str]:
    subtype_order = ["0", "1"]
    if preferred_subtype in {"0", "1"}:
        subtype_order = [preferred_subtype, "1" if preferred_subtype == "0" else "0"]

    urls: list[str] = []
    for subtype in subtype_order:
        paths = [
            f"/cam/realmonitor?channel={channel}&subtype={subtype}",
            f"/cam/realmonitor?channel={channel}&subtype={subtype}&unicast=true&proto=Onvif",
        ]
        for path in paths:
            if include_auth and password:
                urls.append(f"rtsp://{username}:{password}@{host}:{port}{path}")
            if try_anonymous:
                urls.append(f"rtsp://{host}:{port}{path}")
    return urls


def wait_tunnel_ready(proc: subprocess.Popen, timeout_sec: int = 90) -> bool:
    ready = False
    deadline = time.time() + timeout_sec
    while time.time() < deadline and proc.poll() is None and not ready:
        time.sleep(0.2)
        # ready flag is set by output pump via shared state
        # read from attribute set by caller
        ready = bool(getattr(proc, "_relay_ready", False))
    return ready


def try_url_open(url: str, frame_wait_sec: int) -> bool:
    cap = cv2.VideoCapture(url, cv2.CAP_FFMPEG)
    if not cap.isOpened():
        cap.release()
        return False

    frames = 0
    start = time.time()
    while time.time() - start < frame_wait_sec:
        ok, _frame = cap.read()
        if ok:
            frames += 1
            if frames >= 3:
                cap.release()
                return True
        else:
            time.sleep(0.1)
    cap.release()
    return False


def ffprobe_has_video(ffprobe: Path, url: str, transport: str, timeout_sec: int) -> bool:
    if not ffprobe.exists():
        return False
    cmd = [
        str(ffprobe),
        "-v",
        "error",
        "-rtsp_transport",
        transport,
        "-rw_timeout",
        "8000000",
        "-i",
        url,
        "-show_streams",
        "-select_streams",
        "v:0",
        "-of",
        "compact",
    ]
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout_sec)
    except subprocess.TimeoutExpired:
        return False
    return p.returncode == 0 and bool(p.stdout.strip())


def main() -> int:
    repo_dir = Path(os.getenv("DH_P2P_REPO_DIR", "")).resolve()
    if not str(repo_dir) or str(repo_dir) == ".":
        print("Missing DH_P2P_REPO_DIR")
        return 2

    serial = os.getenv("IMOU_CAMERA_SN", "").strip()
    if not serial:
        print("Missing IMOU_CAMERA_SN")
        return 2

    username = os.getenv("IMOU_CAMERA_USERNAME", "admin").strip()
    password = os.getenv("IMOU_CAMERA_PASSWORD", "").strip()
    camera_type = os.getenv("IMOU_CAMERA_TYPE", "1").strip()
    host = first_env("IMOU_RTSP_HOST", default="127.0.0.1")
    port = first_env("IMOU_RTSP_PORT", default="554")
    channel = first_env("IMOU_RTSP_CHANNEL", default="1")
    preferred_subtype = first_env("IMOU_RTSP_SUBTYPE", default="0")
    include_auth = as_bool(first_env("IMOU_RTSP_INCLUDE_AUTH", default="1"))
    try_anonymous = as_bool(first_env("IMOU_RTSP_TRY_ANON", default="0"))
    force_relay = as_bool(first_env("IMOU_FORCE_RELAY", default="1"))
    max_attempts = int(first_env("IMOU_RELAY_ATTEMPTS", default="4"))
    frame_wait_sec = int(first_env("IMOU_FRAME_WAIT_SEC", default="12"))
    probe_timeout_sec = int(first_env("IMOU_PROBE_TIMEOUT_SEC", default="8"))
    use_ffprobe = as_bool(first_env("IMOU_USE_FFPROBE", default="0"))
    one_url_per_tunnel = as_bool(first_env("IMOU_ONE_URL_PER_TUNNEL", default="1"))
    ffmpeg_bin_dir = Path(first_env("FFMPEG_BIN_DIR", default=r"F:\ffmpeg\bin"))
    ffprobe = ffmpeg_bin_dir / "ffprobe.exe"

    os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "rtsp_transport;tcp"
    urls = build_urls(
        host=host,
        port=port,
        channel=channel,
        username=username,
        password=password,
        preferred_subtype=preferred_subtype,
        include_auth=include_auth,
        try_anonymous=try_anonymous,
    )

    for attempt in range(1, max_attempts + 1):
        cmd = [sys.executable, "-u", str(repo_dir / "main.py")]
        if force_relay:
            cmd.append("-r")
        cmd.extend(["-t", camera_type])
        if username:
            cmd.extend(["-u", username])
        if password:
            cmd.extend(["-p", password])
        cmd.append(serial)
        print(f"[INFO] Tunnel attempt {attempt}/{max_attempts}: {' '.join(cmd)}")

        proc = subprocess.Popen(
            cmd,
            cwd=str(repo_dir),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )
        proc._relay_ready = False  # type: ignore[attr-defined]

        def pump() -> None:
            assert proc.stdout is not None
            for line in proc.stdout:
                line = line.rstrip("\r\n")
                print("[TUNNEL]", line)
                if "Ready to connect" in line:
                    proc._relay_ready = True  # type: ignore[attr-defined]

        t = threading.Thread(target=pump, daemon=True)
        t.start()

        if not wait_tunnel_ready(proc, timeout_sec=90):
            print("[WARN] Tunnel not ready in this attempt")
            if proc.poll() is None:
                proc.terminate()
                time.sleep(1)
                if proc.poll() is None:
                    proc.kill()
            continue

        for idx, url in enumerate(urls, start=1):
            masked = url.replace(password, "***") if password else url
            print(f"[INFO] RTSP candidate {idx}/{len(urls)}:", masked)
            if use_ffprobe:
                probe_ok = ffprobe_has_video(
                    ffprobe=ffprobe, url=url, transport="tcp", timeout_sec=probe_timeout_sec
                ) or ffprobe_has_video(
                    ffprobe=ffprobe, url=url, transport="udp", timeout_sec=probe_timeout_sec
                )
                if not probe_ok:
                    if one_url_per_tunnel:
                        break
                    continue

                print("[INFO] Probe passed, opening via OpenCV:", masked)
            if try_url_open(url, frame_wait_sec=frame_wait_sec):
                print("[SUCCESS] Stream is working on:", masked)
                if proc.poll() is None:
                    proc.terminate()
                return 0
            if one_url_per_tunnel:
                break

        print("[WARN] No stream in this tunnel attempt; restarting tunnel...")
        if proc.poll() is None:
            proc.terminate()
            time.sleep(1)
            if proc.poll() is None:
                proc.kill()
        time.sleep(2)

    print("[ERROR] Could not read frames from relay tunnel after retries")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
