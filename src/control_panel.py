from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from pathlib import Path

THIS_DIR = Path(__file__).resolve().parent
if str(THIS_DIR) not in sys.path:
    sys.path.insert(0, str(THIS_DIR))

from PySide6.QtCore import QProcess, Qt
from PySide6.QtGui import QAction, QTextCursor
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QPlainTextEdit,
    QSizePolicy,
    QSplitter,
    QStatusBar,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

from mtimou_v2.app_state import OperatorSettingsState
from mtimou_v2.viewmodels.control_panel_vm import ControlPanelViewModel
from venv_guard import enforce_venv_python


ROOT_DIR = Path(__file__).resolve().parents[1]
ENV_PATH = ROOT_DIR / "camera.env.bat"
WINDOW_TITLE = "MTImou Control Panel"
MODE_OPTIONS = ["auto", "lan", "ddns", "public"]

@dataclass(slots=True)
class CameraRow:
    camera_id: str
    label: str


@dataclass(slots=True)
class PasswordField:
    camera_id: str
    env_name: str
    edit: QLineEdit


class ControlPanelWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(WINDOW_TITLE)
        self.resize(1180, 760)
        self.setMinimumSize(980, 680)

        self.vm = ControlPanelViewModel(root_dir=ROOT_DIR, env_path=ENV_PATH)
        self.health_process: QProcess | None = None

        self.mode_combo = QComboBox()
        self.mode_combo.addItems(MODE_OPTIONS)
        self.ddns_edit = QLineEdit()
        self.user_edit = QLineEdit()
        self.show_passwords_checkbox = QCheckBox("Show passwords")
        self.show_passwords_checkbox.toggled.connect(self.toggle_password_visibility)
        self.open_log_checkbox = QCheckBox("Open logs folder after health check")
        self.open_log_checkbox.setChecked(True)
        self.camera_list = QListWidget()
        self.output = QPlainTextEdit()
        self.output.setReadOnly(True)
        self.password_fields: list[PasswordField] = []
        self.password_rows_host = QWidget()
        self.password_rows_layout = QVBoxLayout(self.password_rows_host)
        self.password_rows_layout.setContentsMargins(0, 0, 0, 0)
        self.password_rows_layout.setSpacing(6)

        self._build_ui()
        self.reload_settings()

    def _build_ui(self) -> None:
        self._build_toolbar()

        central = QWidget()
        root_layout = QVBoxLayout(central)
        root_layout.setContentsMargins(16, 16, 16, 16)
        root_layout.setSpacing(12)

        title = QLabel("MTImou Control Panel")
        title.setStyleSheet("font-size: 26px; font-weight: 700;")
        subtitle = QLabel(
            "Launch cameras, choose target mode, update local settings, and validate the system from one place."
        )
        subtitle.setStyleSheet("color: #555; font-size: 13px;")
        root_layout.addWidget(title)
        root_layout.addWidget(subtitle)

        splitter = QSplitter(Qt.Horizontal)
        splitter.setChildrenCollapsible(False)
        splitter.addWidget(self._build_left_panel())
        splitter.addWidget(self._build_right_panel())
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 2)
        root_layout.addWidget(splitter, 1)

        self.setCentralWidget(central)

        status = QStatusBar()
        status.showMessage("Ready")
        self.setStatusBar(status)

    def _build_toolbar(self) -> None:
        toolbar = QToolBar("Main")
        toolbar.setMovable(False)
        self.addToolBar(toolbar)

        save_action = QAction("Save Settings", self)
        save_action.triggered.connect(self.save_settings)
        toolbar.addAction(save_action)

        reload_action = QAction("Reload", self)
        reload_action.triggered.connect(self.reload_settings)
        toolbar.addAction(reload_action)

        toolbar.addSeparator()

        logs_action = QAction("Open Logs", self)
        logs_action.triggered.connect(self.open_logs_folder)
        toolbar.addAction(logs_action)

        readme_action = QAction("Open README", self)
        readme_action.triggered.connect(self.open_readme)
        toolbar.addAction(readme_action)

    def _build_left_panel(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        camera_box = QGroupBox("Cameras")
        camera_layout = QVBoxLayout(camera_box)
        self.camera_list.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.camera_list.setAlternatingRowColors(True)
        camera_layout.addWidget(self.camera_list)
        layout.addWidget(camera_box, 2)

        settings_box = QGroupBox("Operator Settings")
        settings_layout = QFormLayout(settings_box)
        settings_layout.setLabelAlignment(Qt.AlignLeft)
        settings_layout.setFormAlignment(Qt.AlignTop)
        settings_layout.addRow("Target mode", self.mode_combo)
        settings_layout.addRow("Shared DDNS host", self.ddns_edit)
        settings_layout.addRow("Camera username", self.user_edit)
        settings_layout.addRow("Camera passwords", self.password_rows_host)
        settings_layout.addRow("", self.show_passwords_checkbox)
        layout.addWidget(settings_box, 1)

        return panel

    def _build_right_panel(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        action_box = QGroupBox("Actions")
        action_layout = QVBoxLayout(action_box)
        action_layout.setSpacing(8)

        btn_selected = QPushButton("View Selected Cameras")
        btn_selected.clicked.connect(self.launch_selected_cameras)
        btn_all = QPushButton("View All Enabled Cameras")
        btn_all.clicked.connect(self.launch_all_cameras)
        btn_health = QPushButton("Run Health Check")
        btn_health.clicked.connect(self.run_health_check)
        btn_logs = QPushButton("Open Logs Folder")
        btn_logs.clicked.connect(self.open_logs_folder)
        btn_readme = QPushButton("Open Project README")
        btn_readme.clicked.connect(self.open_readme)

        for btn in [btn_selected, btn_all, btn_health, btn_logs, btn_readme]:
            btn.setMinimumHeight(40)
            action_layout.addWidget(btn)

        action_layout.addWidget(self.open_log_checkbox)
        action_layout.addStretch(1)
        layout.addWidget(action_box, 0)

        info_box = QGroupBox("Last Output")
        info_layout = QVBoxLayout(info_box)
        self.output.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        info_layout.addWidget(self.output)
        layout.addWidget(info_box, 1)

        hint = QFrame()
        hint.setFrameShape(QFrame.StyledPanel)
        hint_layout = QVBoxLayout(hint)
        hint_title = QLabel("Operator Flow")
        hint_title.setStyleSheet("font-weight: 700;")
        hint_text = QLabel(
            "1. Save settings\n"
            "2. Run health check\n"
            "3. Launch single or multi-camera view\n"
            "4. Use auto mode for normal operation"
        )
        hint_text.setStyleSheet("color: #444;")
        hint_layout.addWidget(hint_title)
        hint_layout.addWidget(hint_text)
        layout.addWidget(hint, 0)

        return panel

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
            rows.append(
                CameraRow(
                    camera_id=camera.camera_id,
                    label=camera.label,
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
            label.setMinimumWidth(190)
            edit = QLineEdit()
            edit.setPlaceholderText(entry.env_name)
            edit.setText(entry.value)
            edit.setEchoMode(QLineEdit.Normal if self.show_passwords_checkbox.isChecked() else QLineEdit.Password)
            hint = QLabel(entry.env_name)
            hint.setStyleSheet("color: #777; font-size: 11px;")

            row_layout.addWidget(label)
            row_layout.addWidget(edit, 1)
            row_layout.addWidget(hint)
            self.password_rows_layout.addWidget(row)
            self.password_fields.append(PasswordField(camera_id=entry.camera_id, env_name=entry.env_name, edit=edit))

        self.password_rows_layout.addStretch(1)

    def _refresh_camera_list(self) -> None:
        rows = self._load_camera_rows()
        current_ids = set(self.selected_camera_ids())
        self.camera_list.clear()
        for index, row in enumerate(rows):
            item = QListWidgetItem(row.label)
            item.setData(Qt.UserRole, row.camera_id)
            self.camera_list.addItem(item)
            if row.camera_id in current_ids:
                item.setSelected(True)
        if self.camera_list.count() and not current_ids:
            self.camera_list.item(0).setSelected(True)

    def selected_camera_ids(self) -> list[str]:
        ids: list[str] = []
        for item in self.camera_list.selectedItems():
            ids.append(str(item.data(Qt.UserRole)))
        return ids

    def toggle_password_visibility(self, visible: bool) -> None:
        mode = QLineEdit.Normal if visible else QLineEdit.Password
        for field in self.password_fields:
            field.edit.setEchoMode(mode)

    def save_settings(self) -> None:
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
        self._refresh_camera_list()
        self.append_output(f"[INFO] Saved settings to {ENV_PATH}")
        self._set_status(f"Saved settings to {ENV_PATH}")

    def reload_settings(self) -> None:
        self.vm.load()
        self.mode_combo.setCurrentText(self.vm.state.target_mode or "auto")
        self.ddns_edit.setText(self.vm.state.ddns_host)
        self.user_edit.setText(self.vm.state.username or "admin")
        self._rebuild_password_fields()
        self._refresh_camera_list()
        self.append_output("[INFO] Reloaded settings from camera.env.bat")
        self._set_status("Reloaded settings")

    def launch_selected_cameras(self) -> None:
        camera_ids = self.selected_camera_ids()
        if not camera_ids:
            QMessageBox.warning(self, WINDOW_TITLE, "Please select one or more cameras first.")
            return
        self.save_settings()
        message, status = self.vm.launch_selected(camera_ids)
        self.append_output(message)
        self._set_status(status)

    def launch_all_cameras(self) -> None:
        self.save_settings()
        ids, result = self.vm.launch_all()
        if not ids:
            QMessageBox.warning(self, WINDOW_TITLE, "No enabled cameras found.")
            return
        if result is not None:
            message, status = result
            self.append_output(message)
            self._set_status(status)

    def run_health_check(self) -> None:
        if self.health_process is not None:
            QMessageBox.information(self, WINDOW_TITLE, "Health check is already running.")
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
        self.append_output(f"[INFO] Health check finished with exit code {exit_code}")
        self.health_process = None
        if self.open_log_checkbox.isChecked():
            self.open_logs_folder()

    def open_logs_folder(self) -> None:
        self.vm.open_logs_folder()

    def open_readme(self) -> None:
        self.vm.open_readme()


def main() -> int:
    enforce_venv_python()
    app = QApplication(sys.argv)
    app.setApplicationName(WINDOW_TITLE)
    window = ControlPanelWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
