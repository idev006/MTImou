# N-Camera Architecture (`1 <= N <= 100`)

## Goal

Run `N cameras` from the same project without turning the operator workflow into a flat list of unrelated endpoints.

The supported architectural model is now:

- `1 camera = 1 config entry`
- `1 camera = 1 password env`
- `1 camera = 1 forwarded public port`
- `1 camera = 1 group`
- `1 camera = 1 tier`
- `1 camera = 2 remote stream policies`
  - `remote_wall_subtype`
  - `remote_focus_subtype`

The codebase is designed to support any integer `N` where `1 <= N <= 100`.

## Important engineering truth

Support for `N <= 100` does **not** mean:

- all 100 cameras should always be opened at once
- all 100 cameras will keep the same FPS in one giant wall view
- one desktop viewer can make camera-source limits disappear

The correct model is:

- configuration supports up to 100
- UI supports managing up to 100
- operator workflow supports grouped selection across up to 100
- runtime strategy separates overview mode from focus mode

## Core Concepts

### Group

Use `group_name` to cluster cameras that belong together operationally.

Recommended groups:

- `front`
- `side`
- `rear`
- `gate`
- `parking`
- `indoor`
- `warehouse`
- `office`

The control panel now supports filtering and selecting cameras by group.

### Tier

Use `tier` to express business importance:

- `critical`
- `standard`
- `archive`

Suggested meaning:

- `critical`: security-sensitive or always-on attention cameras
- `standard`: normal live-view cameras
- `archive`: useful mostly for playback, evidence, or occasional checks

The control panel now supports filtering by tier.

### Stream Policy

Each camera carries its own remote-view policy:

- `remote_wall_subtype`
- `remote_focus_subtype`

Recommended defaults:

- `remote_wall_subtype=1`
  - use lower-bandwidth substream for wall views
- `remote_focus_subtype=0`
  - use higher-detail mainstream for focused viewing

## Operating Model For Large N

### Wall View

Use wall view for overview, not maximum detail.

Recommended:

- all enabled cameras in a small deployment
- one selected group in a larger deployment
- `remote_wall_subtype=1`

Examples:

- `N <= 4`: all cameras in one wall is usually acceptable
- `5 <= N <= 9`: one wall can still be acceptable depending on stream profiles
- `10 <= N <= 16`: prefer grouped walls instead of a single always-on board
- `17 <= N <= 100`: treat walls as operational slices, not as one permanent all-camera canvas

### Focus View

Use split viewers when you care about per-camera FPS or detail.

Recommended:

- selected cameras only
- `critical` tier first
- `remote_focus_subtype=0`
- `run_multi_camera_high_fps.bat`

## Performance Strategy

### If the target is broad situational awareness

Use:

- tiled view
- grouped selection
- `remote_wall_subtype=1`

### If the target is highest practical FPS per camera

Use:

- split view
- selected cameras only
- `remote_focus_subtype=0`

### Engineering rule

Do not assume higher bandwidth alone means higher FPS.

Always separate:

1. source capability
2. wall-view runtime FPS
3. split-view runtime FPS

## UI/UX Expectations For Large N

The control panel should help operators manage large inventories by:

- search
- group filter
- tier filter
- grouped selection
- camera inventory editing
- source-ceiling visibility

This is more important than trying to make one giant grid look clever.

## Recommended Deployment Patterns

### Small Site (`N <= 4`)

- wall view for all enabled cameras
- focus view for detailed incidents

### Medium Site (`5 <= N <= 16`)

- organize by zones
- use grouped walls
- reserve high-FPS split view for `critical` cameras

### Large Site (`17 <= N <= 100`)

- define groups carefully
- use tiering consistently
- avoid opening all cameras at once unless the operator explicitly wants overview mode
- rely on grouped walls plus focused split views

## Operator Workflow

1. Add cameras in `Camera Management`
2. Assign `group_name`
3. Assign `tier`
4. Set `remote_wall_subtype` and `remote_focus_subtype`
5. Save inventory
6. Run health check
7. Run source capability check
8. Launch either:
   - a grouped wall view
   - a grouped high-FPS split view

## Template Files

Use:

- `cameras.scaleout.template.json`
- `cameras.ten-camera.template.json`

These are examples of the same N-camera schema, not separate architectures.
