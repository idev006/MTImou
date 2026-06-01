from __future__ import annotations

import json
import os
import re
import socket
from dataclasses import dataclass
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG_PATH = ROOT_DIR / "cameras.json"


@dataclass(slots=True)
class CameraConfig:
    camera_id: str
    name: str
    lan_host: str
    lan_port: int
    ddns_host: str
    ddns_port: int
    public_host: str
    public_port: int
    channel: str
    subtype: str
    transport: str
    username: str
    password: str
    enabled: bool


@dataclass(slots=True)
class CameraTarget:
    camera: CameraConfig
    mode: str
    host: str
    port: int


def _probe_tcp(host: str, port: int, timeout_sec: float = 1.2) -> bool:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(timeout_sec)
    try:
        sock.connect((host, port))
        return True
    except Exception:
        return False
    finally:
        sock.close()


def _load_raw_config(config_path: Path | None = None) -> dict:
    path = config_path or DEFAULT_CONFIG_PATH
    return json.loads(path.read_text(encoding="utf-8"))


def _resolve_username(item: dict) -> str:
    env_name = item.get("username_env", "IMOU_CAMERA_USERNAME")
    return os.getenv(env_name, "admin").strip() or "admin"


def default_password_env_names(camera_id: str) -> list[str]:
    normalized = re.sub(r"[^A-Za-z0-9]+", "_", camera_id.strip()).upper()
    names = [f"IMOU_CAM_{normalized}_PASSWORD"]
    match = re.search(r"(\d+)$", camera_id.strip().lower())
    if match:
        index = int(match.group(1))
        if index <= 1:
            names.append("IMOU_CAMERA_PASSWORD")
        else:
            names.append(f"IMOU_CAMERA{index}_PASSWORD")
    names.append("IMOU_CAMERA_PASSWORD")
    deduped: list[str] = []
    for name in names:
        if name and name not in deduped:
            deduped.append(name)
    return deduped


def _resolve_password(item: dict) -> str:
    env_names = [str(name).strip() for name in item.get("password_envs", []) if str(name).strip()]
    env_names.extend(default_password_env_names(str(item.get("id", ""))))
    seen: set[str] = set()
    for env_name in env_names:
        if env_name in seen:
            continue
        seen.add(env_name)
        value = os.getenv(env_name, "").strip()
        if value:
            return value
    return item.get("password", "").strip()


def _resolve_ddns_host(item: dict) -> str:
    direct_value = str(item.get("ddns_host", "")).strip()
    if direct_value:
        return direct_value

    env_names: list[str] = []
    single_env = str(item.get("ddns_host_env", "")).strip()
    if single_env:
        env_names.append(single_env)
    env_names.extend(str(name).strip() for name in item.get("ddns_host_envs", []) if str(name).strip())
    env_names.extend(["IMOU_CAMERA_DDNS_HOST", "IMOU_DDNS_HOST"])

    for env_name in env_names:
        value = os.getenv(env_name, "").strip()
        if value:
            return value
    return ""


def load_cameras(config_path: Path | None = None) -> list[CameraConfig]:
    raw = _load_raw_config(config_path)
    cameras: list[CameraConfig] = []
    for item in raw.get("cameras", []):
        cameras.append(
            CameraConfig(
                camera_id=str(item["id"]),
                name=str(item.get("name", item["id"])),
                lan_host=str(item["lan_host"]),
                lan_port=int(item.get("lan_port", 554)),
                ddns_host=_resolve_ddns_host(item),
                ddns_port=int(item.get("ddns_port", item.get("public_port", 45554))),
                public_host=str(item["public_host"]),
                public_port=int(item.get("public_port", 45554)),
                channel=str(item.get("channel", "1")),
                subtype=str(item.get("subtype", "0")),
                transport=str(item.get("transport", "tcp")),
                username=_resolve_username(item),
                password=_resolve_password(item),
                enabled=bool(item.get("enabled", True)),
            )
        )
    return cameras


def get_camera(camera_id: str, config_path: Path | None = None) -> CameraConfig:
    for camera in load_cameras(config_path):
        if camera.camera_id == camera_id:
            return camera
    raise KeyError(f"Camera id not found: {camera_id}")


def pick_target(camera: CameraConfig, timeout_sec: float = 1.2, preferred_mode: str = "auto") -> CameraTarget:
    preferred_mode = preferred_mode.strip().lower()

    def lan_target() -> CameraTarget | None:
        if _probe_tcp(camera.lan_host, camera.lan_port, timeout_sec=timeout_sec):
            return CameraTarget(camera=camera, mode="lan", host=camera.lan_host, port=camera.lan_port)
        return None

    def ddns_target() -> CameraTarget | None:
        if camera.ddns_host:
            return CameraTarget(camera=camera, mode="ddns", host=camera.ddns_host, port=camera.ddns_port)
        return None

    def public_target() -> CameraTarget:
        return CameraTarget(camera=camera, mode="public", host=camera.public_host, port=camera.public_port)

    if preferred_mode == "lan":
        target = lan_target()
        if target is None:
            raise RuntimeError(f"LAN target unavailable for {camera.camera_id}")
        return target
    if preferred_mode == "ddns":
        target = ddns_target()
        if target is None:
            raise RuntimeError(f"DDNS target not configured for {camera.camera_id}")
        return target
    if preferred_mode == "public":
        return public_target()

    target = lan_target()
    if target is not None:
        return target
    target = ddns_target()
    if target is not None:
        return target
    return public_target()


def target_modes_summary(camera: CameraConfig) -> list[str]:
    modes = [f"lan={camera.lan_host}:{camera.lan_port}"]
    if camera.ddns_host:
        modes.append(f"ddns={camera.ddns_host}:{camera.ddns_port}")
    modes.append(f"public={camera.public_host}:{camera.public_port}")
    return modes


def enabled_cameras(config_path: Path | None = None) -> list[CameraConfig]:
    return [camera for camera in load_cameras(config_path) if camera.enabled]
