# Implementation Start: First Stream Probe

## Readiness

Status: **Ready for controlled implementation spike**.

Not yet production-ready because the concrete Dahua/Imou wrapper binding still needs to be implemented in:
- `src/mtimou/p2p_adapter.py`

## First Goal

Get first successful stream chunks from camera into Python process.

## Runtime Setup

1. Activate venv:
```powershell
F:\programming\python\MTImou\.venv\Scripts\Activate.ps1
```

2. Set credentials:
```powershell
$env:IMOU_CAMERA_SN="YOUR_CAMERA_SN"
$env:IMOU_CAMERA_SAFETY_CODE="YOUR_8_DIGIT_CODE"
```

3. Run probe:
```powershell
python F:\programming\python\MTImou\src\stream_probe.py
```

## Expected Result

- `handshake_start` then `handshake_ok`
- recurring `stream_chunk` events
- final `probe_success`

## Next Binding Task

Implement `PlaceholderDhP2PClient` with selected library calls:
1. connect/auth by SN + safety code
2. open video stream
3. yield encoded chunks in `read_stream_chunks()`

