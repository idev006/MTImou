from __future__ import annotations

import subprocess
from dataclasses import replace
from fractions import Fraction
import os
from pathlib import Path

from mtimou_v2.logging_utils import make_logger
from mtimou_v2.registry import enabled_cameras, get_camera
from mtimou_v2.targets import pick_target
from mtimou_v2.viewer_common import effective_camera_profile
from mtimou_v2.settings import viewer_runtime_settings


ROOT_DIR = Path(__file__).resolve().parents[2]


def resolve_ffprobe_path() -> Path:
    env_bin = os.getenv("FFMPEG_BIN_DIR", "").strip()
    candidates = []
    if env_bin:
        candidates.append(Path(env_bin) / "ffprobe.exe")
    candidates.extend(
        [
            Path(r"F:\ffmpeg\bin\ffprobe.exe"),
            ROOT_DIR / "ffmpeg" / "bin" / "ffprobe.exe",
            ROOT_DIR.parent / "ffmpeg" / "bin" / "ffprobe.exe",
        ]
    )
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return candidates[0]


def _fraction_to_float(value: str) -> float:
    value = value.strip()
    if not value:
        return 0.0
    try:
        return float(Fraction(value))
    except Exception:
        return 0.0


def _probe_stream(ffprobe_path: Path, url: str, duration_sec: float) -> dict[str, str]:
    cmd = [
        str(ffprobe_path),
        "-v",
        "error",
        "-rtsp_transport",
        "tcp",
        "-count_frames",
        "-read_intervals",
        f"%+{max(1, int(duration_sec))}",
        "-select_streams",
        "v:0",
        "-show_entries",
        "stream=codec_name,width,height,avg_frame_rate,r_frame_rate,nb_read_frames",
        "-of",
        "default=nw=1",
        url,
    ]
    cp = subprocess.run(cmd, capture_output=True, text=True, timeout=max(20, int(duration_sec) + 20))
    if cp.returncode != 0:
        raise RuntimeError(cp.stderr.strip() or f"ffprobe failed with code {cp.returncode}")
    result: dict[str, str] = {}
    for line in cp.stdout.splitlines():
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        result[key.strip()] = value.strip()
    return result


def run_source_capability_check(
    *,
    camera_ids: list[str] | None,
    mode: str,
    duration_sec: float,
    log_path: Path,
) -> int:
    ffprobe_path = resolve_ffprobe_path()
    if not ffprobe_path.exists():
        print(f"[ERROR] Missing ffprobe: {ffprobe_path}")
        return 101

    cameras = [get_camera(camera_id) for camera_id in camera_ids] if camera_ids else enabled_cameras()
    if not cameras:
        print("[ERROR] No cameras configured.")
        return 2

    settings = viewer_runtime_settings(log_path=log_path, window_name="MTImou Source Capability Check")
    settings = replace(settings, preferred_mode=mode.strip().lower() or "public")
    log = make_logger(log_path)
    log(
        f"[INFO] Source capability check mode={settings.preferred_mode} "
        f"duration_sec={duration_sec:.1f} cameras={','.join(camera.camera_id for camera in cameras)}"
    )

    hard_failures = 0
    for camera in cameras:
        target = pick_target(camera, preferred_mode=settings.preferred_mode, timeout_sec=settings.target_probe_timeout_sec)
        log(
            f"[INFO] Camera={camera.camera_id} name={camera.name} mode={target.mode} "
            f"target={target.host}:{target.port}"
        )
        for subtype in ("0", "1"):
            probe_camera = replace(camera, subtype=subtype)
            runtime_camera = effective_camera_profile(
                probe_camera,
                target_mode=target.mode,
                camera_count=1,
                settings=replace(settings, remote_single_subtype=subtype),
            )
            from mtimou_v2.rtsp import build_rtsp_url

            url, safe_url = build_rtsp_url(runtime_camera, target)
            try:
                info = _probe_stream(ffprobe_path, url, duration_sec)
            except Exception as exc:
                hard_failures += 1
                log(
                    f"[ERROR] camera={camera.camera_id} subtype={subtype} "
                    f"url={safe_url} probe_failed={exc}"
                )
                continue

            avg_frame_rate = info.get("avg_frame_rate", "")
            nb_read_frames = int(info.get("nb_read_frames", "0") or "0")
            measured_fps = nb_read_frames / max(duration_sec, 1e-6)
            log(
                f"[RESULT] camera={camera.camera_id} subtype={subtype} codec={info.get('codec_name', '?')} "
                f"size={info.get('width', '?')}x{info.get('height', '?')} "
                f"r_frame_rate={info.get('r_frame_rate', '?')} avg_frame_rate={avg_frame_rate or '?'} "
                f"avg_frame_rate_num={_fraction_to_float(avg_frame_rate):.2f} "
                f"nb_read_frames={nb_read_frames} measured_fps={measured_fps:.2f}"
            )

    log(
        f"[SUMMARY] cameras={len(cameras)} hard_failures={hard_failures} "
        f"mode={settings.preferred_mode} duration_sec={duration_sec:.1f} log={log_path}"
    )
    return 0 if hard_failures == 0 else 1
