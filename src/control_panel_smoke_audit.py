from __future__ import annotations

import os
import sys
import time
import traceback
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDialog,
    QDoubleSpinBox,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QToolBar,
    QToolButton,
)

import control_panel_app.actions_mixin as actions_mod
import control_panel_app.window as window_mod
from control_panel_app.components import CameraWizardDialog, FirstRunGuideDialog, PresetDialog
from control_panel_app.styles import build_app_chrome_stylesheet, build_app_palette
from control_panel_app.window import ControlPanelWindow
from mtimou_v2.app_state import CameraEditorEntry, OperatorSettingsState, SelectionPreset


ROOT_DIR = Path(__file__).resolve().parents[1]
PYTHON_EXE = ROOT_DIR / ".venv" / "Scripts" / "python.exe"


class FakeFirstRunGuideDialog(QDialog):
    Accepted = QDialog.Accepted

    def __init__(self, *, issues: list[str], tips: list[str], parent=None) -> None:
        super().__init__(parent)
        self.issues = issues
        self.tips = tips
        self.target_tab: str | None = None

    def exec(self) -> int:
        return QDialog.Accepted


class FakePresetDialog(QDialog):
    Accepted = QDialog.Accepted

    def __init__(self, *, suggested_name: str = "", parent=None) -> None:
        super().__init__(parent)
        self._suggested_name = suggested_name

    def exec(self) -> int:
        return QDialog.Accepted

    def values(self) -> dict[str, str]:
        return {
            "name": self._suggested_name or "audit-preset",
            "description": "smoke audit preset",
            "launch_mode": "normal",
        }


class FakeCameraWizardDialog(QDialog):
    Accepted = QDialog.Accepted

    def __init__(self, *, next_camera_id: str, ddns_host: str, public_host: str, public_port: int, parent=None) -> None:
        super().__init__(parent)
        self._values = {
            "camera_id": next_camera_id,
            "name": f"Audit {next_camera_id}",
            "group_name": "audit",
            "tier": "standard",
            "lan_host": "192.168.1.250",
            "lan_port": 554,
            "ddns_host": ddns_host,
            "ddns_port": public_port,
            "public_host": public_host,
            "public_port": public_port,
            "remote_wall_subtype": "0",
            "remote_focus_subtype": "0",
            "password_env_name": f"IMOU_CAM_{next_camera_id.upper()}_PASSWORD",
            "enabled": True,
        }

    def exec(self) -> int:
        return QDialog.Accepted

    def values(self) -> dict[str, object]:
        return dict(self._values)


class AuditFailure(RuntimeError):
    pass


class ControlPanelSmokeAudit:
    def __init__(self) -> None:
        self.messages: list[tuple[str, str]] = []
        self.failures: list[str] = []
        self.passes: list[str] = []
        self.originals: dict[str, object] = {}

    def install_test_doubles(self) -> None:
        self.originals["first_run_dialog"] = window_mod.FirstRunGuideDialog
        self.originals["preset_dialog"] = actions_mod.PresetDialog
        self.originals["camera_wizard_dialog"] = actions_mod.CameraWizardDialog
        window_mod.FirstRunGuideDialog = FakeFirstRunGuideDialog
        actions_mod.PresetDialog = FakePresetDialog
        actions_mod.CameraWizardDialog = FakeCameraWizardDialog

        self.originals["warning"] = QMessageBox.warning
        self.originals["information"] = QMessageBox.information
        self.originals["question"] = QMessageBox.question

        def warning(_parent, _title, text, *args, **kwargs):
            self.messages.append(("warning", str(text)))
            return QMessageBox.Ok

        def information(_parent, _title, text, *args, **kwargs):
            self.messages.append(("info", str(text)))
            return QMessageBox.Ok

        def question(_parent, _title, text, *args, **kwargs):
            self.messages.append(("question", str(text)))
            return QMessageBox.Yes

        QMessageBox.warning = staticmethod(warning)
        QMessageBox.information = staticmethod(information)
        QMessageBox.question = staticmethod(question)

    def restore_test_doubles(self) -> None:
        if not self.originals:
            return
        window_mod.FirstRunGuideDialog = self.originals["first_run_dialog"]
        actions_mod.PresetDialog = self.originals["preset_dialog"]
        actions_mod.CameraWizardDialog = self.originals["camera_wizard_dialog"]
        QMessageBox.warning = self.originals["warning"]
        QMessageBox.information = self.originals["information"]
        QMessageBox.question = self.originals["question"]

    def fake_viewmodel_side_effects(self, window: ControlPanelWindow) -> None:
        original_state = window.vm.state
        window._prompt_unsaved_inventory_decision = lambda _action_label: "save"

        def fake_save(new_state: OperatorSettingsState):
            window.vm.state = OperatorSettingsState(
                target_mode=new_state.target_mode,
                ddns_host=new_state.ddns_host,
                username=new_state.username,
                single_overlay_title_scale=new_state.single_overlay_title_scale,
                single_overlay_meta_scale=new_state.single_overlay_meta_scale,
                single_overlay_small_scale=new_state.single_overlay_small_scale,
                multi_overlay_title_scale=new_state.multi_overlay_title_scale,
                multi_overlay_meta_scale=new_state.multi_overlay_meta_scale,
                multi_overlay_small_scale=new_state.multi_overlay_small_scale,
                password_entries=list(new_state.password_entries),
                cameras=list(original_state.cameras),
                camera_editor_entries=list(window.vm.state.camera_editor_entries),
                selection_presets=list(window.vm.state.selection_presets),
                output_lines=list(window.vm.state.output_lines),
            )
            return window.vm.state

        def fake_save_camera_inventory(entries: list[CameraEditorEntry]):
            window.vm.state.camera_editor_entries = list(entries)
            return window.vm.state

        def fake_save_preset(name: str, camera_ids: list[str], *, description: str = "", launch_mode: str = "normal"):
            presets = [item for item in window.vm.state.selection_presets if item.name != name]
            presets.append(
                SelectionPreset(
                    name=name,
                    camera_ids=list(camera_ids),
                    description=description,
                    launch_mode=launch_mode,
                )
            )
            window.vm.state.selection_presets = presets
            return window.vm.state

        def fake_delete_preset(name: str):
            window.vm.state.selection_presets = [item for item in window.vm.state.selection_presets if item.name != name]
            return window.vm.state

        fake_process_env = dict(os.environ)
        fake_process_env["PYTHONUTF8"] = "1"
        fake_process_env["PYTHONIOENCODING"] = "utf-8"

        def fake_health_command():
            return (
                str(PYTHON_EXE),
                ["-c", "print('audit health ok')"],
                fake_process_env,
            )

        def fake_source_command(camera_ids: list[str] | None = None):
            label = ",".join(camera_ids or ["all"])
            return (
                str(PYTHON_EXE),
                ["-c", f"print('audit source ok {label}')"],
                fake_process_env,
            )

        launch_calls: list[tuple[str, list[str]]] = []
        open_calls: list[str] = []

        window.vm.save = fake_save
        window.vm.save_camera_inventory = fake_save_camera_inventory
        window.vm.save_preset = fake_save_preset
        window.vm.delete_preset = fake_delete_preset
        window.vm.health_check_command = fake_health_command
        window.vm.source_capability_command = fake_source_command
        window.vm.services.launch_batch = lambda batch, args: launch_calls.append((batch, list(args)))
        window.vm.services.open_logs_folder = lambda: open_calls.append("logs")
        window.vm.services.open_readme = lambda: open_calls.append("readme")
        window._audit_launch_calls = launch_calls
        window._audit_open_calls = open_calls

    def wait_until(self, app: QApplication, predicate, timeout_sec: float = 4.0) -> None:
        deadline = time.monotonic() + timeout_sec
        while time.monotonic() < deadline:
            app.processEvents()
            if predicate():
                return
            time.sleep(0.01)
        raise AuditFailure("Timed out waiting for async UI action")

    def find_button(self, window: ControlPanelWindow, text: str) -> QPushButton:
        for button in window.findChildren(QPushButton):
            if button.text().strip() == text:
                return button
        raise AuditFailure(f"Button not found: {text}")

    def find_toolbutton(self, window: ControlPanelWindow, text: str) -> QToolButton:
        for button in window.findChildren(QToolButton):
            if button.text().strip() == text:
                return button
        raise AuditFailure(f"Tool button not found: {text}")

    def require(self, condition: bool, message: str) -> None:
        if not condition:
            raise AuditFailure(message)

    def pass_step(self, name: str) -> None:
        self.passes.append(name)
        print(f"[PASS] {name}")

    def run(self) -> int:
        self.install_test_doubles()
        original_excepthook = sys.excepthook

        def audit_excepthook(exc_type, exc_value, exc_traceback):
            self.failures.append(f"{exc_type.__name__}: {exc_value}")
            traceback.print_exception(exc_type, exc_value, exc_traceback)

        sys.excepthook = audit_excepthook
        app = QApplication([])
        app.setApplicationName("MTImou Control Panel Smoke Audit")
        app.setStyle("Fusion")
        app.setPalette(build_app_palette())
        app.setStyleSheet(build_app_chrome_stylesheet())
        window = ControlPanelWindow()
        self.fake_viewmodel_side_effects(window)
        window.show()
        app.processEvents()

        try:
            self.audit_dialogs(app)
            self.audit_controls(app, window)
            self.audit_buttons_and_actions(app, window)
        except Exception as exc:
            self.failures.append(f"{type(exc).__name__}: {exc}")
            traceback.print_exc()
        finally:
            window.close()
            app.processEvents()
            self.restore_test_doubles()
            sys.excepthook = original_excepthook
            app.quit()

        print("")
        print(f"[SUMMARY] passes={len(self.passes)} failures={len(self.failures)} messages={len(self.messages)}")
        if self.failures:
            for item in self.failures:
                print(f"[FAIL] {item}")
            return 1
        return 0

    def audit_dialogs(self, app: QApplication) -> None:
        wizard = CameraWizardDialog(
            next_camera_id="cam99",
            ddns_host="example.ddns.net",
            public_host="203.0.113.10",
            public_port=45599,
        )
        wizard.id_edit.setText("cam99")
        wizard.name_edit.setText("Audit Camera")
        wizard.group_edit.setText("audit")
        wizard.lan_host_edit.setText("192.168.1.99")
        wizard.wall_subtype_combo.setCurrentText("1")
        wizard.focus_subtype_combo.setCurrentText("0")
        wizard.show()
        app.processEvents()
        wizard_values = wizard.values()
        self.require(wizard_values["camera_id"] == "cam99", "Camera wizard did not preserve camera id")
        self.require(wizard_values["remote_wall_subtype"] == "1", "Camera wizard wall subtype did not update")
        wizard.close()

        preset = PresetDialog(suggested_name="audit")
        preset.name_edit.setText("audit-preset")
        preset.description_edit.setText("audit description")
        preset.launch_mode_combo.setCurrentText("high-fps")
        preset.show()
        app.processEvents()
        preset_values = preset.values()
        self.require(preset_values["launch_mode"] == "high-fps", "Preset dialog launch mode did not update")
        preset.close()

        guide = FirstRunGuideDialog(issues=["issue"], tips=["tip"])
        guide.show()
        app.processEvents()
        guide._accept_with_target("settings")
        self.require(guide.target_tab == "settings", "First-run guide target tab did not update")
        guide.close()
        self.pass_step("Audited dialogs")

    def audit_controls(self, app: QApplication, window: ControlPanelWindow) -> None:
        self.require(window.camera_table.rowCount() > 0, "Camera table did not load any rows")
        self.require(window.inventory_table.rowCount() > 0, "Inventory table did not load any rows")

        for index in range(window.tabs.count()):
            window.tabs.setCurrentIndex(index)
            app.processEvents()
        self.pass_step("Switched all tabs")

        for section in window.collapsible_sections.values():
            collapsed = section.is_collapsed()
            section.set_collapsed(not collapsed)
            app.processEvents()
            section.set_collapsed(collapsed)
            app.processEvents()
        self.pass_step("Toggled collapsible sections")

        line_edits = [
            window.ddns_edit,
            window.user_edit,
            window.camera_search_edit,
            window.bulk_group_edit,
            *[field.edit for field in window.password_fields],
        ]
        for edit in line_edits:
            original = edit.text()
            edit.setText(original + " ")
            app.processEvents()
            self.require(edit.text().endswith(" "), "Line edit did not accept input")
            edit.setText(original)
            app.processEvents()
        self.pass_step("Edited all line edits")

        combo_boxes = [
            window.mode_combo,
            window.group_filter_combo,
            window.tier_filter_combo,
            window.preset_combo,
            window.bulk_tier_combo,
            window.bulk_wall_combo,
            window.bulk_focus_combo,
        ]
        for combo in combo_boxes:
            if combo.count() <= 1:
                continue
            original_index = combo.currentIndex()
            new_index = 1 if original_index == 0 else 0
            combo.setCurrentIndex(new_index)
            app.processEvents()
            self.require(combo.currentIndex() == new_index, "Combo box did not change selection")
            combo.setCurrentIndex(original_index)
            app.processEvents()
        self.pass_step("Changed combo boxes")

        for checkbox in [window.compact_ui_checkbox, window.show_passwords_checkbox, window.open_log_checkbox]:
            original = checkbox.isChecked()
            checkbox.setChecked(not original)
            app.processEvents()
            self.require(checkbox.isChecked() != original, "Checkbox did not toggle")
            checkbox.setChecked(original)
            app.processEvents()
        self.pass_step("Toggled checkboxes")

        for spinbox in [
            window.single_title_scale_spin,
            window.single_meta_scale_spin,
            window.single_small_scale_spin,
            window.multi_title_scale_spin,
            window.multi_meta_scale_spin,
            window.multi_small_scale_spin,
        ]:
            original = spinbox.value()
            spinbox.setValue(min(spinbox.maximum(), original + 0.01))
            app.processEvents()
            self.require(spinbox.value() != original or spinbox.maximum() == original, "Spin box did not accept value change")
            spinbox.setValue(original)
            app.processEvents()
        self.pass_step("Adjusted overlay spin boxes")

        window.camera_table.selectRow(0)
        window.inventory_table.selectRow(0)
        app.processEvents()
        self.require(bool(window.selected_camera_ids()), "Camera selection did not register")
        self.pass_step("Selected table rows")

        self.require(window.output.isReadOnly(), "Output panel is unexpectedly editable")
        self.pass_step("Verified output panel read-only state")

    def audit_buttons_and_actions(self, app: QApplication, window: ControlPanelWindow) -> None:
        def select_first_camera() -> None:
            window._action_cooldowns.clear()
            window.tabs.setCurrentIndex(0)
            window.camera_table.clearSelection()
            window.camera_table.selectRow(0)
            app.processEvents()

        def select_first_inventory_row() -> None:
            window.tabs.setCurrentIndex(2)
            window.inventory_table.clearSelection()
            window.inventory_table.selectRow(0)
            app.processEvents()

        def select_specific_group() -> None:
            if window.group_filter_combo.count() > 1:
                window.group_filter_combo.setCurrentIndex(1)
            app.processEvents()

        dashboard_buttons = [
            ("Show Setup Guide", lambda: None),
            ("Open Settings", lambda: None),
            ("Open Camera Management", lambda: None),
            ("Select All", lambda: None),
            ("Select Enabled", lambda: None),
            ("Select Group", select_specific_group),
            ("Clear Selection", select_first_camera),
            ("View Selected Cameras", select_first_camera),
            ("View Selected Cameras (High FPS)", select_first_camera),
            ("Show Selected Stream URLs", select_first_camera),
            ("Copy Selected Stream URLs", select_first_camera),
            ("Copy LAN RTSP", select_first_camera),
            ("Copy Public RTSP (Main)", select_first_camera),
            ("Copy DDNS RTSP (Main)", select_first_camera),
            ("Copy Public RTSP (Substream)", select_first_camera),
            ("Copy DDNS RTSP (Substream)", select_first_camera),
            ("View All Enabled Cameras", lambda: None),
            ("View Critical Cameras", lambda: None),
            ("View Critical Cameras (High FPS)", lambda: None),
            ("View Filtered Group", select_specific_group),
            ("View Filtered Group (High FPS)", select_specific_group),
            ("Run Health Check", lambda: None),
            ("Run Source Capability Check", select_first_camera),
            ("Open Logs Folder", lambda: None),
            ("Open Project README", lambda: None),
            ("Save Current Selection", select_first_camera),
            ("Apply Preset", lambda: window.preset_combo.setCurrentText("audit-preset")),
            ("Run Preset", lambda: window.preset_combo.setCurrentText("audit-preset")),
            ("Run Preset (High FPS)", lambda: window.preset_combo.setCurrentText("audit-preset")),
            ("Delete Preset", lambda: window.preset_combo.setCurrentText("audit-preset")),
        ]

        for text, setup in dashboard_buttons:
            setup()
            app.processEvents()
            self.find_button(window, text).click()
            if text == "Run Health Check":
                self.wait_until(app, lambda: window.health_process is None)
            elif text == "Run Source Capability Check":
                self.wait_until(app, lambda: window.source_process is None)
            app.processEvents()
        self.pass_step("Clicked dashboard buttons")

        inventory_buttons = [
            ("Add Camera Wizard", lambda: None),
            ("Add Draft Row", lambda: None),
            ("Remove Selected", select_first_inventory_row),
            ("Reload Inventory", lambda: None),
            ("Save Camera Inventory", select_first_inventory_row),
            ("Enable Selected", select_first_inventory_row),
            ("Disable Selected", select_first_inventory_row),
            ("Apply Bulk Edit", select_first_inventory_row),
        ]
        window.bulk_group_edit.setText("audit-group")
        if window.bulk_tier_combo.count() > 1:
            window.bulk_tier_combo.setCurrentIndex(1)
        if window.bulk_wall_combo.count() > 1:
            window.bulk_wall_combo.setCurrentIndex(1)
        if window.bulk_focus_combo.count() > 1:
            window.bulk_focus_combo.setCurrentIndex(1)
        for text, setup in inventory_buttons:
            setup()
            app.processEvents()
            self.find_button(window, text).click()
            app.processEvents()
        self.pass_step("Clicked inventory buttons")

        self.find_button(window, "Restore Display Defaults").click()
        app.processEvents()
        self.pass_step("Clicked settings button")

        toolbar = window.findChild(QToolBar)
        self.require(toolbar is not None, "Toolbar not found")
        for action in toolbar.actions():
            action.trigger()
            if action.text() == "Source Capability":
                self.wait_until(app, lambda: window.source_process is None)
            app.processEvents()
        self.pass_step("Triggered toolbar actions")

        self.require(bool(getattr(window, "_audit_launch_calls", [])), "Launch actions did not record any batch calls")
        self.require("logs" in getattr(window, "_audit_open_calls", []), "Open Logs action did not run")
        self.require("readme" in getattr(window, "_audit_open_calls", []), "Open README action did not run")


def main() -> int:
    audit = ControlPanelSmokeAudit()
    return audit.run()


if __name__ == "__main__":
    raise SystemExit(main())
