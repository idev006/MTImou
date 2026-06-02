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
- Runtime failover is implemented on reconnect (`LAN -> DDNS -> public` in `auto` mode)
- Mode selection supports `auto`, `lan`, `ddns`, `public`

## Runtime Rules

- Always use project Python only:
  - `F:\programming\python\MTImou\.venv\Scripts\python.exe`
- Desktop control panel uses `PySide6` installed in the same `.venv`
- Camera secrets and runtime defaults live in `camera.env.bat`
- Recommended N-camera password naming: `IMOU_CAM_<CAMERA_ID_UPPER>_PASSWORD`
- Camera registry lives in [`cameras.json`](./cameras.json)

## Quick Start

Recommended operator entrypoint:

```bat
cd /d F:\programming\python\MTImou
run_control_panel.bat
```

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

High-FPS split view for remote operation:

```bat
cd /d F:\programming\python\MTImou
run_multi_camera_high_fps.bat cam1 cam2
```

Source capability check:

```bat
cd /d F:\programming\python\MTImou
run_source_capability_check.bat cam1 cam2
```

Grid behavior:

- `1 camera` -> `1x1`
- `2 cameras` -> `1x2`
- `3-4 cameras` -> `2x2`
- `5-9 cameras` -> `3x3`
- `10-16 cameras` -> square-ish grid, but grouped wall views are recommended over one giant always-on board
- `17-100 cameras` -> grouped wall views and focused split views are the supported operating model

Backward-compatible default:

```bat
cd /d F:\programming\python\MTImou
run_direct_stable.bat
```

System health check:

```bat
cd /d F:\programming\python\MTImou
run_system_health_check.bat
```

Resilience smoke check:

```bat
cd /d F:\programming\python\MTImou
run_resilience_smoke.bat cam1 cam2
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

## FPS Tuning

For remote multi-camera tiled viewing, the runtime now defaults to substream on `ddns/public`
targets to improve FPS and reduce uplink pressure:

- `IMOU_REMOTE_MULTI_SUBTYPE=1` (default)

Useful overrides:

```bat
set IMOU_REMOTE_MULTI_SUBTYPE=1
set IMOU_REMOTE_SINGLE_SUBTYPE=0
```

Notes:

- Multi-camera remote viewing usually performs better with `subtype=1`
- Single-camera remote viewing can stay on `subtype=0` for higher detail
- Multi-camera viewing now uses parallel camera readers so one stream no longer drags the other down as much
- `run_multi_camera_high_fps.bat` now defaults to main stream (`subtype=0`) so it does not artificially cap source FPS
- If you need the highest practical FPS per camera, use `run_multi_camera_high_fps.bat` so each camera runs in its own viewer process
- Use `run_source_capability_check.bat` to separate camera-source limits from viewer/runtime limits before tuning further

## N-Camera Strategy

The production model now supports `N cameras` with data-driven fields per camera, for any integer `1 <= N <= 100`:

- `group_name`
- `tier`
- `remote_wall_subtype`
- `remote_focus_subtype`

Recommended operating pattern for large `N`:

- wall view:
  - group-based or all-enabled
  - `remote_wall_subtype=1`
- focus view:
  - selected cameras only
  - `remote_focus_subtype=0`

The control panel now lets the operator:

- manage group and tier per camera
- select cameras by group
- filter cameras by group and tier
- search large inventories
- save and reuse selection presets
- add preset description and default launch mode
- launch `critical` tier cameras directly
- launch a filtered group directly
- bulk-edit group/tier/wall/focus policy in camera management
- bulk enable or disable selected cameras
- save presets with `normal` or `high-fps` launch intent
- run presets directly from the dashboard
- define wall vs focus stream policy per camera
- see enabled camera counts by tier on the dashboard
- resize the app window safely with x/y scrolling when content is tighter than the viewport
- work with collapsible settings and inventory sections
- reopen the UI with the last window size, tab, and section state restored

## Control Panel Safety Guards

The control panel now includes operator-safety protections for repeated clicks and draft changes:

- launch buttons use a short cooldown so repeated clicks do not spawn duplicate viewer batches immediately
- preset execution now runs against the preset's stored `camera_ids`, even if the table currently has search/group/tier filters applied
- if `Camera Management` has unsaved changes, the UI prompts `Save / Discard / Cancel` before:
  - reloading settings
  - launching viewers
  - running health/source checks
  - closing the control panel
- saving a preset with an existing name now asks for overwrite confirmation
- `Open Logs` and `Open README` are debounced to avoid spamming duplicate OS windows
- `camera.env.bat` is loaded in a streaming, compacting way so pathological blank-line growth cannot make the control panel unusable

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

- `src/mtimou_v2/`
  - Clean production-core rewrite for config, target selection, viewers, health, and resilience
- `src/mtimou_v2/viewmodels/`
  - MVVM foundation for the operator UI
- [`run_camera_stable.bat`](./run_camera_stable.bat)
  - Run one camera by `camera-id`
- [`run_multi_camera_stable.bat`](./run_multi_camera_stable.bat)
  - Run multiple cameras in one window
- [`run_direct_stable.bat`](./run_direct_stable.bat)
  - Default single-camera entrypoint, currently points to `cam1`
- [`run_system_health_check.bat`](./run_system_health_check.bat)
  - Validate LAN, DDNS, and public paths with TCP and RTSP first-frame checks
- [`run_resilience_smoke.bat`](./run_resilience_smoke.bat)
  - Repeat first-frame checks across selected modes/cycles to catch short-lived instability
- [`run_control_panel.bat`](./run_control_panel.bat)
  - Desktop control panel for launching cameras, selecting mode, editing common settings, managing camera inventory, onboarding new cameras, and running health checks
- [`src/direct_rtsp_opencv.py`](./src/direct_rtsp_opencv.py)
  - Single-camera live viewer with reconnect logic
- [`src/multi_camera_view.py`](./src/multi_camera_view.py)
  - Multi-camera tiled viewer
- [`src/camera_registry.py`](./src/camera_registry.py)
  - Camera config loading and target selection
## Logs

- Single camera:
  - `logs\direct_<camera-id>_latest.log`
- Multi camera:
  - `logs\multi_camera_latest.log`

Each viewer writes a `[SUMMARY]` line on exit.

## Failure Handling

- If a stream stalls, the viewer will reopen the stream automatically
- In `auto` mode, reconnects re-evaluate `LAN`, then `DDNS`, then `public`
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
- [`docs/12-production-hardening-plan.md`](./docs/12-production-hardening-plan.md)
- [`docs/13-incident-runbook.md`](./docs/13-incident-runbook.md)
- [`docs/14-final-acceptance-checklist.md`](./docs/14-final-acceptance-checklist.md)
- [`docs/15-cam3-cam4-rollout-template.md`](./docs/15-cam3-cam4-rollout-template.md)
- [`docs/16-ui-control-panel-plan.md`](./docs/16-ui-control-panel-plan.md)
- [`docs/18-clean-runtime-rewrite-plan.md`](./docs/18-clean-runtime-rewrite-plan.md)
- [`docs/19-actors-usecases-sequences.md`](./docs/19-actors-usecases-sequences.md)
- [`docs/20-ui-mvvm-ssot-architecture.md`](./docs/20-ui-mvvm-ssot-architecture.md)
- [`docs/21-robustness-process-engineering.md`](./docs/21-robustness-process-engineering.md)
- [`docs/22-n-camera-architecture.md`](./docs/22-n-camera-architecture.md)

Scale-out templates:

- [`cameras.scaleout.template.json`](./cameras.scaleout.template.json)
- [`cameras.ten-camera.template.json`](./cameras.ten-camera.template.json)

## Legacy Archive

Historical relay-era, Rust probe, OpenAPI spike, and troubleshooting scripts have
been moved to [`legacy`](./legacy). They are preserved for reference, but they
are no longer part of the supported production runtime path.

## Roadmap

- Add real DDNS hostname configuration and failover validation
- Expand tiled layout for `N > 2`
- Add recording and snapshot flows per camera
