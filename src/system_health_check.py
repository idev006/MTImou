from __future__ import annotations

import os
import sys
from pathlib import Path

THIS_DIR = Path(__file__).resolve().parent
if str(THIS_DIR) not in sys.path:
    sys.path.insert(0, str(THIS_DIR))

from mtimou_v2.health import run_health_check
from venv_guard import enforce_venv_python


ROOT_DIR = Path(__file__).resolve().parents[1]


def main() -> int:
    enforce_venv_python()
    args = [arg for arg in sys.argv[1:] if not arg.startswith("--")]
    modes_raw = os.getenv("IMOU_HEALTH_MODES", "lan,ddns,public")
    modes = [part.strip().lower() for part in modes_raw.split(",") if part.strip()]
    required_modes_raw = os.getenv("IMOU_HEALTH_REQUIRED_MODES", modes_raw)
    required_modes = {part.strip().lower() for part in required_modes_raw.split(",") if part.strip()}
    tcp_timeout = float(os.getenv("IMOU_HEALTH_TCP_TIMEOUT_SEC", "2.0"))
    frame_timeout = float(os.getenv("IMOU_HEALTH_FRAME_TIMEOUT_SEC", "5.0"))
    log_path = Path(os.getenv("IMOU_HEALTH_LOG_PATH", str(ROOT_DIR / "logs" / "system_health_check_latest.log")))
    return run_health_check(
        modes=modes,
        required_modes=required_modes,
        tcp_timeout=tcp_timeout,
        frame_timeout=frame_timeout,
        log_path=log_path,
        camera_ids=args or None,
    )


if __name__ == "__main__":
    raise SystemExit(main())
