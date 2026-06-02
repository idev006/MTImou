from __future__ import annotations

import json
import os
import re
from pathlib import Path

from mtimou_v2.models import CameraConfig


ROOT_DIR = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG_PATH = ROOT_DIR / "cameras.json"


def load_raw_config(config_path: Path | None = None) -> dict:
    path = config_path or DEFAULT_CONFIG_PATH
    return json.loads(path.read_text(encoding="utf-8"))


def resolve_username(item: dict) -> str:
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
    deduped: list[str] = []
    for name in names:
        if name and name not in deduped:
            deduped.append(name)
    return deduped


def resolve_password(item: dict) -> str:
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


def resolve_ddns_host(item: dict) -> str:
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
    raw = load_raw_config(config_path)
    cameras: list[CameraConfig] = []
    for item in raw.get("cameras", []):
        cameras.append(
            CameraConfig(
                camera_id=str(item["id"]),
                name=str(item.get("name", item["id"])),
                group_name=str(item.get("group_name", "default")).strip() or "default",
                tier=str(item.get("tier", "standard")).strip() or "standard",
                lan_host=str(item["lan_host"]),
                lan_port=int(item.get("lan_port", 554)),
                ddns_host=resolve_ddns_host(item),
                ddns_port=int(item.get("ddns_port", item.get("public_port", 45554))),
                public_host=str(item["public_host"]),
                public_port=int(item.get("public_port", 45554)),
                channel=str(item.get("channel", "1")),
                subtype=str(item.get("subtype", "0")),
                transport=str(item.get("transport", "tcp")),
                remote_wall_subtype=str(item.get("remote_wall_subtype", "1")).strip() or "1",
                remote_focus_subtype=str(item.get("remote_focus_subtype", "0")).strip() or "0",
                username=resolve_username(item),
                password=resolve_password(item),
                enabled=bool(item.get("enabled", True)),
            )
        )
    return cameras


def get_camera(camera_id: str, config_path: Path | None = None) -> CameraConfig:
    for camera in load_cameras(config_path):
        if camera.camera_id == camera_id:
            return camera
    raise KeyError(f"Camera id not found: {camera_id}")


def enabled_cameras(config_path: Path | None = None) -> list[CameraConfig]:
    return [camera for camera in load_cameras(config_path) if camera.enabled]


def target_modes_summary(camera: CameraConfig) -> list[str]:
    modes = [f"lan={camera.lan_host}:{camera.lan_port}"]
    if camera.ddns_host:
        modes.append(f"ddns={camera.ddns_host}:{camera.ddns_port}")
    modes.append(f"public={camera.public_host}:{camera.public_port}")
    return modes
