from __future__ import annotations

import re

from PySide6.QtCore import QItemSelectionModel, Qt
from PySide6.QtGui import QTextCursor
from PySide6.QtWidgets import QHBoxLayout, QLabel, QLineEdit, QTableWidgetItem, QWidget

from control_panel_app.components import CameraRow, PasswordField
from control_panel_app.constants import ROOT_DIR, TIER_OPTIONS


class ControlPanelStateMixin:
    def append_output(self, text: str) -> None:
        if not text:
            return
        self.output.moveCursor(QTextCursor.End)
        self.output.insertPlainText(text.rstrip() + "\n")
        self.output.moveCursor(QTextCursor.End)

    def _set_status(self, message: str) -> None:
        if self.statusBar() is not None:
            self.statusBar().showMessage(message)

    def _load_camera_rows(self) -> list[CameraRow]:
        rows: list[CameraRow] = []
        for camera in self.vm.state.cameras:
            parts = [segment.strip() for segment in camera.label.split(" | ")]
            target_segments: dict[str, str] = {}
            for segment in parts[2:]:
                if "=" in segment:
                    key, value = segment.split("=", 1)
                    target_segments[key.strip()] = value.strip()
            rows.append(
                CameraRow(
                    camera_id=camera.camera_id,
                    name=camera.name,
                    group_name=camera.group_name,
                    tier=camera.tier,
                    lan=target_segments.get("lan", "-"),
                    ddns=target_segments.get("ddns", "-"),
                    public=target_segments.get("public", "-"),
                    enabled=camera.enabled,
                )
            )
        return rows

    def _rebuild_password_fields(self) -> None:
        while self.password_rows_layout.count():
            item = self.password_rows_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        self.password_fields.clear()

        for entry in self.vm.state.password_entries:
            row = QWidget()
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(0, 0, 0, 0)
            row_layout.setSpacing(8)

            label = QLabel(f"{entry.camera_name} ({entry.camera_id})")
            label.setMinimumWidth(200)
            edit = QLineEdit()
            edit.setPlaceholderText(entry.env_name)
            edit.setText(entry.value)
            edit.setEchoMode(QLineEdit.Normal if self.show_passwords_checkbox.isChecked() else QLineEdit.Password)
            hint = QLabel(entry.env_name)
            hint.setStyleSheet("color: #6b7280; font-size: 11px;")

            row_layout.addWidget(label)
            row_layout.addWidget(edit, 1)
            row_layout.addWidget(hint)
            self.password_rows_layout.addWidget(row)
            self.password_fields.append(PasswordField(camera_id=entry.camera_id, env_name=entry.env_name, edit=edit))

        self.password_rows_layout.addStretch(1)

    def _refresh_camera_table(self) -> None:
        rows = self._load_camera_rows()
        current_ids = set(self.selected_camera_ids())
        self.camera_table.setRowCount(len(rows))

        for row_index, row in enumerate(rows):
            status_value, status_helper = self.camera_health_status.get(
                row.camera_id,
                ("Disabled" if not row.enabled else "Unknown", "Run health check to verify"),
            )
            values = [
                f"{row.camera_id} | {row.name} | {row.group_name} | {row.tier}",
                row.lan,
                row.ddns,
                row.public,
                status_value,
            ]
            for col_index, value in enumerate(values):
                item = QTableWidgetItem(value)
                item.setData(Qt.UserRole, row.camera_id)
                _source_fps, source_helper = self.source_capability_status.get(
                    row.camera_id,
                    (0.0, "Run source capability check to measure stream ceiling"),
                )
                tooltip_parts = []
                if col_index == 4:
                    item.setData(Qt.ToolTipRole, status_helper)
                    tooltip_parts.append(status_helper)
                if source_helper:
                    tooltip_parts.append(source_helper)
                if tooltip_parts:
                    item.setData(Qt.ToolTipRole, "\n".join(tooltip_parts))
                if col_index == 4:
                    item.setTextAlignment(Qt.AlignCenter)
                    if value == "Healthy":
                        item.setForeground(Qt.darkGreen)
                    elif value == "Degraded":
                        item.setForeground(Qt.darkYellow)
                    elif value == "Disabled":
                        item.setForeground(Qt.darkGray)
                    else:
                        item.setForeground(Qt.darkRed)
                if col_index == 0 and row.enabled:
                    item.setForeground(Qt.darkGreen)
                self.camera_table.setItem(row_index, col_index, item)
            if row.camera_id in current_ids:
                self.camera_table.selectRow(row_index)

        self.camera_table.resizeRowsToContents()
        self._apply_camera_table_filters()
        self._refresh_selection_summary()
        self._refresh_first_run_guidance()

    def _refresh_inventory_table(self) -> None:
        entries = self.vm.state.camera_editor_entries
        self._suspend_inventory_dirty_tracking = True
        try:
            self.inventory_table.setRowCount(len(entries))
            for row_index, entry in enumerate(entries):
                enabled_item = QTableWidgetItem("Yes" if entry.enabled else "No")
                enabled_item.setFlags(enabled_item.flags() | Qt.ItemIsUserCheckable | Qt.ItemIsEditable)
                enabled_item.setCheckState(Qt.Checked if entry.enabled else Qt.Unchecked)
                enabled_item.setTextAlignment(Qt.AlignCenter)
                self.inventory_table.setItem(row_index, 0, enabled_item)

                values = [
                    entry.camera_id,
                    entry.name,
                    entry.group_name,
                    entry.tier,
                    entry.lan_host,
                    str(entry.lan_port),
                    entry.ddns_host,
                    str(entry.ddns_port),
                    entry.public_host,
                    str(entry.public_port),
                    entry.remote_wall_subtype,
                    entry.remote_focus_subtype,
                    entry.password_env_name,
                ]
                for offset, value in enumerate(values, start=1):
                    item = QTableWidgetItem(value)
                    self.inventory_table.setItem(row_index, offset, item)
            self.inventory_table.resizeRowsToContents()
        finally:
            self._suspend_inventory_dirty_tracking = False
        self._refresh_first_run_guidance()

    def _inventory_row_to_entry(self, row: int):
        from mtimou_v2.app_state import CameraEditorEntry

        enabled_item = self.inventory_table.item(row, 0)
        camera_id_item = self.inventory_table.item(row, 1)
        name_item = self.inventory_table.item(row, 2)
        group_item = self.inventory_table.item(row, 3)
        tier_item = self.inventory_table.item(row, 4)
        lan_host_item = self.inventory_table.item(row, 5)
        lan_port_item = self.inventory_table.item(row, 6)
        ddns_host_item = self.inventory_table.item(row, 7)
        ddns_port_item = self.inventory_table.item(row, 8)
        public_host_item = self.inventory_table.item(row, 9)
        public_port_item = self.inventory_table.item(row, 10)
        wall_subtype_item = self.inventory_table.item(row, 11)
        focus_subtype_item = self.inventory_table.item(row, 12)
        password_env_item = self.inventory_table.item(row, 13)

        camera_id = (camera_id_item.text() if camera_id_item else "").strip()
        name = (name_item.text() if name_item else "").strip()
        group_name = (group_item.text() if group_item else "").strip()
        tier = (tier_item.text() if tier_item else "").strip()
        lan_host = (lan_host_item.text() if lan_host_item else "").strip()
        ddns_host = (ddns_host_item.text() if ddns_host_item else "").strip()
        public_host = (public_host_item.text() if public_host_item else "").strip()
        remote_wall_subtype = (wall_subtype_item.text() if wall_subtype_item else "").strip()
        remote_focus_subtype = (focus_subtype_item.text() if focus_subtype_item else "").strip()
        password_env = (password_env_item.text() if password_env_item else "").strip()

        if not camera_id:
            raise ValueError(f"Row {row + 1}: Camera ID is required.")
        if not lan_host:
            raise ValueError(f"Row {row + 1}: LAN host is required.")
        if not public_host:
            raise ValueError(f"Row {row + 1}: Public host is required.")
        if not password_env:
            raise ValueError(f"Row {row + 1}: Password env is required.")

        try:
            lan_port = int((lan_port_item.text() if lan_port_item else "554").strip())
            ddns_port = int((ddns_port_item.text() if ddns_port_item else "45554").strip())
            public_port = int((public_port_item.text() if public_port_item else "45554").strip())
        except ValueError as exc:
            raise ValueError(f"Row {row + 1}: ports must be integers.") from exc

        return CameraEditorEntry(
            camera_id=camera_id,
            name=name or camera_id,
            group_name=group_name or "default",
            tier=tier or "standard",
            lan_host=lan_host,
            lan_port=lan_port,
            ddns_host=ddns_host,
            ddns_port=ddns_port,
            public_host=public_host,
            public_port=public_port,
            channel="1",
            subtype="0",
            transport="tcp",
            remote_wall_subtype=remote_wall_subtype or "0",
            remote_focus_subtype=remote_focus_subtype or "0",
            enabled=enabled_item.checkState() == Qt.Checked if enabled_item else True,
            username_env="IMOU_CAMERA_USERNAME",
            password_env_name=password_env,
        )

    def _validate_inventory_entries(self, entries) -> None:
        seen_ids: set[str] = set()
        seen_password_envs: set[str] = set()
        seen_public: set[tuple[str, int]] = set()
        seen_ddns: set[tuple[str, int]] = set()

        for index, entry in enumerate(entries, start=1):
            if not re.fullmatch(r"[A-Za-z0-9_-]+", entry.camera_id):
                raise ValueError(f"Row {index}: Camera ID must use only letters, numbers, dash, or underscore.")
            if entry.camera_id in seen_ids:
                raise ValueError(f"Row {index}: Duplicate camera ID '{entry.camera_id}'.")
            seen_ids.add(entry.camera_id)
            if not re.fullmatch(r"[A-Za-z0-9_-]+", entry.group_name):
                raise ValueError(f"Row {index}: Group should use letters, numbers, dash, or underscore.")
            if entry.tier not in TIER_OPTIONS:
                raise ValueError(f"Row {index}: Tier must be one of {', '.join(TIER_OPTIONS)}.")

            if not re.fullmatch(r"IMOU_[A-Z0-9_]+", entry.password_env_name):
                raise ValueError(f"Row {index}: Password env should look like IMOU_CAM_CAM3_PASSWORD.")
            if entry.password_env_name in seen_password_envs:
                raise ValueError(f"Row {index}: Duplicate password env '{entry.password_env_name}'.")
            seen_password_envs.add(entry.password_env_name)

            if entry.remote_wall_subtype not in {"0", "1"}:
                raise ValueError(f"Row {index}: Wall subtype must be 0 or 1.")
            if entry.remote_focus_subtype not in {"0", "1"}:
                raise ValueError(f"Row {index}: Focus subtype must be 0 or 1.")

            for label, port in [("LAN", entry.lan_port), ("DDNS", entry.ddns_port), ("Public", entry.public_port)]:
                if port < 1 or port > 65535:
                    raise ValueError(f"Row {index}: {label} port must be between 1 and 65535.")

            public_key = (entry.public_host, entry.public_port)
            if public_key in seen_public:
                raise ValueError(f"Row {index}: Duplicate public host/port {entry.public_host}:{entry.public_port}.")
            seen_public.add(public_key)

            if entry.ddns_host:
                ddns_key = (entry.ddns_host, entry.ddns_port)
                if ddns_key in seen_ddns:
                    raise ValueError(f"Row {index}: Duplicate DDNS host/port {entry.ddns_host}:{entry.ddns_port}.")
                seen_ddns.add(ddns_key)

    def _refresh_health_snapshot(self) -> None:
        health_log = ROOT_DIR / "logs" / "system_health_check_latest.log"
        status_map: dict[str, list[tuple[str, bool]]] = {}
        if health_log.exists():
            for line in health_log.read_text(encoding="utf-8", errors="ignore").splitlines():
                if "camera=" not in line or "mode=" not in line:
                    continue
                camera_match = re.search(r"camera=([A-Za-z0-9_-]+)", line)
                mode_match = re.search(r"mode=([a-z]+)", line)
                frame_match = re.search(r"frame_ok=(True|False)", line)
                tcp_match = re.search(r"tcp_ok=(True|False)", line)
                if not camera_match or not mode_match or not frame_match or not tcp_match:
                    continue
                ok = frame_match.group(1) == "True" and tcp_match.group(1) == "True"
                status_map.setdefault(camera_match.group(1), []).append((mode_match.group(1), ok))

        self.camera_health_status = {}
        healthy = 0
        degraded = 0
        unknown = 0
        for camera in self.vm.state.cameras:
            if not camera.enabled:
                self.camera_health_status[camera.camera_id] = ("Disabled", "Camera is disabled in inventory")
                continue
            checks = status_map.get(camera.camera_id, [])
            if not checks:
                self.camera_health_status[camera.camera_id] = ("Unknown", "Run health check to populate live status")
                unknown += 1
                continue
            failed_modes = [mode for mode, ok in checks if not ok]
            if failed_modes:
                self.camera_health_status[camera.camera_id] = ("Degraded", f"Failed modes: {', '.join(sorted(set(failed_modes)))}")
                degraded += 1
            else:
                self.camera_health_status[camera.camera_id] = ("Healthy", "All checked modes passed in the latest health run")
                healthy += 1

        summary = f"{healthy} healthy"
        helper_parts = []
        if degraded:
            helper_parts.append(f"{degraded} degraded")
        if unknown:
            helper_parts.append(f"{unknown} unknown")
        helper = ", ".join(helper_parts) if helper_parts else "Latest health snapshot is green"
        self.metric_health.set_value(summary, helper)
        self._refresh_source_snapshot()

    def _refresh_source_snapshot(self) -> None:
        capability_log = ROOT_DIR / "logs" / "source_capability_latest.log"
        self.source_capability_status = {}
        measured_by_camera: dict[str, list[tuple[str, float]]] = {}
        if capability_log.exists():
            for line in capability_log.read_text(encoding="utf-8", errors="ignore").splitlines():
                if "[RESULT]" not in line:
                    continue
                camera_match = re.search(r"camera=([A-Za-z0-9_-]+)", line)
                subtype_match = re.search(r"subtype=([01])", line)
                fps_match = re.search(r"measured_fps=([0-9.]+)", line)
                if not camera_match or not subtype_match or not fps_match:
                    continue
                measured_by_camera.setdefault(camera_match.group(1), []).append((subtype_match.group(1), float(fps_match.group(1))))

        cameras_over_20 = 0
        measured_cameras = 0
        for camera in self.vm.state.cameras:
            results = measured_by_camera.get(camera.camera_id, [])
            if not results:
                continue
            measured_cameras += 1
            best_subtype, best_fps = max(results, key=lambda item: item[1])
            helper = f"Best measured source ~{best_fps:.1f} fps on subtype={best_subtype}"
            self.source_capability_status[camera.camera_id] = (best_fps, helper)
            if best_fps > 20.0:
                cameras_over_20 += 1

        if measured_cameras == 0:
            self.metric_source.set_value("Not measured", "Run source capability check to see the real stream ceiling")
        else:
            self.metric_source.set_value(
                f"{cameras_over_20}/{measured_cameras} > 20 fps",
                "Best measured source FPS from latest capability run",
            )

    def _next_camera_seed(self) -> tuple[str, int]:
        existing_ids = {entry.camera_id for entry in self.vm.state.camera_editor_entries}
        draft = self.vm.new_camera_entry(existing_ids)
        return draft.camera_id, draft.public_port

    def _refresh_group_filter(self) -> None:
        current = self.group_filter_combo.currentText()
        groups = sorted({camera.group_name for camera in self.vm.state.cameras if camera.group_name})
        self.group_filter_combo.blockSignals(True)
        self.group_filter_combo.clear()
        self.group_filter_combo.addItem("All Groups")
        for group in groups:
            self.group_filter_combo.addItem(group)
        if current and self.group_filter_combo.findText(current) >= 0:
            self.group_filter_combo.setCurrentText(current)
        self.group_filter_combo.blockSignals(False)

    def _refresh_presets(self) -> None:
        current = self.preset_combo.currentData() or self.preset_combo.currentText()
        self.preset_combo.blockSignals(True)
        self.preset_combo.clear()
        self.preset_combo.addItem("No preset selected", "")
        for preset in self.vm.state.selection_presets:
            label = preset.name
            if preset.launch_mode:
                label += f" [{preset.launch_mode}]"
            self.preset_combo.addItem(label, preset.name)
        if current:
            for idx in range(self.preset_combo.count()):
                if self.preset_combo.itemData(idx) == current:
                    self.preset_combo.setCurrentIndex(idx)
                    break
        self.preset_combo.blockSignals(False)

    def _apply_camera_table_filters(self) -> None:
        search_text = self.camera_search_edit.text().strip().lower()
        group_value = self.group_filter_combo.currentText().strip()
        tier_value = self.tier_filter_combo.currentText().strip()
        for row in range(self.camera_table.rowCount()):
            label_item = self.camera_table.item(row, 0)
            lan_item = self.camera_table.item(row, 1)
            ddns_item = self.camera_table.item(row, 2)
            public_item = self.camera_table.item(row, 3)
            status_item = self.camera_table.item(row, 4)
            haystack = " ".join(
                item.text().lower()
                for item in [label_item, lan_item, ddns_item, public_item, status_item]
                if item is not None and item.text()
            )
            parts = label_item.text().split(" | ") if label_item is not None else []
            group_name = parts[2] if len(parts) >= 3 else ""
            tier = parts[3] if len(parts) >= 4 else ""
            visible = True
            if search_text and search_text not in haystack:
                visible = False
            if visible and group_value and group_value != "All Groups" and group_name != group_value:
                visible = False
            if visible and tier_value and tier_value != "All Tiers" and tier != tier_value:
                visible = False
            self.camera_table.setRowHidden(row, not visible)

    def _refresh_selection_summary(self) -> None:
        rows = self.selected_camera_rows()
        if not rows:
            self.selection_summary.setText("No camera selected. Choose one camera for focused viewing or multiple cameras for the wall view.")
            return
        if len(rows) == 1:
            row = rows[0]
            self.selection_summary.setText(
                f"Selected 1 camera: {row['camera']} | LAN {row['lan']} | DDNS {row['ddns']} | Public {row['public']}"
            )
            return
        names = ", ".join(row["camera"].split(" | ", 1)[1] for row in rows)
        groups = sorted({row["group_name"] for row in rows if row["group_name"]})
        self.selection_summary.setText(
            f"Selected {len(rows)} cameras for multi-view"
            + (f" across groups {', '.join(groups)}" if groups else "")
            + f": {names}"
        )

    def selected_camera_rows(self) -> list[dict[str, str]]:
        selected: list[dict[str, str]] = []
        seen_rows: set[int] = set()
        for item in self.camera_table.selectedItems():
            row = item.row()
            if self.camera_table.isRowHidden(row):
                continue
            if row in seen_rows:
                continue
            seen_rows.add(row)
            label_text = self.camera_table.item(row, 0).text()
            parts = label_text.split(" | ")
            selected.append(
                {
                    "camera_id": str(self.camera_table.item(row, 0).data(Qt.UserRole)),
                    "camera": label_text,
                    "group_name": parts[2] if len(parts) >= 3 else "",
                    "lan": self.camera_table.item(row, 1).text(),
                    "ddns": self.camera_table.item(row, 2).text(),
                    "public": self.camera_table.item(row, 3).text(),
                }
            )
        selected.sort(key=lambda item: item["camera_id"])
        return selected

    def selected_camera_ids(self) -> list[str]:
        return [row["camera_id"] for row in self.selected_camera_rows()]

    def _select_all_cameras(self) -> None:
        self.camera_table.clearSelection()
        for row in range(self.camera_table.rowCount()):
            if not self.camera_table.isRowHidden(row):
                index = self.camera_table.model().index(row, 0)
                self.camera_table.selectionModel().select(index, QItemSelectionModel.Select | QItemSelectionModel.Rows)
        self._refresh_selection_summary()

    def _select_enabled_cameras(self) -> None:
        self.camera_table.clearSelection()
        for row in range(self.camera_table.rowCount()):
            if self.camera_table.isRowHidden(row):
                continue
            status_item = self.camera_table.item(row, 4)
            if status_item is not None and status_item.text() != "Disabled":
                index = self.camera_table.model().index(row, 0)
                self.camera_table.selectionModel().select(index, QItemSelectionModel.Select | QItemSelectionModel.Rows)
        self._refresh_selection_summary()

    def _select_group_cameras(self) -> None:
        selected_group = self.group_filter_combo.currentText().strip()
        if not selected_group or selected_group == "All Groups":
            self._select_all_cameras()
            return
        self.camera_table.clearSelection()
        for row in range(self.camera_table.rowCount()):
            if self.camera_table.isRowHidden(row):
                continue
            label_item = self.camera_table.item(row, 0)
            if label_item is None:
                continue
            parts = label_item.text().split(" | ")
            if len(parts) >= 3 and parts[2] == selected_group:
                index = self.camera_table.model().index(row, 0)
                self.camera_table.selectionModel().select(index, QItemSelectionModel.Select | QItemSelectionModel.Rows)
        self._refresh_selection_summary()

    def _select_tier_cameras(self, tier: str) -> None:
        self.camera_table.clearSelection()
        for row in range(self.camera_table.rowCount()):
            if self.camera_table.isRowHidden(row):
                continue
            label_item = self.camera_table.item(row, 0)
            if label_item is None:
                continue
            parts = label_item.text().split(" | ")
            if len(parts) >= 4 and parts[3] == tier:
                index = self.camera_table.model().index(row, 0)
                self.camera_table.selectionModel().select(index, QItemSelectionModel.Select | QItemSelectionModel.Rows)
        self._refresh_selection_summary()

    def toggle_password_visibility(self, visible: bool) -> None:
        mode = QLineEdit.Normal if visible else QLineEdit.Password
        for field in self.password_fields:
            field.edit.setEchoMode(mode)

    def _update_metric_cards(self) -> None:
        enabled_count = sum(1 for camera in self.vm.state.cameras if camera.enabled)
        total_count = len(self.vm.state.cameras)
        self.metric_enabled.set_value(str(enabled_count), f"{enabled_count} of {total_count} cameras enabled")
        self.metric_mode.set_value(self.mode_combo.currentText().strip() or "auto", "Preferred connection route for launches")
        ddns_value = self.ddns_edit.text().strip() or "Not set"
        self.metric_ddns.set_value(ddns_value, "Used when remote access needs a stable hostname")
        critical_count = sum(1 for camera in self.vm.state.cameras if camera.enabled and camera.tier == "critical")
        standard_count = sum(1 for camera in self.vm.state.cameras if camera.enabled and camera.tier == "standard")
        archive_count = sum(1 for camera in self.vm.state.cameras if camera.enabled and camera.tier == "archive")
        self.metric_critical.set_value(str(critical_count), "Enabled critical cameras")
        self.metric_standard.set_value(str(standard_count), "Enabled standard cameras")
        self.metric_archive.set_value(str(archive_count), "Enabled archive cameras")

    def _collect_first_run_issues(self) -> list[str]:
        issues: list[str] = []
        values = getattr(getattr(self.vm, "document", None), "values", {})
        if any("YOUR_" in value for value in values.values()):
            issues.append("Replace placeholder values in camera.env.bat, especially camera passwords and any optional OpenAPI keys.")

        missing_passwords = [
            f"{entry.camera_name} ({entry.camera_id})"
            for entry in self.vm.state.password_entries
            if not entry.value.strip() or "YOUR_" in entry.value
        ]
        if missing_passwords:
            issues.append("Fill in camera passwords for: " + ", ".join(missing_passwords))

        if not self.vm.state.camera_editor_entries:
            issues.append("Add at least one camera in Camera Management.")
        elif not any(entry.enabled for entry in self.vm.state.camera_editor_entries):
            issues.append("Enable at least one camera in Camera Management before launching viewers.")

        return issues

    def _collect_first_run_tips(self) -> list[str]:
        tips: list[str] = []
        if not self.ddns_edit.text().strip():
            tips.append("Add a shared DDNS host in Settings when you want stable remote access outside the home network.")
        if not self.vm.state.selection_presets:
            tips.append("Create a preset after your first successful launch so daily operation is one click.")
        return tips

    def _refresh_first_run_guidance(self) -> None:
        if not hasattr(self, "first_run_box"):
            return
        issues = self._collect_first_run_issues()
        tips = self._collect_first_run_tips()
        visible = bool(issues or tips)
        self.first_run_box.setVisible(visible)
        if not visible:
            return

        lines: list[str] = []
        if issues:
            lines.append("Finish these first:")
            lines.extend(f"- {issue}" for issue in issues)
        if tips:
            if lines:
                lines.append("")
            lines.append("Helpful next steps:")
            lines.extend(f"- {tip}" for tip in tips)
        self.first_run_label.setText("\n".join(lines))
