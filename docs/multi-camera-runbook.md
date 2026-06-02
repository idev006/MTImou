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

High-FPS split view:

```bat
cd /d F:\programming\python\MTImou
run_multi_camera_high_fps.bat cam1 cam2
```

Source capability check:

```bat
cd /d F:\programming\python\MTImou
run_source_capability_check.bat cam1 cam2
```

## Health Check

```bat
cd /d F:\programming\python\MTImou
run_system_health_check.bat
```

Resilience smoke:

```bat
cd /d F:\programming\python\MTImou
run_resilience_smoke.bat cam1 cam2
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
- `10-16 cameras` -> grouped wall-view is recommended over one giant always-on board
- `17-100 cameras` -> grouped operation is the supported model

Optional manual override:

```bat
set IMOU_MULTI_GRID_COLS=2
```

## 10-Camera Operating Model

For larger deployments, each camera should carry:

- `group_name`
- `tier`
- `remote_wall_subtype`
- `remote_focus_subtype`

Recommended defaults:

- `remote_wall_subtype=1`
- `remote_focus_subtype=0`

Suggested usage:

- wall view:
  - all enabled cameras or one selected group
  - use substream to protect total system FPS
- focus view:
  - selected cameras only
  - use split-view mode with mainstream

Operator shortcuts now available in the control panel:

- search by camera/group/tier/host
- filter by group
- filter by tier
- launch `critical` tier cameras directly
- launch the currently filtered group directly
- save current selection as a preset
- attach a description and default launch mode to presets
- run a preset directly using its saved default mode
- run a preset in normal or high-FPS mode
- bulk enable/disable inventory rows
- bulk-edit `group`, `tier`, `wall`, and `focus` policy in inventory
- monitor enabled counts for `critical`, `standard`, and `archive` from dashboard cards
- resize the app and rely on x/y scrolling instead of crushed layouts
- collapse settings or inventory sections that are not needed right now
- reopen the control panel with the last active tab and section state restored

Suggested operator workflow for larger deployments:

1. Filter by `group` or `tier`
2. Launch a wall view for overview
3. Save recurring camera sets as presets
4. Use `High FPS` only for smaller focus sets or critical incidents
5. Disable archive cameras from day-to-day operations if they are not needed live

Suggested groups:

- `front`
- `side`
- `rear`
- `gate`
- `parking`
- `indoor`

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
- In `auto` mode, reconnects re-check `LAN`, then `DDNS`, then `public`
- A bad camera should not drag down a healthy camera in multi-view
- If a camera shows repeated auth failures, verify its password env in `camera.env.bat`
- If FPS is unexpectedly low, run `run_source_capability_check.bat` before tuning the viewer
