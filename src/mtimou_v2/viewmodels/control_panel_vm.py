from __future__ import annotations

import os
from pathlib import Path

from mtimou_v2.app_state import CameraEditorEntry, OperatorSettingsState, SelectionPreset
from mtimou_v2.camera_config_store import CameraConfigDocument, CameraConfigStore
from mtimou_v2.operator_services import OperatorServices
from mtimou_v2.preset_store import PresetDocument, PresetStore
from mtimou_v2.registry import DEFAULT_CONFIG_PATH, default_password_env_names, enabled_cameras
from mtimou_v2.settings_store import BatchEnvSettingsStore, SettingsDocument


class ControlPanelViewModel:
    def __init__(self, *, root_dir: Path, env_path: Path) -> None:
        self.root_dir = root_dir
        self.env_path = env_path
        self.store = BatchEnvSettingsStore(env_path)
        self.camera_store = CameraConfigStore(DEFAULT_CONFIG_PATH)
        self.preset_store = PresetStore(root_dir / "camera_presets.json")
        self.services = OperatorServices(root_dir)
        self.document: SettingsDocument | None = None
        self.camera_document: CameraConfigDocument | None = None
        self.preset_document: PresetDocument | None = None
        self.state = OperatorSettingsState()

    def load(self) -> OperatorSettingsState:
        self.document, self.state = self.store.load_state()
        self.camera_document, entries = self.camera_store.load_entries()
        self.preset_document, presets = self.preset_store.load_presets()
        self.state.camera_editor_entries = entries
        self.state.selection_presets = presets
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
        self.camera_document, entries = self.camera_store.load_entries()
        self.preset_document, presets = self.preset_store.load_presets()
        self.state.camera_editor_entries = entries
        self.state.selection_presets = presets
        self._apply_env_values_to_process()
        return self.state

    def save_camera_inventory(self, entries: list[CameraEditorEntry]) -> OperatorSettingsState:
        if self.camera_document is None:
            self.camera_document = CameraConfigDocument(raw={"cameras": []})
        self.camera_document = self.camera_store.save_entries(self.camera_document, entries)
        self.document, self.state = self.store.load_state()
        self.camera_document, camera_entries = self.camera_store.load_entries()
        self.preset_document, presets = self.preset_store.load_presets()
        self.state.camera_editor_entries = camera_entries
        self.state.selection_presets = presets
        self._apply_env_values_to_process()
        return self.state

    def save_preset(self, name: str, camera_ids: list[str]) -> OperatorSettingsState:
        clean_name = name.strip()
        if not clean_name:
            raise ValueError("Preset name is required.")
        normalized_ids = [camera_id.strip() for camera_id in camera_ids if camera_id.strip()]
        if not normalized_ids:
            raise ValueError("Select one or more cameras before saving a preset.")
        presets = [preset for preset in self.state.selection_presets if preset.name != clean_name]
        presets.append(SelectionPreset(name=clean_name, camera_ids=normalized_ids))
        self.preset_document = self.preset_store.save_presets(presets)
        _, reloaded = self.preset_store.load_presets()
        self.state.selection_presets = reloaded
        return self.state

    def delete_preset(self, name: str) -> OperatorSettingsState:
        presets = [preset for preset in self.state.selection_presets if preset.name != name]
        self.preset_document = self.preset_store.save_presets(presets)
        _, reloaded = self.preset_store.load_presets()
        self.state.selection_presets = reloaded
        return self.state

    def new_camera_entry(self, existing_ids: set[str]) -> CameraEditorEntry:
        index = 1
        while f"cam{index}" in existing_ids:
            index += 1
        camera_id = f"cam{index}"
        password_env = default_password_env_names(camera_id)[0]
        return CameraEditorEntry(
            camera_id=camera_id,
            name=f"Camera {index}",
            group_name="default",
            tier="standard",
            lan_host="192.168.1.10",
            lan_port=554,
            ddns_host=self.state.ddns_host.strip(),
            ddns_port=45553 + index,
            public_host="125.27.213.148",
            public_port=45553 + index,
            channel="1",
            subtype="0",
            transport="tcp",
            remote_wall_subtype="1",
            remote_focus_subtype="0",
            enabled=True,
            username_env="IMOU_CAMERA_USERNAME",
            password_env_name=password_env,
        )

    def launch_selected(self, camera_ids: list[str]) -> tuple[str, str]:
        if len(camera_ids) == 1:
            self.services.launch_batch("run_camera_stable.bat", [camera_ids[0]])
            return (f"[INFO] Launched run_camera_stable.bat {camera_ids[0]}", f"Launched camera viewer for {camera_ids[0]}")
        self.services.launch_batch("run_multi_camera_stable.bat", camera_ids)
        return (f"[INFO] Launched run_multi_camera_stable.bat {' '.join(camera_ids)}", f"Launched selected cameras: {', '.join(camera_ids)}")

    def launch_selected_high_fps(self, camera_ids: list[str]) -> tuple[str, str]:
        self.services.launch_batch("run_multi_camera_high_fps.bat", camera_ids)
        return (
            f"[INFO] Launched run_multi_camera_high_fps.bat {' '.join(camera_ids)}",
            f"Launched high-FPS split view for: {', '.join(camera_ids)}",
        )

    def launch_all(self) -> tuple[list[str], tuple[str, str] | None]:
        ids = [camera.camera_id for camera in enabled_cameras()]
        if not ids:
            return ids, None
        self.services.launch_batch("run_multi_camera_stable.bat", ids)
        return ids, (f"[INFO] Launched run_multi_camera_stable.bat {' '.join(ids)}", "Launched multi-camera viewer")

    def launch_tier(self, tier: str, *, high_fps: bool = False) -> tuple[list[str], tuple[str, str] | None]:
        ids = [camera.camera_id for camera in self.state.cameras if camera.enabled and camera.tier == tier]
        if not ids:
            return ids, None
        batch_name = "run_multi_camera_high_fps.bat" if high_fps else "run_multi_camera_stable.bat"
        self.services.launch_batch(batch_name, ids)
        mode_label = "high-FPS " if high_fps else ""
        return ids, (f"[INFO] Launched {batch_name} {' '.join(ids)}", f"Launched {mode_label}{tier} cameras")

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

    def source_capability_command(self, camera_ids: list[str] | None = None) -> tuple[str, list[str], dict[str, str]]:
        process_env = {key: value for key, value in os.environ.items()}
        arguments = [str(self.root_dir / "src" / "source_capability_check.py")]
        if camera_ids:
            arguments.extend(camera_ids)
        return (
            str(self.root_dir / ".venv" / "Scripts" / "python.exe"),
            arguments,
            process_env,
        )

    def _apply_env_values_to_process(self) -> None:
        if self.document is None:
            return
        for key, value in self.document.values.items():
            if key.startswith("IMOU_"):
                os.environ[key] = value
