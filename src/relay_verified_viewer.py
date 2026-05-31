from __future__ import annotations

import os
import signal
import subprocess
import sys
import threading
import time
from pathlib import Path

import cv2

from venv_guard import enforce_venv_python


def env(name: str, default: str) -> str:
    value = os.getenv(name, "").strip()
    return value if value else default


def as_bool(value: str) -> bool:
    return value.strip().lower() in {"1", "true", "yes", "on"}


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


def find_listening_pid_on_port(port: int) -> int | None:
    cmd = f'netstat -ano | findstr /R /C:":{port} .*LISTENING"'
    p = subprocess.run(cmd, capture_output=True, text=True, shell=True)
    if p.returncode != 0 or not p.stdout.strip():
        return None
    for line in p.stdout.splitlines():
        parts = line.split()
        if len(parts) >= 5:
            try:
                return int(parts[-1])
            except ValueError:
                continue
    return None


def ensure_rtsp_port_free(port: int) -> None:
    pid = find_listening_pid_on_port(port)
    if pid is None:
        return
    print(f"[WARN] Port {port} is busy by PID {pid}; terminating...")
    subprocess.run(f"taskkill /PID {pid} /T /F >nul 2>&1", shell=True)
    time.sleep(0.6)
    pid2 = find_listening_pid_on_port(port)
    if pid2 is not None:
        raise RuntimeError(f"Port {port} still busy by PID {pid2}")


def build_urls(host: str, port: str, channel: str, user: str, pwd: str, preferred_subtype: str) -> list[str]:
    subtype_order = [preferred_subtype] if preferred_subtype in {"0", "1"} else ["0", "1"]
    if preferred_subtype == "0":
        subtype_order = ["0", "1"]
    elif preferred_subtype == "1":
        subtype_order = ["1", "0"]
    urls: list[str] = []
    for subtype in subtype_order:
        urls.append(f"rtsp://{user}:{pwd}@{host}:{port}/cam/realmonitor?channel={channel}&subtype={subtype}")
    return urls


def wait_tunnel_ready(proc: subprocess.Popen, timeout_sec: int = 90) -> bool:
    deadline = time.time() + timeout_sec
    while time.time() < deadline and proc.poll() is None:
        time.sleep(0.2)
        if bool(getattr(proc, "_relay_ready", False)):
            return True
    return False


def can_read_frames(url: str, seconds: int = 8) -> bool:
    os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "rtsp_transport;tcp"
    cap = cv2.VideoCapture(url, cv2.CAP_FFMPEG)
    if not cap.isOpened():
        cap.release()
        return False
    start = time.time()
    ok_frames = 0
    while time.time() - start < seconds:
        ok, _ = cap.read()
        if ok:
            ok_frames += 1
            if ok_frames >= 3:
                cap.release()
                return True
        else:
            time.sleep(0.1)
    cap.release()
    return False


def show_opencv_stream(url: str) -> int:
    os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "rtsp_transport;tcp"
    cap = cv2.VideoCapture(url, cv2.CAP_FFMPEG)
    if not cap.isOpened():
        print("[ERROR] OpenCV cannot open verified RTSP URL")
        return 1

    cv2.namedWindow("IMOU Remote Stream (Verified)", cv2.WINDOW_NORMAL)
    frames = 0
    started = time.monotonic()
    last_ok = time.monotonic()
    first_frame_deadline = time.monotonic() + 12
    try:
        while True:
            ok, frame = cap.read()
            if ok:
                frames += 1
                last_ok = time.monotonic()
                fps = frames / max(time.monotonic() - started, 0.001)
                cv2.putText(
                    frame,
                    f"frames={frames} fps~{fps:.1f}",
                    (20, 35),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.75,
                    (80, 255, 80),
                    2,
                    cv2.LINE_AA,
                )
                cv2.putText(
                    frame,
                    time.strftime("%Y-%m-%d %H:%M:%S"),
                    (20, 70),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.7,
                    (80, 220, 255),
                    2,
                    cv2.LINE_AA,
                )
                cv2.imshow("IMOU Remote Stream (Verified)", frame)
            else:
                if frames == 0 and time.monotonic() > first_frame_deadline:
                    print("[WARN] No first frame from OpenCV within 12s")
                    return 2
                if (time.monotonic() - last_ok) > 8:
                    print("[WARN] Stream stalled for >8s, reopening capture...")
                    cap.release()
                    time.sleep(0.8)
                    cap = cv2.VideoCapture(url, cv2.CAP_FFMPEG)
                    last_ok = time.monotonic()

            key = cv2.waitKey(20) & 0xFF
            if key == ord("q"):
                return 0
    finally:
        cap.release()
        cv2.destroyAllWindows()


def run_ffplay(ffplay: Path, selected_url: str) -> int:
    if not ffplay.exists():
        print(f"[ERROR] ffplay not found: {ffplay}")
        return 2
    print("[INFO] Launching ffplay on verified tunnel...")
    ffplay_cmd = [
        str(ffplay),
        "-loglevel",
        "warning",
        "-rtsp_transport",
        "tcp",
        "-analyzeduration",
        env("IMOU_FFPLAY_ANALYZEDURATION", "2000000"),
        "-probesize",
        env("IMOU_FFPLAY_PROBESIZE", "1000000"),
    ]
    autoexit_sec = env("IMOU_FFPLAY_AUTOEXIT_SEC", "").strip()
    if autoexit_sec:
        ffplay_cmd.extend(["-t", autoexit_sec, "-autoexit"])
    ffplay_cmd.append(selected_url)
    return subprocess.call(ffplay_cmd)


def verify_with_ffplay(ffplay: Path, url: str) -> bool:
    if not ffplay.exists():
        print(f"[ERROR] ffplay not found: {ffplay}")
        return False
    test_sec = env("IMOU_FFPLAY_VERIFY_SEC", "6")
    cmd = [
        str(ffplay),
        "-v",
        "warning",
        "-rtsp_transport",
        "tcp",
        "-t",
        test_sec,
        "-autoexit",
        "-nodisp",
        url,
    ]
    return subprocess.call(cmd) == 0


def main() -> int:
    enforce_venv_python()
    print(f"[INFO] Runtime python: {sys.executable}")

    repo_dir = Path(env("DH_P2P_REPO_DIR", "")).resolve()
    if not str(repo_dir) or str(repo_dir) == ".":
        print("[ERROR] Missing DH_P2P_REPO_DIR")
        return 2

    serial = env("IMOU_CAMERA_SN", "")
    user = env("IMOU_CAMERA_USERNAME", "admin")
    pwd = env("IMOU_CAMERA_PASSWORD", "")
    ctype = env("IMOU_CAMERA_TYPE", "1")
    host = env("IMOU_RTSP_HOST", "127.0.0.1")
    port = env("IMOU_RTSP_PORT", "554")
    channel = env("IMOU_RTSP_CHANNEL", "1")
    preferred_subtype = env("IMOU_RTSP_SUBTYPE", "0")
    force_relay = as_bool(env("IMOU_FORCE_RELAY", "1"))
    attempts = int(env("IMOU_RELAY_ATTEMPTS", "4"))
    probe_wait_sec = int(env("IMOU_FRAME_WAIT_SEC", "8"))
    viewer_mode = env("IMOU_VERIFIED_VIEWER", "opencv").lower()
    ffmpeg_bin = Path(env("FFMPEG_BIN_DIR", r"F:\ffmpeg\bin"))
    ffplay = ffmpeg_bin / "ffplay.exe"
    if viewer_mode == "ffplay" and not ffplay.exists():
        print(f"[ERROR] ffplay not found: {ffplay}")
        return 2
    if not serial or not pwd:
        print("[ERROR] Missing IMOU_CAMERA_SN or IMOU_CAMERA_PASSWORD")
        return 2

    urls = build_urls(host, port, channel, user, pwd, preferred_subtype)
    tunnel_python = env("IMOU_TUNNEL_PYTHON_EXE", sys.executable)
    print("[INFO] Tunnel python:", tunnel_python)
    ensure_rtsp_port_free(int(port))

    for attempt in range(1, attempts + 1):
        ensure_rtsp_port_free(int(port))
        cmd = [tunnel_python, "-u", str(repo_dir / "main.py")]
        if force_relay:
            cmd.append("-r")
        cmd.extend(["-t", ctype, "-u", user, "-p", pwd, serial])
        print(f"[INFO] Tunnel attempt {attempt}/{attempts}: {' '.join(cmd)}")

        tunnel = subprocess.Popen(
            cmd,
            cwd=str(repo_dir),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )
        tunnel._relay_ready = False  # type: ignore[attr-defined]

        def pump() -> None:
            assert tunnel.stdout is not None
            for line in tunnel.stdout:
                line = line.rstrip("\r\n")
                print("[TUNNEL]", line)
                if "Ready to connect" in line:
                    tunnel._relay_ready = True  # type: ignore[attr-defined]

        t = threading.Thread(target=pump, daemon=True)
        t.start()

        if not wait_tunnel_ready(tunnel, timeout_sec=90):
            print("[WARN] Tunnel not ready in this attempt")
            stop_process(tunnel)
            continue

        selected_url: str | None = None
        for url in urls:
            masked = url.replace(pwd, "***")
            print("[INFO] Probe URL:", masked)
            if viewer_mode == "ffplay":
                if verify_with_ffplay(ffplay, url):
                    selected_url = url
                    break
            elif can_read_frames(url, seconds=probe_wait_sec):
                selected_url = url
                break

        if selected_url is None:
            print("[WARN] No decodable frames on this tunnel; retry...")
            stop_process(tunnel)
            time.sleep(1.5)
            continue

        masked = selected_url.replace(pwd, "***")
        print("[SUCCESS] Verified stream on:", masked)
        if viewer_mode == "ffplay":
            run_ffplay(ffplay, selected_url)
        else:
            print("[INFO] Launching OpenCV viewer on verified tunnel (press q to exit)...")
            rc = show_opencv_stream(selected_url)
            if rc != 0:
                print("[WARN] OpenCV viewer failed/stalled; fallback to ffplay...")
                run_ffplay(ffplay, selected_url)
        stop_process(tunnel)
        return 0

    print("[ERROR] Could not verify relay stream after retries")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
