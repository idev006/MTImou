# N-Camera Secret Model

## Goal

Move the project from a `2-camera special case` to an `N-camera secret model` that scales cleanly.

## Recommended Convention

Use one environment variable per camera:

```bat
set IMOU_CAM_CAM1_PASSWORD=...
set IMOU_CAM_CAM2_PASSWORD=...
set IMOU_CAM_CAM3_PASSWORD=...
set IMOU_CAM_CAM4_PASSWORD=...
```

Pattern:

- `IMOU_CAM_<CAMERA_ID_UPPER>_PASSWORD`

Examples:

- `cam1` -> `IMOU_CAM_CAM1_PASSWORD`
- `front_yard` -> `IMOU_CAM_FRONT_YARD_PASSWORD`

## Compatibility

The software still accepts legacy names:

- `IMOU_CAMERA_PASSWORD`
- `IMOU_CAMERA2_PASSWORD`
- `IMOU_CAMERA3_PASSWORD`

This keeps existing deployments working while new deployments use the scalable convention.

## Why This Model

1. It scales to `N cameras`
2. The UI can generate fields automatically from `cameras.json`
3. Process documentation becomes consistent
4. Secrets stay outside tracked JSON while camera topology stays inside tracked JSON
