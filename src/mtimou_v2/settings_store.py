from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from mtimou_v2.app_state import CameraListItem, OperatorSettingsState, PasswordEntry
from mtimou_v2.registry import default_password_env_names, load_cameras, target_modes_summary


def unescape_batch_value(value: str) -> str:
    unescaped = value.replace("%%", "%")
    unescaped = unescaped.replace('^"', '"')
    unescaped = unescaped.replace("^^", "^")
    return unescaped


def escape_batch_value(value: str) -> str:
    escaped = value.replace("^", "^^")
    escaped = escaped.replace("%", "%%")
    escaped = escaped.replace('"', '^"')
    return escaped


@dataclass(slots=True)
class SettingsDocument:
    lines: list[str]
    values: dict[str, str]


class BatchEnvSettingsStore:
    def __init__(self, env_path: Path) -> None:
        self.env_path = env_path

    def load_document(self) -> SettingsDocument:
        lines: list[str] = []
        values: dict[str, str] = {}
        if self.env_path.exists():
            previous_blank = False
            with self.env_path.open("r", encoding="ascii", errors="ignore") as handle:
                for raw_line in handle:
                    line = raw_line.rstrip("\r\n")
                    stripped = line.strip()
                    if not stripped:
                        # Keep at most a single separator blank line in memory, and
                        # never allow pathological blank-line growth to bloat the file
                        # on the next save.
                        if lines and not previous_blank:
                            lines.append("")
                        previous_blank = True
                        continue
                    previous_blank = False
                    lines.append(line)
                    if stripped.lower().startswith("set ") and "=" in stripped:
                        payload = stripped[4:]
                        if payload.startswith('"') and payload.endswith('"'):
                            payload = payload[1:-1]
                        key, value = payload.split("=", 1)
                        values[key.strip()] = unescape_batch_value(value.strip())
        return SettingsDocument(lines=lines, values=values)

    def save_document(self, document: SettingsDocument, updates: dict[str, str]) -> SettingsDocument:
        remaining = dict(updates)
        new_lines: list[str] = []
        for line in document.lines:
            stripped = line.strip()
            if stripped.lower().startswith("set ") and "=" in stripped:
                payload = stripped[4:]
                if payload.startswith('"') and payload.endswith('"'):
                    payload = payload[1:-1]
                key, _ = payload.split("=", 1)
                key = key.strip()
                if key in remaining:
                    new_lines.append(f'set "{key}={escape_batch_value(remaining.pop(key))}"')
                    continue
            new_lines.append(line)
        if remaining:
            if new_lines and new_lines[-1].strip():
                new_lines.append("")
            for key, value in remaining.items():
                new_lines.append(f'set "{key}={escape_batch_value(value)}"')
        self.env_path.write_text("\r\n".join(new_lines) + "\r\n", encoding="ascii")
        return self.load_document()

    def load_state(self) -> tuple[SettingsDocument, OperatorSettingsState]:
        document = self.load_document()
        values = document.values
        cameras = load_cameras()
        state = OperatorSettingsState(
            target_mode=values.get("IMOU_TARGET_MODE", "auto") or "auto",
            ddns_host=values.get("IMOU_DDNS_HOST", ""),
            username=values.get("IMOU_CAMERA_USERNAME", "admin") or "admin",
        )
        for camera in cameras:
            env_names = default_password_env_names(camera.camera_id)
            primary_env = env_names[0]
            value = ""
            for env_name in env_names:
                value = values.get(env_name, "")
                if value:
                    break
            state.password_entries.append(
                PasswordEntry(
                    camera_id=camera.camera_id,
                    camera_name=camera.name,
                    env_name=primary_env,
                    value=value,
                )
            )
            state.cameras.append(
                CameraListItem(
                    camera_id=camera.camera_id,
                    name=camera.name,
                    group_name=camera.group_name,
                    tier=camera.tier,
                    label=f"{camera.camera_id} | {camera.name} | group={camera.group_name} | tier={camera.tier} | {' ; '.join(target_modes_summary(camera))}",
                    enabled=camera.enabled,
                )
            )
        return document, state
