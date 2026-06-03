# Product Requirements Document (PRD)

## 1. Objective

Build a production-grade Python service that reliably obtains live video streams from Imou cameras remotely without any always-on home gateway device.

## 2. Scope

### In Scope
- P2P handshake/authentication via unofficial Dahua/Imou wrapper.
- Live stream acquisition and frame decoding (PyAV/OpenCV).
- Resilient reconnect/session recovery.
- Observability: logs, metrics, alerting.

### Out of Scope (Phase 1)
- Writing camera firmware integrations.
- Home network infrastructure changes.
- Public API productization for third parties.

## 3. Stakeholders

- Product Owner: You
- System Architect: You + engineering lead
- Python Engineer(s): stream client and decoding pipeline
- Ops/SRE role: telemetry and runtime reliability

## 4. Functional Requirements

1. The system shall authenticate to camera via SN + safety code.
2. The system shall establish a P2P session via vendor network traversal.
3. The system shall read encoded video chunks (H.264/H.265 if available).
4. The system shall decode and emit frames for analysis pipeline.
5. The system shall auto-reconnect on tunnel or stream loss.
6. The system shall support configuration via environment variables or config file.
7. The system shall display and allow copying exportable stream endpoints, including RTSP targets, so operators can reuse them in external programs.

## 5. Non-Functional Requirements

- Availability target (client runtime): 99.0% monthly.
- Recovery target after disconnect: median < 15s, p95 < 60s.
- Time-to-first-frame target: p50 < 8s after start.
- Security: no plaintext credential leaks in logs.
- Maintainability: clear module boundaries and contract tests.

## 6. Constraints

- Zero-device policy at home (no persistent gateway/server).
- Dependence on reverse-engineered protocol library.
- Potentially unstable vendor protocol/firmware behavior.

## 7. Assumptions

- Camera is online and bound to valid cloud/P2P backend.
- SN and safety code are correct and authorized.
- Network egress from runtime environment is allowed.

## 8. Acceptance Criteria

- A demo script can connect, decode, and print frame timestamps for 30 minutes.
- Forced network interruption test recovers automatically without process restart.
- Failures produce structured log events with root-cause category.
