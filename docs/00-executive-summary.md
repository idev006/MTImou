# Executive Summary

## Problem

You need remote live-video access from Imou cameras under strict constraints:
- Cameras are behind NAT and dynamic IP.
- No always-on home gateway/PC is allowed.
- Vendor protocol is proprietary (Dahua/Imou P2P).

## Proposed Direction

Adopt a **P2P protocol tunneling client** in Python as a virtual client that:
- Authenticates using camera SN + safety code.
- Establishes vendor-mediated NAT traversal tunnel.
- Receives raw video stream for local decoding and analysis.

## Strategic Position

This is the highest-feasibility path under your constraints, but it carries protocol fragility risk because it depends on reverse-engineered behavior.

## Success Criteria (Phase 1)

- Connect and authenticate to at least one target camera.
- Sustain stream for >= 30 minutes with auto-reconnect.
- Decode frames to `numpy.ndarray` for downstream analytics.
- Provide structured logs and alerting for handshake/stream failures.

