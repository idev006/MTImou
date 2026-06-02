from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class CameraListItem:
    camera_id: str
    name: str
    group_name: str
    tier: str
    label: str
    enabled: bool


@dataclass(slots=True)
class PasswordEntry:
    camera_id: str
    camera_name: str
    env_name: str
    value: str


@dataclass(slots=True)
class CameraEditorEntry:
    camera_id: str
    name: str
    group_name: str
    tier: str
    lan_host: str
    lan_port: int
    ddns_host: str
    ddns_port: int
    public_host: str
    public_port: int
    channel: str
    subtype: str
    transport: str
    remote_wall_subtype: str
    remote_focus_subtype: str
    enabled: bool
    username_env: str
    password_env_name: str


@dataclass(slots=True)
class OperatorSettingsState:
    target_mode: str = "auto"
    ddns_host: str = ""
    username: str = "admin"
    password_entries: list[PasswordEntry] = field(default_factory=list)
    cameras: list[CameraListItem] = field(default_factory=list)
    camera_editor_entries: list[CameraEditorEntry] = field(default_factory=list)
    output_lines: list[str] = field(default_factory=list)
