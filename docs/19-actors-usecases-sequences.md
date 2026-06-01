# Actors, Use Cases, and Sequence Flows

## Actors

1. **Operator**
   - launches viewers
   - changes runtime settings
   - runs health and resilience checks

2. **System Administrator**
   - updates `cameras.json`
   - manages password and DDNS configuration
   - validates rollout for new cameras

3. **Viewer Runtime**
   - opens RTSP sessions
   - reconnects after no-frame events
   - fails over between `LAN`, `DDNS`, and `public`

4. **Camera Device**
   - provides RTSP stream
   - may be reachable via LAN and/or WAN path

5. **Home Router / DDNS**
   - forwards public ports
   - resolves DDNS hostname

6. **Health/Resilience Engine**
   - validates path reachability
   - validates first-frame acquisition

## Use Cases By Actor

### Operator

- Configure local operator settings
- View one camera
- View multiple cameras
- Run health check
- Run resilience smoke check
- Inspect logs and README

### System Administrator

- Add a new camera
- Enable/disable a camera
- Rotate credentials
- Update DDNS hostname
- Verify rollout after topology change

### Viewer Runtime

- Resolve best target
- Open RTSP session
- Detect stalled stream
- Reconnect
- Fail over to another reachable target

## Use Case Diagram

```mermaid
flowchart LR
    Operator["Operator"] --> UC1["Configure Settings"]
    Operator --> UC2["View Single Camera"]
    Operator --> UC3["View Multi Camera"]
    Operator --> UC4["Run Health Check"]
    Operator --> UC5["Run Resilience Smoke"]

    Admin["System Administrator"] --> UC6["Add/Update Camera"]
    Admin --> UC7["Rotate Secrets"]
    Admin --> UC8["Update DDNS / Ports"]

    Runtime["Viewer Runtime"] --> UC9["Resolve Target"]
    Runtime --> UC10["Open Stream"]
    Runtime --> UC11["Reconnect / Failover"]

    Router["Router / DDNS"] --> UC9
    Camera["Camera Device"] --> UC10
    Health["Health Engine"] --> UC4
    Health --> UC5
```

## Sequence: View Single Camera

```mermaid
sequenceDiagram
    participant Operator
    participant UI as "Control Panel UI"
    participant VM as "ViewModel / SSOT"
    participant Viewer as "Viewer Runtime"
    participant Resolver as "Target Resolver"
    participant Camera

    Operator->>UI: Select cam1 + click View
    UI->>VM: request_view_single(cam1)
    VM->>Viewer: launch(cam1)
    Viewer->>Resolver: pick_target(auto)
    Resolver-->>Viewer: lan / ddns / public target
    Viewer->>Camera: Open RTSP
    Camera-->>Viewer: Frames
    Viewer-->>Operator: Render live video
```

## Sequence: Reconnect With Failover

```mermaid
sequenceDiagram
    participant Viewer
    participant Resolver as "Target Resolver"
    participant Router as "Router / DDNS"
    participant Camera

    Viewer->>Viewer: Detect no-frame timeout
    Viewer->>Resolver: Re-evaluate target(auto)
    Resolver->>Router: Probe DDNS/public if needed
    Resolver-->>Viewer: best reachable target
    Viewer->>Camera: Re-open RTSP on new target
    Camera-->>Viewer: Frames resume
```

## Sequence: Health Check

```mermaid
sequenceDiagram
    participant Operator
    participant UI as "Control Panel UI"
    participant VM as "ViewModel"
    participant Health as "Health Engine"
    participant Resolver as "Target Resolver"
    participant Camera

    Operator->>UI: Run health check
    UI->>VM: request_health_check()
    VM->>Health: run()
    loop each camera x mode
        Health->>Resolver: target_for_mode()
        Resolver-->>Health: target
        Health->>Camera: TCP probe + first-frame check
        Camera-->>Health: success/failure
    end
    Health-->>VM: summary
    VM-->>UI: render output
```

## Runtime State Diagram

```mermaid
stateDiagram-v2
    [*] --> Idle
    Idle --> ResolvingTarget
    ResolvingTarget --> Opening
    Opening --> Streaming
    Opening --> WaitingRetry
    Streaming --> WaitingRetry: no-frame timeout
    WaitingRetry --> ResolvingTarget: retry / failover
    WaitingRetry --> Failed: target unavailable
    Failed --> ResolvingTarget: operator reruns or path returns
```
