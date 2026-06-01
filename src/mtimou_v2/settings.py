from __future__ import annotations

import os
from pathlib import Path

from mtimou_v2.models import ViewerRuntimeSettings


def viewer_runtime_settings(*, log_path: Path, window_name: str) -> ViewerRuntimeSettings:
    return ViewerRuntimeSettings(
        test_seconds=float(os.getenv("IMOU_DIRECT_TEST_SECONDS", "0") or "0"),
        restart_idle_sec=float(os.getenv("IMOU_DIRECT_NO_FRAME_RESTART_SEC", "8")),
        reconnect_sleep_sec=float(os.getenv("IMOU_DIRECT_RECONNECT_SLEEP_SEC", "1.5")),
        first_frame_timeout_sec=float(os.getenv("IMOU_DIRECT_FIRST_FRAME_TIMEOUT_SEC", "6")),
        target_probe_timeout_sec=float(os.getenv("IMOU_TARGET_PROBE_TIMEOUT_SEC", "1.2")),
        preferred_mode=os.getenv("IMOU_TARGET_MODE", "auto").strip().lower(),
        remote_multi_subtype=os.getenv("IMOU_REMOTE_MULTI_SUBTYPE", "1").strip(),
        remote_single_subtype=os.getenv("IMOU_REMOTE_SINGLE_SUBTYPE", "").strip(),
        log_path=log_path,
        window_name=window_name,
    )
