# Remote Free dh-p2p Status (2026-05-31)

## Scope

- Goal: receive IMOU stream from outside home network with zero always-on home gateway and zero paid cloud.
- Constraint: use `dh-p2p` path only.

## Current Result

- LAN receive is **successful** (Python + OpenCV receiver on local RTSP from camera IP).
- Remote free `dh-p2p` is now **working** using Python tunnel in forced relay mode.
- Validation done by `run_relay_test.bat` with OpenCV frame-read checks and repeated successful runs (`Exit code 0`).
- Stability is still **best-effort**: the tunnel can intermittently drop and may require automatic retry.

## Evidence Summary

- Control-plane reaches full relay sequence: `probe` -> `p2p-channel` -> `relay-start` -> `relay-channel`.
- Media-plane confirms RTSP workflow over localhost tunnel:
  - `OPTIONS 401` -> auth retry -> `OPTIONS 200`
  - `DESCRIBE 200`
  - `SETUP trackID=0/1 200`
- OpenCV frame-read condition is satisfied and script returns success.

## Engineering Fixes Already Applied

- Fixed launcher deadlock risk: replaced blocking `readline()` wait with non-blocking output pump and explicit timeout.
- Fixed local port collision risk: Rust launchers no longer reuse `IMOU_RTSP_PORT=554` automatically; local bind port now uses `IMOU_LOCAL_RTSP_PORT` or safe candidates.
- Added relay-side compatibility handling in `dh-p2p/main.py`:
  - relay sign negotiation (`0x17/0x18`)
  - relay auth step (`0x19/0x1A`)
  - relay heartbeat keepalive while idle
  - tolerant realm handshake loop with timeout and packet-type handling
- Updated `src/relay_stream_test.py` to improve practical success rate:
  - auth-first RTSP candidates
  - optional ffprobe gate (disabled by default)
  - one-URL-per-tunnel retry strategy to reduce session churn
- Updated `run_relay_test.bat` defaults for IMOU Ranger 2:
  - relay on
  - auth-only by default
  - probe-less OpenCV validation path

## Sequence (Current Working Path)

```mermaid
sequenceDiagram
    participant App as "Python Probe Runner"
    participant Rust as "dh-p2p.exe"
    participant Cloud as "Easy4IP Relay"
    participant Cam as "IMOU Camera"

    App->>Py as "dh-p2p main.py (-r)"
    Py->>Cloud: probe + p2p-channel + relay-start + relay-channel
    Cloud-->>Py: control-plane responses (200)
    Py->>Cam: PTCP relay setup + realm
    App->>Py: RTSP via 127.0.0.1:554
    Py-->>App: RTSP responses + media packets
    App-->>App: OpenCV reads frames (success)
```

## Runbook Commands

```bat
cd /d F:\programming\python\MTImou
run_relay_test.bat
```

Optional tuning env:

```bat
set IMOU_FORCE_RELAY=1
set IMOU_RTSP_INCLUDE_AUTH=1
set IMOU_RTSP_TRY_ANON=0
set IMOU_ONE_URL_PER_TUNNEL=1
set IMOU_RELAY_ATTEMPTS=5
set IMOU_FRAME_WAIT_SEC=18
```

## Residual Risks

- `dh-p2p` is reverse-engineered and can break after firmware/server-side protocol changes.
- Relay agent quality varies by session; retries are still required in real-world operation.
- For production-grade uptime/SLA, official OpenAPI path remains the long-term safer architecture.
