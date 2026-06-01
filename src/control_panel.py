from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path

from PySide6.QtCore import QProcess, Qt
from PySide6.QtGui import QAction, QTextCursor
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QCheckBox,
    QComboBox,
    QFormLayout,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHeaderView,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QSizePolicy,
    QStatusBar,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
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
TABLE_COLUMNS = ["Camera", "LAN", "DDNS", "Public", "Status"]


@dataclass(slots=True)
class CameraRow:
    camera_id: str
    name: str
    lan: str
    ddns: str
    public: str
    enabled: bool


@dataclass(slots=True)
class PasswordField:
    camera_id: str
    env_name: str
    edit: QLineEdit


class MetricCard(QFrame):
    def __init__(self, title: str, accent: str) -> None:
        super().__init__()
        self.setObjectName("metricCard")
        self.setProperty("accent", accent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(6)

        self.title_label = QLabel(title)
        self.title_label.setObjectName("metricTitle")
        self.value_label = QLabel("-")
        self.value_label.setObjectName("metricValue")
        self.helper_label = QLabel("")
        self.helper_label.setObjectName("metricHelper")
        self.helper_label.setWordWrap(True)

        layout.addWidget(self.title_label)
        layout.addWidget(self.value_label)
        layout.addWidget(self.helper_label)

    def set_value(self, value: str, helper: str = "") -> None:
        self.value_label.setText(value)
        self.helper_label.setText(helper)


class ControlPanelWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(WINDOW_TITLE)
        self.resize(1360, 860)
        self.setMinimumSize(1120, 760)

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

        self.camera_table = QTableWidget(0, len(TABLE_COLUMNS))
        self.camera_table.setHorizontalHeaderLabels(TABLE_COLUMNS)
        self.camera_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.camera_table.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.camera_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.camera_table.setAlternatingRowColors(True)
        self.camera_table.verticalHeader().setVisible(False)
        self.camera_table.itemSelectionChanged.connect(self._refresh_selection_summary)

        self.output = QPlainTextEdit()
        self.output.setReadOnly(True)
        self.output.setPlaceholderText("Activity and health-check output will appear here.")

        self.selection_summary = QLabel("No camera selected")
        self.selection_summary.setWordWrap(True)
        self.selection_summary.setObjectName("selectionSummary")

        self.password_fields: list[PasswordField] = []
        self.password_rows_host = QWidget()
        self.password_rows_layout = QVBoxLayout(self.password_rows_host)
        self.password_rows_layout.setContentsMargins(0, 0, 0, 0)
        self.password_rows_layout.setSpacing(8)

        self.metric_enabled = MetricCard("Enabled Cameras", "green")
        self.metric_mode = MetricCard("Target Mode", "blue")
        self.metric_ddns = MetricCard("DDNS Host", "orange")

        self._build_ui()
        self._apply_styles()
        self.reload_settings()

    def _apply_styles(self) -> None:
        self.setStyleSheet(
            """
            QMainWindow {
                background: #f4f7fb;
            }
            QToolBar {
                spacing: 8px;
                padding: 6px;
                background: #ffffff;
                border-bottom: 1px solid #d9e2ef;
            }
            QGroupBox {
                font-weight: 600;
                border: 1px solid #d9e2ef;
                border-radius: 12px;
                margin-top: 12px;
                background: #ffffff;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 12px;
                padding: 0 6px;
            }
            QFrame#metricCard {
                border-radius: 14px;
                border: 1px solid #d9e2ef;
                background: #ffffff;
            }
            QFrame[accent="green"] {
                border-left: 5px solid #1f9d64;
            }
            QFrame[accent="blue"] {
                border-left: 5px solid #2374e1;
            }
            QFrame[accent="orange"] {
                border-left: 5px solid #d97706;
            }
            QLabel#metricTitle {
                color: #5b6472;
                font-size: 12px;
                font-weight: 600;
            }
            QLabel#metricValue {
                color: #172233;
                font-size: 22px;
                font-weight: 700;
            }
            QLabel#metricHelper {
                color: #6b7280;
                font-size: 11px;
            }
            QLabel#selectionSummary {
                color: #334155;
                background: #f8fafc;
                border: 1px solid #d9e2ef;
                border-radius: 10px;
                padding: 10px 12px;
            }
            QTabWidget::pane {
                border: 1px solid #d9e2ef;
                background: #ffffff;
                border-radius: 12px;
                top: -1px;
            }
            QTabBar::tab {
                background: #e9eef6;
                color: #334155;
                padding: 10px 18px;
                margin-right: 4px;
                border-top-left-radius: 10px;
                border-top-right-radius: 10px;
            }
            QTabBar::tab:selected {
                background: #ffffff;
                font-weight: 700;
            }
            QPushButton {
                min-height: 40px;
                border-radius: 10px;
                border: 1px solid #d0d9e7;
                background: #ffffff;
                padding: 8px 12px;
            }
            QPushButton:hover {
                background: #f8fbff;
                border-color: #98b4df;
            }
            QPushButton#primary {
                background: #2374e1;
                color: white;
                border-color: #2374e1;
                font-weight: 700;
            }
            QPushButton#primary:hover {
                background: #1b63c4;
            }
            QLineEdit, QComboBox, QPlainTextEdit, QTableWidget {
                border: 1px solid #d0d9e7;
                border-radius: 10px;
                background: #ffffff;
                selection-background-color: #dbeafe;
            }
            QHeaderView::section {
                background: #eef3f9;
                border: 0;
                border-bottom: 1px solid #d0d9e7;
                padding: 8px;
                font-weight: 700;
            }
            """
        )

    def _build_ui(self) -> None:
        self._build_toolbar()

        central = QWidget()
        root_layout = QVBoxLayout(central)
        root_layout.setContentsMargins(18, 18, 18, 18)
        root_layout.setSpacing(14)

        title = QLabel("MTImou Control Panel")
        title.setStyleSheet("font-size: 30px; font-weight: 800; color: #172233;")
        subtitle = QLabel(
            "Operate cameras from one place: choose the safest route, verify system health, and launch single or multi-camera views."
        )
        subtitle.setStyleSheet("color: #536173; font-size: 13px;")
        root_layout.addWidget(title)
        root_layout.addWidget(subtitle)

        metric_layout = QHBoxLayout()
        metric_layout.setSpacing(12)
        metric_layout.addWidget(self.metric_enabled)
        metric_layout.addWidget(self.metric_mode)
        metric_layout.addWidget(self.metric_ddns)
        root_layout.addLayout(metric_layout)

        tabs = QTabWidget()
        tabs.addTab(self._build_dashboard_tab(), "Dashboard")
        tabs.addTab(self._build_settings_tab(), "Settings")
        tabs.addTab(self._build_help_tab(), "Operator Guide")
        root_layout.addWidget(tabs, 1)

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

    def _build_dashboard_tab(self) -> QWidget:
        tab = QWidget()
        layout = QGridLayout(tab)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setHorizontalSpacing(14)
        layout.setVerticalSpacing(14)

        camera_box = QGroupBox("Camera Grid")
        camera_layout = QVBoxLayout(camera_box)

        helper = QLabel("Select one or more cameras. The table is optimized for N cameras and keeps network endpoints readable.")
        helper.setStyleSheet("color: #5b6472; font-size: 12px;")
        helper.setWordWrap(True)
        camera_layout.addWidget(helper)

        header = self.camera_table.horizontalHeader()
        header.setStretchLastSection(False)
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        self.camera_table.setColumnWidth(1, 170)
        self.camera_table.setColumnWidth(2, 260)
        self.camera_table.setColumnWidth(3, 180)
        self.camera_table.setColumnWidth(4, 90)
        camera_layout.addWidget(self.camera_table, 1)

        row_buttons = QHBoxLayout()
        btn_select_all = QPushButton("Select All")
        btn_select_all.clicked.connect(self._select_all_cameras)
        btn_clear = QPushButton("Clear Selection")
        btn_clear.clicked.connect(self.camera_table.clearSelection)
        btn_enabled = QPushButton("Select Enabled")
        btn_enabled.clicked.connect(self._select_enabled_cameras)
        row_buttons.addWidget(btn_select_all)
        row_buttons.addWidget(btn_enabled)
        row_buttons.addWidget(btn_clear)
        row_buttons.addStretch(1)
        camera_layout.addLayout(row_buttons)
        camera_layout.addWidget(self.selection_summary)

        action_box = QGroupBox("Launch & Validation")
        action_layout = QVBoxLayout(action_box)
        action_layout.setSpacing(10)

        btn_selected = QPushButton("View Selected Cameras")
        btn_selected.setObjectName("primary")
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
            action_layout.addWidget(btn)

        action_layout.addWidget(self.open_log_checkbox)
        action_layout.addStretch(1)

        output_box = QGroupBox("Recent Activity")
        output_layout = QVBoxLayout(output_box)
        self.output.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        output_layout.addWidget(self.output)

        layout.addWidget(camera_box, 0, 0, 2, 1)
        layout.addWidget(action_box, 0, 1)
        layout.addWidget(output_box, 1, 1)
        layout.setColumnStretch(0, 3)
        layout.setColumnStretch(1, 2)
        layout.setRowStretch(1, 1)
        return tab

    def _build_settings_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(14)

        settings_box = QGroupBox("Operator Settings")
        settings_layout = QFormLayout(settings_box)
        settings_layout.setContentsMargins(16, 18, 16, 16)
        settings_layout.setSpacing(12)
        settings_layout.addRow("Target mode", self.mode_combo)
        settings_layout.addRow("Shared DDNS host", self.ddns_edit)
        settings_layout.addRow("Camera username", self.user_edit)
        settings_layout.addRow("Camera passwords", self.password_rows_host)
        settings_layout.addRow("", self.show_passwords_checkbox)
        layout.addWidget(settings_box)

        notes_box = QGroupBox("How To Use Settings")
        notes_layout = QVBoxLayout(notes_box)
        notes = QLabel(
            "Auto mode is the normal choice. It prefers LAN when you are at home, then DDNS, then public IP.\n\n"
            "Use DDNS mode when you want to verify remote access specifically.\n\n"
            "Passwords are stored in camera.env.bat and mapped per camera using the environment names shown on the right."
        )
        notes.setWordWrap(True)
        notes.setStyleSheet("color: #4b5563;")
        notes_layout.addWidget(notes)
        layout.addWidget(notes_box)
        layout.addStretch(1)
        return tab

    def _build_help_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(14)

        flow_box = QGroupBox("Recommended Operator Flow")
        flow_layout = QVBoxLayout(flow_box)
        flow_text = QLabel(
            "1. Save settings after any credential or DDNS change.\n"
            "2. Run health check before opening long-running views.\n"
            "3. Use View Selected Cameras for focused work.\n"
            "4. Use View All Enabled Cameras for the normal wall view.\n"
            "5. Keep target mode on auto for day-to-day operation."
        )
        flow_text.setWordWrap(True)
        flow_layout.addWidget(flow_text)

        mode_box = QGroupBox("Target Modes")
        mode_layout = QVBoxLayout(mode_box)
        mode_text = QLabel(
            "auto: best default, re-evaluates LAN, DDNS, and public targets.\n"
            "lan: use only local network addresses.\n"
            "ddns: use the dynamic DNS hostname for remote access.\n"
            "public: use the public IP and forwarded port directly."
        )
        mode_text.setWordWrap(True)
        mode_layout.addWidget(mode_text)

        layout.addWidget(flow_box)
        layout.addWidget(mode_box)
        layout.addStretch(1)
        return tab

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
            values = [
                f"{row.camera_id} | {row.name}",
                row.lan,
                row.ddns,
                row.public,
                "Enabled" if row.enabled else "Disabled",
            ]
            for col_index, value in enumerate(values):
                item = QTableWidgetItem(value)
                item.setData(Qt.UserRole, row.camera_id)
                if col_index == 4:
                    item.setTextAlignment(Qt.AlignCenter)
                if col_index == 0 and row.enabled:
                    item.setForeground(Qt.darkGreen)
                self.camera_table.setItem(row_index, col_index, item)
            if row.camera_id in current_ids:
                self.camera_table.selectRow(row_index)

        self.camera_table.resizeRowsToContents()
        self._refresh_selection_summary()

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
        self.selection_summary.setText(
            f"Selected {len(rows)} cameras for multi-view: {names}"
        )

    def selected_camera_rows(self) -> list[dict[str, str]]:
        selected: list[dict[str, str]] = []
        seen_rows: set[int] = set()
        for item in self.camera_table.selectedItems():
            row = item.row()
            if row in seen_rows:
                continue
            seen_rows.add(row)
            selected.append(
                {
                    "camera_id": str(self.camera_table.item(row, 0).data(Qt.UserRole)),
                    "camera": self.camera_table.item(row, 0).text(),
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
        self.camera_table.selectAll()
        self._refresh_selection_summary()

    def _select_enabled_cameras(self) -> None:
        self.camera_table.clearSelection()
        for row in range(self.camera_table.rowCount()):
            status_item = self.camera_table.item(row, 4)
            if status_item is not None and status_item.text() == "Enabled":
                self.camera_table.selectRow(row)
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
        self._refresh_camera_table()
        self._update_metric_cards()
        self.append_output(f"[INFO] Saved settings to {ENV_PATH}")
        self._set_status(f"Saved settings to {ENV_PATH}")

    def reload_settings(self) -> None:
        self.vm.load()
        self.mode_combo.setCurrentText(self.vm.state.target_mode or "auto")
        self.ddns_edit.setText(self.vm.state.ddns_host)
        self.user_edit.setText(self.vm.state.username or "admin")
        self._rebuild_password_fields()
        self._refresh_camera_table()
        self._update_metric_cards()
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
