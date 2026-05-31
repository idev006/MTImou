# IMOU Remote Stream Report (2026-05-31)

## Goal

Receive live video stream from IMOU camera into local program over remote network, with no always-on device at home.

## Confirmed Working Path

- Camera: IMOU Ranger 2
- Firmware line seen in logs: `6.6.21001`
- Tunnel: `dh-p2p` Python relay mode
- Local ingest URL:
  - `rtsp://127.0.0.1:554/cam/realmonitor?channel=1&subtype=0`
- Python runtime:
  - `F:\programming\python\MTImou\.venv\Scripts\python.exe`

## What Was Fixed

1. Hard crash on stream drop (`RuntimeError`) in OpenCV viewer loop.
- Fix: changed to resilient recovery flow.
- New behavior: when tunnel/frame fails, app re-runs bootstrap attempts and continues instead of exiting.

2. Decoder thread instability (`cv2.error` / FFmpeg async lock side effects).
- Fix: catch read exceptions in reader thread, guard release path, and re-bootstrap safely.

3. `run_viewer.bat` confusion for subtype override.
- Root cause: values from `camera.env.bat` overwrote user pre-set values.
- Fix: batch now supports argument override and skips `camera.env.bat` if `IMOU_CAMERA_SN` already exists.

## Stable Commands (Operator Runbook)

1. Clean old processes first:

```bat
cd /d F:\programming\python\MTImou
run_stop_all.bat
```

2. Watch video with ffplay (default, more tolerant for live view):

```bat
run_viewer.bat
```

3. Force subtype directly from command line:

```bat
run_viewer.bat 1
```

4. Force subtype and channel:

```bat
run_viewer.bat 0 0
```

5. OpenCV viewer (with auto-recovery loop):

```bat
run_viewer_opencv.bat
```

## Notes for Operations

- Intermittent relay drops are expected on unofficial P2P/relay path.
- Current design now handles these by repeated bootstrap/reconnect.
- If window freezes or stream disappears, run `run_stop_all.bat` then `run_viewer.bat` again.

## Residual Risks

- Reverse-engineered protocol can break after firmware/cloud behavior change.
- Relay quality can vary by region/time, causing temporary stalls.
- For long sessions, keep monitoring reconnect frequency in logs.
