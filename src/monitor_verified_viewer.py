from __future__ import annotations

import os
import subprocess
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


@dataclass(slots=True)
class Config:
    runs: int
    interval_sec: float
    subtype: str
    autoexit_sec: str
    verify_sec: str
    logs_dir: Path
    repo_root: Path


def load_config() -> Config:
    repo_root = Path(__file__).resolve().parents[1]
    runs = int(os.getenv("IMOU_MONITOR_RUNS", "12"))
    interval_sec = float(os.getenv("IMOU_MONITOR_INTERVAL_SEC", "8"))
    subtype = os.getenv("IMOU_RTSP_SUBTYPE", "0").strip() or "0"
    autoexit_sec = os.getenv("IMOU_FFPLAY_AUTOEXIT_SEC", "15").strip() or "15"
    verify_sec = os.getenv("IMOU_FFPLAY_VERIFY_SEC", "5").strip() or "5"
    logs_dir = Path(os.getenv("IMOU_MONITOR_LOGS_DIR", str(repo_root / "logs"))).resolve()
    return Config(runs, interval_sec, subtype, autoexit_sec, verify_sec, logs_dir, repo_root)


def main() -> int:
    cfg = load_config()
    cfg.logs_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    summary_log = cfg.logs_dir / f"verified_monitor_{ts}.log"

    ok_runs = 0
    print(f"[INFO] Monitor verified viewer runs={cfg.runs}, interval={cfg.interval_sec}s")
    print(f"[INFO] Summary log: {summary_log}")

    with summary_log.open("w", encoding="utf-8") as outf:
        for i in range(1, cfg.runs + 1):
            run_log = cfg.logs_dir / f"verified_run_{ts}_{i:03d}.log"
            env = os.environ.copy()
            env["IMOU_VERIFIED_VIEWER"] = "ffplay"
            env["IMOU_FFPLAY_AUTOEXIT_SEC"] = cfg.autoexit_sec
            env["IMOU_FFPLAY_VERIFY_SEC"] = cfg.verify_sec

            start = time.monotonic()
            cmd = ["cmd", "/c", f"run_viewer_verified.bat {cfg.subtype}"]
            print(f"[INFO] Run {i}/{cfg.runs} starting...")

            with run_log.open("w", encoding="utf-8") as runf:
                proc = subprocess.Popen(
                    cmd,
                    cwd=str(cfg.repo_root),
                    env=env,
                    stdout=runf,
                    stderr=subprocess.STDOUT,
                    text=True,
                )
                rc = proc.wait()

            elapsed = time.monotonic() - start
            text = run_log.read_text(encoding="utf-8", errors="replace")
            ok = (
                rc == 0
                and "[SUCCESS] Verified stream on:" in text
                and "[INFO] Exit code: 0" in text
            )
            if ok:
                ok_runs += 1

            status = "SUCCESS" if ok else "FAIL"
            line = f"[RESULT] run={i} status={status} rc={rc} elapsed={elapsed:.1f}s log={run_log}"
            print(line)
            outf.write(line + "\n")
            outf.flush()

            if i < cfg.runs:
                time.sleep(cfg.interval_sec)

        rate = (ok_runs / cfg.runs) * 100.0 if cfg.runs else 0.0
        summary = f"[SUMMARY] success={ok_runs}/{cfg.runs} ({rate:.1f}%)"
        print(summary)
        outf.write(summary + "\n")

    return 0 if ok_runs == cfg.runs else 1


if __name__ == "__main__":
    raise SystemExit(main())

