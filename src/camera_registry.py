from __future__ import annotations

import json
import os
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


def _resolve_password(item: dict) -> str:
    for env_name in item.get("password_envs", []):
        value = os.getenv(env_name, "").strip()
        if value:
            return value
    return item.get("password", "").strip()


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


def pick_target(camera: CameraConfig, timeout_sec: float = 1.2) -> CameraTarget:
    if _probe_tcp(camera.lan_host, camera.lan_port, timeout_sec=timeout_sec):
        return CameraTarget(camera=camera, mode="lan", host=camera.lan_host, port=camera.lan_port)
    return CameraTarget(camera=camera, mode="public", host=camera.public_host, port=camera.public_port)


def enabled_cameras(config_path: Path | None = None) -> list[CameraConfig]:
    return [camera for camera in load_cameras(config_path) if camera.enabled]
