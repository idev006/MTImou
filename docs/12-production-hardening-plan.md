# Production Hardening Plan

## Purpose

This document closes the gap between "works in normal use" and "ready for sustained operation".

The current system already supports:

- `LAN` viewing
- `DDNS` viewing
- `public` fallback viewing
- multi-camera viewing
- reconnect behavior

The remaining work is operational hardening, validation, and failure handling.

## Analysis

### What Is Already Strong

1. Camera registry supports multiple targets per camera
2. Viewer logic reconnects after stream loss
3. Router-level DDNS is now live
4. Multi-camera layout already scales to `N = 3-4`

### What Still Creates Real Risk

1. ISP reconnect can create a DDNS propagation lag window
2. A credential change can silently break camera or DDNS access
3. Router/NAT state can partially fail while the WAN stays up
4. Operators need a single command to validate the whole stack
5. There is not yet a formal acceptance checklist for production-light operation

## Plan

### Objective 1: Add Health Checks

Create one operator command that verifies:

- required Python runtime
- camera registry load
- DDNS resolution
- TCP reachability for camera targets
- RTSP first-frame acquisition for selected modes

### Objective 2: Add Incident Playbook

Create a symptom-driven runbook for:

- no video
- repeated reconnects
- DDNS failure
- public access failure
- auth failure

### Objective 3: Add Acceptance Criteria

Define a minimum production-light acceptance bar:

1. `LAN` path works for all active cameras
2. `DDNS` path works for all active cameras
3. `public` path remains a valid fallback
4. health-check exits successfully
5. reconnect count is bounded during a short soak window

## Implementation Scope

This phase will implement:

1. `run_system_health_check.bat`
2. `src/system_health_check.py`
3. `docs/13-incident-runbook.md`
4. README/runbook updates for operator usage

## Validation Matrix

| Case | Expected Result |
| --- | --- |
| `LAN` target reachable | first frame acquired |
| `DDNS` target reachable | first frame acquired |
| `public` target reachable | first frame acquired |
| camera password missing | health check fails clearly |
| DDNS hostname broken | DDNS check fails clearly |
| router port broken | TCP and RTSP checks fail clearly |

## Out Of Scope

- Automated DDNS account creation
- Automatic router self-healing
- Full NVR-grade recording, retention, and alerting
