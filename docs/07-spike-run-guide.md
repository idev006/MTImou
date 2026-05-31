# Spike Run Guide (dh-p2p + OpenCV)

## 1) Prerequisites

- Active venv: `F:\programming\python\MTImou\.venv`
- Local clone of `khoanguyen-3fc/dh-p2p`
- Install dependencies in your venv:
  - OpenCV (`opencv-python`)
  - dh-p2p repo requirements

## 2) Environment Variables (cmd)

```bat
cd /d F:\programming\python\MTImou
.venv\Scripts\activate

set DH_P2P_REPO_DIR=F:\path\to\dh-p2p
set IMOU_CAMERA_SN=YOUR_CAMERA_SN
set IMOU_CAMERA_USERNAME=admin
set IMOU_CAMERA_PASSWORD=YOUR_PASSWORD
set IMOU_CAMERA_TYPE=0
set IMOU_FORCE_RELAY=1
set IMOU_RTSP_SUBTYPE=1
set IMOU_RTSP_HOST=127.0.0.1
set IMOU_RTSP_PORT=554
set IMOU_RTSP_INCLUDE_AUTH=1
set IMOU_RTSP_TRY_ANON=0
set IMOU_USE_FFPROBE=0
set IMOU_ONE_URL_PER_TUNNEL=1
```

## 3) Run

```bat
python F:\programming\python\MTImou\src\imou_opencv_spike.py
```

Press `q` to quit.

Quick verification-only run:
```bat
python F:\programming\python\MTImou\src\relay_stream_test.py
```

Recommended one-command remote run:
```bat
cd /d F:\programming\python\MTImou
run_relay_test.bat
```

Remote free diagnostic run (Rust tunnel + ffprobe matrix):
```bat
cd /d F:\programming\python\MTImou
run_rust_probe.bat
```

## 4) Notes

- If RTSP fails, try `IMOU_RTSP_SUBTYPE=1`.
- If tunnel exits, script auto-restarts it.
- If frame reads fail repeatedly, script restarts tunnel and reconnects.
- `dh-p2p` Python PoC is unstable by design; relay mode is usually more reliable than direct mode.
- For IMOU Ranger 2 (`DevVersion 6.6.21001`), use relay mode + auth URL first for higher success rate.
- Use `docs/09-remote-free-dhp2p-status.md` as the current source of truth for remote-free status.

## 5) Official OpenAPI Path (Recommended)

Run the official Imou Cloud live flow:

```bat
cd /d F:\programming\python\MTImou
run_openapi_live_test.bat
```

Required env vars (in `camera.env.bat` or prompt):

- `IMOU_APP_ID`
- `IMOU_APP_SECRET`
- `IMOU_CAMERA_SN`
- `IMOU_OPENAPI_DC` (`sg`/`fk`/`or`) or `IMOU_OPENAPI_DOMAIN`

Output:

- HLS URL printed in console
- Result json: `F:\programming\python\MTImou\logs\openapi_live_result.json`
