# System Architecture

## 1. Context Diagram (Logical)

1. Python Runtime (remote location)
2. Dahua/Imou P2P Cloud Services
3. Imou Camera Device (home NAT network)
4. Analysis Consumer (local module using decoded frames)

Data path:
- Runtime authenticates to P2P cloud using SN + safety code.
- P2P cloud coordinates NAT traversal between runtime and camera.
- Runtime receives encoded stream packets.
- Decoder converts to frames and forwards to analysis layer.

## 2. Component Architecture

### 2.1 `config`
- Load and validate environment/config values.
- Secrets redaction policy for logs.

### 2.2 `p2p_client`
- Wrapper adapter to unofficial protocol library.
- Handshake lifecycle: init -> auth -> session active.
- Heartbeat/session keepalive where protocol supports it.

### 2.3 `stream_receiver`
- Pull encoded packets from active P2P session.
- Backpressure-safe buffering with bounded queue.

### 2.4 `decoder`
- PyAV/OpenCV decoding pipeline.
- Emit frame object (`timestamp`, `frame_id`, `numpy array`).

### 2.5 `reliability_manager`
- Error classifier: auth/network/protocol/decoder.
- Retry policy with exponential backoff and jitter.
- Circuit-breaker style cool-off after repeated failures.

### 2.6 `observability`
- Structured JSON logs.
- Metrics: reconnect count, session duration, decode FPS.
- Health status for external monitors.

## 3. Sequence Flow (Happy Path)

1. Service starts and validates config.
2. Client opens connection to P2P entry endpoint.
3. Client authenticates with SN + safety code.
4. P2P tunnel becomes active.
5. Stream receiver collects encoded packets.
6. Decoder converts packets to frames.
7. Frames flow to analysis callback/consumer.

## 4. Sequence Flow (Failure and Recovery)

1. Packet read timeout or socket loss detected.
2. Reliability manager marks session degraded.
3. Existing session is closed gracefully.
4. Reconnect loop starts with bounded exponential backoff.
5. On success, stream resumes and recovery event is logged.
6. On repeated failure threshold, alert is emitted.

## 5. Data Contracts (Internal)

- `CameraCredentials`: `serial_number`, `safety_code`
- `FrameEnvelope`: `camera_id`, `ts_utc`, `seq`, `image_bgr`
- `SessionEvent`: `event_type`, `reason_code`, `attempt`, `latency_ms`

## 6. Security Controls

- Keep SN/safety code in environment variables or secret manager.
- Mask all sensitive fields in logs.
- Restrict outbound network policy to required endpoints only.

## 7. Observability Baseline

- Log levels: `INFO`, `WARN`, `ERROR`, `DEBUG`.
- Correlation id per connection attempt.
- Alert rules:
  - Handshake failure rate > 30% for 10 minutes.
  - No frames received for > 90 seconds while process alive.

