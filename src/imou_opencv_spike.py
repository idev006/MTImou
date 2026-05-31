from __future__ import annotations

import os
import signal
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from threading import Event, Thread
from queue import Queue, Empty

import cv2
import numpy as np


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
    no_frame_restart_sec: float
    headless: bool
    headless_target_frames: int
    max_session_sec: float
    bootstrap_attempts: int
    first_frame_timeout_sec: float


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
    no_frame_restart_sec = float(os.getenv("IMOU_NO_FRAME_RESTART_SEC", "12"))
    headless = os.getenv("IMOU_HEADLESS", "0").strip() == "1"
    headless_target_frames = int(os.getenv("IMOU_HEADLESS_TARGET_FRAMES", "180"))
    max_session_sec = float(os.getenv("IMOU_MAX_SESSION_SEC", "0"))
    bootstrap_attempts = int(os.getenv("IMOU_BOOTSTRAP_ATTEMPTS", "4"))
    first_frame_timeout_sec = float(os.getenv("IMOU_FIRST_FRAME_TIMEOUT_SEC", "8"))

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
        no_frame_restart_sec=no_frame_restart_sec,
        headless=headless,
        headless_target_frames=headless_target_frames,
        max_session_sec=max_session_sec,
        bootstrap_attempts=bootstrap_attempts,
        first_frame_timeout_sec=first_frame_timeout_sec,
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
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        cap.set(cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, 10000)
        cap.set(cv2.CAP_PROP_READ_TIMEOUT_MSEC, 10000)
    except Exception:
        pass
    return cap


class FrameReader:
    def __init__(self, cap: cv2.VideoCapture) -> None:
        self.cap = cap
        self.stop_event = Event()
        self.queue: Queue = Queue(maxsize=1)
        self.read_failures = 0
        self.total_frames = 0
        self.last_ok_ts = time.monotonic()
        self.last_exception: str | None = None
        self.thread = Thread(target=self._run, daemon=True)
        self.thread.start()

    def _run(self) -> None:
        while not self.stop_event.is_set():
            try:
                ok, frame = self.cap.read()
            except cv2.error as exc:
                self.read_failures += 1
                self.last_exception = f"cv2.error: {exc}"
                time.sleep(0.1)
                continue
            except Exception as exc:
                self.read_failures += 1
                self.last_exception = f"{type(exc).__name__}: {exc}"
                time.sleep(0.1)
                continue
            if not ok:
                self.read_failures += 1
                time.sleep(0.05)
                continue

            self.read_failures = 0
            self.total_frames += 1
            self.last_ok_ts = time.monotonic()
            if self.queue.full():
                try:
                    self.queue.get_nowait()
                except Empty:
                    pass
            self.queue.put(frame)

    def get_latest(self, timeout: float = 0.05):
        try:
            return self.queue.get(timeout=timeout)
        except Empty:
            return None

    def stop(self, timeout_sec: float = 12.0) -> bool:
        self.stop_event.set()
        self.thread.join(timeout=timeout_sec)
        return not self.thread.is_alive()


def stop_reader_and_release(reader: FrameReader | None, cap: cv2.VideoCapture | None) -> None:
    stopped = True
    if reader is not None:
        stopped = reader.stop(timeout_sec=12.0)
        if not stopped:
            print("[WARN] FrameReader thread did not stop in time; skip cap.release() to avoid decoder crash.")
    if cap is not None and stopped:
        try:
            cap.release()
        except Exception as exc:
            print(f"[WARN] cap.release() failed: {exc}")


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


def wait_first_frame(reader: FrameReader, timeout_sec: float) -> bool:
    deadline = time.monotonic() + timeout_sec
    while time.monotonic() < deadline:
        if reader.get_latest(timeout=0.05) is not None:
            return True
    return False


def main() -> None:
    cfg = load_config()
    repo_dir = Path(os.getenv("DH_P2P_REPO_DIR", "")).resolve()
    if not str(repo_dir) or str(repo_dir) == ".":
        raise ValueError("Missing env DH_P2P_REPO_DIR")

    rtsp_url = build_rtsp_url(cfg)
    tunnel: subprocess.Popen | None = None
    cap: cv2.VideoCapture | None = None
    reader: FrameReader | None = None

    for attempt in range(1, cfg.bootstrap_attempts + 1):
        print(f"[INFO] Bootstrap attempt {attempt}/{cfg.bootstrap_attempts}")
        print("[INFO] Starting tunnel process...")
        tunnel = start_tunnel(cfg, repo_dir)
        ready, lines = wait_tunnel_ready(tunnel, cfg.startup_wait_sec)
        if not ready:
            stop_process(tunnel)
            tail = "\n".join(lines[-12:]) if lines else "(no tunnel output)"
            print(
                "[WARN] Tunnel not ready in bootstrap attempt.\n"
                f"Recent tunnel log:\n{tail}"
            )
            continue

        print("[INFO] Opening RTSP:", rtsp_url.replace(cfg.password, "***"))
        cap = open_capture(rtsp_url)
        if not cap.isOpened():
            print("[WARN] RTSP open failed on this tunnel, retrying...")
            cap.release()
            stop_process(tunnel)
            continue

        reader = FrameReader(cap)
        if not wait_first_frame(reader, cfg.first_frame_timeout_sec):
            print("[WARN] No first frame yet, restarting bootstrap...")
            stop_reader_and_release(reader, cap)
            stop_process(tunnel)
            reader = None
            cap = None
            tunnel = None
            continue
        break
    else:
        raise RuntimeError(
            "Failed to bootstrap stream after retries. "
            "Relay session established but no decodable frame arrived."
        )
    assert tunnel is not None
    assert cap is not None
    assert reader is not None

    print("[INFO] Stream connected. Press 'q' to exit.")
    print(
        "[INFO] Health guard:",
        f"restart if no frame for {cfg.no_frame_restart_sec:.1f}s",
        f"(headless={cfg.headless})",
    )
    last_frame = None
    last_frame_ts = time.monotonic()
    session_started = time.monotonic()
    no_frame_warn_logged_at = 0.0

    if not cfg.headless:
        cv2.namedWindow("IMOU Remote Stream", cv2.WINDOW_NORMAL)

    try:
        while True:
            # Keep UI event loop active to avoid "Not Responding" on Windows.
            if not cfg.headless:
                key = cv2.waitKey(20) & 0xFF
                if key == ord("q"):
                    break

            if tunnel.poll() is not None:
                print("[WARN] Tunnel exited. Restarting...")
                stop_reader_and_release(reader, cap)
                stop_process(tunnel)
                tunnel = start_tunnel(cfg, repo_dir)
                ready, lines = wait_tunnel_ready(tunnel, cfg.startup_wait_sec)
                if not ready:
                    tail = "\n".join(lines[-12:]) if lines else "(no tunnel output)"
                    raise RuntimeError(
                        "Tunnel restart failed to become ready.\n"
                        f"Recent tunnel log:\n{tail}"
                    )
                cap = open_capture(rtsp_url)
                reader = FrameReader(cap)
                last_frame_ts = time.monotonic()
                continue

            if reader.last_exception:
                print(f"[WARN] Reader exception detected, restarting capture+tunnel... {reader.last_exception}")
                reader.last_exception = None
                stop_reader_and_release(reader, cap)
                stop_process(tunnel)
                tunnel = start_tunnel(cfg, repo_dir)
                ready, lines = wait_tunnel_ready(tunnel, cfg.startup_wait_sec)
                if not ready:
                    tail = "\n".join(lines[-12:]) if lines else "(no tunnel output)"
                    raise RuntimeError(
                        "Tunnel restart failed after reader exception.\n"
                        f"Recent tunnel log:\n{tail}"
                    )
                cap = open_capture(rtsp_url)
                if not cap.isOpened():
                    raise RuntimeError("Cannot reopen RTSP after reader exception restart.")
                reader = FrameReader(cap)
                last_frame = None
                last_frame_ts = time.monotonic()
                continue

            frame = reader.get_latest(timeout=0.02)
            if frame is None:
                idle_sec = time.monotonic() - reader.last_ok_ts
                now = time.monotonic()
                if idle_sec >= 1.5 and now - no_frame_warn_logged_at >= 2.0:
                    print(f"[WARN] No frame for {idle_sec:.1f}s")
                    no_frame_warn_logged_at = now

                if idle_sec < cfg.no_frame_restart_sec:
                    if not cfg.headless and last_frame is None:
                        canvas = np.zeros((360, 640, 3), dtype=np.uint8)
                        cv2.putText(
                            canvas,
                            "Waiting for first frame...",
                            (20, 90),
                            cv2.FONT_HERSHEY_SIMPLEX,
                            0.8,
                            (0, 200, 255),
                            2,
                            cv2.LINE_AA,
                        )
                        cv2.putText(
                            canvas,
                            f"idle={idle_sec:.1f}s",
                            (20, 140),
                            cv2.FONT_HERSHEY_SIMPLEX,
                            0.7,
                            (180, 180, 180),
                            2,
                            cv2.LINE_AA,
                        )
                        cv2.imshow("IMOU Remote Stream", canvas)
                    continue

                print(
                    "[WARN] Frame stalled, restarting capture+tunnel...",
                    f"idle={idle_sec:.1f}s",
                )
                stop_reader_and_release(reader, cap)
                stop_process(tunnel)
                tunnel = start_tunnel(cfg, repo_dir)
                ready, lines = wait_tunnel_ready(tunnel, cfg.startup_wait_sec)
                if not ready:
                    tail = "\n".join(lines[-12:]) if lines else "(no tunnel output)"
                    raise RuntimeError(
                        "Tunnel restart failed after read errors.\n"
                        f"Recent tunnel log:\n{tail}"
                    )
                cap = open_capture(rtsp_url)
                if not cap.isOpened():
                    raise RuntimeError("Cannot reopen RTSP after tunnel restart.")
                reader = FrameReader(cap)
                last_frame = None
                last_frame_ts = time.monotonic()
                continue

            last_frame = frame
            last_frame_ts = time.monotonic()

            if cfg.headless and reader.total_frames >= cfg.headless_target_frames:
                elapsed = time.monotonic() - session_started
                fps = reader.total_frames / max(elapsed, 0.001)
                print(
                    f"[SUCCESS] Headless stream OK: {reader.total_frames} frames in "
                    f"{elapsed:.2f}s ({fps:.2f} fps)"
                )
                return

            if not cfg.headless:
                elapsed = time.monotonic() - session_started
                fps = reader.total_frames / max(elapsed, 0.001)
                cv2.putText(
                    last_frame,
                    f"frames={reader.total_frames} fps~{fps:.1f}",
                    (20, 35),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.75,
                    (80, 255, 80),
                    2,
                    cv2.LINE_AA,
                )
                cv2.putText(
                    last_frame,
                    time.strftime("%Y-%m-%d %H:%M:%S"),
                    (20, 70),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.7,
                    (80, 220, 255),
                    2,
                    cv2.LINE_AA,
                )
                cv2.imshow("IMOU Remote Stream", last_frame)

            if cfg.max_session_sec > 0 and (time.monotonic() - session_started) >= cfg.max_session_sec:
                print("[INFO] Max session reached, stopping.")
                return
    finally:
        try:
            stop_reader_and_release(reader, cap)
        except Exception:
            pass
        if not cfg.headless:
            cv2.destroyAllWindows()
        stop_process(tunnel)


if __name__ == "__main__":
    main()
