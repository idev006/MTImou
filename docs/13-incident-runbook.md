# Incident Runbook

## Purpose

Use this runbook when the system stops behaving as expected in production-light operation.

## Command Set

Quick health check:

```bat
cd /d F:\programming\python\MTImou
run_system_health_check.bat
```

Single camera:

```bat
run_camera_stable.bat cam1
run_camera_stable.bat cam2
```

Two cameras:

```bat
run_multi_camera_stable.bat cam1 cam2
```

## Symptom: No Video At All

Check in order:

1. Run `run_system_health_check.bat`
2. Confirm `.venv\Scripts\python.exe` still runs
3. Confirm camera credentials in `camera.env.bat`
4. Confirm router and cameras have power

Most likely causes:

- broken Python environment
- camera password mismatch
- router/network outage

## Symptom: LAN Works, DDNS Fails

Check in order:

1. Resolve `biiigbee-home.servecounterstrike.com`
2. Confirm router DDNS status is still `Connected`
3. Confirm No-IP hostname still points to the current WAN IP

Most likely causes:

- DDNS update lag after ISP reconnect
- DDNS key rotated but router not updated

## Symptom: DDNS Works, But Viewer Reconnects Often

Check in order:

1. Review `logs\multi_camera_latest.log`
2. Look for repeated `reconnects`
3. Test one camera at a time with `run_camera_stable.bat`

Most likely causes:

- camera Wi-Fi instability
- upload bandwidth saturation
- transient ISP jitter

## Symptom: Public And DDNS Both Fail

Check in order:

1. Verify home internet is online
2. Verify port forwarding still exists in router
3. Verify WAN IP changed unexpectedly
4. Re-run `run_system_health_check.bat`

Most likely causes:

- router reset or NAT rule removed
- ISP outage
- CGNAT/policy change

## Symptom: One Camera Fails, Others Work

Check in order:

1. Run `run_camera_stable.bat <camera-id>`
2. Verify the specific password env for that camera
3. Verify its LAN IP did not change
4. Verify its forwarded port still maps correctly

Most likely causes:

- per-camera password mismatch
- camera reboot or Wi-Fi drop
- wrong NAT mapping for that camera

## Recovery Actions

### Level 1

- restart viewer only
- re-run single-camera test

### Level 2

- verify DDNS and public TCP reachability
- reboot affected camera

### Level 3

- inspect router port-forward rules
- inspect router DDNS state
- rotate DDNS key if credentials were exposed

## Escalation Thresholds

Escalate if any of these happen:

- health check fails for both `ddns` and `public`
- reconnects repeat continuously for more than 10 minutes
- multiple cameras fail at once
- DDNS hostname no longer resolves to the home WAN IP
