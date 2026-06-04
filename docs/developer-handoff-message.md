# Developer Clone Handoff Message

Use this as a ready-to-send message when handing the repository to the next engineer.

## Short Version

Clone from `main` now. The repository is ready for handoff.

After cloning, run:

```bat
cd /d F:\programming\python\MTImou
setup_windows.bat
run_doctor.bat
run_control_panel_smoke_audit.bat
run_control_panel.bat
```

Read these first:

1. `README.md`
2. `DEVELOPER_GUIDE.md`
3. `docs/developer-handoff-checklist.md`
4. `CHANGELOG.md`
5. `VERSION`

Important:

- `camera.env.bat` is local-only
- `camera_presets.json` is local-only
- do not commit live secrets
- start from `camera.env.bat.example`, `cameras.example.json`, and `camera_presets.example.json` when setting up a new machine

## Copy-Paste Message

```text
Please clone from `main`. The repository is ready for developer handoff.

After cloning, run these commands first:

cd /d F:\programming\python\MTImou
setup_windows.bat
run_doctor.bat
run_control_panel_smoke_audit.bat
run_control_panel.bat

Read these files in order:
1. README.md
2. DEVELOPER_GUIDE.md
3. docs/developer-handoff-checklist.md
4. CHANGELOG.md
5. VERSION

Important notes:
- camera.env.bat is local-only
- camera_presets.json is local-only
- do not commit live secrets
- use camera.env.bat.example, cameras.example.json, and camera_presets.example.json as setup references
```
