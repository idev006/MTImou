# Operational Runbook

## 1. Runtime Prerequisites

- Python: 3.12
- Virtual environment: `F:\programming\python\MTImou\.venv`
- Required credentials: camera SN + safety code

## 2. Startup Checklist

1. Verify credentials are loaded from secure env vars.
2. Confirm network egress is available to vendor endpoints.
3. Start service with structured logging enabled.
4. Validate first-frame arrival and FPS metric.

## 3. Monitoring

- Core metrics:
  - `session_connect_success_total`
  - `session_connect_failure_total`
  - `reconnect_attempt_total`
  - `frames_decoded_total`
  - `time_to_first_frame_ms`

- Core logs:
  - Handshake start/success/failure
  - Stream timeout/disconnect
  - Decoder errors

## 4. Incident Playbook

### Incident A: Cannot handshake
- Check credential validity (SN/safety code).
- Check latest firmware changes and wrapper version drift.
- Roll back to last known good wrapper version if needed.

### Incident B: Frequent disconnects
- Inspect network quality and timeout thresholds.
- Tune backoff/jitter and heartbeat behavior.
- Collect session event timeline for root cause.

### Incident C: Decoder failures
- Confirm codec path (H.264/H.265 support).
- Validate packet integrity and decoder library versions.

## 5. Change Management

- Pin dependencies and document version matrix.
- Test changes in canary camera first.
- Never upgrade firmware and wrapper simultaneously.

