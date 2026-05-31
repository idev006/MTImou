# ADR-001: Use Unofficial Dahua/Imou P2P Wrapper

- Status: Accepted
- Date: 2026-05-30

## Context

Direct inbound connectivity is not feasible due to NAT + dynamic IP and zero-device policy at home. Vendor official cloud APIs may not expose raw stream in a programmable way for this use case.

## Decision

Use a reverse-engineered Dahua/Imou P2P Python wrapper as the integration layer for handshake, authentication, and stream transport.

## Consequences

### Positive
- Meets hard constraint (no home gateway).
- Enables frame-level analytics in custom Python pipeline.

### Negative
- Protocol may break after vendor firmware/backend changes.
- Limited formal support and uncertain long-term compatibility.

## Mitigations

- Abstract wrapper behind `p2p_client` interface to allow swap.
- Build integration tests against recorded protocol expectations.
- Add runtime feature flags and graceful degradation modes.
- Maintain version pinning and staged upgrade validation.

## Alternatives Considered

1. Port forwarding/DDNS:
   - Rejected due to security and operational complexity.
2. Home VPN gateway:
   - Rejected by zero-device policy.
3. Vendor mobile app only:
   - Rejected because no programmable frame analytics pipeline.

