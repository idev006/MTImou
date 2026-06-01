# Multi-Camera Runbook

## Modes

- `auto`: prefer `LAN`, then `DDNS` if configured, then `public`
- `lan`: force local RTSP
- `ddns`: force DDNS hostname target
- `public`: force public IP/port target

Set mode with:

```bat
set IMOU_TARGET_MODE=auto
```

## Single Camera

```bat
cd /d F:\programming\python\MTImou
run_camera_stable.bat cam1
run_camera_stable.bat cam2
```

## Multi Camera

```bat
cd /d F:\programming\python\MTImou
run_multi_camera_stable.bat cam1 cam2
```

## Health Check

```bat
cd /d F:\programming\python\MTImou
run_system_health_check.bat
```

This checks:

- `.venv` runtime
- `LAN` target
- `DDNS` target
- `public` target
- TCP reachability
- RTSP first-frame acquisition

Grid behavior:

- `1 camera` -> `1x1`
- `2 cameras` -> `1x2`
- `3-4 cameras` -> `2x2`
- `5-9 cameras` -> `3x3`

Optional manual override:

```bat
set IMOU_MULTI_GRID_COLS=2
```

## Current Mapping

- `cam1` / `Front House`
  - LAN: `192.168.1.2:554`
  - Public: `125.27.213.148:45554`
- `cam2` / `Side House`
  - LAN: `192.168.1.5:554`
  - Public: `125.27.213.148:45555`

## Worldwide Access

- Works now through `public` mode because both forwarded ports are live.
- If the home's public IP changes after an ISP reconnect, set `ddns_host` in `cameras.json` and use `IMOU_TARGET_MODE=ddns` or leave `auto`.
- Current DDNS hostname: `biiigbee-home.servecounterstrike.com`
- You can also set one shared env hostname for the whole house:

```bat
set IMOU_DDNS_HOST=YOUR-HOSTNAME.ddns.net
```

- In that model, each camera still uses its own forwarded port.

## Logs

- Single camera logs: `logs\direct_<camera-id>_<mode>_latest.log`
- Multi camera log: `logs\multi_camera_latest.log`

## Failure Handling

- The viewers auto-reconnect after `IMOU_DIRECT_NO_FRAME_RESTART_SEC`
- A bad camera should not drag down a healthy camera in multi-view
- If a camera shows repeated auth failures, verify its password env in `camera.env.bat`
