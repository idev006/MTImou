# UI Control Panel Plan

## Goal

Provide a simple desktop UI so an operator can use MTImou without editing batch files or remembering command sequences.

## User Problems To Solve

1. Operators should not need to remember `run_*.bat` commands
2. Operators should not need to edit `camera.env.bat` manually for common settings
3. Operators need one obvious place to:
   - launch one or more selected cameras
   - launch all enabled cameras
   - choose target mode
   - run health checks
   - inspect last results

## Current UX Scope

The current UI release provides:

1. A dashboard-oriented layout instead of one long form
   - top summary cards for enabled cameras, target mode, and DDNS host
   - tabbed layout for `Dashboard`, `Settings`, and `Operator Guide`
2. A multi-column camera table
   - columns for camera name, LAN, DDNS, public target, and enabled status
   - supports multi-select for launching a chosen subset
   - includes quick actions for `Select All`, `Select Enabled`, and `Clear Selection`
3. Operator launch actions
   - view selected camera(s)
   - view all enabled cameras
   - run health check
   - open logs and README
4. Settings fields
   - target mode: `auto`, `lan`, `ddns`, `public`
   - shared DDNS host
   - shared camera username
   - camera passwords generated dynamically from the current deployment
   - password visibility toggle
5. Activity and guidance panels
   - recent command output
   - concise operator flow and target mode explanations

## Technical Approach

- Use `PySide6`
- Run only with project `.venv`
- Reuse existing scripts and config files
- Update only local operator config in `camera.env.bat`
- Keep View logic thin and route state/commands through the ViewModel and settings store

## Non-Goals

- Full router administration in the UI
- Video embedding inside the control panel
- Advanced recording/NVR workflows
- Full camera CRUD management in this release
