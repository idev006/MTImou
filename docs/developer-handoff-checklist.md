# Developer Handoff Checklist

Use this checklist when a new engineer takes over `MTImou`, or when you hand work from one developer to another.

## 1. First-Day Setup

Run these in order:

```bat
cd /d F:\programming\python\MTImou
setup_windows.bat
run_doctor.bat
run_control_panel_smoke_audit.bat
run_control_panel.bat
```

Expected result:

- `.venv` exists and uses the project Python
- `run_doctor.bat` reports `ok` and no `fail`
- control-panel smoke audit passes
- the control panel opens without startup errors

## 2. Read These Files First

Read in this order:

1. [`../README.md`](../README.md)
2. [`../DEVELOPER_GUIDE.md`](../DEVELOPER_GUIDE.md)
3. [`20-ui-mvvm-ssot-architecture.md`](./20-ui-mvvm-ssot-architecture.md)
4. [`22-n-camera-architecture.md`](./22-n-camera-architecture.md)
5. [`multi-camera-runbook.md`](./multi-camera-runbook.md)
6. [`23-developer-architecture-map.md`](./23-developer-architecture-map.md)

## 3. Files You Must Understand

- `src/control_panel_app/window.py`
  - tab layout and responsive structure
- `src/control_panel_app/actions_mixin.py`
  - button actions, dialogs, launches, and diagnostics
- `src/control_panel_app/state_mixin.py`
  - filters, tables, metrics, and UI state refresh
- `src/mtimou_v2/viewmodels/control_panel_vm.py`
  - bridge between UI and persistence/runtime
- `src/mtimou_v2/viewer_common.py`
  - stream-state creation, reconnect, failover, effective subtype selection
- `src/mtimou_v2/settings_store.py`
  - safe `camera.env.bat` load/save behavior
- `src/mtimou_v2/camera_config_store.py`
  - `cameras.json` round-trip behavior

## 4. Local Files And Secrets

Do not commit live secrets from:

- `camera.env.bat`
- `camera_presets.json`
- generated logs under `logs/`

Use tracked templates instead:

- `camera.env.bat.example`
- `camera_presets.example.json`
- `cameras.example.json`

## 5. Before You Change Behavior

Check these first:

- is the behavior owned by UI, persistence, launcher, or runtime?
- is there already a safety guard that this change might weaken?
- does the change affect `LAN`, `DDNS`, `public`, or all three?
- does the change affect `main stream`, `substream`, or both?
- does the change require README or docs updates?

## 6. Verification Checklist

Always run:

```bat
cd /d F:\programming\python\MTImou
run_doctor.bat
run_control_panel_smoke_audit.bat
```

If UI behavior changed:

- open `run_control_panel.bat`
- exercise the changed workflow manually

If runtime/viewer behavior changed:

```bat
cd /d F:\programming\python\MTImou
run_system_health_check.bat
run_source_capability_check.bat cam1 cam2
run_performance_benchmark.bat cam1 cam2
```

## 7. Before You Hand Off Again

Make sure these are true:

- docs match the current behavior
- `CHANGELOG.md` has a short entry for meaningful changes
- `VERSION` is bumped only when you intentionally define a new baseline
- local-only files were not committed
- the next engineer knows which commands to run first

## 8. Good Handoff Note Template

Include these bullets in your handoff:

- what changed
- which files matter most
- what was verified
- what is still risky or unverified
- whether any local secrets or local files need manual setup
