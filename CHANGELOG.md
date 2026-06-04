# Changelog

All notable handoff-relevant changes to this repository should be recorded here.

This file is intentionally concise. It is for the next engineer, not for marketing.

## 0.1.0 - 2026-06-04

Initial documented handoff baseline.

### Added

- control-panel smoke audit launcher: `run_control_panel_smoke_audit.bat`
- automated control-panel smoke audit script: `src/control_panel_smoke_audit.py`
- dedicated RTSP copy shortcuts for:
  - `LAN`
  - `DDNS main`
  - `DDNS substream`
  - `public main`
  - `public substream`
- first explicit `VERSION` file for repo handoff/release baselines

### Changed

- control panel defaults toward a more compact operator workspace
- button, dropdown, spinbox, and popup styling were tightened for consistent appearance
- window/dialog colors were stabilized so the UI looks more consistent across machines
- remote wall-view default now prefers main stream (`subtype=0`) for sharper public/DDNS multi-camera viewing
- local batch startup now self-heals UTF-8 BOM in `camera.env.bat`
- stream export/copy flows now support external tools such as VLC more directly

### Notes For The Next Engineer

- local secrets still belong only in `camera.env.bat`
- `camera_presets.json` is local operator state, not a guaranteed shared default
- use `run_doctor.bat` and `run_control_panel_smoke_audit.bat` before trusting a local environment
