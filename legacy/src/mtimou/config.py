from __future__ import annotations

import os
from dataclasses import dataclass

from .models import CameraCredentials


@dataclass(slots=True)
class AppConfig:
    credentials: CameraCredentials
    max_retries: int = 20
    backoff_initial_sec: float = 1.0
    backoff_max_sec: float = 30.0
    stream_probe_seconds: int = 60


def load_config_from_env() -> AppConfig:
    sn = os.getenv("IMOU_CAMERA_SN", "").strip()
    safety = os.getenv("IMOU_CAMERA_SAFETY_CODE", "").strip()

    if not sn:
        raise ValueError("Missing env IMOU_CAMERA_SN")
    if not safety:
        raise ValueError("Missing env IMOU_CAMERA_SAFETY_CODE")

    return AppConfig(
        credentials=CameraCredentials(serial_number=sn, safety_code=safety),
        max_retries=int(os.getenv("MTIMOU_MAX_RETRIES", "20")),
        backoff_initial_sec=float(os.getenv("MTIMOU_BACKOFF_INITIAL_SEC", "1")),
        backoff_max_sec=float(os.getenv("MTIMOU_BACKOFF_MAX_SEC", "30")),
        stream_probe_seconds=int(os.getenv("MTIMOU_STREAM_PROBE_SECONDS", "60")),
    )

