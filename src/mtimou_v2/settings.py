from __future__ import annotations

import os
from pathlib import Path

from mtimou_v2.models import ViewerRuntimeSettings
from mtimou_v2.numeric_parsing import parse_env_float, parse_env_int


def viewer_runtime_settings(*, log_path: Path, window_name: str) -> ViewerRuntimeSettings:
    return ViewerRuntimeSettings(
        test_seconds=parse_env_float("IMOU_DIRECT_TEST_SECONDS", 0.0),
        restart_idle_sec=parse_env_float("IMOU_DIRECT_NO_FRAME_RESTART_SEC", 8.0),
        reconnect_sleep_sec=parse_env_float("IMOU_DIRECT_RECONNECT_SLEEP_SEC", 1.5),
        first_frame_timeout_sec=parse_env_float("IMOU_DIRECT_FIRST_FRAME_TIMEOUT_SEC", 6.0),
        target_probe_timeout_sec=parse_env_float("IMOU_TARGET_PROBE_TIMEOUT_SEC", 1.2),
        preferred_mode=os.getenv("IMOU_TARGET_MODE", "auto").strip().lower(),
        remote_multi_subtype=os.getenv("IMOU_REMOTE_MULTI_SUBTYPE", "1").strip(),
        remote_single_subtype=os.getenv("IMOU_REMOTE_SINGLE_SUBTYPE", "").strip(),
        wait_key_ms=max(1, parse_env_int("IMOU_VIEW_WAITKEY_MS", 1)),
        multi_tile_width=max(160, parse_env_int("IMOU_MULTI_TILE_WIDTH", 480)),
        multi_tile_height=max(120, parse_env_int("IMOU_MULTI_TILE_HEIGHT", 270)),
        log_path=log_path,
        window_name=window_name,
    )
