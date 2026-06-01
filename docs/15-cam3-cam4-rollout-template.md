# Cam3 And Cam4 Rollout Template

## Purpose

Use this template when expanding the house deployment from `N = 2` to `N = 3` or `N = 4`.

## Target Model

All cameras share one DDNS hostname:

- `biiigbee-home.servecounterstrike.com`

Each camera gets its own forwarded port:

- `cam1` -> `45554`
- `cam2` -> `45555`
- `cam3` -> `45556`
- `cam4` -> `45557`

## Pre-Flight

Before adding a new camera:

1. Confirm its LAN IP is stable
2. Confirm RTSP works on LAN first
3. Confirm username/password
4. Reserve a unique public/DDNS port

## Suggested Mapping

| Camera | Example LAN IP | Public/DDNS Port |
| --- | --- | --- |
| `cam3` | `192.168.1.8` | `45556` |
| `cam4` | `192.168.1.9` | `45557` |

## Router Work

Create one port-forward rule per camera:

- `45556 -> 192.168.1.8:554`
- `45557 -> 192.168.1.9:554`

## Environment Work

Add per-camera passwords to `camera.env.bat`:

```bat
set IMOU_CAM_CAM3_PASSWORD=YOUR_THIRD_CAMERA_PASSWORD
set IMOU_CAM_CAM4_PASSWORD=YOUR_FOURTH_CAMERA_PASSWORD
```

## Registry Work

Add entries like these to `cameras.json`:

```json
{
  "id": "cam3",
  "name": "Third Camera",
  "lan_host": "192.168.1.8",
  "lan_port": 554,
  "ddns_host": "biiigbee-home.servecounterstrike.com",
  "ddns_port": 45556,
  "public_host": "125.27.213.148",
  "public_port": 45556,
  "channel": "1",
  "subtype": "0",
  "transport": "tcp",
  "username_env": "IMOU_CAMERA_USERNAME",
  "password_envs": ["IMOU_CAM_CAM3_PASSWORD", "IMOU_CAMERA_PASSWORD"],
  "enabled": true
}
```

```json
{
  "id": "cam4",
  "name": "Fourth Camera",
  "lan_host": "192.168.1.9",
  "lan_port": 554,
  "ddns_host": "biiigbee-home.servecounterstrike.com",
  "ddns_port": 45557,
  "public_host": "125.27.213.148",
  "public_port": 45557,
  "channel": "1",
  "subtype": "0",
  "transport": "tcp",
  "username_env": "IMOU_CAMERA_USERNAME",
  "password_envs": ["IMOU_CAM_CAM4_PASSWORD", "IMOU_CAMERA_PASSWORD"],
  "enabled": true
}
```

## Validation

Run after each addition:

```bat
cd /d F:\programming\python\MTImou
run_system_health_check.bat cam3
run_system_health_check.bat cam4
```

Then validate the 4-camera grid:

```bat
cd /d F:\programming\python\MTImou
run_multi_camera_stable.bat cam1 cam2 cam3 cam4
```

Expected layout:

- `4 cameras` -> `2x2`

## Acceptance For Expansion

`cam3/cam4` are accepted only if:

1. Health check passes for `LAN`
2. Health check passes for `DDNS`
3. Health check passes for `public`
4. Multi-camera viewer renders all 4 tiles
