from __future__ import annotations

import os
import sys
from pathlib import Path

THIS_DIR = Path(__file__).resolve().parent
if str(THIS_DIR) not in sys.path:
    sys.path.insert(0, str(THIS_DIR))

from mtimou_v2.resilience import run_resilience_smoke
from venv_guard import enforce_venv_python


def main() -> int:
    enforce_venv_python()
    camera_ids = [arg for arg in sys.argv[1:] if not arg.startswith("--")]
    modes_raw = os.getenv("IMOU_RESILIENCE_MODES", "lan,ddns,public")
    modes = [part.strip().lower() for part in modes_raw.split(",") if part.strip()]
    cycles = int(os.getenv("IMOU_RESILIENCE_CYCLES", "3"))
    sleep_sec = float(os.getenv("IMOU_RESILIENCE_SLEEP_SEC", "1.5"))
    tcp_timeout = float(os.getenv("IMOU_HEALTH_TCP_TIMEOUT_SEC", "2.0"))
    frame_timeout = float(os.getenv("IMOU_HEALTH_FRAME_TIMEOUT_SEC", "5.0"))
    return run_resilience_smoke(
        modes=modes,
        cycles=cycles,
        sleep_sec=sleep_sec,
        tcp_timeout=tcp_timeout,
        frame_timeout=frame_timeout,
        camera_ids=camera_ids or None,
    )


if __name__ == "__main__":
    raise SystemExit(main())
