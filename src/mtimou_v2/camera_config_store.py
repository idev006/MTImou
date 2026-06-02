from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from mtimou_v2.app_state import CameraEditorEntry
from mtimou_v2.registry import default_password_env_names


@dataclass(slots=True)
class CameraConfigDocument:
    raw: dict


class CameraConfigStore:
    def __init__(self, config_path: Path) -> None:
        self.config_path = config_path

    def load_document(self) -> CameraConfigDocument:
        if not self.config_path.exists():
            return CameraConfigDocument(raw={"cameras": []})
        return CameraConfigDocument(raw=json.loads(self.config_path.read_text(encoding="utf-8")))

    def load_entries(self) -> tuple[CameraConfigDocument, list[CameraEditorEntry]]:
        document = self.load_document()
        entries: list[CameraEditorEntry] = []
        for item in document.raw.get("cameras", []):
            camera_id = str(item.get("id", "")).strip()
            password_envs = [str(name).strip() for name in item.get("password_envs", []) if str(name).strip()]
            default_password = password_envs[0] if password_envs else default_password_env_names(camera_id)[0]
            entries.append(
                CameraEditorEntry(
                    camera_id=camera_id,
                    name=str(item.get("name", camera_id)).strip(),
                    group_name=str(item.get("group_name", "default")).strip() or "default",
                    tier=str(item.get("tier", "standard")).strip() or "standard",
                    lan_host=str(item.get("lan_host", "")).strip(),
                    lan_port=int(item.get("lan_port", 554)),
                    ddns_host=str(item.get("ddns_host", "")).strip(),
                    ddns_port=int(item.get("ddns_port", item.get("public_port", 45554))),
                    public_host=str(item.get("public_host", "")).strip(),
                    public_port=int(item.get("public_port", 45554)),
                    channel=str(item.get("channel", "1")).strip() or "1",
                    subtype=str(item.get("subtype", "0")).strip() or "0",
                    transport=str(item.get("transport", "tcp")).strip() or "tcp",
                    remote_wall_subtype=str(item.get("remote_wall_subtype", "1")).strip() or "1",
                    remote_focus_subtype=str(item.get("remote_focus_subtype", "0")).strip() or "0",
                    enabled=bool(item.get("enabled", True)),
                    username_env=str(item.get("username_env", "IMOU_CAMERA_USERNAME")).strip() or "IMOU_CAMERA_USERNAME",
                    password_env_name=default_password,
                )
            )
        return document, entries

    def save_entries(self, document: CameraConfigDocument, entries: list[CameraEditorEntry]) -> CameraConfigDocument:
        old_by_id = {
            str(item.get("id", "")).strip(): item
            for item in document.raw.get("cameras", [])
            if str(item.get("id", "")).strip()
        }
        new_cameras: list[dict] = []
        for entry in entries:
            base = dict(old_by_id.get(entry.camera_id, {}))
            base.update(
                {
                    "id": entry.camera_id.strip(),
                    "name": entry.name.strip() or entry.camera_id.strip(),
                    "group_name": entry.group_name.strip() or "default",
                    "tier": entry.tier.strip() or "standard",
                    "lan_host": entry.lan_host.strip(),
                    "lan_port": int(entry.lan_port),
                    "ddns_host": entry.ddns_host.strip(),
                    "ddns_port": int(entry.ddns_port),
                    "public_host": entry.public_host.strip(),
                    "public_port": int(entry.public_port),
                    "channel": entry.channel.strip() or "1",
                    "subtype": entry.subtype.strip() or "0",
                    "transport": entry.transport.strip() or "tcp",
                    "remote_wall_subtype": entry.remote_wall_subtype.strip() or "1",
                    "remote_focus_subtype": entry.remote_focus_subtype.strip() or "0",
                    "username_env": entry.username_env.strip() or "IMOU_CAMERA_USERNAME",
                    "password_envs": [entry.password_env_name.strip() or default_password_env_names(entry.camera_id)[0]],
                    "enabled": bool(entry.enabled),
                }
            )
            new_cameras.append(base)

        payload = dict(document.raw)
        payload["cameras"] = new_cameras
        self.config_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        return self.load_document()
