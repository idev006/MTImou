from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class CameraListItem:
    camera_id: str
    name: str
    label: str
    enabled: bool


@dataclass(slots=True)
class PasswordEntry:
    camera_id: str
    camera_name: str
    env_name: str
    value: str


@dataclass(slots=True)
class OperatorSettingsState:
    target_mode: str = "auto"
    ddns_host: str = ""
    username: str = "admin"
    password_entries: list[PasswordEntry] = field(default_factory=list)
    cameras: list[CameraListItem] = field(default_factory=list)
    output_lines: list[str] = field(default_factory=list)

