# Clean Runtime Rewrite Plan

## Why Rewrite

The current repository contains both:

- production entrypoints that the operator uses every day, and
- historical spikes / experiments from the relay era.

That mix makes maintenance harder than it should be. The goal of this rewrite is
to create a clean production core for the **direct RTSP architecture** that the
project actually runs today, while keeping working batch entrypoints stable.

## Rewrite Scope

This rewrite covers only the production runtime path:

1. camera registry and secret resolution
2. target selection (`lan`, `ddns`, `public`, `auto`)
3. direct RTSP viewers
4. health check
5. resilience smoke check

It does **not** delete historical spike files yet. They remain in the repo until
we intentionally archive or remove them in a later cleanup pass.

## Design Principles

1. **Single responsibility**
   - config loading, target resolution, viewer loop, and health checks are separate modules
2. **Compatibility-first migration**
   - existing batch entrypoints continue to work
3. **.venv-only runtime**
   - all production Python entrypoints enforce `.venv\Scripts\python.exe`
4. **Data-driven camera topology**
   - `cameras.json` remains the system of record
5. **Conservative runtime behavior**
   - prefer proven OpenCV capture flow over unproven concurrency patterns in this environment
6. **Operational honesty**
   - health and resilience tools verify what the system can really do today

## v2 Module Layout

`src/mtimou_v2/`

- `models.py`
  - shared dataclasses
- `logging_utils.py`
  - consistent log writer
- `registry.py`
  - camera config loading, env resolution, summaries
- `targets.py`
  - reachable target selection and probing
- `rtsp.py`
  - RTSP URL building and OpenCV capture opening
- `settings.py`
  - runtime knobs from environment
- `single_viewer.py`
  - single-camera production viewer
- `multi_viewer.py`
  - multi-camera production viewer
- `health.py`
  - health-check engine
- `resilience.py`
  - resilience smoke engine

## Migration Strategy

1. Implement `mtimou_v2` beside the current code
2. Point existing production wrappers to the new v2 modules
3. Keep file names and batch entrypoints stable:
   - `run_camera_stable.bat`
   - `run_multi_camera_stable.bat`
   - `run_system_health_check.bat`
   - `run_resilience_smoke.bat`
4. Verify parity with:
   - compile check
   - health check
   - resilience smoke
   - short single-camera viewer run
   - short multi-camera viewer run

## Non-Goals For This Pass

- removing all legacy files
- redesigning the UI
- replacing OpenCV with a different decode stack
- process-per-camera isolation

Those are worthwhile future steps, but they are not required for a clean and
safe production-core rewrite.

## Acceptance Criteria

- production runtime code is concentrated in `src/mtimou_v2/`
- old wrapper scripts call the v2 core
- health check passes for `lan`, `ddns`, and `public`
- resilience smoke passes for repeated cycles
- single and multi viewer still launch successfully with `.venv` only
