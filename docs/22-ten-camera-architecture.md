# 10-Camera Architecture

## Goal

Run `N cameras` from the same project without turning the operator workflow into a flat list of unrelated endpoints.

For a 10-camera house or site, the production model is:

- `1 camera = 1 config entry`
- `1 camera = 1 password env`
- `1 camera = 1 forwarded public port`
- `1 camera = 1 group`
- `1 camera = 1 tier`
- `1 camera = 2 stream policies`
  - `remote_wall_subtype`
  - `remote_focus_subtype`

## Core Concepts

### Group

Use `group_name` to cluster cameras that belong together operationally.

Recommended groups:

- `front`
- `side`
- `rear`
- `indoor`
- `gate`
- `parking`

The control panel can now select cameras by group, which matters much more once the inventory grows beyond 4 cameras.

### Tier

Use `tier` to communicate business importance:

- `critical`
- `standard`
- `archive`

Suggested meaning:

- `critical`: security-sensitive or always-on attention cameras
- `standard`: normal live-view cameras
- `archive`: useful mostly for playback, evidence, or occasional checks

### Stream Policy

Each camera now carries its own remote-view policy:

- `remote_wall_subtype`
- `remote_focus_subtype`

Recommended default strategy:

- `remote_wall_subtype=1`
  - use substream for wall views to protect total system FPS
- `remote_focus_subtype=0`
  - use mainstream for single-camera detailed viewing

## Recommended 10-Camera Deployment

### Wall View

Use wall view for broad situational awareness, not maximum detail per camera.

Recommended:

- all non-disabled cameras
- `remote_wall_subtype=1`
- grouped selection by zone or floor

### High-FPS Focus View

Use split viewers when you care about per-camera FPS or detail.

Recommended:

- select only a subset, usually `critical` cameras
- keep `remote_focus_subtype=0`
- launch with `run_multi_camera_high_fps.bat`

### Suggested Layout Pattern

- `front`: 2 cameras
- `side`: 2 cameras
- `rear`: 2 cameras
- `gate`: 2 cameras
- `indoor`: 2 cameras

Operationally:

- wall view: all 10 cameras with substream
- focus view: only the active group or only `critical` tier cameras

## Performance Strategy

### If the target is broad coverage

Use:

- tiled view
- `remote_wall_subtype=1`

This keeps decode and uplink pressure lower.

### If the target is highest FPS per camera

Use:

- split view
- `remote_focus_subtype=0`

This isolates viewers by process and avoids the grid compositor becoming the main bottleneck.

### Important engineering rule

Do not assume higher bandwidth alone means higher FPS.

Always measure:

1. source capability
2. wall-view runtime FPS
3. split-view runtime FPS

## Operator Workflow

1. Add cameras in `Camera Management`
2. Assign `group_name`
3. Assign `tier`
4. Set `remote_wall_subtype` and `remote_focus_subtype`
5. Save inventory
6. Run health check
7. Run source capability check
8. Launch either:
   - grouped wall view
   - grouped split view

## Future Scale Guidance

If the system goes beyond 10 cameras:

- prefer grouped operations over “all cameras all the time”
- keep a small `critical` set for detailed viewing
- reserve wall views for overview
- use source-capability checks when a camera underperforms
