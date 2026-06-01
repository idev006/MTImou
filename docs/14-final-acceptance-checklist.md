# Final Acceptance Checklist

## Purpose

Use this checklist to decide whether the MTImou deployment is accepted for production-light operation.

## Deployment Scope

- Home router with No-IP DDNS
- Multi-camera RTSP access
- `LAN`, `DDNS`, and `public` target modes
- Current active cameras:
  - `cam1` / Front House
  - `cam2` / Side House

## Acceptance Criteria

### Runtime

- [x] Project runs only with `F:\programming\python\MTImou\.venv\Scripts\python.exe`
- [x] `camera.env.bat` exists and contains active credentials
- [x] `cameras.json` matches current deployed network targets

### Router And Network

- [x] Port forward exists for `cam1` on `45554 -> 192.168.1.2:554`
- [x] Port forward exists for `cam2` on `45555 -> 192.168.1.5:554`
- [x] No-IP DDNS is connected on the router
- [x] `biiigbee-home.servecounterstrike.com` resolves to the current WAN IP

### Stream Validation

- [x] `LAN` path works for `cam1`
- [x] `LAN` path works for `cam2`
- [x] `DDNS` path works for `cam1`
- [x] `DDNS` path works for `cam2`
- [x] `public` path works for `cam1`
- [x] `public` path works for `cam2`

### Operator Validation

- [x] `run_camera_stable.bat cam1` works
- [x] `run_camera_stable.bat cam2` works
- [x] `run_multi_camera_stable.bat cam1 cam2` works
- [x] `run_system_health_check.bat` exits successfully
- [x] Incident runbook exists

## Latest Verified Result

Health check result:

```text
[SUMMARY] ok=6/6 hard_failures=0
```

## Residual Risks

These do not block acceptance, but they remain external risks:

1. ISP can still switch to CGNAT in the future
2. Camera firmware can change RTSP behavior
3. Credentials can drift if changed outside this repo
4. Power loss or router reset can remove forwarding/state

## Acceptance Decision

Current decision:

- [x] Accepted for production-light use
- [ ] Rejected

## Recommended Next Reviews

1. Re-run health check after router reboot
2. Re-run health check after ISP reconnect
3. Re-run health check after adding any new camera
