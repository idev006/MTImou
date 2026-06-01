from __future__ import annotations

import hashlib
import json
import os
import subprocess
import time
import urllib.error
import urllib.request
import uuid
from pathlib import Path
from typing import Any


def first_env(*names: str, default: str = "") -> str:
    for name in names:
        value = os.getenv(name, "").strip()
        if value:
            return value
    return default


def build_domain() -> str:
    explicit = first_env("IMOU_OPENAPI_DOMAIN")
    if explicit:
        return explicit

    dc = first_env("IMOU_OPENAPI_DC", "IMOU_DATACENTER", default="sg").lower()
    domain_map = {
        "sg": "openapi-sg.easy4ip.com",
        "fk": "openapi-fk.easy4ip.com",
        "or": "openapi-or.easy4ip.com",
    }
    if dc not in domain_map:
        raise ValueError("Invalid IMOU_OPENAPI_DC. Use sg/fk/or or IMOU_OPENAPI_DOMAIN.")
    return domain_map[dc]


def build_sign(timestamp: int, nonce: str, app_secret: str) -> str:
    raw = f"time:{timestamp},nonce:{nonce},appSecret:{app_secret}".encode("utf-8")
    return hashlib.md5(raw).hexdigest()


def openapi_call(
    method: str,
    *,
    domain: str,
    app_id: str,
    app_secret: str,
    params: dict[str, Any],
    timeout_sec: int = 30,
) -> dict[str, Any]:
    ts = int(time.time())
    nonce = str(uuid.uuid4())
    payload = {
        "system": {
            "ver": "1.0",
            "appId": app_id,
            "sign": build_sign(ts, nonce, app_secret),
            "time": ts,
            "nonce": nonce,
        },
        "id": str(uuid.uuid4()),
        "params": params,
    }
    url = f"https://{domain}/openapi/{method}"
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url=url,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout_sec) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as err:
        detail = err.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {err.code} calling {method}: {detail}") from err


def assert_ok(resp: dict[str, Any], method: str) -> dict[str, Any]:
    result = resp.get("result", {})
    code = str(result.get("code", ""))
    msg = str(result.get("msg", ""))
    data = result.get("data", {})
    if code != "0":
        raise RuntimeError(f"{method} failed: code={code} msg={msg}")
    if not isinstance(data, dict):
        raise RuntimeError(f"{method} returned unexpected data")
    return data


def probe_hls(ffprobe: Path, hls_url: str) -> bool:
    if not ffprobe.exists():
        print("[WARN] ffprobe not found, skip media probe:", ffprobe)
        return False
    cmd = [
        str(ffprobe),
        "-v",
        "error",
        "-rw_timeout",
        "15000000",
        "-i",
        hls_url,
        "-show_streams",
        "-select_streams",
        "v:0",
        "-of",
        "compact",
    ]
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=25)
    except subprocess.TimeoutExpired:
        print("[WARN] ffprobe timeout on HLS URL")
        return False
    if p.returncode == 0 and p.stdout.strip():
        print("[SUCCESS] ffprobe detected video stream from HLS")
        return True
    if p.stderr.strip():
        print("[WARN] ffprobe error:", p.stderr.strip().splitlines()[-1])
    return False


def pick_hls_url(streams: list[dict[str, Any]], stream_id: int) -> str:
    preferred = None
    fallback = None
    for item in streams:
        hls = str(item.get("hls", "")).strip()
        if not hls:
            continue
        if fallback is None:
            fallback = hls
        item_stream_id = item.get("streamId")
        if str(item_stream_id) == str(stream_id):
            preferred = hls
            break
    if preferred:
        return preferred
    if fallback:
        return fallback
    raise RuntimeError("No HLS URL found in streams")


def main() -> int:
    app_id = first_env("IMOU_APP_ID")
    app_secret = first_env("IMOU_APP_SECRET")
    device_id = first_env("IMOU_CAMERA_SN")
    channel_id = first_env("IMOU_OPENAPI_CHANNEL_ID", default="0")
    stream_id = int(first_env("IMOU_OPENAPI_STREAM_ID", default=first_env("IMOU_RTSP_SUBTYPE", default="0")))

    if not app_id:
        print("Missing IMOU_APP_ID")
        return 2
    if not app_secret:
        print("Missing IMOU_APP_SECRET")
        return 2
    if not device_id:
        print("Missing IMOU_CAMERA_SN")
        return 2

    domain = build_domain()
    ffmpeg_bin = Path(first_env("FFMPEG_BIN_DIR", default=r"F:\ffmpeg\bin"))
    ffprobe = ffmpeg_bin / "ffprobe.exe"

    print("[INFO] OpenAPI domain:", domain)
    print("[INFO] Device:", device_id)
    print("[INFO] Channel ID:", channel_id)
    print("[INFO] Stream ID:", stream_id)

    access_resp = openapi_call(
        "accessToken",
        domain=domain,
        app_id=app_id,
        app_secret=app_secret,
        params={},
    )
    access_data = assert_ok(access_resp, "accessToken")
    token = str(access_data.get("accessToken", "")).strip()
    if not token:
        raise RuntimeError("accessToken response missing accessToken")
    print("[INFO] accessToken acquired")

    bind_error = ""
    bind_data: dict[str, Any] = {}
    try:
        bind_resp = openapi_call(
            "bindDeviceLive",
            domain=domain,
            app_id=app_id,
            app_secret=app_secret,
            params={
                "token": token,
                "deviceId": device_id,
                "channelId": channel_id,
                "streamId": stream_id,
                "liveMode": "proxy",
            },
        )
        bind_data = assert_ok(bind_resp, "bindDeviceLive")
        print("[INFO] bindDeviceLive succeeded")
    except Exception as err:  # noqa: BLE001
        bind_error = str(err)
        print("[WARN] bindDeviceLive warning:", bind_error)
        print("[WARN] Continue with getLiveStreamInfo...")

    info_resp = openapi_call(
        "getLiveStreamInfo",
        domain=domain,
        app_id=app_id,
        app_secret=app_secret,
        params={
            "token": token,
            "deviceId": device_id,
            "channelId": channel_id,
        },
    )
    info_data = assert_ok(info_resp, "getLiveStreamInfo")
    live_status = info_data.get("liveStatus")
    streams = info_data.get("streams", [])
    if not isinstance(streams, list):
        raise RuntimeError("getLiveStreamInfo returned invalid streams")

    hls_url = pick_hls_url(streams, stream_id)
    print("[SUCCESS] HLS URL:", hls_url)
    print("[INFO] liveStatus:", live_status)

    logs_dir = Path(r"F:\programming\python\MTImou\logs")
    logs_dir.mkdir(parents=True, exist_ok=True)
    out_path = logs_dir / "openapi_live_result.json"
    out_payload = {
        "time": int(time.time()),
        "domain": domain,
        "deviceId": device_id,
        "channelId": channel_id,
        "streamId": stream_id,
        "liveStatus": live_status,
        "hls": hls_url,
        "bindWarning": bind_error,
        "bindData": bind_data,
        "streamCount": len(streams),
    }
    out_path.write_text(json.dumps(out_payload, indent=2), encoding="utf-8")
    print("[INFO] Saved:", out_path)

    probe_hls(ffprobe, hls_url)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as err:  # noqa: BLE001
        print("[ERROR]", err)
        raise SystemExit(1)
