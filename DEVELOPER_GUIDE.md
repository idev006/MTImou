# Developer Guide

This guide is the shortest path for a new engineer to get productive in `MTImou`.

## 1. First-Time Setup

```bat
cd /d F:\programming\python\MTImou
setup_windows.bat
run_doctor.bat
```

Expected result:

- `.venv` exists
- pinned dependencies are installed
- `camera.env.bat` exists or a clear warning explains what is missing
- `cameras.json` loads correctly

If `run_doctor.bat` reports `FAIL`, fix those first. `WARN` usually means user-specific
camera credentials or hostnames still need to be filled in.

## 2. Recommended Entry Points

Operator UI:

```bat
run_control_panel.bat
```

Single camera:

```bat
run_camera_stable.bat cam1
```

Multi-camera wall view:

```bat
run_multi_camera_stable.bat cam1 cam2
```

High-FPS split view:

```bat
run_multi_camera_high_fps.bat cam1 cam2
```

Health and diagnostics:

```bat
run_system_health_check.bat
run_resilience_smoke.bat cam1 cam2
run_source_capability_check.bat cam1 cam2
run_performance_benchmark.bat cam1 cam2
run_doctor.bat
```

## 3. Production vs Legacy

Production path:

- `src/mtimou_v2/`
- `src/control_panel_app/`
- top-level `run_*.bat` launchers that are still in the project root

Historical/archived path:

- [`legacy`](./legacy)

Do not add new production behavior into `legacy`. Use it only for historical reference.

## 4. Code Map

### Core runtime

- [`src/mtimou_v2/registry.py`](F:\programming\python\MTImou\src\mtimou_v2\registry.py)
  - loads `cameras.json`
  - resolves password env names
- [`src/mtimou_v2/targets.py`](F:\programming\python\MTImou\src\mtimou_v2\targets.py)
  - picks `lan`, `ddns`, or `public`
- [`src/mtimou_v2/rtsp.py`](F:\programming\python\MTImou\src\mtimou_v2\rtsp.py)
  - builds RTSP URLs
  - opens OpenCV capture
- [`src/mtimou_v2/viewer_common.py`](F:\programming\python\MTImou\src\mtimou_v2\viewer_common.py)
  - reconnect logic
  - failover logic
  - multi-reader helpers
- [`src/mtimou_v2/single_viewer.py`](F:\programming\python\MTImou\src\mtimou_v2\single_viewer.py)
  - single-camera runtime
- [`src/mtimou_v2/multi_viewer.py`](F:\programming\python\MTImou\src\mtimou_v2\multi_viewer.py)
  - tiled multi-camera runtime

### UI

- [`src/control_panel.py`](F:\programming\python\MTImou\src\control_panel.py)
  - thin entrypoint
- [`src/control_panel_app/window.py`](F:\programming\python\MTImou\src\control_panel_app\window.py)
  - layout, tabs, responsive behavior
- [`src/control_panel_app/state_mixin.py`](F:\programming\python\MTImou\src\control_panel_app\state_mixin.py)
  - table refresh, filters, metrics
- [`src/control_panel_app/actions_mixin.py`](F:\programming\python\MTImou\src\control_panel_app\actions_mixin.py)
  - user-triggered actions, guards, dialogs
- [`src/mtimou_v2/viewmodels/control_panel_vm.py`](F:\programming\python\MTImou\src\mtimou_v2\viewmodels\control_panel_vm.py)
  - UI orchestration and persistence bridge

### Persistence and configuration

- [`camera.env.bat`](F:\programming\python\MTImou\camera.env.bat)
  - user- and machine-specific runtime settings
- [`camera.env.bat.example`](F:\programming\python\MTImou\camera.env.bat.example)
  - starter template
- [`cameras.json`](F:\programming\python\MTImou\cameras.json)
  - camera inventory and target topology
- [`src/mtimou_v2/settings_store.py`](F:\programming\python\MTImou\src\mtimou_v2\settings_store.py)
  - safe env-file loading and atomic save
- [`src/mtimou_v2/camera_config_store.py`](F:\programming\python\MTImou\src\mtimou_v2\camera_config_store.py)
  - `cameras.json` round-trip
- [`src/mtimou_v2/preset_store.py`](F:\programming\python\MTImou\src\mtimou_v2\preset_store.py)
  - selection presets

## 5. Normal Developer Workflow

1. Run `run_doctor.bat`
2. Make changes
3. Re-run at least:
   - `run_doctor.bat`
   - `run_system_health_check.bat`
4. If viewer behavior changed:
   - `run_source_capability_check.bat`
   - `run_performance_benchmark.bat`
5. If UI behavior changed:
   - open `run_control_panel.bat`
   - exercise the changed workflow manually

## 6. Safety Rules

- Always use `.venv\Scripts\python.exe`
- Prefer editing production code under `src/mtimou_v2` and `src/control_panel_app`
- Keep UI and runtime changes consistent with `README.md`
- Do not remove safety guards lightly:
  - launch cooldown
  - dirty inventory prompts
  - preset execution by stored camera ids
  - atomic env-file writes

## 7. Where To Read Next

- [`README.md`](F:\programming\python\MTImou\README.md)
- [`docs/22-n-camera-architecture.md`](F:\programming\python\MTImou\docs\22-n-camera-architecture.md)
- [`docs/20-ui-mvvm-ssot-architecture.md`](F:\programming\python\MTImou\docs\20-ui-mvvm-ssot-architecture.md)
- [`docs/multi-camera-runbook.md`](F:\programming\python\MTImou\docs\multi-camera-runbook.md)
