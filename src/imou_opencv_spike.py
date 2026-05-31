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
from typing import Any

import cv2
import numpy as np

from venv_guard import enforce_venv_python


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
    tunnel_restart_cooldown_sec: float
    recover_backoff_sec: float
    ffmpeg_bin_dir: str
    capture_backend: str


@dataclass(slots=True)
class SessionStats:
    bootstrap_successes: int = 0
    stall_events: int = 0
    capture_only_recover_successes: int = 0
    capture_only_recover_failures: int = 0
    tunnel_restarts: int = 0
    tunnel_restart_skips_cooldown: int = 0
    first_frame_latency_sec: float = -1.0


CaptureLike = Any


def last_good_subtype_path() -> Path:
    explicit = os.getenv("IMOU_LAST_GOOD_SUBTYPE_FILE", "").strip()
    if explicit:
        return Path(explicit)
    return Path("logs") / "last_good_subtype.txt"


def load_last_good_subtype() -> str | None:
    path = last_good_subtype_path()
    try:
        value = path.read_text(encoding="utf-8").strip()
    except OSError:
        return None
    return value if value in {"0", "1"} else None


def save_last_good_subtype(subtype: str) -> None:
    if subtype not in {"0", "1"}:
        return
    path = last_good_subtype_path()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(subtype, encoding="utf-8")
    except OSError:
        pass


def subtype_from_url(url: str) -> str | None:
    marker = "subtype="
    idx = url.find(marker)
    if idx < 0:
        return None
    value = url[idx + len(marker) : idx + len(marker) + 1]
    return value if value in {"0", "1"} else None


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
    tunnel_restart_cooldown_sec = float(os.getenv("IMOU_TUNNEL_RESTART_COOLDOWN_SEC", "45"))
    recover_backoff_sec = float(os.getenv("IMOU_RECOVER_BACKOFF_SEC", "2.5"))
    ffmpeg_bin_dir = os.getenv("FFMPEG_BIN_DIR", r"F:\ffmpeg\bin").strip()
    capture_backend = os.getenv("IMOU_CAPTURE_BACKEND", "ffmpeg_pipe").strip().lower()

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
        tunnel_restart_cooldown_sec=tunnel_restart_cooldown_sec,
        recover_backoff_sec=recover_backoff_sec,
        ffmpeg_bin_dir=ffmpeg_bin_dir,
        capture_backend=capture_backend,
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


def build_rtsp_urls(cfg: SpikeConfig) -> list[str]:
    remembered = load_last_good_subtype()
    preferred = remembered or (cfg.subtype if cfg.subtype in {"0", "1"} else "0")
    other = "1" if preferred == "0" else "0"
    urls: list[str] = []
    for subtype in [preferred, other]:
        if cfg.include_rtsp_auth:
            urls.append(
                f"rtsp://{cfg.username}:{cfg.password}@{cfg.rtsp_host}:{cfg.rtsp_port}"
                f"/cam/realmonitor?channel={cfg.rtsp_channel}&subtype={subtype}"
            )
        else:
            urls.append(
                f"rtsp://{cfg.rtsp_host}:{cfg.rtsp_port}"
                f"/cam/realmonitor?channel={cfg.rtsp_channel}&subtype={subtype}"
            )
    return urls


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


class FFmpegPipeCapture:
    def __init__(self, url: str, ffmpeg_path: Path) -> None:
        self.url = url
        self.ffmpeg_path = ffmpeg_path
        self.stop_event = Event()
        self.frames: Queue[np.ndarray] = Queue(maxsize=2)
        self.last_error: str | None = None
        self.proc: subprocess.Popen | None = None
        self.reader_thread: Thread | None = None
        self.stderr_thread: Thread | None = None
        self._opened = False
        self._start()

    def _start(self) -> None:
        analyzeduration = os.getenv("IMOU_FFPIPE_ANALYZEDURATION", "1000000").strip()
        probesize = os.getenv("IMOU_FFPIPE_PROBESIZE", "1000000").strip()
        rw_timeout_us = os.getenv("IMOU_RTSP_FFMPEG_RW_TIMEOUT_US", "2000000").strip()
        cmd = [
            str(self.ffmpeg_path),
            "-hide_banner",
            "-loglevel",
            "error",
            "-rtsp_transport",
            "tcp",
            "-rw_timeout",
            rw_timeout_us,
            "-analyzeduration",
            analyzeduration,
            "-probesize",
            probesize,
            "-fflags",
            "nobuffer",
            "-flags",
            "low_delay",
            "-i",
            self.url,
            "-f",
            "image2pipe",
            "-vcodec",
            "mjpeg",
            "-q:v",
            "5",
            "pipe:1",
        ]
        self.proc = subprocess.Popen(
            cmd,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            bufsize=0,
        )
        self.reader_thread = Thread(target=self._pump_stdout, daemon=True)
        self.stderr_thread = Thread(target=self._pump_stderr, daemon=True)
        self.reader_thread.start()
        self.stderr_thread.start()

    def _pump_stderr(self) -> None:
        assert self.proc is not None
        assert self.proc.stderr is not None
        for raw in self.proc.stderr:
            if self.stop_event.is_set():
                break
            line = raw.decode("utf-8", errors="replace").strip()
            if line:
                self.last_error = line

    def _pump_stdout(self) -> None:
        assert self.proc is not None
        assert self.proc.stdout is not None
        buf = bytearray()
        while not self.stop_event.is_set():
            chunk = self.proc.stdout.read(4096)
            if not chunk:
                break
            buf.extend(chunk)
            while True:
                start = buf.find(b"\xff\xd8")
                if start < 0:
                    if len(buf) > 1024 * 1024:
                        del buf[:-2]
                    break
                end = buf.find(b"\xff\xd9", start + 2)
                if end < 0:
                    if start > 0:
                        del buf[:start]
                    break
                jpg = bytes(buf[start : end + 2])
                del buf[: end + 2]
                arr = np.frombuffer(jpg, dtype=np.uint8)
                frame = cv2.imdecode(arr, cv2.IMREAD_COLOR)
                if frame is None:
                    continue
                self._opened = True
                if self.frames.full():
                    try:
                        self.frames.get_nowait()
                    except Empty:
                        pass
                self.frames.put(frame)

    def isOpened(self) -> bool:
        return self.proc is not None and self.proc.poll() is None

    def read(self) -> tuple[bool, np.ndarray | None]:
        try:
            frame = self.frames.get(timeout=0.5)
            return True, frame
        except Empty:
            if self.proc is not None and self.proc.poll() is not None and self.last_error:
                raise RuntimeError(f"ffmpeg exited: {self.last_error}")
            return False, None

    def release(self) -> None:
        self.stop_event.set()
        if self.proc is not None and self.proc.poll() is None:
            try:
                self.proc.terminate()
                self.proc.wait(timeout=3)
            except Exception:
                try:
                    self.proc.kill()
                except Exception:
                    pass
        if self.reader_thread is not None:
            self.reader_thread.join(timeout=1)
        if self.stderr_thread is not None:
            self.stderr_thread.join(timeout=1)


def open_capture(cfg: SpikeConfig, url: str):
    if cfg.capture_backend == "ffmpeg_pipe":
        ffmpeg = Path(cfg.ffmpeg_bin_dir) / "ffmpeg.exe"
        if ffmpeg.exists():
            return FFmpegPipeCapture(url, ffmpeg)
        print(f"[WARN] ffmpeg not found for ffmpeg_pipe backend: {ffmpeg}. Falling back to OpenCV.")
    ff_timeout_us = os.getenv("IMOU_RTSP_FFMPEG_TIMEOUT_US", "5000000").strip()
    ff_rw_timeout_us = os.getenv("IMOU_RTSP_FFMPEG_RW_TIMEOUT_US", ff_timeout_us).strip()
    ff_max_delay_us = os.getenv("IMOU_RTSP_FFMPEG_MAX_DELAY_US", "500000").strip()
    ff_opts = [
        "rtsp_transport;tcp",
        f"timeout;{ff_timeout_us}",
        f"rw_timeout;{ff_rw_timeout_us}",
        f"max_delay;{ff_max_delay_us}",
    ]
    os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "|".join(ff_opts)
    cap = cv2.VideoCapture(url, cv2.CAP_FFMPEG)
    try:
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        open_timeout_ms = int(os.getenv("IMOU_CAPTURE_OPEN_TIMEOUT_MS", "6000"))
        read_timeout_ms = int(os.getenv("IMOU_CAPTURE_READ_TIMEOUT_MS", "6000"))
        cap.set(cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, open_timeout_ms)
        cap.set(cv2.CAP_PROP_READ_TIMEOUT_MSEC, read_timeout_ms)
    except Exception:
        pass
    return cap


class FrameReader:
    def __init__(self, cap: CaptureLike) -> None:
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


def try_open_reader_timed(
    cfg: SpikeConfig,
    rtsp_url: str,
    timeout_sec: float,
) -> tuple[CaptureLike | None, FrameReader | None, str | None]:
    result: dict[str, object] = {"cap": None, "reader": None, "err": None}
    done = Event()

    def worker() -> None:
        cap = open_capture(cfg, rtsp_url)
        if not cap.isOpened():
            try:
                cap.release()
            except Exception:
                pass
            result["err"] = "open_failed"
            done.set()
            return
        reader = FrameReader(cap)
        if not wait_first_frame(reader, cfg.first_frame_timeout_sec):
            stop_reader_and_release(reader, cap)
            result["err"] = "first_frame_timeout"
            done.set()
            return
        result["cap"] = cap
        result["reader"] = reader
        done.set()

    t = Thread(target=worker, daemon=True)
    t.start()
    if not done.wait(timeout=timeout_sec):
        return None, None, "worker_timeout"
    return (
        result["cap"] if result["cap"] is not None else None,
        result["reader"] if isinstance(result["reader"], FrameReader) else None,
        result["err"] if isinstance(result["err"], str) else None,
    )


def stop_reader_and_release(reader: FrameReader | None, cap: CaptureLike | None) -> None:
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


def bootstrap_session(
    cfg: SpikeConfig,
    repo_dir: Path,
    rtsp_urls: list[str],
    phase: str = "bootstrap",
) -> tuple[subprocess.Popen, CaptureLike, FrameReader] | None:
    for attempt in range(1, cfg.bootstrap_attempts + 1):
        print(f"[INFO] {phase} attempt {attempt}/{cfg.bootstrap_attempts}")
        print("[INFO] Starting tunnel process...")
        tunnel = start_tunnel(cfg, repo_dir)
        ready, lines = wait_tunnel_ready(tunnel, cfg.startup_wait_sec)
        if not ready:
            stop_process(tunnel)
            tail = "\n".join(lines[-12:]) if lines else "(no tunnel output)"
            print(
                f"[WARN] Tunnel not ready in {phase} attempt.\n"
                f"Recent tunnel log:\n{tail}"
            )
            time.sleep(1.0)
            continue

        cap = None
        reader = None
        opened = False
        for rtsp_url in rtsp_urls:
            print("[INFO] Opening RTSP:", rtsp_url.replace(cfg.password, "***"))
            cap, reader, err = try_open_reader_timed(
                cfg,
                rtsp_url,
                timeout_sec=max(cfg.first_frame_timeout_sec + 3.0, 8.0),
            )
            if cap is None or reader is None:
                print(f"[WARN] RTSP open failed on this subtype in {phase} attempt ({err})")
                continue
            opened = True
            break

        if not opened or cap is None or reader is None:
            stop_process(tunnel)
            time.sleep(1.0)
            continue

        chosen_subtype = subtype_from_url(rtsp_url)
        if chosen_subtype is not None:
            save_last_good_subtype(chosen_subtype)
        print(f"[INFO] {phase} success.")
        return tunnel, cap, reader

    return None


def recover_capture_only(
    cfg: SpikeConfig,
    rtsp_urls: list[str],
    cap: CaptureLike | None,
    reader: FrameReader | None,
    phase: str = "recover:capture-only",
) -> tuple[CaptureLike, FrameReader] | None:
    saw_worker_timeout = False
    for attempt in range(1, 3):
        print(f"[INFO] {phase} attempt {attempt}/2")
        stop_reader_and_release(reader, cap)
        for rtsp_url in rtsp_urls:
            print("[INFO] Reopen RTSP:", rtsp_url.replace(cfg.password, "***"))
            cap2, reader2, err = try_open_reader_timed(
                cfg,
                rtsp_url,
                timeout_sec=max(min(cfg.first_frame_timeout_sec, 6.0) + 2.0, 6.0),
            )
            if cap2 is None or reader2 is None:
                print(f"[WARN] Reopen failed in {phase} attempt ({err})")
                if err == "worker_timeout":
                    saw_worker_timeout = True
                    break
                continue
            chosen_subtype = subtype_from_url(rtsp_url)
            if chosen_subtype is not None:
                save_last_good_subtype(chosen_subtype)
            print(f"[INFO] {phase} success.")
            return cap2, reader2
        if saw_worker_timeout:
            print(f"[WARN] {phase}: worker timeout detected, escalate to tunnel restart")
            return None
        time.sleep(0.6)
    return None


def main() -> None:
    enforce_venv_python()
    print(f"[INFO] Runtime python: {sys.executable}")
    cfg = load_config()
    repo_dir = Path(os.getenv("DH_P2P_REPO_DIR", "")).resolve()
    if not str(repo_dir) or str(repo_dir) == ".":
        raise ValueError("Missing env DH_P2P_REPO_DIR")

    rtsp_urls = build_rtsp_urls(cfg)
    tunnel: subprocess.Popen | None = None
    cap: CaptureLike | None = None
    reader: FrameReader | None = None
    stats = SessionStats()
    started_at = time.monotonic()
    last_tunnel_restart_ts = 0.0

    while True:
        boot = bootstrap_session(cfg, repo_dir, rtsp_urls, phase="bootstrap")
        if boot is not None:
            tunnel, cap, reader = boot
            stats.bootstrap_successes += 1
            stats.first_frame_latency_sec = time.monotonic() - started_at
            break
        print("[WARN] Bootstrap failed after retries. Waiting 5s before next round...")
        time.sleep(5.0)

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
                print("[WARN] Tunnel exited. Re-bootstrap session...")
                stop_reader_and_release(reader, cap)
                stop_process(tunnel)
                last_tunnel_restart_ts = time.monotonic()
                stats.tunnel_restarts += 1
                boot = bootstrap_session(cfg, repo_dir, rtsp_urls, phase="recover:tunnel-exit")
                if boot is None:
                    print("[WARN] Recover failed after tunnel exit. Sleep 5s and retry recovery.")
                    time.sleep(5.0)
                    continue
                tunnel, cap, reader = boot
                stats.bootstrap_successes += 1
                last_frame = None
                last_frame_ts = time.monotonic()
                continue

            if reader.last_exception:
                print(f"[WARN] Reader exception detected, restarting capture+tunnel... {reader.last_exception}")
                reader.last_exception = None
                rec = recover_capture_only(cfg, rtsp_urls, cap, reader, phase="recover:reader-exception")
                if rec is not None:
                    cap, reader = rec
                    stats.capture_only_recover_successes += 1
                    last_frame = None
                    last_frame_ts = time.monotonic()
                    continue
                stats.capture_only_recover_failures += 1
                stop_reader_and_release(reader, cap)
                stop_process(tunnel)
                last_tunnel_restart_ts = time.monotonic()
                stats.tunnel_restarts += 1
                boot = bootstrap_session(cfg, repo_dir, rtsp_urls, phase="recover:reader-exception")
                if boot is None:
                    print("[WARN] Recover failed after reader exception. Sleep 5s and retry recovery.")
                    time.sleep(5.0)
                    continue
                tunnel, cap, reader = boot
                stats.bootstrap_successes += 1
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
                stats.stall_events += 1
                rec = recover_capture_only(cfg, rtsp_urls, cap, reader, phase="recover:stalled-frame:capture-only")
                if rec is not None:
                    cap, reader = rec
                    stats.capture_only_recover_successes += 1
                    last_frame = None
                    last_frame_ts = time.monotonic()
                    continue
                stats.capture_only_recover_failures += 1
                now = time.monotonic()
                since_tunnel_restart = now - last_tunnel_restart_ts
                if since_tunnel_restart < cfg.tunnel_restart_cooldown_sec:
                    wait_left = cfg.tunnel_restart_cooldown_sec - since_tunnel_restart
                    stats.tunnel_restart_skips_cooldown += 1
                    print(
                        f"[WARN] Skip tunnel restart due cooldown; wait {wait_left:.1f}s, backoff..."
                    )
                    time.sleep(min(wait_left, cfg.recover_backoff_sec))
                    continue
                stop_reader_and_release(reader, cap)
                stop_process(tunnel)
                last_tunnel_restart_ts = time.monotonic()
                stats.tunnel_restarts += 1
                boot = bootstrap_session(cfg, repo_dir, rtsp_urls, phase="recover:stalled-frame")
                if boot is None:
                    print(
                        "[WARN] Recover failed after stalled frame. "
                        f"Sleep {cfg.recover_backoff_sec:.1f}s and retry recovery."
                    )
                    time.sleep(cfg.recover_backoff_sec)
                    continue
                tunnel, cap, reader = boot
                stats.bootstrap_successes += 1
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
        total_sec = time.monotonic() - started_at
        print(
            "[SUMMARY]",
            f"uptime_sec={total_sec:.1f}",
            f"first_frame_sec={stats.first_frame_latency_sec:.1f}",
            f"bootstrap_successes={stats.bootstrap_successes}",
            f"stall_events={stats.stall_events}",
            f"capture_recover_ok={stats.capture_only_recover_successes}",
            f"capture_recover_fail={stats.capture_only_recover_failures}",
            f"tunnel_restarts={stats.tunnel_restarts}",
            f"restart_cooldown_skips={stats.tunnel_restart_skips_cooldown}",
        )
        try:
            stop_reader_and_release(reader, cap)
        except Exception:
            pass
        if not cfg.headless:
            cv2.destroyAllWindows()
        stop_process(tunnel)


if __name__ == "__main__":
    main()
