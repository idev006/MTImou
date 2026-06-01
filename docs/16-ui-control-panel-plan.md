# UI Control Panel Plan

## Goal

Provide a simple desktop UI so an operator can use MTImou without editing batch files or remembering command sequences.

## User Problems To Solve

1. Operators should not need to remember `run_*.bat` commands
2. Operators should not need to edit `camera.env.bat` manually for common settings
3. Operators need one obvious place to:
   - launch a single camera
   - launch multi-camera view
   - choose target mode
   - run health checks
   - inspect last results

## UX Scope

The first UI release will provide:

1. Camera list with names and current targets
2. Mode selector: `auto`, `lan`, `ddns`, `public`
3. Buttons:
   - view selected camera
   - view all enabled cameras
   - run health check
4. Settings fields:
   - shared DDNS host
   - camera passwords used by the current deployment
5. Output panel:
   - last command output
   - health-check result

## Technical Approach

- Use `tkinter`
- Run only with project `.venv`
- Reuse existing scripts and config files
- Update only local operator config in `camera.env.bat`

## Non-Goals

- Full router administration in the UI
- Video embedding inside the control panel in the first release
- Advanced recording/NVR workflows
