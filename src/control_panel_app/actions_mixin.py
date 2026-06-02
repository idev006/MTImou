from __future__ import annotations

from PySide6.QtCore import QItemSelectionModel, QProcess, Qt
from PySide6.QtWidgets import QApplication, QLineEdit, QMessageBox

from control_panel_app.components import CameraWizardDialog, PresetDialog
from control_panel_app.constants import ENV_PATH, ROOT_DIR, WINDOW_TITLE
from mtimou_v2.app_state import OperatorSettingsState


class ControlPanelActionsMixin:
    def _prompt_unsaved_inventory_decision(self, action_label: str) -> str:
        dialog = QMessageBox(self)
        dialog.setWindowTitle(WINDOW_TITLE)
        dialog.setIcon(QMessageBox.Warning)
        dialog.setText("Camera inventory has unsaved changes.")
        dialog.setInformativeText(f"Do you want to save before you {action_label}?")
        save_button = dialog.addButton("Save", QMessageBox.AcceptRole)
        discard_button = dialog.addButton("Discard", QMessageBox.DestructiveRole)
        cancel_button = dialog.addButton("Cancel", QMessageBox.RejectRole)
        dialog.setDefaultButton(save_button)
        dialog.exec()
        clicked = dialog.clickedButton()
        if clicked is save_button:
            return "save"
        if clicked is discard_button:
            return "discard"
        return "cancel"

    def _ensure_inventory_ready(self, action_label: str) -> bool:
        if not getattr(self, "inventory_dirty", False):
            return True
        decision = self._prompt_unsaved_inventory_decision(action_label)
        if decision == "save":
            return self.save_camera_inventory()
        if decision == "discard":
            self.reload_settings(confirm_dirty=False)
            return True
        self.append_output(f"[INFO] Cancelled action: {action_label}")
        self._set_status(f"Cancelled action: {action_label}")
        return False

    def _resolve_selected_preset(self):
        preset_name = str(self.preset_combo.currentData() or "").strip()
        if not preset_name:
            QMessageBox.information(self, WINDOW_TITLE, "Choose a preset first.")
            return None
        preset = next((item for item in self.vm.state.selection_presets if item.name == preset_name), None)
        if preset is None:
            QMessageBox.warning(self, WINDOW_TITLE, "Preset not found.")
            return None
        return preset

    def _select_camera_ids_in_table(self, camera_ids: list[str]) -> None:
        wanted = set(camera_ids)
        if not wanted:
            self.camera_table.clearSelection()
            self._refresh_selection_summary()
            return
        if self.camera_search_edit.text().strip():
            self.camera_search_edit.clear()
        if self.group_filter_combo.currentText().strip() != "All Groups":
            self.group_filter_combo.setCurrentText("All Groups")
        if self.tier_filter_combo.currentText().strip() != "All Tiers":
            self.tier_filter_combo.setCurrentText("All Tiers")
        self._apply_camera_table_filters()
        self.camera_table.clearSelection()
        for row in range(self.camera_table.rowCount()):
            item = self.camera_table.item(row, 0)
            if item is not None and str(item.data(Qt.UserRole)) in wanted:
                index = self.camera_table.model().index(row, 0)
                self.camera_table.selectionModel().select(index, QItemSelectionModel.Select | QItemSelectionModel.Rows)
        self._refresh_selection_summary()

    def open_add_camera_wizard(self) -> None:
        next_camera_id, next_public_port = self._next_camera_seed()
        public_host = self.vm.state.camera_editor_entries[0].public_host if self.vm.state.camera_editor_entries else "125.27.213.148"
        dialog = CameraWizardDialog(
            next_camera_id=next_camera_id,
            ddns_host=self.ddns_edit.text().strip(),
            public_host=public_host,
            public_port=next_public_port,
            parent=self,
        )
        if dialog.exec() != dialog.Accepted:
            return
        payload = dialog.values()
        from mtimou_v2.app_state import CameraEditorEntry

        entry = CameraEditorEntry(
            camera_id=str(payload["camera_id"]),
            name=str(payload["name"]) or str(payload["camera_id"]),
            group_name=str(payload["group_name"]) or "default",
            tier=str(payload["tier"]) or "standard",
            lan_host=str(payload["lan_host"]),
            lan_port=int(payload["lan_port"]),
            ddns_host=str(payload["ddns_host"]),
            ddns_port=int(payload["ddns_port"]),
            public_host=str(payload["public_host"]),
            public_port=int(payload["public_port"]),
            channel="1",
            subtype="0",
            transport="tcp",
            remote_wall_subtype=str(payload["remote_wall_subtype"]) or "1",
            remote_focus_subtype=str(payload["remote_focus_subtype"]) or "0",
            enabled=bool(payload["enabled"]),
            username_env="IMOU_CAMERA_USERNAME",
            password_env_name=str(payload["password_env_name"]),
        )
        self.vm.state.camera_editor_entries.append(entry)
        self._refresh_inventory_table()
        self._set_inventory_dirty(True, reason="Added draft camera inventory changes")
        self.append_output(f"[INFO] Added wizard camera row for {entry.camera_id}")

    def add_camera_inventory_row(self) -> None:
        existing_ids = set()
        for row in range(self.inventory_table.rowCount()):
            item = self.inventory_table.item(row, 1)
            if item and item.text().strip():
                existing_ids.add(item.text().strip())
        entry = self.vm.new_camera_entry(existing_ids)
        self.vm.state.camera_editor_entries.append(entry)
        self._refresh_inventory_table()
        self._set_inventory_dirty(True, reason="Added draft camera inventory changes")
        self.append_output(f"[INFO] Added draft camera row for {entry.camera_id}")

    def remove_selected_inventory_rows(self) -> None:
        selected_rows = sorted({item.row() for item in self.inventory_table.selectedItems()}, reverse=True)
        if not selected_rows:
            QMessageBox.information(self, WINDOW_TITLE, "Select one or more inventory rows to remove.")
            return
        for row in selected_rows:
            del self.vm.state.camera_editor_entries[row]
        self._refresh_inventory_table()
        self._set_inventory_dirty(True, reason="Removed camera inventory rows")
        self.append_output(f"[INFO] Removed {len(selected_rows)} draft camera row(s)")

    def apply_bulk_edit_to_inventory(self) -> None:
        selected_rows = sorted({item.row() for item in self.inventory_table.selectedItems()})
        if not selected_rows:
            QMessageBox.information(self, WINDOW_TITLE, "Select one or more inventory rows first.")
            return
        group_value = self.bulk_group_edit.text().strip()
        tier_value = self.bulk_tier_combo.currentText().strip()
        wall_value = self.bulk_wall_combo.currentText().strip()
        focus_value = self.bulk_focus_combo.currentText().strip()
        for row in selected_rows:
            if group_value:
                item = self.inventory_table.item(row, 3)
                if item is not None:
                    item.setText(group_value)
            if tier_value and tier_value != "No change":
                item = self.inventory_table.item(row, 4)
                if item is not None:
                    item.setText(tier_value)
            if wall_value and wall_value != "No change":
                item = self.inventory_table.item(row, 11)
                if item is not None:
                    item.setText(wall_value)
            if focus_value and focus_value != "No change":
                item = self.inventory_table.item(row, 12)
                if item is not None:
                    item.setText(focus_value)
        self._set_inventory_dirty(True, reason="Bulk-edited camera inventory")
        self.append_output(f"[INFO] Applied bulk edit to {len(selected_rows)} row(s)")
        self._set_status(f"Bulk edited {len(selected_rows)} inventory row(s)")

    def bulk_set_enabled_state(self, enabled: bool) -> None:
        selected_rows = sorted({item.row() for item in self.inventory_table.selectedItems()})
        if not selected_rows:
            QMessageBox.information(self, WINDOW_TITLE, "Select one or more inventory rows first.")
            return
        for row in selected_rows:
            item = self.inventory_table.item(row, 0)
            if item is not None:
                item.setCheckState(Qt.Checked if enabled else Qt.Unchecked)
                item.setText("Yes" if enabled else "No")
        self._set_inventory_dirty(True, reason="Changed enabled state in camera inventory")
        action = "enabled" if enabled else "disabled"
        self.append_output(f"[INFO] Bulk {action} {len(selected_rows)} row(s)")
        self._set_status(f"Bulk {action} {len(selected_rows)} row(s)")

    def save_camera_inventory(self) -> bool:
        entries = []
        try:
            for row in range(self.inventory_table.rowCount()):
                entries.append(self._inventory_row_to_entry(row))
            self._validate_inventory_entries(entries)
        except ValueError as exc:
            QMessageBox.warning(self, WINDOW_TITLE, str(exc))
            return False

        self.vm.save_camera_inventory(entries)
        self._rebuild_password_fields()
        self._refresh_health_snapshot()
        self._refresh_group_filter()
        self._refresh_presets()
        self._refresh_camera_table()
        self._refresh_inventory_table()
        self._update_metric_cards()
        self._set_inventory_dirty(False)
        self.append_output("[INFO] Saved camera inventory to cameras.json")
        self._set_status("Saved camera inventory")
        return True

    def save_settings(self) -> bool:
        new_state = OperatorSettingsState(
            target_mode=self.mode_combo.currentText().strip() or "auto",
            ddns_host=self.ddns_edit.text().strip(),
            username=self.user_edit.text().strip() or "admin",
            password_entries=[
                self.vm.state.password_entries[index].__class__(
                    camera_id=self.vm.state.password_entries[index].camera_id,
                    camera_name=self.vm.state.password_entries[index].camera_name,
                    env_name=field.env_name,
                    value=field.edit.text().strip(),
                )
                for index, field in enumerate(self.password_fields)
            ],
            cameras=self.vm.state.cameras,
            output_lines=self.vm.state.output_lines,
        )
        self.vm.save(new_state)
        self._refresh_camera_table()
        self._update_metric_cards()
        self.append_output(f"[INFO] Saved settings to {ENV_PATH}")
        self._set_status(f"Saved settings to {ENV_PATH}")
        return True

    def reload_settings(self, *, confirm_dirty: bool = True) -> bool:
        if confirm_dirty and not self._ensure_inventory_ready("reload settings"):
            return False
        self.vm.load()
        self.mode_combo.setCurrentText(self.vm.state.target_mode or "auto")
        self.ddns_edit.setText(self.vm.state.ddns_host)
        self.user_edit.setText(self.vm.state.username or "admin")
        self._rebuild_password_fields()
        self._refresh_health_snapshot()
        self._refresh_camera_table()
        self._refresh_inventory_table()
        self._update_metric_cards()
        self._set_inventory_dirty(False)
        self.append_output("[INFO] Reloaded settings from camera.env.bat")
        self._set_status("Reloaded settings")
        return True

    def _launch_camera_ids(self, camera_ids: list[str], *, high_fps: bool = False) -> None:
        if not camera_ids:
            QMessageBox.warning(self, WINDOW_TITLE, "Please select one or more cameras first.")
            return
        if not self._guard_action(
            f"launch:{'highfps' if high_fps else 'normal'}:{','.join(camera_ids)}",
            cooldown_sec=2.0,
            message="Launch ignored because the same action was just triggered",
        ):
            return
        if not self._ensure_inventory_ready("launch viewers"):
            return
        self.save_settings()
        if high_fps:
            message, status = self.vm.launch_selected_high_fps(camera_ids)
        else:
            message, status = self.vm.launch_selected(camera_ids)
        self.append_output(message)
        self._set_status(status)

    def launch_selected_cameras(self) -> None:
        self._launch_camera_ids(self.selected_camera_ids(), high_fps=False)

    def launch_selected_cameras_high_fps(self) -> None:
        self._launch_camera_ids(self.selected_camera_ids(), high_fps=True)

    def launch_all_cameras(self) -> None:
        if not self._guard_action("launch:all", cooldown_sec=2.0, message="Launch ignored because all-enabled view was just triggered"):
            return
        if not self._ensure_inventory_ready("launch all enabled cameras"):
            return
        self.save_settings()
        ids, result = self.vm.launch_all()
        if not ids:
            QMessageBox.warning(self, WINDOW_TITLE, "No enabled cameras found.")
            return
        if result is not None:
            message, status = result
            self.append_output(message)
            self._set_status(status)

    def launch_critical_cameras(self) -> None:
        if not self._guard_action("launch:critical", cooldown_sec=2.0, message="Launch ignored because critical view was just triggered"):
            return
        if not self._ensure_inventory_ready("launch critical cameras"):
            return
        self.save_settings()
        ids, result = self.vm.launch_tier("critical", high_fps=False)
        if not ids:
            QMessageBox.warning(self, WINDOW_TITLE, "No enabled critical cameras found.")
            return
        if result is not None:
            message, status = result
            self.append_output(message)
            self._set_status(status)

    def launch_critical_cameras_high_fps(self) -> None:
        if not self._guard_action("launch:critical:highfps", cooldown_sec=2.0, message="Launch ignored because critical high-FPS view was just triggered"):
            return
        if not self._ensure_inventory_ready("launch critical cameras in high-FPS mode"):
            return
        self.save_settings()
        ids, result = self.vm.launch_tier("critical", high_fps=True)
        if not ids:
            QMessageBox.warning(self, WINDOW_TITLE, "No enabled critical cameras found.")
            return
        if result is not None:
            message, status = result
            self.append_output(message)
            self._set_status(status)

    def launch_filtered_group_cameras(self) -> None:
        group_name = self.group_filter_combo.currentText().strip()
        if not group_name or group_name == "All Groups":
            QMessageBox.information(self, WINDOW_TITLE, "Choose a specific group in the group filter first.")
            return
        if not self._guard_action(f"launch:group:{group_name}", cooldown_sec=2.0, message=f"Launch ignored because group {group_name} was just triggered"):
            return
        if not self._ensure_inventory_ready(f"launch group {group_name}"):
            return
        self.save_settings()
        ids, result = self.vm.launch_group(group_name, high_fps=False)
        if not ids:
            QMessageBox.warning(self, WINDOW_TITLE, f"No enabled cameras found in group '{group_name}'.")
            return
        if result is not None:
            message, status = result
            self.append_output(message)
            self._set_status(status)

    def launch_filtered_group_cameras_high_fps(self) -> None:
        group_name = self.group_filter_combo.currentText().strip()
        if not group_name or group_name == "All Groups":
            QMessageBox.information(self, WINDOW_TITLE, "Choose a specific group in the group filter first.")
            return
        if not self._guard_action(f"launch:group:{group_name}:highfps", cooldown_sec=2.0, message=f"Launch ignored because high-FPS group {group_name} was just triggered"):
            return
        if not self._ensure_inventory_ready(f"launch group {group_name} in high-FPS mode"):
            return
        self.save_settings()
        ids, result = self.vm.launch_group(group_name, high_fps=True)
        if not ids:
            QMessageBox.warning(self, WINDOW_TITLE, f"No enabled cameras found in group '{group_name}'.")
            return
        if result is not None:
            message, status = result
            self.append_output(message)
            self._set_status(status)

    def run_health_check(self) -> None:
        if self.health_process is not None:
            QMessageBox.information(self, WINDOW_TITLE, "Health check is already running.")
            return
        if not self._ensure_inventory_ready("run health check"):
            return
        self.save_settings()
        self.append_output("[INFO] Running system health check...")
        self._set_status("Running health check...")

        program, arguments, process_env_values = self.vm.health_check_command()
        self.health_process = QProcess(self)
        self.health_process.setProgram(program)
        self.health_process.setArguments(arguments)
        self.health_process.setWorkingDirectory(str(ROOT_DIR))
        process_env = self.health_process.processEnvironment()
        for key, value in process_env_values.items():
            process_env.insert(key, value)
        self.health_process.setProcessEnvironment(process_env)
        self.health_process.readyReadStandardOutput.connect(self._read_health_stdout)
        self.health_process.readyReadStandardError.connect(self._read_health_stderr)
        self.health_process.finished.connect(self._health_finished)
        self.health_process.start()

    def run_source_capability_check(self) -> None:
        if self.source_process is not None:
            QMessageBox.information(self, WINDOW_TITLE, "Source capability check is already running.")
            return
        if not self._ensure_inventory_ready("run source capability check"):
            return
        self.save_settings()
        camera_ids = self.selected_camera_ids()
        label = ", ".join(camera_ids) if camera_ids else "all enabled cameras"
        self.append_output(f"[INFO] Running source capability check for {label}...")
        self._set_status("Running source capability check...")

        program, arguments, process_env_values = self.vm.source_capability_command(camera_ids or None)
        self.source_process = QProcess(self)
        self.source_process.setProgram(program)
        self.source_process.setArguments(arguments)
        self.source_process.setWorkingDirectory(str(ROOT_DIR))
        process_env = self.source_process.processEnvironment()
        for key, value in process_env_values.items():
            process_env.insert(key, value)
        self.source_process.setProcessEnvironment(process_env)
        self.source_process.readyReadStandardOutput.connect(self._read_source_stdout)
        self.source_process.readyReadStandardError.connect(self._read_source_stderr)
        self.source_process.finished.connect(self._source_finished)
        self.source_process.start()

    def _read_source_stdout(self) -> None:
        if self.source_process is None:
            return
        text = bytes(self.source_process.readAllStandardOutput()).decode(errors="ignore")
        self.append_output(text)

    def _read_source_stderr(self) -> None:
        if self.source_process is None:
            return
        text = bytes(self.source_process.readAllStandardError()).decode(errors="ignore")
        self.append_output(text)

    def _source_finished(self, exit_code: int) -> None:
        if exit_code == 0:
            self._set_status("Source capability check passed")
        else:
            self._set_status(f"Source capability check failed (exit {exit_code})")
        self._refresh_source_snapshot()
        self._refresh_camera_table()
        self.append_output(f"[INFO] Source capability check finished with exit code {exit_code}")
        self.source_process = None

    def save_current_selection_as_preset(self) -> None:
        camera_ids = self.selected_camera_ids()
        if not camera_ids:
            QMessageBox.warning(self, WINDOW_TITLE, "Select one or more cameras before saving a preset.")
            return
        dialog = PresetDialog(parent=self)
        if dialog.exec() != dialog.Accepted:
            return
        payload = dialog.values()
        existing = next((item for item in self.vm.state.selection_presets if item.name == payload["name"]), None)
        if existing is not None:
            overwrite = QMessageBox.question(
                self,
                WINDOW_TITLE,
                f"Preset '{payload['name']}' already exists. Overwrite it?",
            )
            if overwrite != QMessageBox.Yes:
                self.append_output(f"[INFO] Preset overwrite cancelled for '{payload['name']}'")
                return
        try:
            self.vm.save_preset(
                payload["name"],
                camera_ids,
                description=payload["description"],
                launch_mode=payload["launch_mode"],
            )
        except ValueError as exc:
            QMessageBox.warning(self, WINDOW_TITLE, str(exc))
            return
        self._refresh_presets()
        self.append_output(f"[INFO] Saved preset '{payload['name']}' mode={payload['launch_mode']} description={payload['description'] or '-'}")
        self._set_status(f"Saved preset {payload['name']}")

    def apply_selected_preset(self) -> None:
        preset = self._resolve_selected_preset()
        if preset is None:
            return
        self._select_camera_ids_in_table(preset.camera_ids)
        self.append_output(
            f"[INFO] Applied preset '{preset.name}'"
            + (f" mode={preset.launch_mode}" if preset.launch_mode else "")
            + (f" description={preset.description}" if preset.description else "")
        )

    def run_selected_preset(self) -> None:
        preset = self._resolve_selected_preset()
        if preset is None:
            return
        self.apply_selected_preset()
        if not self._guard_action(f"preset:{preset.name}:{preset.launch_mode}", cooldown_sec=2.0, message=f"Launch ignored because preset {preset.name} was just triggered"):
            return
        if not self._ensure_inventory_ready(f"run preset {preset.name}"):
            return
        self.save_settings()
        if preset.launch_mode == "high-fps":
            message, status = self.vm.launch_selected_high_fps(list(preset.camera_ids))
        else:
            message, status = self.vm.launch_selected(list(preset.camera_ids))
        self.append_output(message)
        self._set_status(status)

    def run_selected_preset_high_fps(self) -> None:
        preset = self._resolve_selected_preset()
        if preset is None:
            return
        self.apply_selected_preset()
        if not self._guard_action(f"preset:{preset.name}:highfps", cooldown_sec=2.0, message=f"Launch ignored because preset {preset.name} high-FPS was just triggered"):
            return
        if not self._ensure_inventory_ready(f"run preset {preset.name} in high-FPS mode"):
            return
        self.save_settings()
        message, status = self.vm.launch_selected_high_fps(list(preset.camera_ids))
        self.append_output(message)
        self._set_status(status)

    def delete_selected_preset(self) -> None:
        preset_name = str(self.preset_combo.currentData() or "").strip()
        if not preset_name:
            QMessageBox.information(self, WINDOW_TITLE, "Choose a preset first.")
            return
        self.vm.delete_preset(preset_name)
        self._refresh_presets()
        self.append_output(f"[INFO] Deleted preset '{preset_name}'")
        self._set_status(f"Deleted preset {preset_name}")

    def _read_health_stdout(self) -> None:
        if self.health_process is None:
            return
        text = bytes(self.health_process.readAllStandardOutput()).decode(errors="ignore")
        self.append_output(text)

    def _read_health_stderr(self) -> None:
        if self.health_process is None:
            return
        text = bytes(self.health_process.readAllStandardError()).decode(errors="ignore")
        self.append_output(text)

    def _health_finished(self, exit_code: int) -> None:
        if exit_code == 0:
            self._set_status("Health check passed")
        else:
            self._set_status(f"Health check failed (exit {exit_code})")
        self._refresh_health_snapshot()
        self._refresh_camera_table()
        self.append_output(f"[INFO] Health check finished with exit code {exit_code}")
        self.health_process = None
        if self.open_log_checkbox.isChecked():
            self.open_logs_folder()

    def open_logs_folder(self) -> None:
        if not self._guard_action("open:logs", cooldown_sec=1.0, message="Open Logs ignored because the folder was just opened"):
            return
        self.vm.open_logs_folder()

    def open_readme(self) -> None:
        if not self._guard_action("open:readme", cooldown_sec=1.0, message="Open README ignored because it was just opened"):
            return
        self.vm.open_readme()
