from __future__ import annotations

import os
from dataclasses import replace
from pathlib import Path

from mtimou_v2.app_state import OperatorSettingsState
from mtimou_v2.operator_services import OperatorServices
from mtimou_v2.registry import enabled_cameras
from mtimou_v2.settings_store import BatchEnvSettingsStore, SettingsDocument


class ControlPanelViewModel:
    def __init__(self, *, root_dir: Path, env_path: Path) -> None:
        self.root_dir = root_dir
        self.env_path = env_path
        self.store = BatchEnvSettingsStore(env_path)
        self.services = OperatorServices(root_dir)
        self.document: SettingsDocument | None = None
        self.state = OperatorSettingsState()

    def load(self) -> OperatorSettingsState:
        self.document, self.state = self.store.load_state()
        self._apply_env_values_to_process()
        return self.state

    def save(self, new_state: OperatorSettingsState) -> OperatorSettingsState:
        updates = {
            "IMOU_TARGET_MODE": new_state.target_mode.strip() or "auto",
            "IMOU_DDNS_HOST": new_state.ddns_host.strip(),
            "IMOU_CAMERA_USERNAME": new_state.username.strip() or "admin",
        }
        for entry in new_state.password_entries:
            updates[entry.env_name] = entry.value.strip()
        if self.document is None:
            self.document = SettingsDocument(
                lines=["@echo off", "REM Local operator settings for MTImou", ""],
                values={},
            )
        self.document = self.store.save_document(self.document, updates)
        self.state = self.store.load_state()[1]
        self._apply_env_values_to_process()
        return self.state

    def launch_selected(self, camera_ids: list[str]) -> tuple[str, str]:
        if len(camera_ids) == 1:
            self.services.launch_batch("run_camera_stable.bat", [camera_ids[0]])
            return (f"[INFO] Launched run_camera_stable.bat {camera_ids[0]}", f"Launched camera viewer for {camera_ids[0]}")
        self.services.launch_batch("run_multi_camera_stable.bat", camera_ids)
        return (f"[INFO] Launched run_multi_camera_stable.bat {' '.join(camera_ids)}", f"Launched selected cameras: {', '.join(camera_ids)}")

    def launch_all(self) -> tuple[list[str], tuple[str, str] | None]:
        ids = [camera.camera_id for camera in enabled_cameras()]
        if not ids:
            return ids, None
        self.services.launch_batch("run_multi_camera_stable.bat", ids)
        return ids, (f"[INFO] Launched run_multi_camera_stable.bat {' '.join(ids)}", "Launched multi-camera viewer")

    def open_logs_folder(self) -> None:
        self.services.open_logs_folder()

    def open_readme(self) -> None:
        self.services.open_readme()

    def health_check_command(self) -> tuple[str, list[str], dict[str, str]]:
        process_env = {key: value for key, value in os.environ.items()}
        return (
            str(self.root_dir / ".venv" / "Scripts" / "python.exe"),
            [str(self.root_dir / "src" / "system_health_check.py")],
            process_env,
        )

    def _apply_env_values_to_process(self) -> None:
        if self.document is None:
            return
        for key, value in self.document.values.items():
            if key.startswith("IMOU_"):
                os.environ[key] = value
