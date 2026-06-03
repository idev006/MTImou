from __future__ import annotations

import os
import sys
from pathlib import Path

THIS_DIR = Path(__file__).resolve().parent
if str(THIS_DIR) not in sys.path:
    sys.path.insert(0, str(THIS_DIR))

from mtimou_v2.performance import run_performance_benchmark
from mtimou_v2.numeric_parsing import parse_env_float
from venv_guard import enforce_venv_python


ROOT_DIR = Path(__file__).resolve().parents[1]


def main() -> int:
    enforce_venv_python()
    camera_ids = [arg for arg in sys.argv[1:] if not arg.startswith("--")]
    mode = os.getenv("IMOU_PERF_MODE", "public")
    duration_sec = parse_env_float("IMOU_PERF_DURATION_SEC", 10.0)
    warmup_sec = parse_env_float("IMOU_PERF_WARMUP_SEC", 2.0)
    min_fps = parse_env_float("IMOU_PERF_MIN_FPS", 16.0)
    log_path = Path(os.getenv("IMOU_PERF_LOG_PATH", str(ROOT_DIR / "logs" / "performance_benchmark_latest.log")))
    return run_performance_benchmark(
        camera_ids=camera_ids or None,
        mode=mode,
        duration_sec=duration_sec,
        warmup_sec=warmup_sec,
        min_fps=min_fps,
        log_path=log_path,
    )


if __name__ == "__main__":
    raise SystemExit(main())
