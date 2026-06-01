from __future__ import annotations

import socket

from mtimou_v2.models import CameraConfig, CameraTarget


def probe_tcp(host: str, port: int, timeout_sec: float = 1.2) -> bool:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(timeout_sec)
    try:
        sock.connect((host, port))
        return True
    except Exception:
        return False
    finally:
        sock.close()


def resolve_host(host: str) -> str:
    try:
        return socket.gethostbyname(host)
    except Exception:
        return ""


def pick_target(camera: CameraConfig, timeout_sec: float = 1.2, preferred_mode: str = "auto") -> CameraTarget:
    preferred_mode = preferred_mode.strip().lower()

    def lan_target() -> CameraTarget | None:
        if probe_tcp(camera.lan_host, camera.lan_port, timeout_sec=timeout_sec):
            return CameraTarget(camera=camera, mode="lan", host=camera.lan_host, port=camera.lan_port)
        return None

    def ddns_target() -> CameraTarget | None:
        if camera.ddns_host and probe_tcp(camera.ddns_host, camera.ddns_port, timeout_sec=timeout_sec):
            return CameraTarget(camera=camera, mode="ddns", host=camera.ddns_host, port=camera.ddns_port)
        return None

    def public_target(probe: bool = False) -> CameraTarget | None:
        if probe and not probe_tcp(camera.public_host, camera.public_port, timeout_sec=timeout_sec):
            return None
        return CameraTarget(camera=camera, mode="public", host=camera.public_host, port=camera.public_port)

    if preferred_mode == "lan":
        target = lan_target()
        if target is None:
            raise RuntimeError(f"LAN target unavailable for {camera.camera_id}")
        return target
    if preferred_mode == "ddns":
        if not camera.ddns_host:
            raise RuntimeError(f"DDNS target not configured for {camera.camera_id}")
        return CameraTarget(camera=camera, mode="ddns", host=camera.ddns_host, port=camera.ddns_port)
    if preferred_mode == "public":
        target = public_target(probe=False)
        if target is None:
            raise RuntimeError(f"Public target not configured for {camera.camera_id}")
        return target

    for resolver in (lan_target, ddns_target):
        target = resolver()
        if target is not None:
            return target
    target = public_target(probe=True)
    if target is not None:
        return target
    raise RuntimeError(f"No reachable target for {camera.camera_id}")

