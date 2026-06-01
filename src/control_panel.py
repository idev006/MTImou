from __future__ import annotations

import os
import subprocess
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

from camera_registry import default_password_env_names, enabled_cameras, load_cameras, target_modes_summary
from venv_guard import enforce_venv_python


ROOT_DIR = Path(__file__).resolve().parents[1]
ENV_PATH = ROOT_DIR / "camera.env.bat"
PYTHON_PATH = ROOT_DIR / ".venv" / "Scripts" / "python.exe"
WINDOW_TITLE = "MTImou Control Panel"
CREATE_NEW_CONSOLE = getattr(subprocess, "CREATE_NEW_CONSOLE", 0)
MODE_OPTIONS = ["auto", "lan", "ddns", "public"]


def parse_env_bat(path: Path) -> tuple[list[str], dict[str, str]]:
    lines: list[str] = []
    values: dict[str, str] = {}
    if path.exists():
        lines = path.read_text(encoding="ascii", errors="ignore").splitlines()
        for line in lines:
            stripped = line.strip()
            if stripped.lower().startswith("set ") and "=" in stripped:
                payload = stripped[4:]
                key, value = payload.split("=", 1)
                values[key.strip()] = value.strip()
    return lines, values


def write_env_bat(path: Path, original_lines: list[str], updates: dict[str, str]) -> None:
    remaining = dict(updates)
    new_lines: list[str] = []
    for line in original_lines:
        stripped = line.strip()
        if stripped.lower().startswith("set ") and "=" in stripped:
            payload = stripped[4:]
            key, _ = payload.split("=", 1)
            key = key.strip()
            if key in remaining:
                new_lines.append(f"set {key}={remaining.pop(key)}")
                continue
        new_lines.append(line)
    if remaining:
        if new_lines and new_lines[-1].strip():
            new_lines.append("")
        for key, value in remaining.items():
            new_lines.append(f"set {key}={value}")
    path.write_text("\r\n".join(new_lines) + "\r\n", encoding="ascii")


def launch_batch(batch_name: str, args: list[str] | None = None) -> None:
    cmd = ["cmd.exe", "/c", str(ROOT_DIR / batch_name)]
    if args:
        cmd.extend(args)
    subprocess.Popen(cmd, cwd=str(ROOT_DIR), creationflags=CREATE_NEW_CONSOLE)


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

        self.env_lines, self.env_values = parse_env_bat(ENV_PATH)
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

    def _apply_env_values_to_process(self) -> None:
        for key, value in self.env_values.items():
            if key.startswith("IMOU_"):
                os.environ[key] = value

    def _load_camera_rows(self) -> list[CameraRow]:
        self._apply_env_values_to_process()
        rows: list[CameraRow] = []
        for camera in load_cameras():
            rows.append(
                CameraRow(
                    camera_id=camera.camera_id,
                    label=f"{camera.camera_id} | {camera.name} | {' ; '.join(target_modes_summary(camera))}",
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

        for camera in load_cameras():
            env_names = default_password_env_names(camera.camera_id)
            primary_env = env_names[0]
            value = ""
            for env_name in env_names:
                value = self.env_values.get(env_name, "")
                if value:
                    break

            row = QWidget()
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(0, 0, 0, 0)
            row_layout.setSpacing(8)

            label = QLabel(f"{camera.name} ({camera.camera_id})")
            label.setMinimumWidth(190)
            edit = QLineEdit()
            edit.setPlaceholderText(primary_env)
            edit.setText(value)
            edit.setEchoMode(QLineEdit.Normal if self.show_passwords_checkbox.isChecked() else QLineEdit.Password)
            hint = QLabel(primary_env)
            hint.setStyleSheet("color: #777; font-size: 11px;")

            row_layout.addWidget(label)
            row_layout.addWidget(edit, 1)
            row_layout.addWidget(hint)
            self.password_rows_layout.addWidget(row)
            self.password_fields.append(PasswordField(camera_id=camera.camera_id, env_name=primary_env, edit=edit))

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
        updates = {
            "IMOU_TARGET_MODE": self.mode_combo.currentText().strip() or "auto",
            "IMOU_DDNS_HOST": self.ddns_edit.text().strip(),
            "IMOU_CAMERA_USERNAME": self.user_edit.text().strip() or "admin",
        }
        for field in self.password_fields:
            updates[field.env_name] = field.edit.text().strip()
        if not ENV_PATH.exists():
            self.env_lines = [
                "@echo off",
                "REM Local operator settings for MTImou",
                "",
            ]
        write_env_bat(ENV_PATH, self.env_lines, updates)
        self.env_lines, self.env_values = parse_env_bat(ENV_PATH)
        self._apply_env_values_to_process()
        self._refresh_camera_list()
        self.append_output(f"[INFO] Saved settings to {ENV_PATH}")
        self._set_status(f"Saved settings to {ENV_PATH}")

    def reload_settings(self) -> None:
        self.env_lines, self.env_values = parse_env_bat(ENV_PATH)
        self._apply_env_values_to_process()
        self.mode_combo.setCurrentText(self.env_values.get("IMOU_TARGET_MODE", "auto") or "auto")
        self.ddns_edit.setText(self.env_values.get("IMOU_DDNS_HOST", ""))
        self.user_edit.setText(self.env_values.get("IMOU_CAMERA_USERNAME", "admin") or "admin")
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
        if len(camera_ids) == 1:
            launch_batch("run_camera_stable.bat", [camera_ids[0]])
            self.append_output(f"[INFO] Launched run_camera_stable.bat {camera_ids[0]}")
            self._set_status(f"Launched camera viewer for {camera_ids[0]}")
            return
        launch_batch("run_multi_camera_stable.bat", camera_ids)
        self.append_output(f"[INFO] Launched run_multi_camera_stable.bat {' '.join(camera_ids)}")
        self._set_status(f"Launched selected cameras: {', '.join(camera_ids)}")

    def launch_all_cameras(self) -> None:
        self.save_settings()
        ids = [camera.camera_id for camera in enabled_cameras()]
        if not ids:
            QMessageBox.warning(self, WINDOW_TITLE, "No enabled cameras found.")
            return
        launch_batch("run_multi_camera_stable.bat", ids)
        self.append_output(f"[INFO] Launched run_multi_camera_stable.bat {' '.join(ids)}")
        self._set_status("Launched multi-camera viewer")

    def run_health_check(self) -> None:
        if self.health_process is not None:
            QMessageBox.information(self, WINDOW_TITLE, "Health check is already running.")
            return
        self.save_settings()
        self.append_output("[INFO] Running system health check...")
        self._set_status("Running health check...")

        self.health_process = QProcess(self)
        self.health_process.setProgram(str(PYTHON_PATH))
        self.health_process.setArguments([str(ROOT_DIR / "src" / "system_health_check.py")])
        self.health_process.setWorkingDirectory(str(ROOT_DIR))
        process_env = self.health_process.processEnvironment()
        for key, value in os.environ.items():
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
        os.startfile(str(ROOT_DIR / "logs"))

    def open_readme(self) -> None:
        os.startfile(str(ROOT_DIR / "README.md"))


def main() -> int:
    enforce_venv_python()
    app = QApplication(sys.argv)
    app.setApplicationName(WINDOW_TITLE)
    window = ControlPanelWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
