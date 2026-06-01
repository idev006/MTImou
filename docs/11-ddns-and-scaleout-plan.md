# DDNS And Scale-Out Plan

## Goal

This document defines the next production hardening steps for MTImou:

1. Make worldwide access resilient to public IP changes
2. Keep the operator workflow simple for `N = 2` today and `N = 3-4` next
3. Ensure the code paths follow the same model described here

## Current Baseline

- `cam1` and `cam2` already work on both `LAN` and `public` targets
- `auto` mode already prefers `LAN -> DDNS -> public`
- `ddns_host` support exists in camera selection logic
- Multi-camera view works, but the layout logic should scale more cleanly for `3-4` cameras

## Production Decision

The project will use this access order:

1. `LAN` when the viewer is inside the home network
2. `DDNS` when outside the home network and a DDNS hostname is configured
3. `public` IP as a fallback when DDNS is not configured yet

This means `auto` remains the default operator mode.

## DDNS Rollout Model

### Why

Direct public-IP access works today, but it breaks when the ISP changes the WAN IP after a reconnect.

### Target State

- The router updates a DDNS hostname automatically
- Each camera entry resolves to the same DDNS hostname with a different forwarded port
- Operators continue to use `IMOU_TARGET_MODE=auto`

### Router-Level Model

For a single home WAN IP:

- `cam1` -> `your-ddns-hostname:45554`
- `cam2` -> `your-ddns-hostname:45555`
- `cam3` -> `your-ddns-hostname:45556`
- `cam4` -> `your-ddns-hostname:45557`

Only the port changes per camera. The DDNS hostname stays the same for all cameras in the same house.

### Configuration Model

The code should support three DDNS input patterns:

1. `ddns_host` directly in `cameras.json`
2. Shared env hostname such as `IMOU_DDNS_HOST`
3. Optional per-camera env override when needed later

## Scale-Out Model For 3-4 Cameras

### Network Pattern

- One internal camera IP per device
- One unique public forwarded port per camera
- One config entry per camera

Example:

- `cam1` -> `192.168.1.2:554` -> public `45554`
- `cam2` -> `192.168.1.5:554` -> public `45555`
- `cam3` -> `192.168.1.8:554` -> public `45556`
- `cam4` -> `192.168.1.9:554` -> public `45557`

### Viewer Layout Model

- `1 camera`: `1x1`
- `2 cameras`: `1x2`
- `3-4 cameras`: `2x2`
- `5-9 cameras`: `3x3`

The operator should not need to set the grid manually in normal use. The layout should auto-fit by camera count, with an optional override env only for debugging or demos.

## Operator Workflow

### Default

```bat
set IMOU_TARGET_MODE=auto
run_multi_camera_stable.bat cam1 cam2
```

### Forced DDNS test

```bat
set IMOU_TARGET_MODE=ddns
run_multi_camera_stable.bat cam1 cam2
```

### Forced public fallback test

```bat
set IMOU_TARGET_MODE=public
run_multi_camera_stable.bat cam1 cam2
```

## Implementation Tasks

1. Add DDNS configuration guidance to operator docs
2. Allow a shared DDNS hostname from environment variables
3. Auto-size the multi-camera grid for `1`, `2`, `3-4`, and `5-9` cameras
4. Keep `.venv`-only runtime enforcement unchanged

## Validation Checklist

- `auto` mode picks `LAN` when at home
- `ddns` mode resolves a configured DDNS hostname
- `public` mode still works as fallback
- `3` cameras render in a `2x2` layout
- `4` cameras render in a `2x2` layout

## Non-Goals

- This change does not replace the current port-forward model
- This change does not add cloud relay as the primary architecture
- This change does not auto-create DDNS accounts on behalf of the operator
