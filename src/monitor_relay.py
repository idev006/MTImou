from __future__ import annotations

import os
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


@dataclass(slots=True)
class MonitorConfig:
    runs: int
    interval_sec: float
    python_exe: str
    logs_dir: Path


def load_config() -> MonitorConfig:
    runs = int(os.getenv("IMOU_MONITOR_RUNS", "6"))
    interval_sec = float(os.getenv("IMOU_MONITOR_INTERVAL_SEC", "6"))
    python_exe = os.getenv("IMOU_MONITOR_PYTHON_EXE", "").strip() or sys.executable
    logs_dir = Path(os.getenv("IMOU_MONITOR_LOGS_DIR", "logs")).resolve()
    return MonitorConfig(
        runs=runs,
        interval_sec=interval_sec,
        python_exe=python_exe,
        logs_dir=logs_dir,
    )


def main() -> int:
    cfg = load_config()
    cfg.logs_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_path = cfg.logs_dir / f"relay_monitor_{ts}.log"

    success_count = 0
    results: list[tuple[int, bool, float]] = []

    print(f"[INFO] Monitor runs={cfg.runs}, interval={cfg.interval_sec:.1f}s")
    print(f"[INFO] Log file: {log_path}")

    with log_path.open("w", encoding="utf-8") as logf:
        for idx in range(1, cfg.runs + 1):
            cmd = [cfg.python_exe, "-u", "src\\relay_stream_test.py"]
            start = time.monotonic()
            print(f"[INFO] Run {idx}/{cfg.runs} starting...")
            logf.write(f"\n===== RUN {idx}/{cfg.runs} =====\n")
            logf.flush()

            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
            )

            ok = False
            assert proc.stdout is not None
            for line in proc.stdout:
                line = line.rstrip("\r\n")
                print(line)
                logf.write(line + "\n")
                if "[SUCCESS] Stream is working on:" in line:
                    ok = True

            rc = proc.wait()
            elapsed = time.monotonic() - start
            if rc == 0 and ok:
                success_count += 1
            else:
                ok = False
            results.append((idx, ok, elapsed))

            status = "SUCCESS" if ok else "FAIL"
            print(f"[INFO] Run {idx} result={status} elapsed={elapsed:.1f}s")
            logf.write(f"[RESULT] run={idx} status={status} elapsed={elapsed:.1f}s rc={rc}\n")
            logf.flush()

            if idx < cfg.runs:
                time.sleep(cfg.interval_sec)

        total = len(results)
        rate = (success_count / total * 100.0) if total else 0.0
        summary = (
            f"[SUMMARY] success={success_count}/{total} "
            f"({rate:.1f}%) log={log_path}"
        )
        print(summary)
        logf.write(summary + "\n")

    return 0 if success_count > 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())

