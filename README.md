# MTImou

Multi-camera IMOU RTSP viewer for LAN and worldwide access, with automatic target selection, reconnect handling, and operator-focused runbooks.

## Current Status

- `cam1` / `Front House`
  - LAN: `192.168.1.2:554`
  - Public: `125.27.213.148:45554`
- `cam2` / `Side House`
  - LAN: `192.168.1.5:554`
  - Public: `125.27.213.148:45555`
- Local multi-camera viewer is working
- Public RTSP forwarding is working for both cameras
- Auto-reconnect is implemented
- Mode selection supports `auto`, `lan`, `ddns`, `public`

## Runtime Rules

- Always use project Python only:
  - `F:\programming\python\MTImou\.venv\Scripts\python.exe`
- Camera secrets and runtime defaults live in `camera.env.bat`
- Camera registry lives in [`cameras.json`](./cameras.json)

## Quick Start

Single camera:

```bat
cd /d F:\programming\python\MTImou
run_camera_stable.bat cam1
```

Second camera:

```bat
cd /d F:\programming\python\MTImou
run_camera_stable.bat cam2
```

Two cameras in one window:

```bat
cd /d F:\programming\python\MTImou
run_multi_camera_stable.bat cam1 cam2
```

Grid behavior:

- `1 camera` -> `1x1`
- `2 cameras` -> `1x2`
- `3-4 cameras` -> `2x2`
- `5-9 cameras` -> `3x3`

Backward-compatible default:

```bat
cd /d F:\programming\python\MTImou
run_direct_stable.bat
```

## Mode Selection

Supported values:

- `auto`: prefer `LAN`, then `DDNS`, then `public`
- `lan`: force local RTSP
- `ddns`: force DDNS hostname target
- `public`: force public IP/port target

Optional shared DDNS hostname for the whole house:

```bat
set IMOU_DDNS_HOST=YOUR-HOSTNAME.ddns.net
```

Example:

```bat
cd /d F:\programming\python\MTImou
set IMOU_TARGET_MODE=public
run_multi_camera_stable.bat cam1 cam2
```

## Public / Worldwide Access

This project already supports worldwide viewing through router port forwarding.

Current public targets:

- `cam1` -> `125.27.213.148:45554`
- `cam2` -> `125.27.213.148:45555`

Important note:

- If the ISP changes the home's public IP, direct public-IP access will stop working until the new IP is known.
- To harden this for real-world operations, configure DDNS in the router and then fill `ddns_host` in [`cameras.json`](./cameras.json).
- Current DDNS hostname: `biiigbee-home.servecounterstrike.com`

## Main Files

- [`run_camera_stable.bat`](./run_camera_stable.bat)
  - Run one camera by `camera-id`
- [`run_multi_camera_stable.bat`](./run_multi_camera_stable.bat)
  - Run multiple cameras in one window
- [`run_direct_stable.bat`](./run_direct_stable.bat)
  - Default single-camera entrypoint, currently points to `cam1`
- [`src/direct_rtsp_opencv.py`](./src/direct_rtsp_opencv.py)
  - Single-camera live viewer with reconnect logic
- [`src/multi_camera_view.py`](./src/multi_camera_view.py)
  - Multi-camera tiled viewer
- [`src/camera_registry.py`](./src/camera_registry.py)
  - Camera config loading and target selection
- [`src/router_live_control.py`](./src/router_live_control.py)
  - Browser-driven router helper used during setup and port-forward work

## Logs

- Single camera:
  - `logs\direct_<camera-id>_<mode>_latest.log`
- Multi camera:
  - `logs\multi_camera_latest.log`

Each viewer writes a `[SUMMARY]` line on exit.

## Failure Handling

- If a stream stalls, the viewer will reopen the stream automatically
- If one camera is bad in multi-view, healthy cameras should continue
- If a camera fails auth, check its password source in `camera.env.bat` and [`cameras.json`](./cameras.json)
- If public mode fails after the home internet reconnects, update to DDNS and use `IMOU_TARGET_MODE=ddns` or `auto`

## Configuration Pattern For More Cameras

To add camera `N+1`:

1. Add a new entry in [`cameras.json`](./cameras.json)
2. Give that camera a unique forwarded public port
3. Add its password env to `camera.env.bat`
4. Test LAN RTSP first
5. Test public RTSP second
6. Add it to `run_multi_camera_stable.bat` invocations as needed

## Documentation

Operational and architecture documents live in [`docs`](./docs):

- [`docs/README.md`](./docs/README.md)
- [`docs/multi-camera-runbook.md`](./docs/multi-camera-runbook.md)

## Roadmap

- Add real DDNS hostname configuration and failover validation
- Expand tiled layout for `N > 2`
- Add recording and snapshot flows per camera
