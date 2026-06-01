from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np


@dataclass(slots=True)
class CameraConfig:
    camera_id: str
    name: str
    lan_host: str
    lan_port: int
    ddns_host: str
    ddns_port: int
    public_host: str
    public_port: int
    channel: str
    subtype: str
    transport: str
    username: str
    password: str
    enabled: bool


@dataclass(slots=True)
class CameraTarget:
    camera: CameraConfig
    mode: str
    host: str
    port: int


@dataclass(slots=True)
class ViewerRuntimeSettings:
    test_seconds: float
    restart_idle_sec: float
    reconnect_sleep_sec: float
    first_frame_timeout_sec: float
    target_probe_timeout_sec: float
    preferred_mode: str
    log_path: Path
    window_name: str


@dataclass(slots=True)
class StreamState:
    camera: CameraConfig
    mode: str
    host: str
    port: int
    url: str
    safe_url: str
    cap: object | None
    frame_count: int = 0
    reconnects: int = 0
    failovers: int = 0
    started: float = 0.0
    last_ok: float = 0.0
    last_frame: np.ndarray | None = None
    next_retry_ts: float = 0.0
    status_text: str = ""
    target_key: tuple[str, str, int] | None = None

