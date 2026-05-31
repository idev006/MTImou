# Risk Register

## Scoring

- Impact: 1 (low) to 5 (critical)
- Likelihood: 1 (rare) to 5 (frequent)
- Risk Score = Impact x Likelihood

## Risks

1. Protocol incompatibility after firmware/backend update  
Impact: 5, Likelihood: 4, Score: 20  
Mitigation: wrapper abstraction, pinned versions, canary validation before camera upgrades.

2. Session instability across long runtimes  
Impact: 4, Likelihood: 4, Score: 16  
Mitigation: heartbeat checks, reconnect FSM, backoff with jitter, memory leak monitoring.

3. Credential exposure in logs/config  
Impact: 5, Likelihood: 2, Score: 10  
Mitigation: secret masking, strict logging policy, environment-based secret loading.

4. Legal/compliance concerns with reverse-engineered protocol use  
Impact: 5, Likelihood: 2, Score: 10  
Mitigation: legal review of jurisdiction and ToS before production rollout.

5. Decoder performance bottleneck on low-resource host  
Impact: 3, Likelihood: 3, Score: 9  
Mitigation: adjustable FPS sampling, frame queue bounds, optional hardware-accelerated decode path.

## Trigger-Based Response

- If handshake failure ratio > 30% for 10 minutes:
  - Trigger incident triage and lock deployment changes.
- If reconnect loops exceed threshold (e.g., 20 attempts/hour):
  - Escalate to protocol compatibility investigation.

